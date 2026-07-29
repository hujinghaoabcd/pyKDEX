"""Prepared radial NetworkKDE ordinary-Bootstrap tests."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import NetworkKDE, NetworkWorkspace, SpatialEvents, load_t_junction
from pykdex.execution import ExecutionPlan
from pykdex.kernels import get_kernel
from pykdex.network.propagation import get_junction_policy
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde
from pykdex.uncertainty.network import (
    _resample_network_workspace,
    bootstrap_network_kde,
)
from pykdex.uncertainty.seeds import build_seed_ledger


def _workspace(
    coordinates=None,
    *,
    weights=None,
    max_snap_distance: float = 0.05,
):
    network = load_t_junction().network
    if coordinates is None:
        coordinates = [[-0.75, 0.0], [0.5, 0.0]]
    events = SpatialEvents.from_array(
        coordinates,
        weights=weights,
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    workspace = NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=0.25,
        max_snap_distance=max_snap_distance,
    )
    return workspace.with_event_lixel_distances().with_event_event_distances()


@pytest.mark.parametrize("junction_policy", ["simple", "discontinuous", "continuous"])
def test_one_event_network_bootstrap_is_degenerate(junction_policy):
    workspace = _workspace([[-0.75, 0.0]])
    result = bootstrap_kde(
        NetworkKDE(
            bandwidth=1.0,
            kernel="epanechnikov",
            junction_policy=junction_policy,
        ),
        workspace,
        plan=BootstrapPlan(n_resamples=3, random_state=11),
    )

    np.testing.assert_allclose(
        result.ensemble.replicate_values,
        np.repeat(result.ensemble.observed_values[None, :], 3, axis=0),
    )
    assert result.estimator_family == "network"
    assert result.ensemble.support is workspace.lixels
    assert result.ensemble.metadata["resampling_stage"] == (
        "after_accepted_event_snapping"
    )
    assert result.ensemble.metadata["junction_policy"] == junction_policy


def test_first_network_replicate_matches_manual_seed_reconstruction():
    workspace = _workspace()
    estimator = NetworkKDE(
        bandwidth=0.8,
        kernel="epanechnikov",
        junction_policy="simple",
        target="intensity",
    )
    plan = BootstrapPlan(n_resamples=4, random_state=123)

    result = bootstrap_kde(estimator, workspace, plan=plan)

    events = workspace.events
    assert events is not None
    ledger = build_seed_ledger(123, 4)
    sampled = ledger.generator(0).integers(
        0,
        events.n_events,
        size=events.n_events,
        dtype=np.int64,
    )
    replicate_workspace = _resample_network_workspace(
        workspace,
        sampled,
        replicate_index=0,
    )
    expected = NetworkKDE(
        bandwidth=0.8,
        kernel="epanechnikov",
        junction_policy="simple",
        target="intensity",
    ).fit_predict(replicate_workspace)

    np.testing.assert_allclose(result.ensemble.replicate_values[0], expected.values)
    assert result.ensemble.replicate_source_fingerprints[0] == (
        replicate_workspace.events.fingerprint
    )


def test_network_distance_assets_are_exactly_reindexed_after_snapping():
    workspace = _workspace(
        [[-0.75, 0.0], [0.5, 0.0], [100.0, 100.0]],
        max_snap_distance=0.05,
    )
    assert workspace.snap_result.n_rejected == 1
    assert workspace.distance_asset is not None
    assert workspace.event_distance_asset is not None
    sampled = np.asarray([1, 1], dtype=np.int64)

    replicate = _resample_network_workspace(
        workspace,
        sampled,
        replicate_index=7,
    )

    assert replicate.network is workspace.network
    assert replicate.lixels is workspace.lixels
    assert replicate.snap_result.n_rejected == 1
    assert replicate.snap_result.rejected.equals(workspace.snap_result.rejected)
    assert replicate.events is not None
    np.testing.assert_array_equal(
        replicate.events.event_ids,
        np.arange(2, dtype=np.int64),
    )
    np.testing.assert_array_equal(
        replicate.events.edge_indices,
        np.repeat(workspace.events.edge_indices[1], 2),
    )
    assert replicate.events.provenance.metadata["sampled_source_indices"] == [1, 1]

    original_lixel = workspace.distance_asset.to_dense()
    assert replicate.distance_asset is not None
    replicate_lixel = replicate.distance_asset.to_dense()
    np.testing.assert_allclose(replicate_lixel[0], original_lixel[1])
    np.testing.assert_allclose(replicate_lixel[1], original_lixel[1])
    assert replicate.distance_asset.metadata["bootstrap_axis_contract"] == (
        "sampled_event_rows_fixed_lixel_columns"
    )

    original_event = workspace.event_distance_asset.to_dense()
    assert replicate.event_distance_asset is not None
    replicate_event = replicate.event_distance_asset.to_dense()
    np.testing.assert_allclose(
        replicate_event,
        np.full((2, 2), original_event[1, 1]),
    )
    assert replicate.event_distance_asset.metadata["bootstrap_axis_contract"] == (
        "sampled_event_rows_and_columns"
    )
    replicate.validate().raise_for_errors()


def test_network_bootstrap_is_invariant_to_workers_and_both_chunk_axes():
    workspace = _workspace()
    estimator = NetworkKDE(
        bandwidth=0.9,
        kernel="epanechnikov",
        junction_policy="continuous",
    )
    sequential = BootstrapPlan(
        n_resamples=5,
        random_state=77,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=268_435_456,
            target_chunk_size=3,
            replicate_chunk_size=1,
            n_jobs=1,
            backend="sequential",
        ),
    )
    threaded = BootstrapPlan(
        n_resamples=5,
        random_state=77,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=536_870_912,
            target_chunk_size=2,
            replicate_chunk_size=2,
            n_jobs=2,
            backend="thread",
        ),
    )

    first = bootstrap_kde(estimator, workspace, plan=sequential)
    second = bootstrap_kde(estimator, workspace, plan=threaded)

    np.testing.assert_allclose(
        first.ensemble.replicate_values,
        second.ensemble.replicate_values,
    )
    assert first.ensemble.replicate_source_fingerprints == (
        second.ensemble.replicate_source_fingerprints
    )
    assert first.ensemble.seed_ledger_fingerprint == (
        second.ensemble.seed_ledger_fingerprint
    )


def test_network_bootstrap_does_not_mutate_workspace_or_fitted_estimator():
    workspace = _workspace()
    estimator = NetworkKDE(
        bandwidth=0.8,
        junction_policy="simple",
        store_propagation=True,
    ).fit(workspace)
    workspace_fingerprint = workspace.fingerprint
    original_values = estimator.values_.copy()
    original_event_fingerprint = estimator.event_fingerprint_
    original_workspace = estimator.workspace_

    result = bootstrap_kde(
        estimator,
        workspace,
        plan=BootstrapPlan(n_resamples=3, random_state=9),
    )

    assert result.ensemble.metadata["source_workspace_fingerprint"] == (
        workspace_fingerprint
    )
    assert workspace.fingerprint == workspace_fingerprint
    assert estimator.workspace_ is original_workspace
    assert estimator.event_fingerprint_ == original_event_fingerprint
    np.testing.assert_allclose(estimator.values_, original_values)


def test_network_bootstrap_rejects_non_unit_weights():
    workspace = _workspace(weights=[1.0, 2.0])

    with pytest.raises(ValueError, match="unit accepted-event weights"):
        bootstrap_kde(
            NetworkKDE(bandwidth=1.0, junction_policy="simple"),
            workspace,
            plan=BootstrapPlan(n_resamples=2, random_state=1),
        )


@pytest.mark.parametrize(
    "bandwidth",
    [True, np.asarray([0.5, 0.5]), np.nan, 0.0, -1.0],
)
def test_network_bootstrap_rejects_non_fixed_scalar_bandwidths(bandwidth):
    workspace = _workspace()
    if isinstance(bandwidth, np.ndarray):
        estimator = NetworkKDE.__new__(NetworkKDE)
        NetworkKDE.__init__(estimator, bandwidth=1.0)
        estimator.bandwidth = bandwidth
    else:
        with pytest.raises((TypeError, ValueError)):
            NetworkKDE(bandwidth=bandwidth)
        return

    with pytest.raises(ValueError, match="fixed numeric scalar"):
        bootstrap_network_kde(
            estimator,
            workspace,
            plan=BootstrapPlan(n_resamples=2, random_state=1),
        )


def test_network_bootstrap_rejects_custom_component_objects():
    workspace = _workspace()

    with pytest.raises(ValueError, match="built-in string names"):
        bootstrap_network_kde(
            NetworkKDE(
                bandwidth=1.0,
                kernel=get_kernel("epanechnikov"),
                junction_policy="simple",
            ),
            workspace,
            plan=BootstrapPlan(n_resamples=2, random_state=1),
        )
    with pytest.raises(ValueError, match="built-in string names"):
        bootstrap_network_kde(
            NetworkKDE(
                bandwidth=1.0,
                kernel="epanechnikov",
                junction_policy=get_junction_policy("simple"),
            ),
            workspace,
            plan=BootstrapPlan(n_resamples=2, random_state=1),
        )


def test_network_bootstrap_rejects_invalid_dispatch_and_path_kernel():
    workspace = _workspace()
    events = SpatialEvents.from_array([[0.0, 0.0]])

    with pytest.raises(TypeError, match="NetworkWorkspace"):
        bootstrap_kde(
            NetworkKDE(bandwidth=1.0),
            events,
            plan=BootstrapPlan(n_resamples=2, random_state=1),
        )
    with pytest.raises(TypeError, match="does not accept support"):
        bootstrap_kde(
            NetworkKDE(bandwidth=1.0),
            workspace,
            workspace.lixels,  # type: ignore[arg-type]
            plan=BootstrapPlan(n_resamples=2, random_state=1),
        )
    with pytest.raises(ValueError, match="finite-support kernel"):
        bootstrap_kde(
            NetworkKDE(
                bandwidth=1.0,
                kernel="gaussian",
                junction_policy="discontinuous",
            ),
            workspace,
            plan=BootstrapPlan(n_resamples=2, random_state=1),
        )


def test_network_bootstrap_fails_memory_audit_before_replicates():
    workspace = _workspace()
    plan = BootstrapPlan(
        n_resamples=2,
        random_state=1,
        execution_plan=ExecutionPlan(memory_budget_bytes=1),
    )

    with pytest.raises(MemoryError, match="memory"):
        bootstrap_kde(
            NetworkKDE(bandwidth=1.0, junction_policy="simple"),
            workspace,
            plan=plan,
        )
