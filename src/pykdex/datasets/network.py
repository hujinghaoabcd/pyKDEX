# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Deterministic geometric-network fixtures and generators.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from typing import Any

import numpy as np

from pykdex.data import DataProvenance, SpatialEvents
from pykdex.network import LinearNetwork
from pykdex.network.dataset import NetworkDataset
from pykdex.network.events import snap_events
from pykdex.network.support import LixelSupport


def _network_from_records(
    records: list[tuple[Any, Any, list[tuple[float, float]]]],
    *,
    directed: bool = False,
    name: str,
) -> LinearNetwork:
    try:
        import geopandas as gpd
        from shapely.geometry import LineString
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Network datasets require the 'network' optional dependencies."
        ) from exc
    frame = gpd.GeoDataFrame(
        {
            "edge_id": np.arange(len(records), dtype=np.int64),
            "u": [record[0] for record in records],
            "v": [record[1] for record in records],
        },
        geometry=[LineString(record[2]) for record in records],
        crs="EPSG:3857",
    )
    return LinearNetwork.from_geodataframe(
        frame,
        edge_id_column="edge_id",
        u_column="u",
        v_column="v",
        directed=directed,
        spatial_unit="m",
        provenance=DataProvenance(
            source="pyKDEX analytical network fixture",
            metadata={"name": name},
        ),
    )


def _bundle(
    name: str,
    network: LinearNetwork,
    event_coordinates: np.ndarray,
    *,
    lixel_length: float,
    description: str,
) -> NetworkDataset:
    events = SpatialEvents.from_array(
        event_coordinates,
        crs=network.crs,
        spatial_unit=network.spatial_unit,
        provenance=DataProvenance(source="pyKDEX analytical network fixture"),
    )
    snapped = snap_events(network, events, max_distance=0.25)
    if snapped.events is None:
        raise RuntimeError("Analytical fixture unexpectedly rejected every event.")
    lixels = LixelSupport.from_network(network, length=lixel_length)
    return NetworkDataset(
        name=name,
        network=network,
        raw_events=events,
        network_events=snapped.events,
        lixels=lixels,
        expected={"total_network_length": network.total_length},
        description=description,
        provenance=DataProvenance(source="pyKDEX analytical network fixture"),
    )


def load_t_junction() -> NetworkDataset:
    """Load a three-branch T-junction with events on each branch."""
    network = _network_from_records(
        [
            (0, 1, [(-1.0, 0.0), (0.0, 0.0)]),
            (1, 2, [(0.0, 0.0), (1.0, 0.0)]),
            (1, 3, [(0.0, 0.0), (0.0, 1.0)]),
        ],
        name="t_junction",
    )
    return _bundle(
        "t_junction",
        network,
        np.asarray([[-0.7, 0.02], [0.65, -0.03], [0.02, 0.75]]),
        lixel_length=0.4,
        description="Three one-unit branches meeting at one degree-three vertex.",
    )


def load_cross_network() -> NetworkDataset:
    """Load a four-branch cross network."""
    network = _network_from_records(
        [
            (0, 1, [(-1.0, 0.0), (0.0, 0.0)]),
            (1, 2, [(0.0, 0.0), (1.0, 0.0)]),
            (3, 1, [(0.0, -1.0), (0.0, 0.0)]),
            (1, 4, [(0.0, 0.0), (0.0, 1.0)]),
        ],
        name="cross_network",
    )
    return _bundle(
        "cross_network",
        network,
        np.asarray([[-0.6, 0.0], [0.0, 0.6]]),
        lixel_length=0.3,
        description="Four one-unit branches meeting at one degree-four vertex.",
    )


def load_ring_network() -> NetworkDataset:
    """Load a closed square ring network."""
    network = _network_from_records(
        [
            (0, 1, [(0.0, 0.0), (1.0, 0.0)]),
            (1, 2, [(1.0, 0.0), (1.0, 1.0)]),
            (2, 3, [(1.0, 1.0), (0.0, 1.0)]),
            (3, 0, [(0.0, 1.0), (0.0, 0.0)]),
        ],
        name="ring_network",
    )
    return _bundle(
        "ring_network",
        network,
        np.asarray([[0.5, 0.02], [0.98, 0.5]]),
        lixel_length=0.35,
        description="A four-edge closed loop for multiple-path tests.",
    )


def load_disconnected_network() -> NetworkDataset:
    """Load two disconnected line components."""
    network = _network_from_records(
        [
            (0, 1, [(0.0, 0.0), (1.0, 0.0)]),
            (2, 3, [(3.0, 0.0), (4.0, 0.0)]),
        ],
        name="disconnected_network",
    )
    return _bundle(
        "disconnected_network",
        network,
        np.asarray([[0.4, 0.0], [3.6, 0.0]]),
        lixel_length=0.4,
        description="Two disconnected one-edge components.",
    )


def load_osmnx_fixture() -> NetworkDataset:
    """Load an offline OSMnx-like directed multigraph fixture."""
    try:
        import networkx as nx
        from shapely.geometry import LineString
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "The OSMnx fixture requires the 'network' optional dependencies."
        ) from exc
    graph = nx.MultiDiGraph()
    graph.graph.update(crs="EPSG:3857", simplified=True)
    graph.add_node(10, x=0.0, y=0.0)
    graph.add_node(20, x=1.0, y=0.0)
    graph.add_node(30, x=2.0, y=0.0)
    graph.add_edge(
        10,
        20,
        key=0,
        osmid=100,
        highway="primary",
        oneway=True,
        length=1.0,
        travel_time=0.1,
        geometry=LineString([(0.0, 0.0), (0.5, 0.1), (1.0, 0.0)]),
    )
    graph.add_edge(
        10,
        20,
        key=1,
        osmid=101,
        highway="service",
        oneway=True,
        bridge=True,
        length=1.2,
        travel_time=0.2,
        geometry=LineString([(0.0, 0.0), (0.5, -0.2), (1.0, 0.0)]),
    )
    graph.add_edge(
        20,
        30,
        key=0,
        osmid=102,
        highway="primary",
        oneway=True,
        length=1.0,
        travel_time=0.1,
    )
    network = LinearNetwork.from_osmnx(
        graph, cost_attribute="travel_time", spatial_unit="m"
    )
    return _bundle(
        "osmnx_fixture",
        network,
        np.asarray([[0.4, 0.08], [1.7, 0.01]]),
        lixel_length=0.4,
        description="Offline directed MultiDiGraph with parallel OSM-style edges.",
    )


def make_grid_network(
    rows: int,
    columns: int,
    *,
    spacing: float = 1.0,
    directed: bool = False,
) -> LinearNetwork:
    """Generate a reproducible rectangular grid network for benchmarks."""
    if isinstance(rows, bool) or not isinstance(rows, int) or rows < 1:
        raise ValueError("rows must be a positive integer.")
    if isinstance(columns, bool) or not isinstance(columns, int) or columns < 1:
        raise ValueError("columns must be a positive integer.")
    spacing_value = float(spacing)
    if not np.isfinite(spacing_value) or spacing_value <= 0.0:
        raise ValueError("spacing must be finite and positive.")
    records: list[tuple[int, int, list[tuple[float, float]]]] = []
    for row in range(rows + 1):
        for column in range(columns):
            node = row * (columns + 1) + column
            records.append(
                (
                    node,
                    node + 1,
                    [
                        (column * spacing_value, row * spacing_value),
                        ((column + 1) * spacing_value, row * spacing_value),
                    ],
                )
            )
    for row in range(rows):
        for column in range(columns + 1):
            node = row * (columns + 1) + column
            records.append(
                (
                    node,
                    node + columns + 1,
                    [
                        (column * spacing_value, row * spacing_value),
                        (column * spacing_value, (row + 1) * spacing_value),
                    ],
                )
            )
    return _network_from_records(
        records,
        directed=directed,
        name=f"grid_{rows}x{columns}",
    )
