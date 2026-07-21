# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""OSMnx acquisition and conversion adapters.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from typing import Any

from pykdex.data import DataProvenance
from pykdex.network.linear_network import LinearNetwork


def _require_osmnx() -> Any:
    try:
        import osmnx as ox
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "OSM download requires the 'osm' optional dependencies: "
            "python -m pip install 'pyKDEX[osm]'."
        ) from exc
    return ox


def from_osmnx_graph(
    graph: Any,
    *,
    cost_attribute: str = "length",
    spatial_unit: str = "m",
    require_projected: bool = True,
    provenance: DataProvenance | None = None,
) -> LinearNetwork:
    """Convert an OSMnx MultiDiGraph while retaining ``u, v, key`` semantics."""
    return LinearNetwork.from_osmnx(
        graph,
        cost_attribute=cost_attribute,
        spatial_unit=spatial_unit,
        require_projected=require_projected,
        provenance=provenance,
    )


def network_from_place(
    place: str | dict[str, Any],
    *,
    network_type: str = "drive",
    simplify: bool = True,
    retain_all: bool = False,
    project: bool = True,
    cost_attribute: str = "length",
    **graph_kwargs: Any,
) -> LinearNetwork:
    """Download an OSM street network by place name and normalize it.

    The download is intentionally outside the core estimator path. Online calls
    are never used by the default test suite, and the resulting graph is
    converted immediately to :class:`LinearNetwork`.
    """
    ox = _require_osmnx()
    graph = ox.graph_from_place(
        place,
        network_type=network_type,
        simplify=simplify,
        retain_all=retain_all,
        **graph_kwargs,
    )
    if project:
        graph = ox.project_graph(graph)
    return from_osmnx_graph(
        graph,
        cost_attribute=cost_attribute,
        require_projected=project,
        provenance=DataProvenance(
            source="OpenStreetMap via OSMnx",
            transformations=(
                ("graph_from_place", "project_graph")
                if project
                else ("graph_from_place",)
            ),
            metadata={
                "place": place,
                "network_type": network_type,
                "simplify": simplify,
                "retain_all": retain_all,
            },
        ),
    )
