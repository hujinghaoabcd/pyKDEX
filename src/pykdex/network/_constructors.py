# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Construction helpers for canonical linear networks."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Mapping

import numpy as np

from pykdex.data._utils import normalize_crs
from pykdex.data.provenance import DataProvenance
from pykdex.network.linear_network import (
    _is_geographic_crs,
    _object_vector,
    _require_geopandas,
    _require_networkx,
    _require_shapely,
)

if TYPE_CHECKING:
    from pykdex.network.linear_network import LinearNetwork


def network_from_geodataframe(
    cls: type[LinearNetwork],
    edges: Any,
    *,
    edge_id_column: str | None = None,
    u_column: str | None = None,
    v_column: str | None = None,
    key_column: str | None = None,
    length_column: str | None = None,
    cost_column: str | None = None,
    directed: bool = False,
    endpoint_tolerance: float = 0.0,
    spatial_unit: str | None = None,
    provenance: DataProvenance | None = None,
) -> "LinearNetwork":
    """Build a network from LineString edge geometries.

    Intersections are not inferred from crossing geometries. Topology is
    defined by explicit ``u_column``/``v_column`` values or by line endpoints.
    This avoids incorrectly connecting bridges, tunnels, and grade-separated
    roads.
    """
    gpd = _require_geopandas()
    if not isinstance(edges, gpd.GeoDataFrame):
        raise TypeError("edges must be a GeoDataFrame.")
    if edges.empty or edges.geometry.isna().any() or edges.geometry.is_empty.any():
        raise ValueError("edge geometries must be non-empty LineString objects.")
    if not edges.geometry.geom_type.eq("LineString").all():
        raise ValueError("edge geometries must all be LineString objects.")
    if endpoint_tolerance < 0.0 or not np.isfinite(endpoint_tolerance):
        raise ValueError("endpoint_tolerance must be finite and non-negative.")
    for column in (
        edge_id_column,
        u_column,
        v_column,
        key_column,
        length_column,
        cost_column,
    ):
        if column is not None and column not in edges.columns:
            raise ValueError(f"GeoDataFrame is missing column {column!r}.")
    if (u_column is None) != (v_column is None):
        raise ValueError("u_column and v_column must be supplied together.")

    geometries = tuple(edges.geometry.tolist())
    starts = np.asarray([geometry.coords[0] for geometry in geometries], dtype=float)
    ends = np.asarray([geometry.coords[-1] for geometry in geometries], dtype=float)
    node_ids_list: list[Any] = []
    node_coordinates_list: list[tuple[float, float]] = []
    node_lookup: dict[Any, int] = {}

    def coordinate_key(
        coordinate: np.ndarray,
    ) -> tuple[float, float] | tuple[int, int]:
        if endpoint_tolerance == 0.0:
            return (float(coordinate[0]), float(coordinate[1]))
        rounded = np.rint(coordinate / endpoint_tolerance).astype(np.int64)
        return (int(rounded[0]), int(rounded[1]))

    def add_node(node_id: Any, coordinate: np.ndarray) -> int:
        if node_id in node_lookup:
            index = node_lookup[node_id]
            if (
                np.linalg.norm(np.asarray(node_coordinates_list[index]) - coordinate)
                > endpoint_tolerance
            ):
                raise ValueError(
                    f"node {node_id!r} is associated with inconsistent coordinates."
                )
            return index
        index = len(node_ids_list)
        node_lookup[node_id] = index
        node_ids_list.append(node_id)
        node_coordinates_list.append((float(coordinate[0]), float(coordinate[1])))
        return index

    edge_u: list[int] = []
    edge_v: list[int] = []
    if u_column is not None and v_column is not None:
        for u_id, v_id, start, end in zip(
            edges[u_column].tolist(),
            edges[v_column].tolist(),
            starts,
            ends,
            strict=True,
        ):
            edge_u.append(add_node(u_id, start))
            edge_v.append(add_node(v_id, end))
    else:
        endpoint_to_id: dict[Any, int] = {}

        def endpoint_node(coordinate: np.ndarray) -> int:
            key = coordinate_key(coordinate)
            if key not in endpoint_to_id:
                endpoint_to_id[key] = len(endpoint_to_id)
            node_id = endpoint_to_id[key]
            return add_node(node_id, coordinate)

        for start, end in zip(starts, ends, strict=True):
            edge_u.append(endpoint_node(start))
            edge_v.append(endpoint_node(end))

    edge_ids = (
        np.arange(len(geometries), dtype=np.int64)
        if edge_id_column is None
        else edges[edge_id_column].to_numpy()
    )
    keys = (
        np.zeros(len(geometries), dtype=np.int64)
        if key_column is None
        else edges[key_column].to_numpy()
    )
    geometric_lengths = np.asarray([geometry.length for geometry in geometries])
    lengths = (
        geometric_lengths
        if length_column is None
        else edges[length_column].to_numpy(dtype=float)
    )
    costs = lengths if cost_column is None else edges[cost_column].to_numpy(dtype=float)
    reserved = {
        edges.geometry.name,
        edge_id_column,
        u_column,
        v_column,
        key_column,
        length_column,
        cost_column,
    }
    attributes = {
        str(column): edges[column].to_numpy()
        for column in edges.columns
        if column not in reserved
    }
    return cls(
        node_ids=np.asarray(node_ids_list, dtype=object),
        node_coordinates=np.asarray(node_coordinates_list, dtype=float),
        edge_ids=np.asarray(edge_ids),
        edge_u=np.asarray(edge_u, dtype=np.int64),
        edge_v=np.asarray(edge_v, dtype=np.int64),
        edge_keys=np.asarray(keys),
        edge_geometries=geometries,
        edge_lengths=np.asarray(lengths, dtype=float),
        edge_costs=np.asarray(costs, dtype=float),
        directed=directed,
        crs=normalize_crs(edges.crs),
        spatial_unit=spatial_unit,
        edge_attributes=attributes,
        metadata={"source_adapter": "geopandas", "topology": "endpoints"},
        provenance=provenance or DataProvenance(source="GeoDataFrame"),
    )


def network_from_networkx(
    cls: type[LinearNetwork],
    graph: Any,
    *,
    cost_attribute: str = "length",
    spatial_unit: str | None = None,
    provenance: DataProvenance | None = None,
) -> "LinearNetwork":
    """Convert a NetworkX graph while retaining direction and parallel edges."""
    nx = _require_networkx()
    if not isinstance(graph, (nx.Graph, nx.DiGraph, nx.MultiGraph, nx.MultiDiGraph)):
        raise TypeError("graph must be a NetworkX graph.")
    if graph.number_of_nodes() == 0 or graph.number_of_edges() == 0:
        raise ValueError("graph must contain at least one node and one edge.")
    LineString, _ = _require_shapely()
    node_ids = _object_vector(list(graph.nodes))
    node_lookup = {node_id: index for index, node_id in enumerate(node_ids.tolist())}
    node_coordinates = []
    for node_id in node_ids.tolist():
        data = graph.nodes[node_id]
        if "x" not in data or "y" not in data:
            raise ValueError("every graph node must provide numeric 'x' and 'y'.")
        node_coordinates.append((float(data["x"]), float(data["y"])))

    records: list[tuple[Any, Any, Any, Mapping[str, Any]]]
    if graph.is_multigraph():
        records = list(graph.edges(keys=True, data=True))
    else:
        records = [(u, v, 0, data) for u, v, data in graph.edges(data=True)]
    edge_ids: list[Any] = []
    edge_u: list[int] = []
    edge_v: list[int] = []
    edge_keys: list[Any] = []
    geometries: list[Any] = []
    lengths: list[float] = []
    costs: list[float] = []
    attribute_names = sorted(
        {
            str(name)
            for _, _, _, data in records
            for name in data
            if name not in {"geometry", "length", cost_attribute, "edge_id"}
        }
    )
    attributes: dict[str, list[Any]] = {name: [] for name in attribute_names}
    for u, v, key, data in records:
        start = node_coordinates[node_lookup[u]]
        end = node_coordinates[node_lookup[v]]
        geometry = data.get("geometry") or LineString([start, end])
        length = float(data.get("length", geometry.length))
        cost = float(data.get(cost_attribute, length))
        edge_ids.append(data.get("edge_id", (u, v, key)))
        edge_u.append(node_lookup[u])
        edge_v.append(node_lookup[v])
        edge_keys.append(key)
        geometries.append(geometry)
        lengths.append(length)
        costs.append(cost)
        for name in attribute_names:
            attributes[name].append(data.get(name))
    return cls(
        node_ids=node_ids,
        node_coordinates=np.asarray(node_coordinates, dtype=float),
        edge_ids=_object_vector(edge_ids),
        edge_u=np.asarray(edge_u, dtype=np.int64),
        edge_v=np.asarray(edge_v, dtype=np.int64),
        edge_keys=_object_vector(edge_keys),
        edge_geometries=tuple(geometries),
        edge_lengths=np.asarray(lengths, dtype=float),
        edge_costs=np.asarray(costs, dtype=float),
        directed=bool(graph.is_directed()),
        crs=normalize_crs(graph.graph.get("crs")),
        spatial_unit=spatial_unit,
        edge_attributes=attributes,
        metadata={**dict(graph.graph), "source_adapter": "networkx"},
        provenance=provenance or DataProvenance(source="NetworkX graph"),
    )


def network_from_osmnx(
    cls: type[LinearNetwork],
    graph: Any,
    *,
    cost_attribute: str = "length",
    spatial_unit: str = "m",
    provenance: DataProvenance | None = None,
    require_projected: bool = True,
) -> "LinearNetwork":
    """Convert an OSMnx graph without making OSMnx a core representation."""
    if require_projected and _is_geographic_crs(graph.graph.get("crs")):
        raise ValueError(
            "OSMnx graph geometry must be projected before network-distance analysis. "
            "Use osmnx.project_graph or pass require_projected=False explicitly."
        )
    network = cls.from_networkx(
        graph,
        cost_attribute=cost_attribute,
        spatial_unit=spatial_unit,
        provenance=provenance or DataProvenance(source="OSMnx graph"),
    )
    metadata = dict(network.metadata)
    metadata["source_adapter"] = "osmnx"
    metadata["osm_simplified"] = bool(graph.graph.get("simplified", False))
    object.__setattr__(network, "metadata", MappingProxyType(metadata))
    return network
