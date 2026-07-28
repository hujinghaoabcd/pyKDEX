# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import numpy as np
import pytest

from pykdex import HeatNetworkKDE, NetworkWorkspace, SpatialEvents, load_t_junction
from pykdex.bandwidths.heat import HeatLikelihoodCVTime
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, BootstrapResult, bootstrap_kde
from pykdex.uncertainty.heat import _resample_heat_workspace
from pykdex.uncertainty.seeds import build_seed_ledger


def _workspace(*, weights: np.ndarray | None = None) -> NetworkWorkspace:
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        [[-0.75, 0.0], [0.50, 0.0], [0.0, 0.50]],
        weights=weights,
        ids=["left", "right", "top"],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
        marks=["a", "b", "c"],
    )
    return NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=0.25,
        max_snap_distance=0.05,
    )


def _plan(
    *,
    seed: int = 20260729,
    replicate_chunk_size: int = 2,
    n_jobs: int = 1,
    backend: str = "sequential",
    target_chunk_size: int | None = None,
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


def test_heat_bootstrap_returns_complete_exact_support_result() -> None:
    workspace = _workspace()
    source = HeatNetworkKDE(
        diffusion_time=0.08,
        mesh_size=0.25,
        target="density",
    )

    result = bootstrap_kde(source, workspace, plan=_plan())

    assert isinstance(result, BootstrapResult)
    assert result.operation == "bootstrap_kde"
    assert result.estimator_family == "heat_network"
    assert result.ensemble.n_replicates == 4
    assert result.ensemble.n_elements == workspace.lixels.n_lixels
    assert result.ensemble.descriptor.fingerprint == workspace.lixels.fingerprint
    assert result.ensemble.field_family == "density"
    assert result.interval.confidence_level == pytest.approx(0.8)
    assert result.metadata["conditional_on_observed_event_count"] is True
    assert result.metadata["resampling_stage"] == "after_accepted_event_snapping"
    assert result.metadata["distance_assets_propagated"] is False
    assert result.metadata["solver"] == "dense_symmetric_eigendecomposition"
    assert result.ensemble.metadata["unit_event_weights"] is True
    assert result.ensemble.metadata["n_rejected_fixed"] == 0
    assert (
        len(result.ensemble.metadata["replicate_heat_compute_plan_fingerprints"]) == 4
    )
    assert not source.is_fitted_
    assert not result.ensemble.replicate_values.flags.writeable
    assert np.dot(
        result.ensemble.observed_values,
        workspace.lixels.lengths,
    ) == pytest.approx(1.0, abs=1e-12)


def test_one_event_heat_bootstrap_is_degenerate() -> None:
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        [[-0.75, 0.0]],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    workspace = NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=0.25,
        max_snap_distance=0.05,
    )

    result = bootstrap_kde(
        HeatNetworkKDE(diffusion_time=0.08, mesh_size=0.25),
        workspace,
        plan=_plan(),
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


def test_first_heat_replicate_matches_manual_post_snap_resample() -> None:
    workspace = _workspace()
    plan = _plan(seed=41)
    result = bootstrap_kde(
        HeatNetworkKDE(diffusion_time=0.08, mesh_size=0.25),
        workspace,
        plan=plan,
    )

    events = workspace.events
    assert events is not None
    ledger = build_seed_ledger(41, plan.n_resamples)
    sampled = ledger.generator(0).integers(
        0,
        events.n_events,
        size=events.n_events,
        dtype=np.int64,
    )
    replicate_workspace = _resample_heat_workspace(
        workspace,
        sampled,
        replicate_index=0,
    )
    expected = HeatNetworkKDE(
        diffusion_time=0.08,
        mesh_size=0.25,
    ).fit_predict(replicate_workspace)

    np.testing.assert_allclose(
        result.ensemble.replicate_values[0],
        expected.values,
        rtol=1e-13,
        atol=1e-15,
    )
    replicate_events = replicate_workspace.events
    assert replicate_events is not None
    assert replicate_events.event_ids.tolist() == list(range(events.n_events))
    assert (
        replicate_events.provenance.metadata["sampled_source_indices"]
        == sampled.tolist()
    )
    assert replicate_workspace.network is workspace.network
    assert replicate_workspace.lixels is workspace.lixels
    assert replicate_workspace.distance_asset is None
    assert replicate_workspace.event_distance_asset is None


def test_heat_bootstrap_is_invariant_to_outer_workers_and_replicate_chunks() -> None:
    workspace = _workspace()
    estimator = HeatNetworkKDE(
        diffusion_time=0.08,
        mesh_size=0.25,
        target="intensity",
    )

    sequential = bootstrap_kde(
        estimator,
        workspace,
        plan=_plan(replicate_chunk_size=4),
    )
    threaded = bootstrap_kde(
        estimator,
        workspace,
        plan=_plan(
            replicate_chunk_size=1,
            n_jobs=2,
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
    assert sequential.ensemble.execution_metadata["parallel_axis"] == "none"
    assert threaded.ensemble.execution_metadata["parallel_axis"] == "replicates"


def test_heat_bootstrap_does_not_mutate_fitted_source_or_workspace() -> None:
    workspace = _workspace()
    source = HeatNetworkKDE(diffusion_time=0.08, mesh_size=0.25).fit(workspace)
    assert source.values_ is not None
    assert source.heat_compute_plan_ is not None
    values = source.values_.copy()
    plan_fingerprint = source.heat_compute_plan_.fingerprint
    workspace_fingerprint = workspace.fingerprint

    bootstrap_kde(source, workspace, plan=_plan())

    assert source.is_fitted_
    np.testing.assert_array_equal(source.values_, values)
    assert source.heat_compute_plan_ is not None
    assert source.heat_compute_plan_.fingerprint == plan_fingerprint
    assert workspace.fingerprint == workspace_fingerprint


def test_heat_bootstrap_rejects_non_unit_weights_and_selected_time() -> None:
    with pytest.raises(ValueError, match="unit accepted-event weights"):
        bootstrap_kde(
            HeatNetworkKDE(diffusion_time=0.08, mesh_size=0.25),
            _workspace(weights=np.array([1.0, 2.0, 1.0])),
            plan=_plan(),
        )

    with pytest.raises(ValueError, match="fixed numeric scalar"):
        bootstrap_kde(
            HeatNetworkKDE(
                diffusion_time=HeatLikelihoodCVTime(),
                mesh_size=0.25,
            ),
            _workspace(),
            plan=_plan(),
        )


def test_heat_bootstrap_rejects_target_chunks_and_explicit_support() -> None:
    workspace = _workspace()
    with pytest.raises(ValueError, match="target_chunk_size"):
        bootstrap_kde(
            HeatNetworkKDE(diffusion_time=0.08, mesh_size=0.25),
            workspace,
            plan=_plan(target_chunk_size=1),
        )
    with pytest.raises(TypeError, match="does not accept support"):
        bootstrap_kde(
            HeatNetworkKDE(diffusion_time=0.08, mesh_size=0.25),
            workspace,
            workspace.lixels,  # type: ignore[arg-type]
            plan=_plan(),
        )


def test_heat_bootstrap_accepts_events_keyword_and_fails_small_memory_preflight() -> (
    None
):
    workspace = _workspace()
    result = bootstrap_kde(
        estimator=HeatNetworkKDE(diffusion_time=0.08, mesh_size=0.25),
        events=workspace,
        plan=_plan(),
    )
    assert result.estimator_family == "heat_network"

    with pytest.raises(MemoryError, match="fixed overhead"):
        bootstrap_kde(
            HeatNetworkKDE(diffusion_time=0.08, mesh_size=0.25),
            workspace,
            plan=BootstrapPlan(
                n_resamples=3,
                random_state=1,
                execution_plan=ExecutionPlan(memory_budget_bytes=100),
            ),
        )
