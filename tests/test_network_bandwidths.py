"""Network bandwidth selection, caching, and adaptive estimator tests."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import (
    NetworkKDE,
    NetworkKNNBandwidth,
    NetworkLeastSquaresCV,
    NetworkLeastSquaresCVBandwidth,
    NetworkLikelihoodCV,
    NetworkLikelihoodCVBandwidth,
    NetworkWorkspace,
    SpatialEvents,
    build_event_event_distances,
    load_disconnected_network,
    load_osmnx_fixture,
    load_t_junction,
)
from pykdex.kernels import EpanechnikovKernel


def _workspace(
    coordinates,
    *,
    weights=None,
    lixel_length: float = 0.05,
) -> NetworkWorkspace:
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        coordinates,
        weights=weights,
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    return NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=lixel_length,
        max_snap_distance=0.05,
    )


def test_event_event_distance_asset_preserves_self_and_duplicate_zero_pairs():
    workspace = _workspace([[-0.75, 0.0], [-0.75, 0.0], [0.5, 0.0]])
    assert workspace.events is not None

    asset = build_event_event_distances(workspace.network, workspace.events)
    dense = asset.to_dense()

    np.testing.assert_allclose(np.diag(dense), 0.0)
    assert dense[0, 1] == pytest.approx(0.0)
    assert dense[1, 0] == pytest.approx(0.0)
    assert asset.shape == (3, 3)


def test_workspace_caches_event_event_distances_and_reports_them():
    workspace = _workspace([[-0.75, 0.0], [0.5, 0.0], [0.0, 0.75]])
    prepared = workspace.with_event_event_distances()

    assert prepared.event_distance_asset is not None
    assert prepared.summary()["n_event_distance_pairs"] == 9
    assert prepared.validate().valid
    assert prepared.fingerprint != workspace.fingerprint


def test_network_knn_bandwidth_matches_manual_network_distances():
    workspace = _workspace([[-0.75, 0.0], [-0.25, 0.0], [0.5, 0.0]])
    strategy = NetworkKNNBandwidth(k=1)

    values = strategy.resolve(
        workspace,
        kernel=EpanechnikovKernel(),
        junction_policy="simple",
        directed=False,
        coefficient_tolerance=1e-12,
        max_records_per_event=10_000,
    )

    np.testing.assert_allclose(values, [0.5, 0.5, 0.75])
    assert strategy.distance_asset_ is not None
    with pytest.raises(ValueError):
        values[0] = 10.0


def test_network_knn_requires_floor_for_duplicate_event_locations():
    workspace = _workspace([[-0.75, 0.0], [-0.75, 0.0], [0.5, 0.0]])

    with pytest.raises(ValueError, match="minimum_bandwidth"):
        NetworkKNNBandwidth(k=1).resolve(
            workspace,
            kernel=EpanechnikovKernel(),
            junction_policy="simple",
            directed=False,
            coefficient_tolerance=1e-12,
            max_records_per_event=10_000,
        )

    values = NetworkKNNBandwidth(k=1, minimum_bandwidth=0.1).resolve(
        workspace,
        kernel=EpanechnikovKernel(),
        junction_policy="simple",
        directed=False,
        coefficient_tolerance=1e-12,
        max_records_per_event=10_000,
    )
    np.testing.assert_allclose(values[:2], 0.1)


def test_adaptive_network_kde_uses_one_bandwidth_per_event_for_simple_policy():
    workspace = _workspace([[-0.75, 0.0], [-0.25, 0.0], [0.5, 0.0]])
    model = NetworkKDE(
        bandwidth=NetworkKNNBandwidth(k=1),
        junction_policy="simple",
    ).fit(workspace)

    field = model.predict_result()
    assert field.adaptive
    assert isinstance(field.bandwidth, np.ndarray)
    np.testing.assert_allclose(field.bandwidth, [0.5, 0.5, 0.75])
    assert model.fit_metadata_["adaptive_bandwidth"] is True
    assert np.all(np.isfinite(field.values))


def test_adaptive_network_kde_supports_path_based_policy():
    workspace = _workspace([[-0.75, 0.0], [-0.25, 0.0], [0.5, 0.0]])

    field = NetworkKDE(
        bandwidth=NetworkKNNBandwidth(k=1, multiplier=1.5),
        junction_policy="continuous",
    ).fit_predict(workspace)

    assert field.adaptive
    assert field.integral() == pytest.approx(1.0, abs=0.04)


def test_network_likelihood_cv_is_deterministic_and_uses_event_cache():
    workspace = _workspace(
        [[-0.8, 0.0], [-0.4, 0.0], [0.3, 0.0], [0.0, 0.65]],
        lixel_length=0.1,
    ).with_event_event_distances()
    selector = NetworkLikelihoodCV(bounds=(0.2, 1.2), maxiter=40)

    first = selector.select(
        workspace,
        kernel=EpanechnikovKernel(),
        junction_policy="simple",
        directed=False,
    )
    second = NetworkLikelihoodCV(bounds=(0.2, 1.2), maxiter=40).select(
        workspace,
        kernel=EpanechnikovKernel(),
        junction_policy="simple",
        directed=False,
    )

    assert first.success
    assert first.method == "network_likelihood_cv"
    assert 0.2 <= first.bandwidth <= 1.2
    assert first.bandwidth == pytest.approx(second.bandwidth)
    assert selector.cache_ is not None
    assert (
        selector.cache_.event_event_distances.fingerprint
        == workspace.event_distance_asset.fingerprint
    )


def test_network_lscv_uses_measured_lixel_integral_for_path_policy():
    workspace = _workspace(
        [[-0.8, 0.0], [-0.4, 0.0], [0.3, 0.0], [0.0, 0.65]],
        lixel_length=0.05,
    )
    selector = NetworkLeastSquaresCV(bounds=(0.3, 1.0), maxiter=30)

    result = selector.select(
        workspace,
        kernel=EpanechnikovKernel(),
        junction_policy="continuous",
        directed=False,
    )

    assert result.success
    assert result.method == "network_least_squares_cv"
    assert 0.3 <= result.bandwidth <= 1.0
    assert selector.cache_ is not None
    assert selector.cache_.propagation_traces is not None
    assert selector.cache_.event_lixel_distances is None


def test_network_selection_bandwidth_wrappers_integrate_with_estimator():
    workspace = _workspace(
        [[-0.8, 0.0], [-0.4, 0.0], [0.3, 0.0], [0.0, 0.65]],
        lixel_length=0.1,
    )
    likelihood = NetworkKDE(
        bandwidth=NetworkLikelihoodCVBandwidth(
            bounds=(0.2, 1.2), maxiter=30
        ),
        junction_policy="simple",
    ).fit(workspace)
    least_squares = NetworkKDE(
        bandwidth=NetworkLeastSquaresCVBandwidth(
            bounds=(0.3, 1.0), maxiter=30
        ),
        junction_policy="continuous",
    ).fit(workspace)

    assert likelihood.bandwidth_selection_ is not None
    assert likelihood.bandwidth_selection_.method == "network_likelihood_cv"
    assert least_squares.bandwidth_selection_ is not None
    assert least_squares.bandwidth_selection_.method == "network_least_squares_cv"
    assert isinstance(likelihood.bandwidth_, float)
    assert isinstance(least_squares.bandwidth_, float)


def test_directed_network_knn_reports_unreachable_neighbour_rank():
    dataset = load_osmnx_fixture()
    workspace = NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=0.2,
        max_snap_distance=0.25,
    )

    with pytest.raises(ValueError, match="cannot reach"):
        NetworkKNNBandwidth(k=1).resolve(
            workspace,
            kernel=EpanechnikovKernel(),
            junction_policy="simple",
            directed=True,
            coefficient_tolerance=1e-12,
            max_records_per_event=10_000,
        )


def test_disconnected_components_fail_automatic_bounds_cleanly():
    dataset = load_disconnected_network()
    workspace = NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=0.2,
        max_snap_distance=0.1,
    )

    with pytest.raises(ValueError, match="mutually reachable"):
        NetworkLikelihoodCV().select(
            workspace,
            kernel=EpanechnikovKernel(),
            junction_policy="simple",
            directed=False,
        )
