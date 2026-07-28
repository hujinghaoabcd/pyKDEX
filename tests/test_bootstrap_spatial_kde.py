# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import numpy as np
import pytest

from pykdex import GridSupport, PointSupport, SpatialEvents, SpatialKDE
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, BootstrapResult, bootstrap_kde
from pykdex.uncertainty.seeds import build_seed_ledger


def _support() -> GridSupport:
    return GridSupport.from_bounds(
        (0.0, 0.0, 2.0, 1.0),
        resolution=0.5,
        spatial_unit="m",
    )


def _events(*, weights: np.ndarray | None = None) -> SpatialEvents:
    return SpatialEvents.from_array(
        [[0.25, 0.25], [1.0, 0.75], [1.75, 0.25]],
        weights=weights,
        ids=["a", "b", "c"],
        coordinate_names=("x", "y"),
        spatial_unit="m",
        marks=["left", "middle", "right"],
    )


def _plan(
    *,
    seed: int = 20260728,
    replicate_chunk_size: int = 2,
    target_chunk_size: int = 2,
    n_jobs: int = 1,
    backend: str = "sequential",
) -> BootstrapPlan:
    return BootstrapPlan(
        n_resamples=6,
        confidence_level=0.8,
        random_state=seed,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=None,
            target_chunk_size=target_chunk_size,
            replicate_chunk_size=replicate_chunk_size,
            n_jobs=n_jobs,
            backend=backend,
        ),
    )


def test_spatial_bootstrap_returns_complete_exact_support_result() -> None:
    events = _events()
    support = _support()
    source = SpatialKDE(
        bandwidth=0.7,
        kernel="epanechnikov",
        metric="euclidean",
        target="density",
    )

    result = bootstrap_kde(source, events, support, plan=_plan())

    assert isinstance(result, BootstrapResult)
    assert result.operation == "bootstrap_kde"
    assert result.estimator_family == "spatial"
    assert result.ensemble.n_replicates == 6
    assert result.ensemble.n_elements == support.n_points
    assert result.ensemble.descriptor.fingerprint == support.fingerprint
    assert result.ensemble.field_family == "density"
    assert result.interval.confidence_level == pytest.approx(0.8)
    assert result.interval.source_ensemble_fingerprint == result.ensemble.fingerprint
    assert result.seed_metadata["n_logical_tasks"] == 6
    assert result.metadata["conditional_on_observed_event_count"] is True
    assert result.ensemble.metadata["unit_event_weights"] is True
    assert result.ensemble.metadata["n_events"] == events.n_events
    assert not source.is_fitted_
    assert not result.ensemble.replicate_values.flags.writeable


def test_one_event_bootstrap_is_degenerate_with_zero_empirical_uncertainty() -> None:
    events = SpatialEvents.from_array(
        [[0.5, 0.5]],
        spatial_unit="m",
    )
    result = bootstrap_kde(
        SpatialKDE(bandwidth=0.8),
        events,
        _support(),
        plan=BootstrapPlan(
            n_resamples=4,
            confidence_level=0.5,
            random_state=3,
            execution_plan=ExecutionPlan(memory_budget_bytes=None),
        ),
    )

    np.testing.assert_allclose(
        result.ensemble.replicate_values,
        np.broadcast_to(
            result.ensemble.observed_values,
            result.ensemble.replicate_values.shape,
        ),
    )
    np.testing.assert_allclose(result.interval.standard_error, 0.0)
    np.testing.assert_allclose(result.interval.bias, 0.0)
    np.testing.assert_allclose(result.interval.lower, result.interval.estimate)
    np.testing.assert_allclose(result.interval.upper, result.interval.estimate)


def test_seed_identity_is_independent_of_workers_and_both_chunk_sizes() -> None:
    events = _events()
    support = _support()
    estimator = SpatialKDE(bandwidth=0.7, target="intensity")

    sequential = bootstrap_kde(
        estimator,
        events,
        support,
        plan=_plan(
            replicate_chunk_size=5,
            target_chunk_size=1,
        ),
    )
    threaded = bootstrap_kde(
        estimator,
        events,
        support,
        plan=_plan(
            replicate_chunk_size=2,
            target_chunk_size=3,
            n_jobs=3,
            backend="thread",
        ),
    )

    np.testing.assert_allclose(
        threaded.ensemble.observed_values,
        sequential.ensemble.observed_values,
        rtol=1e-13,
        atol=1e-15,
    )
    np.testing.assert_allclose(
        threaded.ensemble.replicate_values,
        sequential.ensemble.replicate_values,
        rtol=1e-13,
        atol=1e-15,
    )
    np.testing.assert_allclose(
        threaded.interval.lower,
        sequential.interval.lower,
        rtol=1e-13,
        atol=1e-15,
    )
    np.testing.assert_allclose(
        threaded.interval.upper,
        sequential.interval.upper,
        rtol=1e-13,
        atol=1e-15,
    )
    assert (
        threaded.ensemble.replicate_source_fingerprints
        == sequential.ensemble.replicate_source_fingerprints
    )
    assert (
        threaded.ensemble.seed_ledger_fingerprint
        == sequential.ensemble.seed_ledger_fingerprint
    )
    assert sequential.ensemble.execution_metadata["parallel_axis"] == "none"
    assert threaded.ensemble.execution_metadata["parallel_axis"] == "replicates"


def test_first_replicate_matches_manual_event_index_resample() -> None:
    events = _events()
    support = _support()
    plan = _plan(seed=41)
    estimator = SpatialKDE(bandwidth=0.7, kernel="gaussian")
    result = bootstrap_kde(estimator, events, support, plan=plan)

    ledger = build_seed_ledger(41, plan.n_resamples)
    sampled = ledger.generator(0).integers(
        0,
        events.n_events,
        size=events.n_events,
        dtype=np.int64,
    )
    manual = SpatialEvents(
        coordinates=events.coordinates[sampled],
        weights=np.ones(events.n_events, dtype=float),
        ids=np.arange(events.n_events, dtype=np.int64),
        coordinate_names=events.coordinate_names,
        crs=events.crs,
        spatial_unit=events.spatial_unit,
        marks=events.marks[sampled],
        provenance=events.provenance.with_transformation(
            "ordinary_bootstrap_resample",
            replicate_index=0,
            sampled_source_indices=sampled.tolist(),
            source_event_fingerprint=events.fingerprint,
        ),
    )
    expected = SpatialKDE(
        bandwidth=0.7,
        kernel="gaussian",
        execution_plan=ExecutionPlan(
            memory_budget_bytes=None,
            target_chunk_size=2,
        ),
    ).fit_predict(manual, support)

    np.testing.assert_allclose(
        result.ensemble.replicate_values[0],
        expected.values,
        rtol=1e-13,
        atol=1e-15,
    )
    assert result.ensemble.replicate_source_fingerprints[0] == manual.fingerprint
    assert manual.ids.tolist() == list(range(events.n_events))
    assert manual.provenance.metadata["sampled_source_indices"] == sampled.tolist()


def test_bootstrap_does_not_mutate_fitted_source_estimator() -> None:
    events = _events()
    source = SpatialKDE(bandwidth=0.7).fit(events)
    event_fingerprint = source.event_fingerprint_
    stored_events = source.events_.copy()

    bootstrap_kde(source, events, _support(), plan=_plan())

    assert source.is_fitted_
    assert source.event_fingerprint_ == event_fingerprint
    np.testing.assert_array_equal(source.events_, stored_events)


@pytest.mark.parametrize(
    "events",
    [
        _events(weights=np.array([1.0, 2.0, 1.0])),
        _events(weights=np.array([0.0, 1.0, 1.0])),
    ],
)
def test_spatial_bootstrap_rejects_non_unit_weights(events: SpatialEvents) -> None:
    with pytest.raises(ValueError, match="unit event weights"):
        bootstrap_kde(
            SpatialKDE(bandwidth=0.7),
            events,
            _support(),
            plan=_plan(),
        )


def test_spatial_bootstrap_rejects_adaptive_or_matrix_bandwidths() -> None:
    with pytest.raises(ValueError, match="fixed numeric scalar"):
        bootstrap_kde(
            SpatialKDE(bandwidth=np.array([0.5, 0.7, 0.9])),
            _events(),
            _support(),
            plan=_plan(),
        )


def test_spatial_bootstrap_rejects_open_input_types() -> None:
    events = _events()
    support = _support()
    point_support = PointSupport.from_array(
        support.coordinates,
        spatial_unit="m",
    )

    with pytest.raises(TypeError, match="SpatialKDE"):
        bootstrap_kde(object(), events, support, plan=_plan())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="SpatialEvents"):
        bootstrap_kde(
            SpatialKDE(bandwidth=0.7),
            events.coordinates,  # type: ignore[arg-type]
            support,
            plan=_plan(),
        )
    with pytest.raises(TypeError, match="GridSupport"):
        bootstrap_kde(
            SpatialKDE(bandwidth=0.7),
            events,
            point_support,  # type: ignore[arg-type]
            plan=_plan(),
        )
    with pytest.raises(TypeError, match="BootstrapPlan"):
        bootstrap_kde(
            SpatialKDE(bandwidth=0.7),
            events,
            support,
            plan="ordinary",  # type: ignore[arg-type]
        )


def test_spatial_bootstrap_memory_rejects_before_replicate_scheduling() -> None:
    plan = BootstrapPlan(
        n_resamples=3,
        random_state=1,
        execution_plan=ExecutionPlan(memory_budget_bytes=100),
    )

    with pytest.raises(MemoryError, match="fixed overhead"):
        bootstrap_kde(
            SpatialKDE(bandwidth=0.7),
            _events(),
            _support(),
            plan=plan,
        )


def test_bootstrap_result_rejects_mismatched_plan() -> None:
    result = bootstrap_kde(
        SpatialKDE(bandwidth=0.7),
        _events(),
        _support(),
        plan=_plan(),
    )

    with pytest.raises(ValueError, match="replicate counts differ"):
        BootstrapResult(
            ensemble=result.ensemble,
            interval=result.interval,
            plan=BootstrapPlan(
                n_resamples=7,
                confidence_level=0.8,
                random_state=20260728,
            ),
            operation="bootstrap_kde",
            estimator_family="spatial",
            seed_metadata=result.seed_metadata,
        )
