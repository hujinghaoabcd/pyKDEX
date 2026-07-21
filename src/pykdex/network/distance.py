# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Exact distances and reusable traversal assets on linear networks.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.csgraph import dijkstra

from pykdex.data._utils import readonly_array, stable_fingerprint
from pykdex.data.validation import DataIssue, DataValidationReport
from pykdex.network.events import NetworkEvents
from pykdex.network.linear_network import LinearNetwork
from pykdex.network.support import LixelSupport


def _unique(values: np.ndarray, *, name: str) -> None:
    if len({repr(value) for value in values.tolist()}) != values.shape[0]:
        raise ValueError(f"{name} must be unique.")


def _resolve_weight(network: LinearNetwork, weight: str) -> np.ndarray:
    normalized = str(weight).strip().lower()
    if normalized == "length":
        return network.edge_lengths
    if normalized == "cost":
        return network.edge_costs
    raise ValueError("weight must be either 'length' or 'cost'.")


def _resolve_directed(network: LinearNetwork, directed: bool | None) -> bool:
    if directed is not None and not isinstance(directed, (bool, np.bool_)):
        raise TypeError("directed must be boolean or None.")
    requested = network.directed if directed is None else bool(directed)
    return bool(requested and network.directed)


def _adjacency(
    network: LinearNetwork,
    *,
    weight: str,
    directed: bool,
) -> sparse.csr_matrix:
    edge_weights = _resolve_weight(network, weight)
    entries: dict[tuple[int, int], float] = {}
    for u, v, value in zip(
        network.edge_u, network.edge_v, edge_weights, strict=True
    ):
        pair = (int(u), int(v))
        entries[pair] = min(entries.get(pair, np.inf), float(value))
        if not directed:
            reverse = (int(v), int(u))
            entries[reverse] = min(entries.get(reverse, np.inf), float(value))
    rows = np.fromiter((pair[0] for pair in entries), dtype=np.int64)
    columns = np.fromiter((pair[1] for pair in entries), dtype=np.int64)
    values = np.fromiter(entries.values(), dtype=float)
    return sparse.csr_matrix(
        (values, (rows, columns)), shape=(network.n_nodes, network.n_nodes)
    )


@dataclass(frozen=True)
class NetworkLocations:
    """Immutable positions represented by edge indices and along-edge offsets."""

    location_ids: np.ndarray
    edge_indices: np.ndarray
    offsets: np.ndarray
    network_fingerprint: str
    kind: str = "location"

    def __post_init__(self) -> None:
        location_ids = readonly_array(
            self.location_ids, ndim=1, name="location_ids"
        )
        n_locations = location_ids.shape[0]
        if n_locations == 0:
            raise ValueError("NetworkLocations must contain at least one location.")
        _unique(location_ids, name="location_ids")
        edge_indices = readonly_array(
            self.edge_indices, dtype=np.int64, ndim=1, name="edge_indices"
        )
        offsets = readonly_array(self.offsets, dtype=float, ndim=1, name="offsets")
        if edge_indices.shape[0] != n_locations or offsets.shape[0] != n_locations:
            raise ValueError("edge_indices and offsets must contain one value per location.")
        if np.any(edge_indices < 0):
            raise ValueError("edge_indices must be non-negative.")
        if not np.all(np.isfinite(offsets)) or np.any(offsets < 0.0):
            raise ValueError("offsets must be finite and non-negative.")
        fingerprint = str(self.network_fingerprint).strip()
        if not fingerprint:
            raise ValueError("network_fingerprint must be a non-empty string.")
        kind = str(self.kind).strip()
        if not kind:
            raise ValueError("kind must be a non-empty string.")
        object.__setattr__(self, "location_ids", location_ids)
        object.__setattr__(self, "edge_indices", edge_indices)
        object.__setattr__(self, "offsets", offsets)
        object.__setattr__(self, "network_fingerprint", fingerprint)
        object.__setattr__(self, "kind", kind)

    @property
    def n_locations(self) -> int:
        """Number of represented locations."""
        return int(self.location_ids.shape[0])

    @property
    def fingerprint(self) -> str:
        """Deterministic location fingerprint."""
        return stable_fingerprint(
            self.location_ids,
            self.edge_indices,
            self.offsets,
            self.network_fingerprint,
            self.kind,
        )

    def validate(self, network: LinearNetwork) -> DataValidationReport:
        """Validate edge references and offsets against a network."""
        issues: list[DataIssue] = []
        if self.network_fingerprint != network.fingerprint:
            issues.append(
                DataIssue(
                    "error",
                    "network_fingerprint_mismatch",
                    "NetworkLocations were prepared for a different network.",
                )
            )
        if np.any(self.edge_indices >= network.n_edges):
            issues.append(
                DataIssue(
                    "error",
                    "missing_edge_index",
                    "Some locations reference an edge outside the network.",
                )
            )
        else:
            lengths = network.edge_lengths[self.edge_indices]
            outside = int(np.count_nonzero(self.offsets > lengths + 1e-9))
            if outside:
                issues.append(
                    DataIssue(
                        "error",
                        "offset_outside_edge",
                        "Some location offsets exceed their edge lengths.",
                        {"count": outside},
                    )
                )
        return DataValidationReport(
            tuple(issues),
            {"n_locations": self.n_locations, "kind": self.kind},
        )

    def to_frame(self) -> pd.DataFrame:
        """Return locations as a DataFrame."""
        return pd.DataFrame(
            {
                "location_id": self.location_ids,
                "edge_index": self.edge_indices,
                "offset": self.offsets,
                "kind": self.kind,
            }
        )

    @classmethod
    def from_events(cls, events: NetworkEvents) -> "NetworkLocations":
        """Create locations from accepted network events."""
        if not isinstance(events, NetworkEvents):
            raise TypeError("events must be a NetworkEvents instance.")
        return cls(
            location_ids=events.event_ids,
            edge_indices=events.edge_indices,
            offsets=events.offsets,
            network_fingerprint=events.network_fingerprint,
            kind="event",
        )

    @classmethod
    def from_lixels(cls, lixels: LixelSupport) -> "NetworkLocations":
        """Create locations from lixel centres."""
        if not isinstance(lixels, LixelSupport):
            raise TypeError("lixels must be a LixelSupport instance.")
        return cls(
            location_ids=lixels.lixel_ids,
            edge_indices=lixels.edge_indices,
            offsets=lixels.center_offsets,
            network_fingerprint=lixels.network_fingerprint,
            kind="lixel_center",
        )


@dataclass(frozen=True)
class NetworkDistanceAsset:
    """Sparse finite distances between two network-location collections.

    Explicit coordinate arrays are used instead of a sparse matrix so that
    reachable zero-distance pairs remain distinguishable from omitted,
    unreachable pairs.
    """

    source_ids: np.ndarray
    target_ids: np.ndarray
    row_indices: np.ndarray
    column_indices: np.ndarray
    distances: np.ndarray
    network_fingerprint: str
    source_fingerprint: str
    target_fingerprint: str
    weight: str
    directed: bool
    cutoff: float | None = None
    metadata: Mapping[str, Any] = MappingProxyType({})

    def __post_init__(self) -> None:
        source_ids = readonly_array(self.source_ids, ndim=1, name="source_ids")
        target_ids = readonly_array(self.target_ids, ndim=1, name="target_ids")
        if source_ids.shape[0] == 0 or target_ids.shape[0] == 0:
            raise ValueError("source_ids and target_ids must be non-empty.")
        _unique(source_ids, name="source_ids")
        _unique(target_ids, name="target_ids")
        rows = readonly_array(
            self.row_indices, dtype=np.int64, ndim=1, name="row_indices"
        )
        columns = readonly_array(
            self.column_indices, dtype=np.int64, ndim=1, name="column_indices"
        )
        distances = readonly_array(
            self.distances, dtype=float, ndim=1, name="distances"
        )
        if rows.shape != columns.shape or rows.shape != distances.shape:
            raise ValueError("row_indices, column_indices, and distances must align.")
        if np.any(rows < 0) or np.any(rows >= source_ids.shape[0]):
            raise ValueError("row_indices contain an out-of-range source index.")
        if np.any(columns < 0) or np.any(columns >= target_ids.shape[0]):
            raise ValueError("column_indices contain an out-of-range target index.")
        if not np.all(np.isfinite(distances)) or np.any(distances < 0.0):
            raise ValueError("distances must be finite and non-negative.")
        pairs = list(zip(rows.tolist(), columns.tolist(), strict=True))
        if len(pairs) != len(set(pairs)):
            raise ValueError("distance coordinate pairs must be unique.")
        if not isinstance(self.directed, (bool, np.bool_)):
            raise TypeError("directed must be boolean.")
        weight = str(self.weight).strip().lower()
        if weight not in {"length", "cost"}:
            raise ValueError("weight must be either 'length' or 'cost'.")
        cutoff = self.cutoff
        if cutoff is not None:
            cutoff = float(cutoff)
            if not np.isfinite(cutoff) or cutoff < 0.0:
                raise ValueError("cutoff must be finite and non-negative or None.")
            if np.any(distances > cutoff + 1e-12):
                raise ValueError("distances exceed the declared cutoff.")
        for name, value in (
            ("network_fingerprint", self.network_fingerprint),
            ("source_fingerprint", self.source_fingerprint),
            ("target_fingerprint", self.target_fingerprint),
        ):
            if not str(value).strip():
                raise ValueError(f"{name} must be a non-empty string.")
        order = np.lexsort((columns, rows))
        object.__setattr__(self, "source_ids", source_ids)
        object.__setattr__(self, "target_ids", target_ids)
        object.__setattr__(self, "row_indices", readonly_array(rows[order]))
        object.__setattr__(self, "column_indices", readonly_array(columns[order]))
        object.__setattr__(self, "distances", readonly_array(distances[order]))
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "directed", bool(self.directed))
        object.__setattr__(self, "cutoff", cutoff)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def shape(self) -> tuple[int, int]:
        """Full source-by-target matrix shape."""
        return (int(self.source_ids.shape[0]), int(self.target_ids.shape[0]))

    @property
    def n_pairs(self) -> int:
        """Number of finite stored source-target pairs."""
        return int(self.distances.shape[0])

    @property
    def density(self) -> float:
        """Fraction of full matrix entries represented by finite pairs."""
        return float(self.n_pairs / (self.shape[0] * self.shape[1]))

    @property
    def fingerprint(self) -> str:
        """Deterministic distance-asset fingerprint."""
        return stable_fingerprint(
            self.source_ids,
            self.target_ids,
            self.row_indices,
            self.column_indices,
            self.distances,
            self.network_fingerprint,
            self.source_fingerprint,
            self.target_fingerprint,
            self.weight,
            self.directed,
            self.cutoff,
            dict(self.metadata),
        )

    def to_dense(self, *, fill_value: float = np.inf) -> np.ndarray:
        """Return a dense matrix, filling omitted pairs with ``fill_value``."""
        if not np.isfinite(fill_value) and not np.isinf(fill_value):
            raise ValueError("fill_value must be finite or infinite.")
        matrix = np.full(self.shape, float(fill_value), dtype=float)
        matrix[self.row_indices, self.column_indices] = self.distances
        return matrix

    def neighbors(self, source_index: int) -> tuple[np.ndarray, np.ndarray]:
        """Return target indices and distances for one source row."""
        if isinstance(source_index, bool) or not isinstance(
            source_index, (int, np.integer)
        ):
            raise TypeError("source_index must be an integer.")
        index = int(source_index)
        if index < 0 or index >= self.shape[0]:
            raise IndexError("source_index is outside the distance asset.")
        selected = self.row_indices == index
        return self.column_indices[selected], self.distances[selected]

    def to_frame(self) -> pd.DataFrame:
        """Return stored finite pairs as a DataFrame."""
        return pd.DataFrame(
            {
                "source_index": self.row_indices,
                "source_id": self.source_ids[self.row_indices],
                "target_index": self.column_indices,
                "target_id": self.target_ids[self.column_indices],
                "distance": self.distances,
            }
        )

    def validate(
        self,
        network: LinearNetwork,
        *,
        sources: NetworkLocations | None = None,
        targets: NetworkLocations | None = None,
    ) -> DataValidationReport:
        """Validate network and optional location fingerprints."""
        issues: list[DataIssue] = []
        if self.network_fingerprint != network.fingerprint:
            issues.append(
                DataIssue(
                    "error",
                    "network_fingerprint_mismatch",
                    "The distance asset belongs to a different network.",
                )
            )
        if sources is not None and self.source_fingerprint != sources.fingerprint:
            issues.append(
                DataIssue(
                    "error",
                    "source_fingerprint_mismatch",
                    "The distance asset belongs to different source locations.",
                )
            )
        if targets is not None and self.target_fingerprint != targets.fingerprint:
            issues.append(
                DataIssue(
                    "error",
                    "target_fingerprint_mismatch",
                    "The distance asset belongs to different target locations.",
                )
            )
        return DataValidationReport(
            tuple(issues),
            {
                "shape": self.shape,
                "n_pairs": self.n_pairs,
                "density": self.density,
                "cutoff": self.cutoff,
            },
        )


@dataclass(frozen=True)
class TraversalState:
    """One oriented edge portion reached by a truncated node traversal."""

    edge_index: int
    edge_id: Any
    from_node_index: int
    to_node_index: int
    reversed: bool
    start_distance: float
    end_distance: float
    reached_fraction: float


@dataclass(frozen=True)
class TraversalResult:
    """Node distances and oriented edge states from a truncated traversal."""

    source_node_id: Any
    source_node_index: int
    cutoff: float
    directed: bool
    weight: str
    node_distances: np.ndarray
    states: tuple[TraversalState, ...]
    network_fingerprint: str

    def __post_init__(self) -> None:
        cutoff = float(self.cutoff)
        if not np.isfinite(cutoff) or cutoff < 0.0:
            raise ValueError("cutoff must be finite and non-negative.")
        distances = readonly_array(
            self.node_distances, dtype=float, ndim=1, name="node_distances"
        )
        if np.any(distances < 0.0):
            raise ValueError("finite node distances must be non-negative.")
        object.__setattr__(self, "cutoff", cutoff)
        object.__setattr__(self, "node_distances", distances)
        object.__setattr__(self, "states", tuple(self.states))

    @property
    def fingerprint(self) -> str:
        """Deterministic traversal fingerprint."""
        return stable_fingerprint(
            self.source_node_id,
            self.source_node_index,
            self.cutoff,
            self.directed,
            self.weight,
            self.node_distances,
            self.states,
            self.network_fingerprint,
        )

    def to_frame(self) -> pd.DataFrame:
        """Return reached oriented edge portions as a DataFrame."""
        return pd.DataFrame(
            [
                {
                    "edge_index": state.edge_index,
                    "edge_id": state.edge_id,
                    "from_node_index": state.from_node_index,
                    "to_node_index": state.to_node_index,
                    "reversed": state.reversed,
                    "start_distance": state.start_distance,
                    "end_distance": state.end_distance,
                    "reached_fraction": state.reached_fraction,
                }
                for state in self.states
            ]
        )


def _position_weight(
    network: LinearNetwork,
    edge_weights: np.ndarray,
    edge_index: int,
    offset: float,
) -> float:
    fraction = float(offset / network.edge_lengths[edge_index])
    return fraction * float(edge_weights[edge_index])


def _departure_options(
    network: LinearNetwork,
    edge_weights: np.ndarray,
    edge_index: int,
    offset: float,
    *,
    directed: bool,
) -> tuple[tuple[int, float], ...]:
    u = int(network.edge_u[edge_index])
    v = int(network.edge_v[edge_index])
    total = float(edge_weights[edge_index])
    position = _position_weight(network, edge_weights, edge_index, offset)
    tolerance = max(1e-12, total * 1e-12)
    if position <= tolerance:
        return ((u, 0.0),)
    if total - position <= tolerance:
        return ((v, 0.0),)
    if directed:
        return ((v, total - position),)
    return ((u, position), (v, total - position))


def _arrival_options(
    network: LinearNetwork,
    edge_weights: np.ndarray,
    edge_index: int,
    offset: float,
    *,
    directed: bool,
) -> tuple[tuple[int, float], ...]:
    u = int(network.edge_u[edge_index])
    v = int(network.edge_v[edge_index])
    total = float(edge_weights[edge_index])
    position = _position_weight(network, edge_weights, edge_index, offset)
    tolerance = max(1e-12, total * 1e-12)
    if position <= tolerance:
        return ((u, 0.0),)
    if total - position <= tolerance:
        return ((v, 0.0),)
    if directed:
        return ((u, position),)
    return ((u, position), (v, total - position))


def build_network_distance_asset(
    network: LinearNetwork,
    sources: NetworkLocations,
    targets: NetworkLocations,
    *,
    cutoff: float | None = None,
    weight: str = "length",
    directed: bool | None = None,
) -> NetworkDistanceAsset:
    """Build exact sparse network distances between arbitrary edge locations.

    Along-edge offsets are converted proportionally when ``weight="cost"``.
    Same-edge direct travel is considered explicitly, while all other routes
    combine endpoint offsets with node shortest paths.
    """
    if not isinstance(network, LinearNetwork):
        raise TypeError("network must be a LinearNetwork instance.")
    if not isinstance(sources, NetworkLocations):
        raise TypeError("sources must be a NetworkLocations instance.")
    if not isinstance(targets, NetworkLocations):
        raise TypeError("targets must be a NetworkLocations instance.")
    sources.validate(network).raise_for_errors()
    targets.validate(network).raise_for_errors()
    if cutoff is not None:
        cutoff = float(cutoff)
        if not np.isfinite(cutoff) or cutoff < 0.0:
            raise ValueError("cutoff must be finite and non-negative or None.")
    effective_directed = _resolve_directed(network, directed)
    edge_weights = _resolve_weight(network, weight)

    departure = [
        _departure_options(
            network,
            edge_weights,
            int(edge_index),
            float(offset),
            directed=effective_directed,
        )
        for edge_index, offset in zip(
            sources.edge_indices, sources.offsets, strict=True
        )
    ]
    arrival = [
        _arrival_options(
            network,
            edge_weights,
            int(edge_index),
            float(offset),
            directed=effective_directed,
        )
        for edge_index, offset in zip(
            targets.edge_indices, targets.offsets, strict=True
        )
    ]
    source_nodes = np.asarray(
        sorted({node for options in departure for node, _ in options}), dtype=np.int64
    )
    matrix = _adjacency(
        network,
        weight=weight,
        directed=effective_directed,
    )
    limit = np.inf if cutoff is None else cutoff
    node_distances = np.asarray(
        dijkstra(
            matrix,
            directed=effective_directed,
            indices=source_nodes,
            limit=limit,
        ),
        dtype=float,
    )
    node_distances = np.atleast_2d(node_distances)
    source_node_rows = {
        int(node): row for row, node in enumerate(source_nodes.tolist())
    }

    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    for source_index in range(sources.n_locations):
        source_edge = int(sources.edge_indices[source_index])
        source_position = _position_weight(
            network,
            edge_weights,
            source_edge,
            float(sources.offsets[source_index]),
        )
        for target_index in range(targets.n_locations):
            target_edge = int(targets.edge_indices[target_index])
            target_position = _position_weight(
                network,
                edge_weights,
                target_edge,
                float(targets.offsets[target_index]),
            )
            best = np.inf
            if source_edge == target_edge:
                if not effective_directed:
                    best = abs(target_position - source_position)
                elif target_position >= source_position:
                    best = target_position - source_position
            for source_node, source_extra in departure[source_index]:
                distance_row = node_distances[source_node_rows[source_node]]
                for target_node, target_extra in arrival[target_index]:
                    node_distance = float(distance_row[target_node])
                    if np.isfinite(node_distance):
                        best = min(best, source_extra + node_distance + target_extra)
            if np.isfinite(best) and (cutoff is None or best <= cutoff + 1e-12):
                rows.append(source_index)
                columns.append(target_index)
                values.append(max(0.0, float(best)))

    return NetworkDistanceAsset(
        source_ids=sources.location_ids,
        target_ids=targets.location_ids,
        row_indices=np.asarray(rows, dtype=np.int64),
        column_indices=np.asarray(columns, dtype=np.int64),
        distances=np.asarray(values, dtype=float),
        network_fingerprint=network.fingerprint,
        source_fingerprint=sources.fingerprint,
        target_fingerprint=targets.fingerprint,
        weight=weight,
        directed=effective_directed,
        cutoff=cutoff,
        metadata={
            "n_nodes_used_as_sources": int(source_nodes.shape[0]),
            "omitted_pairs_are_unreachable_or_beyond_cutoff": True,
        },
    )


def build_event_lixel_distances(
    network: LinearNetwork,
    events: NetworkEvents,
    lixels: LixelSupport,
    *,
    cutoff: float | None = None,
    weight: str = "length",
    directed: bool | None = None,
) -> NetworkDistanceAsset:
    """Build reusable exact distances from accepted events to lixel centres."""
    return build_network_distance_asset(
        network,
        NetworkLocations.from_events(events),
        NetworkLocations.from_lixels(lixels),
        cutoff=cutoff,
        weight=weight,
        directed=directed,
    )


def truncated_traversal(
    network: LinearNetwork,
    source_node_id: Any,
    *,
    cutoff: float,
    weight: str = "length",
    directed: bool | None = None,
) -> TraversalResult:
    """Traverse explicit edge records within a node-distance cutoff.

    Parallel edges are retained as separate states. Undirected traversal emits
    both orientations of each reachable edge. A state may represent only a
    fraction of an edge when the cutoff falls inside that edge.
    """
    if not isinstance(network, LinearNetwork):
        raise TypeError("network must be a LinearNetwork instance.")
    cutoff_value = float(cutoff)
    if not np.isfinite(cutoff_value) or cutoff_value < 0.0:
        raise ValueError("cutoff must be finite and non-negative.")
    try:
        source_index = int(network.node_index[source_node_id])
    except KeyError as exc:
        raise KeyError(f"Unknown source node identifier: {source_node_id!r}.") from exc
    effective_directed = _resolve_directed(network, directed)
    edge_weights = _resolve_weight(network, weight)
    matrix = _adjacency(
        network,
        weight=weight,
        directed=effective_directed,
    )
    node_distances = np.asarray(
        dijkstra(
            matrix,
            directed=effective_directed,
            indices=source_index,
            limit=cutoff_value,
        ),
        dtype=float,
    )
    states: list[TraversalState] = []
    for edge_index in range(network.n_edges):
        orientations = [
            (
                int(network.edge_u[edge_index]),
                int(network.edge_v[edge_index]),
                False,
            )
        ]
        if not effective_directed:
            orientations.append(
                (
                    int(network.edge_v[edge_index]),
                    int(network.edge_u[edge_index]),
                    True,
                )
            )
        edge_weight = float(edge_weights[edge_index])
        for from_node, to_node, reversed_state in orientations:
            start = float(node_distances[from_node])
            if not np.isfinite(start) or start >= cutoff_value:
                continue
            reached = min(edge_weight, cutoff_value - start)
            if reached <= 0.0:
                continue
            states.append(
                TraversalState(
                    edge_index=edge_index,
                    edge_id=network.edge_ids[edge_index],
                    from_node_index=from_node,
                    to_node_index=to_node,
                    reversed=reversed_state,
                    start_distance=start,
                    end_distance=start + reached,
                    reached_fraction=reached / edge_weight,
                )
            )
    states.sort(
        key=lambda state: (
            state.start_distance,
            state.edge_index,
            state.reversed,
            state.to_node_index,
        )
    )
    return TraversalResult(
        source_node_id=source_node_id,
        source_node_index=source_index,
        cutoff=cutoff_value,
        directed=effective_directed,
        weight=str(weight).strip().lower(),
        node_distances=node_distances,
        states=tuple(states),
        network_fingerprint=network.fingerprint,
    )
