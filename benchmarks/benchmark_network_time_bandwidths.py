# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Small repeatable benchmark for factorized network-time candidate reuse."""

from __future__ import annotations

from time import perf_counter

import numpy as np

from pykdex import (
    NetworkTimeBandwidthExperiment,
    NetworkTimeWorkspace,
    SpatialEvents,
    make_grid_network,
)


def main() -> None:
    """Build one cache and evaluate a moderate deterministic candidate grid."""
    network = make_grid_network(8, 8, spacing=100.0)
    rng = np.random.default_rng(20260723)
    edge_indices = rng.integers(0, network.n_edges, size=100)
    fractions = rng.uniform(0.05, 0.95, size=100)
    coordinates = np.vstack(
        [
            network.edge_geometries[index]
            .interpolate(fraction, normalized=True)
            .coords[0]
            for index, fraction in zip(edge_indices, fractions)
        ]
    )
    events = SpatialEvents.from_array(
        coordinates,
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    workspace = NetworkTimeWorkspace.prepare(
        network,
        events,
        rng.uniform(0.0, 24.0, size=100),
        temporal_unit="hours",
        lixel_length=50.0,
        temporal_resolution=1.0,
        temporal_bounds=(0.0, 24.0),
        max_snap_distance=1e-6,
    )
    experiment = NetworkTimeBandwidthExperiment(
        np.geomspace(100.0, 800.0, 8),
        np.geomspace(0.5, 6.0, 8),
        objective="least_squares",
        junction_policy="simple",
    )
    started = perf_counter()
    result = experiment.run(workspace)
    elapsed = perf_counter() - started
    assert experiment.cache_ is not None
    print(
        {
            "n_events": workspace.events.n_events,
            "n_arixels": workspace.arixels.n_arixels,
            "candidate_pairs": result.score_matrix.size,
            "elapsed_seconds": round(elapsed, 3),
            "selected": (
                result.spatial_bandwidth,
                result.temporal_bandwidth,
            ),
            "cache_fingerprint": experiment.cache_.fingerprint,
        }
    )


if __name__ == "__main__":
    main()
