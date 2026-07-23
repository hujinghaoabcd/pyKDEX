# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Measured temporal-network KDE on a reusable T-junction workspace."""

from __future__ import annotations

from pykdex import (
    ArixelSupport,
    CyclicTimeDomain,
    NetworkTimeDistanceAsset,
    NetworkTimeEvents,
    NetworkTimeField,
    NetworkTimeWorkspace,
    SpatialEvents,
    TemporalNetworkKDE,
    build_network_time_distance_asset,
    load_t_junction,
)

dataset = load_t_junction()
network = dataset.network
raw_events = SpatialEvents.from_array(
    [[-0.75, 0.0], [0.5, 0.0], [0.0, 0.75]],
    weights=[1.0, 2.0, 1.0],
    crs=network.crs,
    spatial_unit=network.spatial_unit,
)
domain = CyclicTimeDomain(period=24.0)
workspace: NetworkTimeWorkspace = NetworkTimeWorkspace.prepare(
    network,
    raw_events,
    [23.0, 0.5, 8.0],
    temporal_unit="hours",
    lixel_length=0.1,
    temporal_resolution=2.0,
    time_domain=domain,
    max_snap_distance=0.05,
)
events: NetworkTimeEvents = workspace.events
support: ArixelSupport = workspace.arixels
asset: NetworkTimeDistanceAsset = build_network_time_distance_asset(
    workspace.network_workspace,
    events,
    support,
    cutoff=0.8,
)
workspace = workspace.with_distances(cutoff=0.8)

field: NetworkTimeField = TemporalNetworkKDE(
    spatial_bandwidth=0.8,
    temporal_bandwidth=2.0,
    junction_policy="continuous",
    time_chunk_size=3,
).fit_predict(workspace)

assert asset.arixel_shape == support.shape
assert field.to_grid().shape == support.shape
assert field.integral() > 0.99
assert field.integral() < 1.01
print(workspace.summary())
print(field.to_frame().head())
