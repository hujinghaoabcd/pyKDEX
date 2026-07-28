# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import numpy as np
import pytest

from pykdex import (
    CyclicTimeDomain,
    GridSupport,
    SpatiotemporalEvents,
    SpatiotemporalGridSupport,
    SpatiotemporalKDE,
    SpatiotemporalPointSupport,
)
from pykdex.execution import ExecutionPlan
from pykdex.kernels import get_kernel
from pykdex.uncertainty import BootstrapPlan, BootstrapResult, bootstrap_kde
from pykdex.uncertainty.seeds import build_seed_ledger
from pykdex.uncertainty.spatiotemporal import _resample_spatiotemporal_events


def _events(
    *,
    weights: np.ndarray | None = None,
    cyclic: bool = False,
) -> SpatiotemporalEvents:
    domain = CyclicTimeDomain(24.0) if cyclic else None
    times = [23.5, 0.5, 8.0] if cyclic else [0.5, 1.5, 2.5]
    return SpatiotemporalEvents.from_arrays(
        [[0.25, 0.25], [1.0, 0.75], [1.75, 0.25]],
        times,
        weights=weights,
        ids=["a", "b", "c"],
        coordinate_names=("x", "y"),
        spatial_unit="km",
        temporal_unit="hours",
        time_domain=domain,
        temporal_origin="study-hour-zero",
        timezone="UTC",
        marks=["left", "middle", "right"],
    )


def _support(*, cyclic: bool = False) -> SpatiotemporalGridSupport:
    spatial = GridSupport.from_bounds(
        (0.0, 0.0, 2.0, 1.0),
        resolution=0.5,
        spatial_unit="km",
    )
    if cyclic:
        return SpatiotemporalGridSupport.from_spatial_grid(
            spatial,
            temporal_resolution=6.0,
            temporal_unit="hours",
            time_domain=CyclicTimeDomain(24.0),
            temporal_origin="study-hour-zero",
            timezone="UTC",
        )
    return SpatiotemporalGridSupport.from_spatial_grid(
        spatial,
        temporal_bounds=(0.0, 3.0),
        temporal_resolution=1.0,
        temporal_unit="hours",
        temporal_origin="study-hour-zero",
        timezone="UTC",
    )


def _plan(
    *,
    seed: int = 20260729,
    target_chunk_size: int = 3,
    replicate_chunk_size: int = 2,
    n_jobs: int = 1,
    backend: str = "sequential",
) -> BootstrapPlan:
    return BootstrapPlan(
        n_resamples=5,
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


def _estimator(*, target: str = "density") -> SpatiotemporalKDE:
    return SpatiotemporalKDE(
        spatial_bandwidth=0.7,
        temporal_bandwidth=0.8,
        spatial_kernel="epanechnikov",
        temporal_kernel="gaussian",
        spatial_metric="euclidean",
        target=target,
    )


def test_spatiotemporal_bootstrap_returns_complete_grid_result() -> None:
    events = _events()
    support = _support()
    source = _estimator()

    result = bootstrap_kde(source, events, support, plan=_plan())

    assert isinstance(result, BootstrapResult)
    assert result.operation == "bootstrap_kde"
    assert result.estimator_family == "spatiotemporal"
    assert result.ensemble.n_replicates == 5
    assert result.ensemble.n_elements == support.n_points
    assert result.ensemble.descriptor.fingerprint == support.fingerprint
    assert result.ensemble.descriptor.kind == "spatiotemporal_grid"
    assert result.ensemble.field_family == "density"
    assert result.interval.confidence_level == pytest.approx(0.8)
    assert result.metadata["resampling_unit"] == "paired_space_time_event_identity"
    assert result.metadata["conditional_on_observed_event_count"] is True
    assert result.metadata["time_domain"] == "linear"
    assert result.ensemble.metadata["unit_event_weights"] is True
    assert result.ensemble.metadata["n_events"] == events.n_events
    assert not source.is_fitted_
    assert not result.ensemble.replicate_values.flags.writeable


def test_first_replicate_matches_manual_paired_space_time_resample() -> None:
    events = _events()
    support = _support()
    plan = _plan(seed=41)
    result = bootstrap_kde(_estimator(), events, support, plan=plan)

    ledger = build_seed_ledger(41, plan.n_resamples)
    sampled = ledger.generator(0).integers(
        0,
        events.n_events,
        size=events.n_events,
        dtype=np.int64,
    )
    replicate_events = _resample_spatiotemporal_events(
        events,
        sampled,
        replicate_index=0,
    )
    expected = SpatiotemporalKDE(
        spatial_bandwidth=0.7,
        temporal_bandwidth=0.8,
        spatial_kernel="epanechnikov",
        temporal_kernel="gaussian",
        spatial_metric="euclidean",
        execution_plan=ExecutionPlan(
            memory_budget_bytes=None,
            target_chunk_size=3,
        ),
    ).fit_predict(replicate_events, support)

    np.testing.assert_allclose(
        result.ensemble.replicate_values[0],
        expected.values,
        rtol=1e-13,
        atol=1e-15,
    )
    np.testing.assert_array_equal(
        replicate_events.spatial_coordinates,
        events.spatial_coordinates[sampled],
    )
    np.testing.assert_array_equal(
        replicate_events.times,
        events.times[sampled],
    )
    assert replicate_events.ids.tolist() == list(range(events.n_events))
    assert (
        replicate_events.provenance.metadata["sampled_source_indices"]
        == sampled.tolist()
    )
    assert (
        replicate_events.provenance.metadata["resampling_unit"]
        == "paired_space_time_event_identity"
    )


def test_spatiotemporal_bootstrap_is_invariant_to_workers_and_both_chunks() -> None:
    events = _events()
    support = _support()
    estimator = _estimator(target="intensity")

    sequential = bootstrap_kde(
        estimator,
        events,
        support,
        plan=_plan(target_chunk_size=1, replicate_chunk_size=5),
    )
    threaded = bootstrap_kde(
        estimator,
        events,
        support,
        plan=_plan(
            target_chunk_size=4,
            replicate_chunk_size=1,
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
    assert (
        threaded.ensemble.replicate_source_fingerprints
        == sequential.ensemble.replicate_source_fingerprints
    )
    assert (
        threaded.ensemble.seed_ledger_fingerprint
        == sequential.ensemble.seed_ledger_fingerprint
    )
    assert (
        threaded.ensemble.observed_field_fingerprint
        == sequential.ensemble.observed_field_fingerprint
    )
    assert sequential.ensemble.execution_metadata["parallel_axis"] == "none"
    assert threaded.ensemble.execution_metadata["parallel_axis"] == "replicates"


def test_cyclic_bootstrap_preserves_domain_origin_and_pairing() -> None:
    events = _events(cyclic=True)
    support = _support(cyclic=True)
    result = bootstrap_kde(
        SpatiotemporalKDE(
            spatial_bandwidth=0.7,
            temporal_bandwidth=2.0,
            cyclic_tail_tolerance=1e-10,
        ),
        events,
        support,
        plan=_plan(seed=9, target_chunk_size=5),
    )

    assert result.metadata["time_domain"] == "cyclic"
    assert result.metadata["time_domain_fingerprint"] == events.temporal.domain.fingerprint
    assert result.metadata["temporal_origin"] == "study-hour-zero"
    assert result.metadata["timezone"] == "UTC"
    assert (
        result.ensemble.descriptor.time_domain_fingerprint
        == support.time_domain.fingerprint
    )
    assert np.all(np.isfinite(result.ensemble.replicate_values))


def test_one_event_cyclic_bootstrap_is_degenerate() -> None:
    domain = CyclicTimeDomain(24.0)
    events = SpatiotemporalEvents.from_arrays(
        [[0.5, 0.5]],
        [23.5],
        spatial_unit="km",
        temporal_unit="hours",
        time_domain=domain,
    )
    spatial = GridSupport.from_bounds(
        (0.0, 0.0, 1.0, 1.0),
        resolution=0.5,
        spatial_unit="km",
    )
    support = SpatiotemporalGridSupport.from_spatial_grid(
        spatial,
        temporal_resolution=6.0,
        temporal_unit="hours",
        time_domain=domain,
    )
    result = bootstrap_kde(
        SpatiotemporalKDE(0.5, 2.0),
        events,
        support,
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
        rtol=1e-13,
        atol=1e-15,
    )
    np.testing.assert_allclose(result.interval.standard_error, 0.0, atol=1e-15)
    np.testing.assert_allclose(result.interval.bias, 0.0, atol=1e-15)


def test_spatiotemporal_bootstrap_does_not_mutate_fitted_source() -> None:
    events = _events()
    source = _estimator().fit(events)
    assert source.events_object_ is not None
    event_fingerprint = source.event_fingerprint_
    stored_times = source.times_.copy()
    stored_coordinates = source.events_.copy()

    bootstrap_kde(source, events, _support(), plan=_plan())

    assert source.is_fitted_
    assert source.event_fingerprint_ == event_fingerprint
    np.testing.assert_array_equal(source.times_, stored_times)
    np.testing.assert_array_equal(source.events_, stored_coordinates)


def test_spatiotemporal_bootstrap_rejects_open_or_incompatible_contracts() -> None:
    events = _events()
    support = _support()
    point_support = SpatiotemporalPointSupport.from_arrays(
        support.spatial_coordinates,
        support.times,
        support_measure=support.measure,
        spatial_unit="km",
        temporal_unit="hours",
        temporal_origin="study-hour-zero",
        timezone="UTC",
    )

    with pytest.raises(ValueError, match="unit event weights"):
        bootstrap_kde(
            _estimator(),
            _events(weights=np.array([1.0, 2.0, 1.0])),
            support,
            plan=_plan(),
        )
    with pytest.raises(TypeError, match="SpatiotemporalGridSupport"):
        bootstrap_kde(
            _estimator(),
            events,
            point_support,  # type: ignore[arg-type]
            plan=_plan(),
        )
    with pytest.raises(ValueError, match="built-in string"):
        bootstrap_kde(
            SpatiotemporalKDE(
                0.7,
                0.8,
                spatial_kernel=get_kernel("gaussian"),
            ),
            events,
            support,
            plan=_plan(),
        )
    incompatible = SpatiotemporalGridSupport.from_spatial_grid(
        support.spatial,
        temporal_bounds=(0.0, 3.0),
        temporal_resolution=1.0,
        temporal_unit="days",
        temporal_origin="study-hour-zero",
        timezone="UTC",
    )
    with pytest.raises(ValueError, match="temporal units"):
        bootstrap_kde(_estimator(), events, incompatible, plan=_plan())


def test_spatiotemporal_bootstrap_accepts_events_keyword_and_rejects_small_budget() -> (
    None
):
    events = _events()
    support = _support()
    result = bootstrap_kde(
        estimator=_estimator(),
        events=events,
        support=support,
        plan=_plan(),
    )
    assert result.estimator_family == "spatiotemporal"

    with pytest.raises(MemoryError, match="fixed overhead"):
        bootstrap_kde(
            _estimator(),
            events,
            support,
            plan=BootstrapPlan(
                n_resamples=3,
                random_state=1,
                execution_plan=ExecutionPlan(memory_budget_bytes=100),
            ),
        )
