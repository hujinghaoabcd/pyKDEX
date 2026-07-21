# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Immutable geometric linear-network representation.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components

from pykdex.data._utils import (
    normalize_crs,
    normalize_unit,
    readonly_array,
    stable_fingerprint,
)
from pykdex.data.provenance import DataProvenance
from pykdex.data.validation import DataIssue, DataValidationReport


def _require_shapely() -> tuple[Any, Any]:
    try:
        from shapely.geometry import LineString
        from shapely.geometry.base import BaseGeometry
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Linear-network geometry requires the 'network' optional dependencies."
        ) from exc
    return LineString, BaseGeometry


def _require_geopandas() -> Any:
    try:
        import geopandas as gpd
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "GeoDataFrame network input requires the 'network' optional dependencies."
        ) from exc
    return gpd


def _require_networkx() -> Any:
    try:
        import networkx as nx
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "NetworkX conversion requires the 'network' optional dependencies."
        ) from exc
    return nx


def _is_geographic_crs(crs: Any | None) -> bool:
    if crs is None:
        return False
    try:
        from pyproj import CRS

        return bool(CRS.from_user_input(crs).is_geographic)
    except (ImportError, ValueError, TypeError):
        return False


def _object_vector(values: list[Any]) -> np.ndarray:
    """Return a one-dimensional object array without tuple expansion."""
    array = np.empty(len(values), dtype=object)
    array[:] = values
    return array


def _unique(values: np.ndarray, *, name: str) -> None:
    if len({repr(value) for value in values.tolist()}) != values.shape[0]:
        raise ValueError(f"{name} must be unique.")


def _readonly_attributes(
    attributes: Mapping[str, Any], *, n_edges: int
) -> Mapping[str, np.ndarray]:
    normalized: dict[str, np.ndarray] = {}
    for raw_name, values in attributes.items():
        name = str(raw_name).strip()
        if not name:
            raise ValueError("edge attribute names must be non-empty strings.")
        array = readonly_array(values, ndim=1, name=f"edge_attributes[{name!r}]")
        if array.shape[0] != n_edges:
            raise ValueError(
                f"edge attribute {name!r} must contain one value per edge."
            )
        normalized[name] = array
    return MappingProxyType(normalized)


@dataclass(frozen=True)
class LinearNetwork:
    """A geometric directed or undirected multigraph with stable internal IDs.

    Node incidence is stored using zero-based internal node indices, while
    ``node_ids`` and ``edge_ids`` preserve user-facing identifiers. Parallel
    edges and edge direction are retained.
    """

    node_ids: np.ndarray
    node_coordinates: np.ndarray
    edge_ids: np.ndarray
    edge_u: np.ndarray
    edge_v: np.ndarray
    edge_keys: np.ndarray
    edge_geometries: tuple[Any, ...]
    edge_lengths: np.ndarray
    edge_costs: np.ndarray
    directed: bool = False
    crs: str | None = None
    spatial_unit: str | None = None
    edge_attributes: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    provenance: DataProvenance = field(default_factory=DataProvenance)

    def __post_init__(self) -> None:
        _, BaseGeometry = _require_shapely()
        node_ids = readonly_array(self.node_ids, ndim=1, name="node_ids")
        node_coordinates = readonly_array(
            self.node_coordinates, dtype=float, ndim=2, name="node_coordinates"
        )
        if node_ids.shape[0] == 0 or node_coordinates.shape != (node_ids.shape[0], 2):
            raise ValueError("node_coordinates must have shape (n_nodes, 2).")
        if not np.all(np.isfinite(node_coordinates)):
            raise ValueError("node_coordinates must contain only finite values.")
        _unique(node_ids, name="node_ids")

        edge_ids = readonly_array(self.edge_ids, ndim=1, name="edge_ids")
        n_edges = edge_ids.shape[0]
        if n_edges == 0:
            raise ValueError("a linear network must contain at least one edge.")
        _unique(edge_ids, name="edge_ids")
        edge_u = readonly_array(self.edge_u, dtype=np.int64, ndim=1, name="edge_u")
        edge_v = readonly_array(self.edge_v, dtype=np.int64, ndim=1, name="edge_v")
        edge_keys = readonly_array(self.edge_keys, ndim=1, name="edge_keys")
        edge_lengths = readonly_array(
            self.edge_lengths, dtype=float, ndim=1, name="edge_lengths"
        )
        edge_costs = readonly_array(
            self.edge_costs, dtype=float, ndim=1, name="edge_costs"
        )
        for name, array in (
            ("edge_u", edge_u),
            ("edge_v", edge_v),
            ("edge_keys", edge_keys),
            ("edge_lengths", edge_lengths),
            ("edge_costs", edge_costs),
        ):
            if array.shape[0] != n_edges:
                raise ValueError(f"{name} must contain one value per edge.")
        if np.any(edge_u < 0) or np.any(edge_v < 0):
            raise ValueError("edge endpoints must use non-negative node indices.")
        if np.any(edge_u >= node_ids.shape[0]) or np.any(edge_v >= node_ids.shape[0]):
            raise ValueError("edge endpoints reference a missing node index.")
        if not np.all(np.isfinite(edge_lengths)) or np.any(edge_lengths <= 0.0):
            raise ValueError("edge_lengths must be finite and positive.")
        if not np.all(np.isfinite(edge_costs)) or np.any(edge_costs <= 0.0):
            raise ValueError("edge_costs must be finite and positive.")

        geometries = tuple(self.edge_geometries)
        if len(geometries) != n_edges:
            raise ValueError("edge_geometries must contain one geometry per edge.")
        for geometry in geometries:
            if not isinstance(geometry, BaseGeometry):
                raise TypeError("edge_geometries must contain Shapely geometries.")
            if geometry.is_empty or geometry.geom_type != "LineString":
                raise ValueError(
                    "edge geometries must be non-empty LineString objects."
                )
            if not geometry.is_valid:
                raise ValueError("edge geometries must be valid.")

        if not isinstance(self.directed, (bool, np.bool_)):
            raise TypeError("directed must be boolean.")
        object.__setattr__(self, "node_ids", node_ids)
        object.__setattr__(self, "node_coordinates", node_coordinates)
        object.__setattr__(self, "edge_ids", edge_ids)
        object.__setattr__(self, "edge_u", edge_u)
        object.__setattr__(self, "edge_v", edge_v)
        object.__setattr__(self, "edge_keys", edge_keys)
        object.__setattr__(self, "edge_geometries", geometries)
        object.__setattr__(self, "edge_lengths", edge_lengths)
        object.__setattr__(self, "edge_costs", edge_costs)
        object.__setattr__(self, "directed", bool(self.directed))
        object.__setattr__(self, "crs", normalize_crs(self.crs))
        object.__setattr__(
            self,
            "spatial_unit",
            normalize_unit(self.spatial_unit, name="spatial_unit"),
        )
        object.__setattr__(
            self,
            "edge_attributes",
            _readonly_attributes(self.edge_attributes, n_edges=n_edges),
        )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def n_nodes(self) -> int:
        """Number of network vertices."""
        return int(self.node_ids.shape[0])

    @property
    def n_edges(self) -> int:
        """Number of directed or undirected edge records."""
        return int(self.edge_ids.shape[0])

    @property
    def total_length(self) -> float:
        """Total geometric edge length."""
        return float(np.sum(self.edge_lengths))

    @property
    def node_index(self) -> Mapping[Any, int]:
        """Read-only mapping from public node identifiers to internal indices."""
        return MappingProxyType(
            {value: index for index, value in enumerate(self.node_ids.tolist())}
        )

    @property
    def edge_index(self) -> Mapping[Any, int]:
        """Read-only mapping from public edge identifiers to internal indices."""
        return MappingProxyType(
            {value: index for index, value in enumerate(self.edge_ids.tolist())}
        )

    @property
    def fingerprint(self) -> str:
        """Deterministic fingerprint of geometry, topology, costs, and metadata."""
        return stable_fingerprint(
            self.node_ids,
            self.node_coordinates,
            self.edge_ids,
            self.edge_u,
            self.edge_v,
            self.edge_keys,
            self.edge_geometries,
            self.edge_lengths,
            self.edge_costs,
            self.directed,
            self.crs,
            self.spatial_unit,
            dict(self.edge_attributes),
            dict(self.metadata),
            self.provenance.fingerprint,
        )

    def adjacency_matrix(
        self, *, weight: str = "cost", binary: bool = False
    ) -> sparse.csr_matrix:
        """Return a sparse node adjacency matrix, retaining minimum parallel cost."""
        if weight not in {"cost", "length"}:
            raise ValueError("weight must be either 'cost' or 'length'.")
        values = self.edge_costs if weight == "cost" else self.edge_lengths
        entries: dict[tuple[int, int], float] = {}
        for u, v, value in zip(self.edge_u, self.edge_v, values, strict=True):
            pair = (int(u), int(v))
            resolved = 1.0 if binary else float(value)
            entries[pair] = min(entries.get(pair, np.inf), resolved)
            if not self.directed:
                reverse = (int(v), int(u))
                entries[reverse] = min(entries.get(reverse, np.inf), resolved)
        rows = np.fromiter((key[0] for key in entries), dtype=np.int64)
        columns = np.fromiter((key[1] for key in entries), dtype=np.int64)
        data = np.fromiter(entries.values(), dtype=float)
        return sparse.csr_matrix(
            (data, (rows, columns)), shape=(self.n_nodes, self.n_nodes)
        )

    @property
    def component_labels(self) -> np.ndarray:
        """Weak connected-component label for every node."""
        matrix = self.adjacency_matrix(binary=True)
        if self.directed:
            matrix = matrix.maximum(matrix.transpose())
        _, labels = connected_components(matrix, directed=False)
        labels = np.asarray(labels, dtype=np.int64)
        labels.setflags(write=False)
        return labels

    @property
    def n_components(self) -> int:
        """Number of weak connected components."""
        return int(np.unique(self.component_labels).shape[0])

    def validate(self, *, endpoint_tolerance: float = 1e-7) -> DataValidationReport:
        """Validate topology, connectivity, and geometry endpoint consistency."""
        if endpoint_tolerance < 0.0 or not np.isfinite(endpoint_tolerance):
            raise ValueError("endpoint_tolerance must be finite and non-negative.")
        issues: list[DataIssue] = []
        component_count = self.n_components
        if component_count > 1:
            issues.append(
                DataIssue(
                    "warning",
                    "disconnected_network",
                    "The network contains multiple weak connected components.",
                    {"n_components": component_count},
                )
            )
        self_loops = int(np.count_nonzero(self.edge_u == self.edge_v))
        if self_loops:
            issues.append(
                DataIssue(
                    "warning",
                    "self_loop_edges",
                    "The network contains self-loop edges.",
                    {"count": self_loops},
                )
            )
        pairs = [
            (int(u), int(v)) if self.directed else tuple(sorted((int(u), int(v))))
            for u, v in zip(self.edge_u, self.edge_v, strict=True)
        ]
        parallel_count = len(pairs) - len(set(pairs))
        endpoint_mismatch = 0
        for index, geometry in enumerate(self.edge_geometries):
            coordinates = np.asarray(geometry.coords, dtype=float)
            expected_start = self.node_coordinates[int(self.edge_u[index])]
            expected_end = self.node_coordinates[int(self.edge_v[index])]
            if (
                np.linalg.norm(coordinates[0] - expected_start) > endpoint_tolerance
                or np.linalg.norm(coordinates[-1] - expected_end) > endpoint_tolerance
            ):
                endpoint_mismatch += 1
        if endpoint_mismatch:
            issues.append(
                DataIssue(
                    "warning",
                    "geometry_endpoint_mismatch",
                    "Some line endpoints differ from their incident node coordinates.",
                    {"count": endpoint_mismatch, "tolerance": endpoint_tolerance},
                )
            )
        if self.crs is None:
            issues.append(
                DataIssue(
                    "warning",
                    "missing_crs",
                    "The network has no CRS; lengths and costs use raw units.",
                )
            )
        elif _is_geographic_crs(self.crs):
            issues.append(
                DataIssue(
                    "warning",
                    "geographic_crs",
                    "The network uses angular coordinates; project it before snapping, lixelization, or distance-based KDE.",
                    {"crs": self.crs},
                )
            )
        return DataValidationReport(
            tuple(issues),
            {
                "n_nodes": self.n_nodes,
                "n_edges": self.n_edges,
                "n_components": component_count,
                "parallel_edge_count": parallel_count,
                "self_loop_count": self_loops,
                "total_length": self.total_length,
            },
        )

    def to_geodataframes(self) -> tuple[Any, Any]:
        """Return node and edge GeoDataFrames."""
        gpd = _require_geopandas()
        from shapely.geometry import Point

        nodes = gpd.GeoDataFrame(
            {
                "node_id": self.node_ids,
                "node_index": np.arange(self.n_nodes, dtype=np.int64),
                "component_id": self.component_labels,
            },
            geometry=[Point(float(x), float(y)) for x, y in self.node_coordinates],
            crs=self.crs,
        )
        data: dict[str, Any] = {
            "edge_id": self.edge_ids,
            "edge_index": np.arange(self.n_edges, dtype=np.int64),
            "u": self.node_ids[self.edge_u],
            "v": self.node_ids[self.edge_v],
            "key": self.edge_keys,
            "length": self.edge_lengths,
            "cost": self.edge_costs,
        }
        data.update(dict(self.edge_attributes))
        edges = gpd.GeoDataFrame(
            data, geometry=list(self.edge_geometries), crs=self.crs
        )
        return nodes, edges

    def to_networkx(self) -> Any:
        """Convert the network to a NetworkX multi-graph."""
        nx = _require_networkx()
        graph = nx.MultiDiGraph() if self.directed else nx.MultiGraph()
        graph.graph.update(dict(self.metadata))
        if self.crs is not None:
            graph.graph["crs"] = self.crs
        for node_id, (x, y) in zip(
            self.node_ids.tolist(), self.node_coordinates, strict=True
        ):
            graph.add_node(node_id, x=float(x), y=float(y))
        for index in range(self.n_edges):
            attributes = {
                name: values[index] for name, values in self.edge_attributes.items()
            }
            attributes.update(
                {
                    "edge_id": self.edge_ids[index],
                    "geometry": self.edge_geometries[index],
                    "length": float(self.edge_lengths[index]),
                    "cost": float(self.edge_costs[index]),
                }
            )
            graph.add_edge(
                self.node_ids[int(self.edge_u[index])],
                self.node_ids[int(self.edge_v[index])],
                key=self.edge_keys[index],
                **attributes,
            )
        return graph

    @classmethod
    def from_geodataframe(
        cls,
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
        """Build a network from LineString edge geometries."""
        from pykdex.network._constructors import network_from_geodataframe

        return network_from_geodataframe(
            cls,
            edges,
            edge_id_column=edge_id_column,
            u_column=u_column,
            v_column=v_column,
            key_column=key_column,
            length_column=length_column,
            cost_column=cost_column,
            directed=directed,
            endpoint_tolerance=endpoint_tolerance,
            spatial_unit=spatial_unit,
            provenance=provenance,
        )

    @classmethod
    def from_networkx(
        cls,
        graph: Any,
        *,
        cost_attribute: str = "length",
        spatial_unit: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "LinearNetwork":
        """Convert a NetworkX graph while retaining direction and parallel edges."""
        from pykdex.network._constructors import network_from_networkx

        return network_from_networkx(
            cls,
            graph,
            cost_attribute=cost_attribute,
            spatial_unit=spatial_unit,
            provenance=provenance,
        )

    @classmethod
    def from_osmnx(
        cls,
        graph: Any,
        *,
        cost_attribute: str = "length",
        spatial_unit: str = "m",
        provenance: DataProvenance | None = None,
        require_projected: bool = True,
    ) -> "LinearNetwork":
        """Convert an OSMnx graph without making OSMnx a core representation."""
        from pykdex.network._constructors import network_from_osmnx

        return network_from_osmnx(
            cls,
            graph,
            cost_attribute=cost_attribute,
            spatial_unit=spatial_unit,
            provenance=provenance,
            require_projected=require_projected,
        )
