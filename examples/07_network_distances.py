# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Build reusable event-to-lixel distances and inspect a traversal."""

from __future__ import annotations

from pykdex import (
    NetworkLocations,
    NetworkWorkspace,
    build_network_distance_asset,
    load_t_junction,
    truncated_traversal,
)


def main() -> None:
    dataset = load_t_junction()
    workspace = NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=0.25,
        max_snap_distance=0.2,
    ).with_event_lixel_distances(cutoff=1.0)

    assert workspace.events is not None
    sources = NetworkLocations.from_events(workspace.events)
    targets = NetworkLocations.from_lixels(workspace.lixels)
    repeated = build_network_distance_asset(
        workspace.network,
        sources,
        targets,
        cutoff=1.0,
    )
    traversal = truncated_traversal(workspace.network, 1, cutoff=0.75)

    print(repeated.to_frame().head())
    print(traversal.to_frame().head())


if __name__ == "__main__":
    main()
