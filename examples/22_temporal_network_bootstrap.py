# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Ordinary Bootstrap uncertainty for a cyclic temporal-network KDE field."""

from pykdex import (
    CyclicTimeDomain,
    NetworkTimeWorkspace,
    SpatialEvents,
    TemporalNetworkKDE,
    load_t_junction,
)
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde

network = load_t_junction().network
events = SpatialEvents.from_array(
    [[-0.75, 0.0], [0.50, 0.0], [0.0, 0.50]],
    ids=["night", "morning", "daytime"],
    crs=network.crs,
    spatial_unit=network.spatial_unit,
)
workspace = NetworkTimeWorkspace.prepare(
    network,
    events,
    [23.5, 0.5, 8.0],
    temporal_unit="hours",
    lixel_length=0.25,
    temporal_resolution=6.0,
    time_domain=CyclicTimeDomain(period=24.0),
    temporal_origin="study-hour-zero",
    timezone="UTC",
    max_snap_distance=0.05,
).with_distances(cutoff=0.8)

result = bootstrap_kde(
    TemporalNetworkKDE(
        spatial_bandwidth=0.8,
        temporal_bandwidth=2.0,
        spatial_kernel="epanechnikov",
        temporal_kernel="gaussian",
        junction_policy="simple",
        target="density",
    ),
    workspace,
    plan=BootstrapPlan(
        n_resamples=199,
        confidence_level=0.95,
        random_state=20260729,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=256 * 1024 * 1024,
            target_chunk_size=2,
            replicate_chunk_size=2,
            n_jobs=2,
            backend="thread",
        ),
    ),
)

estimate = workspace.arixels.reshape(result.interval.estimate)
lower = workspace.arixels.reshape(result.interval.lower)
upper = workspace.arixels.reshape(result.interval.upper)

print("field shape:", estimate.shape)
print("time domain:", result.metadata["time_domain"])
print("resampling unit:", result.metadata["resampling_unit"])
print(
    "first arixel estimate and interval:",
    estimate.flat[0],
    lower.flat[0],
    upper.flat[0],
)
