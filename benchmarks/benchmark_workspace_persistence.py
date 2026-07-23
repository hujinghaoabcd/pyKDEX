# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Repeatable size, save-time, and reload-time persistence benchmark."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

import numpy as np

from pykdex import NetworkTimeWorkspace, SpatialEvents, make_grid_network


def main() -> None:
    """Persist and reload a moderate prepared network-time workspace."""
    network = make_grid_network(10, 10, spacing=100.0)
    rng = np.random.default_rng(20260723)
    edge_indices = rng.integers(0, network.n_edges, size=250)
    fractions = rng.uniform(0.05, 0.95, size=250)
    coordinates = np.vstack(
        [
            network.edge_geometries[index]
            .interpolate(fraction, normalized=True)
            .coords[0]
            for index, fraction in zip(edge_indices, fractions, strict=True)
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
        rng.uniform(0.0, 24.0, size=250),
        temporal_unit="hours",
        lixel_length=50.0,
        temporal_resolution=1.0,
        temporal_bounds=(0.0, 24.0),
        max_snap_distance=1e-6,
    ).with_distances(cutoff=500.0)

    with TemporaryDirectory() as temporary:
        path = Path(temporary) / "benchmark.pykdex"
        started = perf_counter()
        workspace.save(path)
        save_seconds = perf_counter() - started
        started = perf_counter()
        restored = NetworkTimeWorkspace.load(path)
        load_seconds = perf_counter() - started
        assert restored.fingerprint == workspace.fingerprint
        print(
            {
                "n_nodes": network.n_nodes,
                "n_edges": network.n_edges,
                "n_events": workspace.events.n_events,
                "n_arixels": workspace.arixels.n_arixels,
                "distance_pairs": workspace.distance_asset.network_distances.n_pairs,
                "archive_bytes": path.stat().st_size,
                "save_seconds": round(save_seconds, 3),
                "load_seconds": round(load_seconds, 3),
            }
        )


if __name__ == "__main__":
    main()
