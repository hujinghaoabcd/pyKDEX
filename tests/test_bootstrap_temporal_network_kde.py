# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import numpy as np
import pytest

from pykdex import (
    CyclicTimeDomain,
    NetworkTimeWorkspace,
    SpatialEvents,
    TemporalNetworkKDE,
    load_t_junction,
)
from pykdex.bandwidths.network_time import NetworkTimeBandwidths
from pykdex.execution import ExecutionPlan
from pykdex.kernels import get_kernel
from pykdex.network.propagation import get_junction_policy
from pykdex.uncertainty import BootstrapPlan, BootstrapResult, bootstrap_kde
from pykdex.uncertainty.network_time import _resample_network_time_workspace
from pykdex.uncertainty.seeds import build_seed_ledger


def _workspace(
    *,
    weights: np.ndarray | None = None,
    cyclic: bool = False,
    one_event: bool = False,
    with_distances: bool = False,
) -> NetworkTimeWorkspace:
    network = load_t_junction().network
    if one_event:
        coordinates = [[-0.75, 0.0]]
        times = [23.5 if cyclic else 0.5]
    else:
        coordinates = [[-0.75, 0.0], [0.50, 0.0], [0.0, 0.50]]
        times = [23.5, 0.5, 8.0] if cyclic else [0.25, 1.25, 2.25]
    events = SpatialEvents.from_array(
        coordinates,
        weights=weights,
        ids=[f"event-{index}" for index in range(len(coordinates))],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
        marks=[f"mark-{index}" for index in range(len(coordinates))],
    )
    workspace = NetworkTimeWorkspace.prepare(
        network,
        events,
        times,
        temporal_unit="hours",
        lixel_length=0.25,
        temporal_resolution=6.0 if cyclic else 1.0,
        temporal_bounds=None if cyclic else (0.0, 3.0),
        time_domain=CyclicTimeDomain(24.0) if cyclic else None,
        temporal_origin="study-hour-zero",
        timezone="UTC",
        max_snap_distance=0.05,
    )
    return workspace.with_distances(cutoff=0.8) if with_distances else workspace


def _plan(
    *,
    seed: int = 20260729,
    target_chunk_size: int | None = 2,
    replicate_chunk_size: int = 2,
    n_jobs: int = 1,
    backend: str = "sequential",
) -> BootstrapPlan:
    return BootstrapPlan(
        n_resamples=4,
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


def _estimator(
    *,
    policy: str = "simple",
    target: str = "density",
    time_chunk_size: int | None = None,
) -> TemporalNetworkKDE:
    return TemporalNetworkKDE(
        spatial_bandwidth=0.8,
        temporal_bandwidth=0.7,
        spatial_kernel="epanechnikov",
        temporal_kernel="gaussian",
        junction_policy=policy,
        target=target,
        time_chunk_size=time_chunk_size,
    )


def test_temporal_network_bootstrap_returns_complete_arixel_result() -> None:
    workspace = _workspace(with_distances=True)
    source = _estimator()

    result = bootstrap_kde(source, workspace, plan=_plan())

    assert isinstance(result, BootstrapResult)
    assert result.operation == "bootstrap_kde"
    assert result.estimator_family == "temporal_network"
    assert result.ensemble.n_replicates == 4
    assert result.ensemble.n_elements == workspace.arixels.n_arixels
    assert result.ensemble.descriptor.fingerprint == workspace.arixels.fingerprint
    assert result.ensemble.descriptor.kind == "network_time_arixel"
    assert result.ensemble.field_family == "density"
    assert result.interval.confidence_level == pytest.approx(0.8)
    assert result.metadata["conditional_on_observed_event_count"] is True
    assert result.metadata["resampling_stage"] == "after_accepted_event_snapping"
    assert (
        result.metadata["resampling_unit"]
        == "paired_snapped_network_time_event_identity"
    )
    assert result.metadata["time_domain"] == "linear"
    assert result.ensemble.metadata["unit_event_weights"] is True
    assert result.ensemble.metadata["n_rejected_fixed"] == 0
    assert not source.is_fitted_
    assert not result.ensemble.replicate_values.flags.writeable


def test_first_replicate_matches_manual_paired_network_time_resample() -> None:
    workspace = _workspace(with_distances=True)
    plan = _plan(seed=41)
    result = bootstrap_kde(_estimator(), workspace, plan=plan)

    ledger = build_seed_ledger(41, plan.n_resamples)
    sampled = ledger.generator(0).integers(
        0,
        workspace.events.n_events,
        size=workspace.events.n_events,
        dtype=np.int64,
    )
    replicate_workspace = _resample_network_time_workspace(
        workspace,
        sampled,
        replicate_index=0,
    )
    expected = TemporalNetworkKDE(
        spatial_bandwidth=0.8,
        temporal_bandwidth=0.7,
        spatial_kernel="epanechnikov",
        temporal_kernel="gaussian",
        junction_policy="simple",
        execution_plan=ExecutionPlan(
            memory_budget_bytes=None,
            target_chunk_size=2,
        ),
    ).fit_predict(replicate_workspace)

    np.testing.assert_allclose(
        result.ensemble.replicate_values[0],
        expected.values,
        rtol=1e-13,
        atol=1e-15,
    )
    np.testing.assert_array_equal(
        replicate_workspace.events.edge_indices,
        workspace.events.edge_indices[sampled],
    )
    np.testing.assert_array_equal(
        replicate_workspace.events.offsets,
        workspace.events.offsets[sampled],
    )
    np.testing.assert_array_equal(
        replicate_workspace.events.times,
        workspace.events.times[sampled],
    )
    assert replicate_workspace.events.event_ids.tolist() == list(
        range(workspace.events.n_events)
    )
    assert (
        replicate_workspace.events.provenance.metadata["sampled_source_indices"]
        == sampled.tolist()
    )


def test_factorized_distance_asset_reindexes_network_rows_and_time_columns() -> None:
    workspace = _workspace(with_distances=True)
    assert workspace.distance_asset is not None
    sampled = np.asarray([2, 2, 0], dtype=np.int64)

    replicate = _resample_network_time_workspace(
        workspace,
        sampled,
        replicate_index=3,
    )

    assert replicate.distance_asset is not None
    source_dense = workspace.distance_asset.network_distances.to_dense()
    replicate_dense = replicate.distance_asset.network_distances.to_dense()
    np.testing.assert_allclose(replicate_dense, source_dense[sampled])
    np.testing.assert_array_equal(
        replicate.distance_asset.temporal_offsets,
        workspace.distance_asset.temporal_offsets[:, sampled],
    )
    np.testing.assert_array_equal(
        replicate.distance_asset.temporal_distances,
        workspace.distance_asset.temporal_distances[:, sampled],
    )
    assert replicate.distance_asset.event_fingerprint == replicate.events.fingerprint
    assert (
        replicate.distance_asset.workspace_fingerprint
        == replicate.network_workspace.fingerprint
    )
    assert replicate.arixels is workspace.arixels
    assert replicate.validate().valid


def test_temporal_network_bootstrap_is_invariant_to_workers_and_chunks() -> None:
    workspace = _workspace(with_distances=True)
    estimator = _estimator(target="intensity")

    sequential = bootstrap_kde(
        estimator,
        workspace,
        plan=_plan(target_chunk_size=1, replicate_chunk_size=4),
    )
    threaded = bootstrap_kde(
        estimator,
        workspace,
        plan=_plan(
            target_chunk_size=3,
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


@pytest.mark.parametrize("policy", ["discontinuous", "continuous"])
def test_path_policy_bootstrap_produces_finite_fields(policy: str) -> None:
    result = bootstrap_kde(
        _estimator(policy=policy),
        _workspace(),
        plan=BootstrapPlan(
            n_resamples=3,
            confidence_level=0.8,
            random_state=5,
            execution_plan=ExecutionPlan(
                memory_budget_bytes=None,
                target_chunk_size=1,
            ),
        ),
    )

    assert result.metadata["junction_policy"] == policy
    assert np.all(np.isfinite(result.ensemble.replicate_values))
    assert np.all(result.ensemble.replicate_values >= 0.0)


def test_cyclic_bootstrap_preserves_period_origin_timezone_and_pairing() -> None:
    workspace = _workspace(cyclic=True, with_distances=True)
    result = bootstrap_kde(
        TemporalNetworkKDE(
            spatial_bandwidth=0.8,
            temporal_bandwidth=2.0,
            junction_policy="simple",
            cyclic_tail_tolerance=1e-10,
        ),
        workspace,
        plan=_plan(seed=9, target_chunk_size=2),
    )

    assert result.metadata["time_domain"] == "cyclic"
    assert (
        result.metadata["time_domain_fingerprint"]
        == workspace.events.temporal.domain.fingerprint
    )
    assert result.metadata["temporal_origin"] == "study-hour-zero"
    assert result.metadata["timezone"] == "UTC"
    assert (
        result.ensemble.descriptor.time_domain_fingerprint
        == workspace.arixels.time_domain.fingerprint
    )
    assert np.all(np.isfinite(result.ensemble.replicate_values))


def test_one_event_cyclic_bootstrap_is_degenerate() -> None:
    workspace = _workspace(cyclic=True, one_event=True)
    result = bootstrap_kde(
        TemporalNetworkKDE(
            spatial_bandwidth=0.8,
            temporal_bandwidth=2.0,
            junction_policy="simple",
        ),
        workspace,
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


def test_bootstrap_does_not_mutate_fitted_source_or_workspace() -> None:
    workspace = _workspace(with_distances=True)
    source = _estimator().fit(workspace)
    assert source.values_ is not None
    values = source.values_.copy()
    event_fingerprint = source.event_fingerprint_
    workspace_fingerprint = workspace.fingerprint
    distance_fingerprint = (
        workspace.distance_asset.fingerprint if workspace.distance_asset else None
    )

    bootstrap_kde(source, workspace, plan=_plan())

    assert source.is_fitted_
    np.testing.assert_array_equal(source.values_, values)
    assert source.event_fingerprint_ == event_fingerprint
    assert workspace.fingerprint == workspace_fingerprint
    assert (
        None
        if workspace.distance_asset is None
        else workspace.distance_asset.fingerprint
    ) == distance_fingerprint


def test_bootstrap_uses_legacy_time_chunk_when_plan_omits_target_chunk() -> None:
    result = bootstrap_kde(
        _estimator(time_chunk_size=1),
        _workspace(),
        plan=_plan(target_chunk_size=None),
    )

    assert result.ensemble.metadata["memory_model"]["time_chunk_rows"] == 1


def test_temporal_network_bootstrap_rejects_open_or_adaptive_contracts() -> None:
    workspace = _workspace()
    with pytest.raises(ValueError, match="unit accepted-event weights"):
        bootstrap_kde(
            _estimator(),
            _workspace(weights=np.asarray([1.0, 2.0, 1.0])),
            plan=_plan(),
        )
    with pytest.raises(ValueError, match="fixed constructor bandwidths"):
        bootstrap_kde(
            TemporalNetworkKDE(
                bandwidths=NetworkTimeBandwidths(0.8, 0.7),
                junction_policy="simple",
            ),
            workspace,
            plan=_plan(),
        )
    with pytest.raises(ValueError, match="fixed numeric scalar"):
        bootstrap_kde(
            TemporalNetworkKDE(
                spatial_bandwidth=np.asarray([0.8, 0.8, 0.8]),
                temporal_bandwidth=0.7,
                junction_policy="simple",
            ),
            workspace,
            plan=_plan(),
        )
    with pytest.raises(ValueError, match="built-in string"):
        bootstrap_kde(
            TemporalNetworkKDE(
                spatial_bandwidth=0.8,
                temporal_bandwidth=0.7,
                spatial_kernel=get_kernel("epanechnikov"),
                junction_policy="simple",
            ),
            workspace,
            plan=_plan(),
        )
    with pytest.raises(ValueError, match="built-in string"):
        bootstrap_kde(
            TemporalNetworkKDE(
                spatial_bandwidth=0.8,
                temporal_bandwidth=0.7,
                junction_policy=get_junction_policy("simple"),
            ),
            workspace,
            plan=_plan(),
        )


def test_temporal_network_bootstrap_accepts_events_keyword_and_rejects_support() -> (
    None
):
    workspace = _workspace()
    result = bootstrap_kde(
        estimator=_estimator(),
        events=workspace,
        plan=_plan(),
    )
    assert result.estimator_family == "temporal_network"

    with pytest.raises(TypeError, match="does not accept support"):
        bootstrap_kde(
            _estimator(),
            workspace,
            workspace.arixels,  # type: ignore[arg-type]
            plan=_plan(),
        )


def test_temporal_network_bootstrap_fails_small_memory_before_replicates() -> None:
    with pytest.raises(MemoryError, match="fixed overhead"):
        bootstrap_kde(
            _estimator(),
            _workspace(with_distances=True),
            plan=BootstrapPlan(
                n_resamples=3,
                random_state=1,
                execution_plan=ExecutionPlan(memory_budget_bytes=100),
            ),
        )
