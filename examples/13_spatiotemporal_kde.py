# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Ordinary space-time KDE with linear or cyclic time."""

from __future__ import annotations

import numpy as np

from pykdex import (
    BaseTimeDomain,
    CyclicTimeDomain,
    GridSupport,
    LinearTimeDomain,
    SpatiotemporalBandwidthExperiment,
    SpatiotemporalBandwidthSelectionResult,
    SpatiotemporalDistanceAsset,
    SpatiotemporalEvents,
    SpatiotemporalGridSupport,
    SpatiotemporalKDE,
    SpatiotemporalKDEResult,
    SpatiotemporalPointSupport,
    TemporalCoordinates,
    build_spatiotemporal_distance_asset,
    make_moving_hotspot_events,
)

domain: BaseTimeDomain = CyclicTimeDomain(period=24.0)
linear = LinearTimeDomain()
moving = make_moving_hotspot_events(10, random_state=7)
temporal = TemporalCoordinates.from_array(
    [23.0, 0.5, 8.0, 9.0],
    domain=domain,
    temporal_unit="hours",
)
events = SpatiotemporalEvents.from_arrays(
    [[0.0, 0.0], [0.2, 0.1], [2.0, 2.0], [2.2, 2.1]],
    temporal.values,
    weights=[1.0, 2.0, 1.0, 2.0],
    spatial_unit="km",
    temporal_unit="hours",
    time_domain=domain,
)
points = SpatiotemporalPointSupport.from_arrays(
    [[0.1, 0.1], [2.1, 2.1]],
    [23.5, 8.5],
    spatial_unit="km",
    temporal_unit="hours",
    time_domain=domain,
)
asset: SpatiotemporalDistanceAsset = build_spatiotemporal_distance_asset(events, points)
result: SpatiotemporalKDEResult = SpatiotemporalKDE(
    spatial_bandwidth=0.5,
    temporal_bandwidth=1.5,
).fit_predict(events, points, distance_asset=asset)

spatial_grid = GridSupport.from_bounds(
    (-1.0, -1.0, 3.0, 3.0),
    resolution=1.0,
    spatial_unit="km",
)
grid = SpatiotemporalGridSupport.from_spatial_grid(
    spatial_grid,
    temporal_resolution=6.0,
    temporal_unit="hours",
    time_domain=domain,
)
grid_result = SpatiotemporalKDE(0.5, 1.5).fit_predict(events, grid)
selection: SpatiotemporalBandwidthSelectionResult = SpatiotemporalBandwidthExperiment(
    spatial_candidates=[0.25, 0.5, 1.0],
    temporal_candidates=[0.5, 1.5, 4.0],
    mode="joint",
).run(events)

assert linear.name == "linear"
assert moving.n_events == 10
assert result.values.shape == (2,)
assert grid_result.to_grid().shape == grid.shape
assert np.isfinite(selection.score)
print(result.to_frame())
print(selection.to_frame())
