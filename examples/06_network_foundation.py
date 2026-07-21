# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Prepare a reusable network workspace from an analytical fixture."""

from __future__ import annotations

from pykdex import NetworkWorkspace, load_osmnx_fixture, load_t_junction


def main() -> None:
    dataset = load_t_junction()
    workspace = NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=0.25,
        max_snap_distance=0.2,
    )
    print(workspace.summary())
    print(workspace.lixels.to_frame().head())

    osm_fixture = load_osmnx_fixture()
    print(osm_fixture.network.metadata["source_adapter"])
    print(osm_fixture.network.to_geodataframes()[1].head())


if __name__ == "__main__":
    main()
