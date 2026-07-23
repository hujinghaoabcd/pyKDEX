"""Small deterministic benchmark for network bandwidth infrastructure."""

from __future__ import annotations

from time import perf_counter

import numpy as np

from pykdex import (
    NetworkKDE,
    NetworkKNNBandwidth,
    NetworkLikelihoodCVBandwidth,
    NetworkWorkspace,
    SpatialEvents,
    make_grid_network,
)


def main() -> None:
    network = make_grid_network(8, 8, spacing=100.0)
    rng = np.random.default_rng(42)
    coordinates = rng.uniform(0.0, 800.0, size=(48, 2))
    events = SpatialEvents.from_array(
        coordinates,
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )

    started = perf_counter()
    workspace = NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=50.0,
        max_snap_distance=80.0,
    )
    prepared = workspace.with_event_event_distances()
    distance_seconds = perf_counter() - started

    started = perf_counter()
    adaptive = NetworkKDE(
        bandwidth=NetworkKNNBandwidth(k=5, minimum_bandwidth=25.0),
        junction_policy="simple",
    ).fit(prepared)
    adaptive_seconds = perf_counter() - started

    started = perf_counter()
    selected = NetworkKDE(
        bandwidth=NetworkLikelihoodCVBandwidth(
            bounds=(50.0, 500.0),
            maxiter=15,
        ),
        junction_policy="simple",
    ).fit(prepared)
    selection_seconds = perf_counter() - started

    print(
        {
            "n_nodes": network.n_nodes,
            "n_edges": network.n_edges,
            "n_events": prepared.events.n_events if prepared.events else 0,
            "n_lixels": prepared.lixels.n_lixels,
            "event_distance_pairs": (
                prepared.event_distance_asset.n_pairs
                if prepared.event_distance_asset
                else 0
            ),
            "distance_seconds": round(distance_seconds, 6),
            "adaptive_seconds": round(adaptive_seconds, 6),
            "selection_seconds": round(selection_seconds, 6),
            "adaptive_bandwidth_min": float(np.min(adaptive.bandwidth_)),
            "adaptive_bandwidth_max": float(np.max(adaptive.bandwidth_)),
            "selected_bandwidth": float(selected.bandwidth_),
        }
    )


if __name__ == "__main__":
    main()
