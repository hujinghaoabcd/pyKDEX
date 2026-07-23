# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Network-time cache, selection, and adaptive bandwidth contracts."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import (
    CyclicTimeDomain,
    NetworkTimeBandwidthExperiment,
    NetworkTimeBandwidths,
    NetworkTimeKNNBandwidth,
    NetworkTimeWorkspace,
    SpatialEvents,
    TemporalNetworkKDE,
    load_t_junction,
)
from pykdex.kernels import GaussianKernel
from pykdex.spatiotemporal import evaluate_temporal_kernel


def _workspace(
    coordinates=((-0.8, 0.0), (-0.4, 0.0), (0.3, 0.0), (0.0, 0.65)),
    times=(0.1, 0.6, 1.7, 2.4),
    *,
    lixel_length: float = 0.1,
    temporal_resolution: float = 0.5,
    temporal_bounds=(0.0, 3.0),
    time_domain=None,
) -> NetworkTimeWorkspace:
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        coordinates,
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    return NetworkTimeWorkspace.prepare(
        network,
        events,
        times,
        temporal_unit="hours",
        lixel_length=lixel_length,
        temporal_resolution=temporal_resolution,
        temporal_bounds=temporal_bounds,
        time_domain=time_domain,
        max_snap_distance=0.05,
    )


def test_network_time_bandwidth_pair_owns_arrays_and_validates_event_count() -> None:
    spatial = np.asarray([0.4, 0.5, 0.6])
    bandwidths = NetworkTimeBandwidths(spatial=spatial, temporal=1.0)
    spatial[0] = 99.0

    assert bandwidths.adaptive
    assert bandwidths.adaptive_spatial
    assert not bandwidths.adaptive_temporal
    np.testing.assert_allclose(bandwidths.spatial, [0.4, 0.5, 0.6])
    with pytest.raises(ValueError):
        bandwidths.spatial[0] = 2.0
    with pytest.raises(ValueError, match="one value per event"):
        bandwidths.validate_for(4)


def test_network_time_knn_resolves_independent_sample_point_bandwidths() -> None:
    workspace = _workspace(
        coordinates=((-0.75, 0.0), (-0.25, 0.0), (0.5, 0.0)),
        times=(0.0, 1.0, 4.0),
        temporal_bounds=(-0.5, 4.5),
    )
    strategy = NetworkTimeKNNBandwidth(spatial_k=1, temporal_k=1)

    bandwidths = strategy.resolve(workspace, directed=False)

    np.testing.assert_allclose(bandwidths.spatial, [0.5, 0.5, 0.75])
    np.testing.assert_allclose(bandwidths.temporal, [1.0, 1.0, 3.0])
    assert strategy.distance_asset_ is not None


def test_network_time_knn_requires_floors_for_duplicate_locations_and_times() -> None:
    workspace = _workspace(
        coordinates=((-0.75, 0.0), (-0.75, 0.0), (0.5, 0.0)),
        times=(0.0, 0.0, 2.0),
        temporal_bounds=(-0.5, 2.5),
    )
    with pytest.raises(ValueError, match="minimum_spatial_bandwidth"):
        NetworkTimeKNNBandwidth(1, 1).resolve(workspace)

    bandwidths = NetworkTimeKNNBandwidth(
        1,
        1,
        minimum_spatial_bandwidth=0.1,
        minimum_temporal_bandwidth=0.2,
    ).resolve(workspace)
    np.testing.assert_allclose(bandwidths.spatial[:2], 0.1)
    np.testing.assert_allclose(bandwidths.temporal[:2], 0.2)


def test_adaptive_temporal_network_kde_supports_simple_and_path_policies() -> None:
    workspace = _workspace()
    strategy = NetworkTimeKNNBandwidth(
        1,
        1,
        spatial_multiplier=1.5,
        temporal_multiplier=1.5,
    )
    simple = TemporalNetworkKDE(
        bandwidths=strategy,
        junction_policy="simple",
    ).fit_predict(workspace)
    continuous = TemporalNetworkKDE(
        bandwidths=strategy,
        junction_policy="continuous",
    ).fit_predict(workspace)

    assert simple.adaptive_spatial and simple.adaptive_temporal
    assert continuous.adaptive
    assert simple.spatial_bandwidth.shape == (workspace.events.n_events,)
    assert simple.temporal_bandwidth.shape == (workspace.events.n_events,)
    assert np.all(np.isfinite(simple.values))
    assert np.all(np.isfinite(continuous.values))
    assert simple.metadata["bandwidth_strategy"] == "NetworkTimeKNNBandwidth"


def test_source_specific_cyclic_temporal_bandwidths_use_periodic_images() -> None:
    offsets = np.asarray([[0.0, 0.0], [12.0, 12.0]])
    bandwidths = np.asarray([0.5, 2.0])
    values = evaluate_temporal_kernel(
        offsets,
        domain=CyclicTimeDomain(period=24.0),
        kernel=GaussianKernel(),
        bandwidth=bandwidths,
    )

    assert values.shape == offsets.shape
    assert values[0, 0] > values[0, 1]
    assert values[1, 1] > values[1, 0]


@pytest.mark.parametrize("mode", ["joint", "separate"])
def test_network_time_likelihood_experiment_is_deterministic_and_cached(
    mode: str,
) -> None:
    workspace = _workspace().with_distances(cutoff=1.2)
    experiment = NetworkTimeBandwidthExperiment(
        [0.5, 0.8, 1.2],
        [0.3, 0.6, 1.0],
        mode=mode,
        junction_policy="simple",
    )
    first = experiment.run(workspace)
    second = NetworkTimeBandwidthExperiment(
        [0.5, 0.8, 1.2],
        [0.3, 0.6, 1.0],
        mode=mode,
        junction_policy="simple",
    ).run(workspace)

    assert first.objective == "loo_likelihood"
    assert first.score_matrix.shape == (3, 3)
    assert first.spatial_bandwidth == second.spatial_bandwidth
    assert first.temporal_bandwidth == second.temporal_bandwidth
    np.testing.assert_allclose(first.score_matrix, second.score_matrix)
    assert experiment.cache_ is not None
    assert (
        experiment.cache_.event_lixel_distances.fingerprint
        == workspace.distance_asset.network_distances.fingerprint
    )
    assert first.to_frame().shape[0] == 9


def test_network_time_lscv_integrates_arixel_measure_for_path_policy() -> None:
    workspace = _workspace(lixel_length=0.05)
    experiment = NetworkTimeBandwidthExperiment(
        [0.5, 0.8],
        [0.4, 0.8],
        objective="least_squares",
        junction_policy="continuous",
    )

    result = experiment.run(workspace)

    assert result.objective == "least_squares_cv"
    assert np.all(np.isfinite(result.score_matrix))
    assert experiment.cache_ is not None
    assert experiment.cache_.propagation_traces is not None
    assert experiment.cache_.event_lixel_distances is None


def test_network_time_experiment_rejects_incompatible_path_kernel() -> None:
    workspace = _workspace()
    with pytest.raises(ValueError, match="finite-support"):
        NetworkTimeBandwidthExperiment(
            [0.5],
            [0.5],
            spatial_kernel="gaussian",
            junction_policy="continuous",
        ).run(workspace)
