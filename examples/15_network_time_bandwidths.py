# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Select and apply network-time bandwidths on one reusable workspace."""

from __future__ import annotations

from pykdex import (
    NetworkTimeBandwidthExperiment,
    NetworkTimeBandwidths,
    NetworkTimeBandwidthSelectionResult,
    NetworkTimeKNNBandwidth,
    NetworkTimeSelectionCache,
    NetworkTimeWorkspace,
    SpatialEvents,
    TemporalNetworkKDE,
    load_t_junction,
)

network = load_t_junction().network
raw = SpatialEvents.from_array(
    [[-0.8, 0.0], [-0.4, 0.0], [0.3, 0.0], [0.0, 0.65]],
    crs=network.crs,
    spatial_unit=network.spatial_unit,
)
workspace = NetworkTimeWorkspace.prepare(
    network,
    raw,
    [0.1, 0.6, 1.7, 2.4],
    temporal_unit="hours",
    lixel_length=0.1,
    temporal_resolution=0.5,
    temporal_bounds=(0.0, 3.0),
    max_snap_distance=0.05,
)

experiment = NetworkTimeBandwidthExperiment(
    spatial_candidates=[0.5, 0.8, 1.2],
    temporal_candidates=[0.3, 0.6, 1.0],
    mode="joint",
    objective="likelihood",
    junction_policy="simple",
)
selection: NetworkTimeBandwidthSelectionResult = experiment.run(workspace)
cache: NetworkTimeSelectionCache = experiment.cache_
selected = NetworkTimeBandwidths(
    spatial=selection.spatial_bandwidth,
    temporal=selection.temporal_bandwidth,
)
selected_field = TemporalNetworkKDE(
    bandwidths=selected,
    junction_policy="simple",
).fit_predict(workspace)

adaptive = NetworkTimeKNNBandwidth(
    spatial_k=1,
    temporal_k=1,
    spatial_multiplier=1.5,
    temporal_multiplier=1.5,
)
adaptive_field = TemporalNetworkKDE(
    bandwidths=adaptive,
    junction_policy="continuous",
).fit_predict(workspace)

assert cache.fingerprint == selection.cache_fingerprint
assert selection.to_frame().shape[0] == 9
assert not selected_field.adaptive
assert adaptive_field.adaptive
print(selection)
print(adaptive_field.to_frame().head())
