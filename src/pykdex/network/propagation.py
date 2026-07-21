# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Junction policies and auditable path propagation on linear networks.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd

from pykdex.data._utils import stable_fingerprint
from pykdex.network.linear_network import LinearNetwork


def _validate_direction_count(n_directions: int) -> int:
    if isinstance(n_directions, bool) or not isinstance(
        n_directions, (int, np.integer)
    ):
        raise TypeError("n_directions must be an integer.")
    count = int(n_directions)
    if count < 0:
        raise ValueError("n_directions must be non-negative.")
    return count


def _validate_reverse_index(reverse_index: int | None, count: int) -> int | None:
    if reverse_index is None:
        return None
    if isinstance(reverse_index, bool) or not isinstance(
        reverse_index, (int, np.integer)
    ):
        raise TypeError("reverse_index must be an integer or None.")
    index = int(reverse_index)
    if index < 0 or index >= count:
        raise IndexError("reverse_index is outside the outgoing directions.")
    return index


@runtime_checkable
class JunctionPolicy(Protocol):
    """Protocol controlling how path amplitude changes at network vertices."""

    name: str
    path_based: bool
    supports_directed: bool

    def initial_weights(self, n_directions: int) -> np.ndarray:
        """Return weights for an event located exactly at a vertex."""

    def transition_weights(
        self,
        n_directions: int,
        reverse_index: int | None,
    ) -> np.ndarray:
        """Return weights for directions available after entering a vertex."""


@dataclass(frozen=True)
class SimpleJunctionPolicy:
    """Biased geodesic propagation without mass splitting at vertices."""

    name: str = field(default="simple", init=False)
    path_based: bool = field(default=False, init=False)
    supports_directed: bool = field(default=True, init=False)

    def initial_weights(self, n_directions: int) -> np.ndarray:
        count = _validate_direction_count(n_directions)
        return np.ones(count, dtype=float)

    def transition_weights(
        self,
        n_directions: int,
        reverse_index: int | None,
    ) -> np.ndarray:
        count = _validate_direction_count(n_directions)
        reverse = _validate_reverse_index(reverse_index, count)
        weights = np.ones(count, dtype=float)
        if reverse is not None:
            weights[reverse] = 0.0
        return weights


@dataclass(frozen=True)
class DiscontinuousJunctionPolicy:
    """Equal-split discontinuous propagation with non-backtracking paths."""

    name: str = field(default="discontinuous", init=False)
    path_based: bool = field(default=True, init=False)
    supports_directed: bool = field(default=True, init=False)

    def initial_weights(self, n_directions: int) -> np.ndarray:
        count = _validate_direction_count(n_directions)
        if count == 0:
            return np.empty(0, dtype=float)
        return np.full(count, 2.0 / count, dtype=float)

    def transition_weights(
        self,
        n_directions: int,
        reverse_index: int | None,
    ) -> np.ndarray:
        count = _validate_direction_count(n_directions)
        reverse = _validate_reverse_index(reverse_index, count)
        if count == 0:
            return np.empty(0, dtype=float)
        if reverse is None:
            return np.full(count, 1.0 / count, dtype=float)
        if count == 1:
            return np.zeros(1, dtype=float)
        weights = np.full(count, 1.0 / (count - 1), dtype=float)
        weights[reverse] = 0.0
        return weights


@dataclass(frozen=True)
class ContinuousJunctionPolicy:
    r"""Equal-split continuous propagation using vertex scattering weights.

    At a vertex of degree :math:`d`, each transmitted direction receives
    :math:`2/d` and the reflected direction receives :math:`2/d - 1`.
    The signed reflected path is the backward correction that enforces a common
    limiting value on all incident edges.
    """

    name: str = field(default="continuous", init=False)
    path_based: bool = field(default=True, init=False)
    supports_directed: bool = field(default=False, init=False)

    def initial_weights(self, n_directions: int) -> np.ndarray:
        count = _validate_direction_count(n_directions)
        if count == 0:
            return np.empty(0, dtype=float)
        return np.full(count, 2.0 / count, dtype=float)

    def transition_weights(
        self,
        n_directions: int,
        reverse_index: int | None,
    ) -> np.ndarray:
        count = _validate_direction_count(n_directions)
        reverse = _validate_reverse_index(reverse_index, count)
        if count == 0:
            return np.empty(0, dtype=float)
        if reverse is None:
            raise ValueError(
                "Continuous propagation requires an undirected reverse direction."
            )
        weights = np.full(count, 2.0 / count, dtype=float)
        weights[reverse] = 2.0 / count - 1.0
        return weights


_POLICIES: dict[
    str,
    type[SimpleJunctionPolicy]
    | type[DiscontinuousJunctionPolicy]
    | type[ContinuousJunctionPolicy],
] = {
    "simple": SimpleJunctionPolicy,
    "geodesic": SimpleJunctionPolicy,
    "geo": SimpleJunctionPolicy,
    "discontinuous": DiscontinuousJunctionPolicy,
    "equal_split_discontinuous": DiscontinuousJunctionPolicy,
    "esd": DiscontinuousJunctionPolicy,
    "continuous": ContinuousJunctionPolicy,
    "equal_split_continuous": ContinuousJunctionPolicy,
    "esc": ContinuousJunctionPolicy,
}


def get_junction_policy(policy: str | JunctionPolicy) -> JunctionPolicy:
    """Resolve a junction policy from a canonical name or compatible object."""
    if isinstance(policy, JunctionPolicy):
        return policy
    if not isinstance(policy, str) or not policy.strip():
        raise TypeError("junction_policy must be a non-empty string or policy object.")
    name = policy.strip().lower()
    try:
        return _POLICIES[name]()
    except KeyError as exc:
        supported = ", ".join(sorted(_POLICIES))
        raise ValueError(
            f"Unknown junction policy '{policy}'. Supported policies: {supported}."
        ) from exc


@dataclass(frozen=True)
class PropagationRecord:
    """One signed oriented edge interval reached from a network source."""

    source_id: Any
    edge_index: int
    direction: int
    start_offset: float
    end_offset: float
    start_distance: float
    coefficient: float
    depth: int
    include_start: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.edge_index, bool) or not isinstance(
            self.edge_index, (int, np.integer)
        ):
            raise TypeError("edge_index must be an integer.")
        if int(self.edge_index) < 0:
            raise ValueError("edge_index must be non-negative.")
        if self.direction not in (-1, 1):
            raise ValueError("direction must be either -1 or 1.")
        start = float(self.start_offset)
        end = float(self.end_offset)
        distance = float(self.start_distance)
        coefficient = float(self.coefficient)
        if not np.isfinite(start) or not np.isfinite(end):
            raise ValueError("record offsets must be finite.")
        if not np.isfinite(distance) or distance < 0.0:
            raise ValueError("start_distance must be finite and non-negative.")
        if not np.isfinite(coefficient):
            raise ValueError("coefficient must be finite.")
        if isinstance(self.depth, bool) or not isinstance(
            self.depth, (int, np.integer)
        ):
            raise TypeError("depth must be an integer.")
        if int(self.depth) < 0:
            raise ValueError("depth must be non-negative.")
        if not isinstance(self.include_start, (bool, np.bool_)):
            raise TypeError("include_start must be boolean.")
        if self.direction == 1 and end < start:
            raise ValueError("positive-direction records must have end >= start.")
        if self.direction == -1 and end > start:
            raise ValueError("negative-direction records must have end <= start.")
        object.__setattr__(self, "edge_index", int(self.edge_index))
        object.__setattr__(self, "start_offset", start)
        object.__setattr__(self, "end_offset", end)
        object.__setattr__(self, "start_distance", distance)
        object.__setattr__(self, "coefficient", coefficient)
        object.__setattr__(self, "depth", int(self.depth))
        object.__setattr__(self, "include_start", bool(self.include_start))

    @property
    def length(self) -> float:
        """Geometric length represented by the record."""
        return abs(self.end_offset - self.start_offset)

    @property
    def end_distance(self) -> float:
        """Distance from the source to the record endpoint."""
        return self.start_distance + self.length


@dataclass(frozen=True)
class PropagationTrace:
    """Immutable collection of propagation records for one network source."""

    source_id: Any
    cutoff: float
    policy: str
    directed: bool
    records: tuple[PropagationRecord, ...]
    network_fingerprint: str

    def __post_init__(self) -> None:
        cutoff = float(self.cutoff)
        if not np.isfinite(cutoff) or cutoff < 0.0:
            raise ValueError("cutoff must be finite and non-negative.")
        if not isinstance(self.directed, (bool, np.bool_)):
            raise TypeError("directed must be boolean.")
        policy = str(self.policy).strip()
        fingerprint = str(self.network_fingerprint).strip()
        if not policy:
            raise ValueError("policy must be a non-empty string.")
        if not fingerprint:
            raise ValueError("network_fingerprint must be a non-empty string.")
        records = tuple(self.records)
        if any(record.source_id != self.source_id for record in records):
            raise ValueError("all records must share the trace source_id.")
        object.__setattr__(self, "cutoff", cutoff)
        object.__setattr__(self, "policy", policy)
        object.__setattr__(self, "directed", bool(self.directed))
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "network_fingerprint", fingerprint)

    @property
    def n_records(self) -> int:
        """Number of oriented intervals in the trace."""
        return len(self.records)

    @property
    def fingerprint(self) -> str:
        """Deterministic trace fingerprint."""
        return stable_fingerprint(
            self.source_id,
            self.cutoff,
            self.policy,
            self.directed,
            self.records,
            self.network_fingerprint,
        )

    def to_frame(self) -> pd.DataFrame:
        """Return propagation records as a DataFrame."""
        return pd.DataFrame(
            [
                {
                    "source_id": record.source_id,
                    "edge_index": record.edge_index,
                    "direction": record.direction,
                    "start_offset": record.start_offset,
                    "end_offset": record.end_offset,
                    "start_distance": record.start_distance,
                    "end_distance": record.end_distance,
                    "coefficient": record.coefficient,
                    "depth": record.depth,
                    "include_start": record.include_start,
                }
                for record in self.records
            ]
        )


@dataclass(frozen=True)
class _PendingState:
    edge_index: int
    direction: int
    start_offset: float
    start_distance: float
    coefficient: float
    depth: int
    include_start: bool


def _effective_directed(network: LinearNetwork, directed: bool | None) -> bool:
    if directed is not None and not isinstance(directed, (bool, np.bool_)):
        raise TypeError("directed must be boolean or None.")
    requested = network.directed if directed is None else bool(directed)
    return bool(requested and network.directed)


def _outgoing_orientations(
    network: LinearNetwork,
    node_index: int,
    *,
    directed: bool,
) -> tuple[tuple[int, int], ...]:
    orientations: list[tuple[int, int]] = []
    for edge_index in range(network.n_edges):
        u = int(network.edge_u[edge_index])
        v = int(network.edge_v[edge_index])
        if directed:
            if u == node_index:
                orientations.append((edge_index, 1))
            continue
        if u == node_index and v == node_index:
            orientations.append((edge_index, 1))
            orientations.append((edge_index, -1))
        else:
            if u == node_index:
                orientations.append((edge_index, 1))
            if v == node_index:
                orientations.append((edge_index, -1))
    return tuple(orientations)


def _orientation_start(
    network: LinearNetwork, edge_index: int, direction: int
) -> float:
    return 0.0 if direction == 1 else float(network.edge_lengths[edge_index])


def _orientation_end(network: LinearNetwork, edge_index: int, direction: int) -> float:
    return float(network.edge_lengths[edge_index]) if direction == 1 else 0.0


def _orientation_target_node(
    network: LinearNetwork,
    edge_index: int,
    direction: int,
) -> int:
    return (
        int(network.edge_v[edge_index])
        if direction == 1
        else int(network.edge_u[edge_index])
    )


def _initial_states(
    network: LinearNetwork,
    *,
    edge_index: int,
    offset: float,
    policy: JunctionPolicy,
    directed: bool,
) -> tuple[_PendingState, ...]:
    length = float(network.edge_lengths[edge_index])
    tolerance = max(1e-12, length * 1e-12)
    node_index: int | None = None
    if offset <= tolerance:
        node_index = int(network.edge_u[edge_index])
    elif length - offset <= tolerance:
        node_index = int(network.edge_v[edge_index])
    if node_index is not None:
        orientations = _outgoing_orientations(
            network,
            node_index,
            directed=directed,
        )
        weights = policy.initial_weights(len(orientations))
        return tuple(
            _PendingState(
                edge_index=next_edge,
                direction=direction,
                start_offset=_orientation_start(network, next_edge, direction),
                start_distance=0.0,
                coefficient=float(weight),
                depth=0,
                include_start=True,
            )
            for (next_edge, direction), weight in zip(
                orientations, weights, strict=True
            )
            if abs(float(weight)) > 0.0
        )
    if directed:
        return (
            _PendingState(
                edge_index=edge_index,
                direction=1,
                start_offset=offset,
                start_distance=0.0,
                coefficient=1.0,
                depth=0,
                include_start=True,
            ),
        )
    return (
        _PendingState(
            edge_index=edge_index,
            direction=-1,
            start_offset=offset,
            start_distance=0.0,
            coefficient=1.0,
            depth=0,
            include_start=False,
        ),
        _PendingState(
            edge_index=edge_index,
            direction=1,
            start_offset=offset,
            start_distance=0.0,
            coefficient=1.0,
            depth=0,
            include_start=True,
        ),
    )


def trace_network_propagation(
    network: LinearNetwork,
    source_edge_index: int,
    source_offset: float,
    *,
    cutoff: float,
    junction_policy: str | JunctionPolicy = "discontinuous",
    directed: bool | None = None,
    coefficient_tolerance: float = 1e-12,
    max_records: int = 100_000,
    source_id: Any = 0,
) -> PropagationTrace:
    """Trace signed oriented paths from an arbitrary along-edge source.

    The discontinuous policy enumerates finite non-backtracking walks and splits
    amplitude among subsequent directions. The continuous policy additionally
    emits a signed reflected walk at every vertex, implementing the backward
    correction required for continuity.
    """
    if not isinstance(network, LinearNetwork):
        raise TypeError("network must be a LinearNetwork instance.")
    if isinstance(source_edge_index, bool) or not isinstance(
        source_edge_index, (int, np.integer)
    ):
        raise TypeError("source_edge_index must be an integer.")
    edge_index = int(source_edge_index)
    if edge_index < 0 or edge_index >= network.n_edges:
        raise IndexError("source_edge_index is outside the network.")
    offset = float(source_offset)
    length = float(network.edge_lengths[edge_index])
    if not np.isfinite(offset) or offset < 0.0 or offset > length + 1e-12:
        raise ValueError("source_offset must lie within the source edge.")
    offset = min(max(offset, 0.0), length)
    cutoff_value = float(cutoff)
    if not np.isfinite(cutoff_value) or cutoff_value < 0.0:
        raise ValueError("cutoff must be finite and non-negative.")
    tolerance = float(coefficient_tolerance)
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("coefficient_tolerance must be finite and positive.")
    if isinstance(max_records, bool) or not isinstance(max_records, (int, np.integer)):
        raise TypeError("max_records must be a positive integer.")
    record_limit = int(max_records)
    if record_limit <= 0:
        raise ValueError("max_records must be greater than zero.")

    policy = get_junction_policy(junction_policy)
    effective_directed = _effective_directed(network, directed)
    if effective_directed and not policy.supports_directed:
        raise ValueError(
            f"The '{policy.name}' junction policy requires an undirected network."
        )

    queue = deque(
        _initial_states(
            network,
            edge_index=edge_index,
            offset=offset,
            policy=policy,
            directed=effective_directed,
        )
    )
    records: list[PropagationRecord] = []
    distance_tolerance = max(1e-12, cutoff_value * 1e-12)

    while queue:
        state = queue.popleft()
        if abs(state.coefficient) < tolerance:
            continue
        if len(records) >= record_limit:
            raise RuntimeError(
                "Propagation exceeded max_records; reduce bandwidth or increase "
                "max_records explicitly."
            )
        remaining = cutoff_value - state.start_distance
        if remaining < -distance_tolerance:
            continue
        canonical_end = _orientation_end(
            network,
            state.edge_index,
            state.direction,
        )
        full_length = abs(canonical_end - state.start_offset)
        reached = min(full_length, max(0.0, remaining))
        end_offset = state.start_offset + state.direction * reached
        if reached > distance_tolerance or (
            state.depth == 0 and state.include_start and remaining >= 0.0
        ):
            records.append(
                PropagationRecord(
                    source_id=source_id,
                    edge_index=state.edge_index,
                    direction=state.direction,
                    start_offset=state.start_offset,
                    end_offset=end_offset,
                    start_distance=state.start_distance,
                    coefficient=state.coefficient,
                    depth=state.depth,
                    include_start=state.include_start,
                )
            )
        if reached + distance_tolerance < full_length:
            continue
        arrival_distance = state.start_distance + full_length
        if arrival_distance >= cutoff_value - distance_tolerance:
            continue
        node_index = _orientation_target_node(
            network,
            state.edge_index,
            state.direction,
        )
        outgoing = _outgoing_orientations(
            network,
            node_index,
            directed=effective_directed,
        )
        reverse_orientation = (state.edge_index, -state.direction)
        reverse_index = None
        for index, orientation in enumerate(outgoing):
            if orientation == reverse_orientation:
                reverse_index = index
                break
        multipliers = policy.transition_weights(len(outgoing), reverse_index)
        for (next_edge, next_direction), multiplier in zip(
            outgoing,
            multipliers,
            strict=True,
        ):
            next_coefficient = state.coefficient * float(multiplier)
            if abs(next_coefficient) < tolerance:
                continue
            queue.append(
                _PendingState(
                    edge_index=next_edge,
                    direction=next_direction,
                    start_offset=_orientation_start(network, next_edge, next_direction),
                    start_distance=arrival_distance,
                    coefficient=next_coefficient,
                    depth=state.depth + 1,
                    include_start=True,
                )
            )

    return PropagationTrace(
        source_id=source_id,
        cutoff=cutoff_value,
        policy=policy.name,
        directed=effective_directed,
        records=tuple(records),
        network_fingerprint=network.fingerprint,
    )
