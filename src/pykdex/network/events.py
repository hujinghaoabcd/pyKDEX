# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Events constrained to a geometric linear network.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
import pandas as pd

from pykdex.data import DataProvenance, SpatialEvents
from pykdex.data._utils import (
    normalize_crs,
    normalize_unit,
    readonly_array,
    stable_fingerprint,
)
from pykdex.data.validation import DataIssue, DataValidationReport
from pykdex.network.linear_network import LinearNetwork


def _require_shapely() -> tuple[Any, Any]:
    try:
        from shapely.geometry import Point
        from shapely.strtree import STRtree
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Network event snapping requires the 'network' optional dependencies."
        ) from exc
    return Point, STRtree


@dataclass(frozen=True)
class NetworkEvents:
    """Immutable events represented by an edge and an along-edge offset."""

    event_ids: np.ndarray
    edge_indices: np.ndarray
    edge_ids: np.ndarray
    offsets: np.ndarray
    coordinates: np.ndarray
    original_coordinates: np.ndarray
    weights: np.ndarray
    snap_distances: np.ndarray
    snap_status: np.ndarray
    network_fingerprint: str
    crs: str | None = None
    spatial_unit: str | None = None
    marks: np.ndarray | None = None
    provenance: DataProvenance = field(default_factory=DataProvenance)

    def __post_init__(self) -> None:
        event_ids = readonly_array(self.event_ids, ndim=1, name="event_ids")
        n_events = event_ids.shape[0]
        if n_events == 0:
            raise ValueError("NetworkEvents must contain at least one accepted event.")
        if len({repr(value) for value in event_ids.tolist()}) != n_events:
            raise ValueError("event_ids must be unique.")
        edge_indices = readonly_array(
            self.edge_indices, dtype=np.int64, ndim=1, name="edge_indices"
        )
        edge_ids = readonly_array(self.edge_ids, ndim=1, name="edge_ids")
        offsets = readonly_array(self.offsets, dtype=float, ndim=1, name="offsets")
        coordinates = readonly_array(
            self.coordinates, dtype=float, ndim=2, name="coordinates"
        )
        original = readonly_array(
            self.original_coordinates,
            dtype=float,
            ndim=2,
            name="original_coordinates",
        )
        weights = readonly_array(self.weights, dtype=float, ndim=1, name="weights")
        distances = readonly_array(
            self.snap_distances, dtype=float, ndim=1, name="snap_distances"
        )
        status = readonly_array(self.snap_status, ndim=1, name="snap_status")
        for name, array in (
            ("edge_indices", edge_indices),
            ("edge_ids", edge_ids),
            ("offsets", offsets),
            ("weights", weights),
            ("snap_distances", distances),
            ("snap_status", status),
        ):
            if array.shape[0] != n_events:
                raise ValueError(f"{name} must contain one value per event.")
        if coordinates.shape != (n_events, 2) or original.shape != (n_events, 2):
            raise ValueError("event coordinates must have shape (n_events, 2).")
        if np.any(edge_indices < 0):
            raise ValueError("edge_indices must be non-negative.")
        if not np.all(np.isfinite(offsets)) or np.any(offsets < 0.0):
            raise ValueError("offsets must be finite and non-negative.")
        if not np.all(np.isfinite(coordinates)) or not np.all(np.isfinite(original)):
            raise ValueError("coordinates must contain only finite values.")
        if not np.all(np.isfinite(weights)) or np.any(weights < 0.0):
            raise ValueError("weights must be finite and non-negative.")
        if not np.any(weights > 0.0):
            raise ValueError("weights must contain at least one positive value.")
        if not np.all(np.isfinite(distances)) or np.any(distances < 0.0):
            raise ValueError("snap_distances must be finite and non-negative.")
        fingerprint = str(self.network_fingerprint).strip()
        if not fingerprint:
            raise ValueError("network_fingerprint must be a non-empty string.")
        marks = None
        if self.marks is not None:
            marks = readonly_array(self.marks, ndim=1, name="marks")
            if marks.shape[0] != n_events:
                raise ValueError("marks must contain one value per event.")
        object.__setattr__(self, "event_ids", event_ids)
        object.__setattr__(self, "edge_indices", edge_indices)
        object.__setattr__(self, "edge_ids", edge_ids)
        object.__setattr__(self, "offsets", offsets)
        object.__setattr__(self, "coordinates", coordinates)
        object.__setattr__(self, "original_coordinates", original)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "snap_distances", distances)
        object.__setattr__(self, "snap_status", status)
        object.__setattr__(self, "network_fingerprint", fingerprint)
        object.__setattr__(self, "crs", normalize_crs(self.crs))
        object.__setattr__(
            self,
            "spatial_unit",
            normalize_unit(self.spatial_unit, name="spatial_unit"),
        )
        object.__setattr__(self, "marks", marks)

    @property
    def n_events(self) -> int:
        """Number of accepted network events."""
        return int(self.event_ids.shape[0])

    @property
    def weight_sum(self) -> float:
        """Total accepted event weight."""
        return float(np.sum(self.weights))

    @property
    def fingerprint(self) -> str:
        """Deterministic event and snapping fingerprint."""
        return stable_fingerprint(
            self.event_ids,
            self.edge_indices,
            self.edge_ids,
            self.offsets,
            self.coordinates,
            self.original_coordinates,
            self.weights,
            self.snap_distances,
            self.snap_status,
            self.network_fingerprint,
            self.crs,
            self.spatial_unit,
            self.marks,
            self.provenance.fingerprint,
        )

    def validate(self, network: LinearNetwork) -> DataValidationReport:
        """Validate compatibility and along-edge offsets against a network."""
        issues: list[DataIssue] = []
        if self.network_fingerprint != network.fingerprint:
            issues.append(
                DataIssue(
                    "error",
                    "network_fingerprint_mismatch",
                    "NetworkEvents were prepared for a different network.",
                )
            )
        if np.any(self.edge_indices >= network.n_edges):
            issues.append(
                DataIssue(
                    "error",
                    "missing_edge_index",
                    "Some events reference an edge index outside the network.",
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
                        "Some event offsets exceed their edge lengths.",
                        {"count": outside},
                    )
                )
        if self.crs is not None and network.crs is not None and self.crs != network.crs:
            issues.append(
                DataIssue(
                    "error",
                    "crs_mismatch",
                    "NetworkEvents and network use different CRS labels.",
                )
            )
        return DataValidationReport(
            tuple(issues),
            {
                "n_events": self.n_events,
                "weight_sum": self.weight_sum,
                "max_snap_distance": float(np.max(self.snap_distances)),
                "ambiguous_count": int(
                    np.count_nonzero(self.snap_status == "ambiguous_nearest")
                ),
            },
        )

    def to_frame(self) -> pd.DataFrame:
        """Return accepted network events as a DataFrame."""
        frame = pd.DataFrame(
            {
                "event_id": self.event_ids,
                "edge_id": self.edge_ids,
                "edge_index": self.edge_indices,
                "offset": self.offsets,
                "original_x": self.original_coordinates[:, 0],
                "original_y": self.original_coordinates[:, 1],
                "snapped_x": self.coordinates[:, 0],
                "snapped_y": self.coordinates[:, 1],
                "snap_distance": self.snap_distances,
                "snap_status": self.snap_status,
                "weight": self.weights,
            }
        )
        if self.marks is not None:
            frame["mark"] = self.marks
        return frame

    def to_geodataframe(self) -> Any:
        """Return accepted events with snapped point geometry."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "GeoDataFrame export requires the 'network' optional dependencies."
            ) from exc
        geometry = [Point(float(x), float(y)) for x, y in self.coordinates]
        return gpd.GeoDataFrame(self.to_frame(), geometry=geometry, crs=self.crs)


@dataclass(frozen=True)
class SnapResult:
    """Accepted and rejected records from an auditable snapping operation."""

    events: NetworkEvents | None
    rejected: pd.DataFrame
    report: DataValidationReport
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.events is not None and not isinstance(self.events, NetworkEvents):
            raise TypeError("events must be NetworkEvents or None.")
        if not isinstance(self.rejected, pd.DataFrame):
            raise TypeError("rejected must be a pandas DataFrame.")
        object.__setattr__(self, "rejected", self.rejected.copy(deep=True))
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))

    @property
    def n_accepted(self) -> int:
        """Number of accepted events."""
        return 0 if self.events is None else self.events.n_events

    @property
    def n_rejected(self) -> int:
        """Number of rejected events."""
        return int(self.rejected.shape[0])


def snap_events(
    network: LinearNetwork,
    events: SpatialEvents,
    *,
    max_distance: float | None = None,
    tie_tolerance: float = 1e-9,
    endpoint_tolerance: float = 1e-9,
) -> SnapResult:
    """Snap planar events to their nearest network edges.

    Offsets use the network edge-length scale. The closest position is first
    calculated on the edge geometry and then converted by its fractional
    position, preserving consistency when an explicit edge length differs
    slightly from the geometric length.
    """
    if not isinstance(network, LinearNetwork):
        raise TypeError("network must be a LinearNetwork instance.")
    if not isinstance(events, SpatialEvents) or events.dimension != 2:
        raise TypeError("events must be a two-dimensional SpatialEvents instance.")
    if max_distance is not None and (
        not np.isfinite(max_distance) or max_distance < 0.0
    ):
        raise ValueError("max_distance must be finite and non-negative or None.")
    if not np.isfinite(tie_tolerance) or tie_tolerance < 0.0:
        raise ValueError("tie_tolerance must be finite and non-negative.")
    if not np.isfinite(endpoint_tolerance) or endpoint_tolerance < 0.0:
        raise ValueError("endpoint_tolerance must be finite and non-negative.")
    issues: list[DataIssue] = []
    if events.crs is not None and network.crs is not None and events.crs != network.crs:
        issues.append(
            DataIssue(
                "error",
                "crs_mismatch",
                "Events and network use different CRS labels.",
                {"events": events.crs, "network": network.crs},
            )
        )
    if (
        events.spatial_unit is not None
        and network.spatial_unit is not None
        and events.spatial_unit != network.spatial_unit
    ):
        issues.append(
            DataIssue(
                "error",
                "spatial_unit_mismatch",
                "Events and network use different spatial units.",
                {"events": events.spatial_unit, "network": network.spatial_unit},
            )
        )
    compatibility = DataValidationReport(tuple(issues))
    compatibility.raise_for_errors()

    event_ids = events.ids
    event_weights = events.weights
    assert event_ids is not None
    assert event_weights is not None

    Point, STRtree = _require_shapely()
    tree = STRtree(network.edge_geometries)
    accepted_indices: list[int] = []
    edge_indices: list[int] = []
    offsets: list[float] = []
    snapped_coordinates: list[tuple[float, float]] = []
    snap_distances: list[float] = []
    statuses: list[str] = []
    rejected_rows: list[dict[str, Any]] = []

    for event_index, coordinate in enumerate(events.coordinates):
        point = Point(float(coordinate[0]), float(coordinate[1]))
        candidates, distances = tree.query_nearest(
            point, all_matches=True, return_distance=True
        )
        candidate_indices = np.asarray(candidates, dtype=np.int64).reshape(-1)
        candidate_distances = np.asarray(distances, dtype=float).reshape(-1)
        minimum = float(np.min(candidate_distances))
        tied = candidate_indices[np.abs(candidate_distances - minimum) <= tie_tolerance]
        selected = int(np.min(tied))
        if max_distance is not None and minimum > max_distance:
            rejected_rows.append(
                {
                    "event_id": event_ids[event_index],
                    "x": float(coordinate[0]),
                    "y": float(coordinate[1]),
                    "weight": float(event_weights[event_index]),
                    "reason": "beyond_max_distance",
                    "nearest_distance": minimum,
                    "candidate_count": int(tied.shape[0]),
                }
            )
            continue
        geometry = network.edge_geometries[selected]
        geometric_length = float(geometry.length)
        projected = float(geometry.project(point))
        if geometric_length <= 0.0:
            raise ValueError("network edge geometry has zero length.")
        fraction = min(max(projected / geometric_length, 0.0), 1.0)
        edge_length = float(network.edge_lengths[selected])
        offset = fraction * edge_length
        if offset <= endpoint_tolerance:
            offset = 0.0
            status = "snapped_to_u"
        elif edge_length - offset <= endpoint_tolerance:
            offset = edge_length
            status = "snapped_to_v"
        elif tied.shape[0] > 1:
            status = "ambiguous_nearest"
        else:
            status = "snapped"
        snapped = geometry.interpolate(fraction, normalized=True)
        accepted_indices.append(event_index)
        edge_indices.append(selected)
        offsets.append(offset)
        snapped_coordinates.append((float(snapped.x), float(snapped.y)))
        snap_distances.append(minimum)
        statuses.append(status)

    accepted: NetworkEvents | None = None
    if accepted_indices:
        index = np.asarray(accepted_indices, dtype=np.int64)
        accepted = NetworkEvents(
            event_ids=event_ids[index],
            edge_indices=np.asarray(edge_indices, dtype=np.int64),
            edge_ids=network.edge_ids[np.asarray(edge_indices, dtype=np.int64)],
            offsets=np.asarray(offsets, dtype=float),
            coordinates=np.asarray(snapped_coordinates, dtype=float),
            original_coordinates=events.coordinates[index],
            weights=event_weights[index],
            snap_distances=np.asarray(snap_distances, dtype=float),
            snap_status=np.asarray(statuses, dtype=object),
            network_fingerprint=network.fingerprint,
            crs=network.crs,
            spatial_unit=network.spatial_unit,
            marks=None if events.marks is None else events.marks[index],
            provenance=events.provenance.with_transformation("snapped_to_network"),
        )
    rejected = pd.DataFrame(
        rejected_rows,
        columns=[
            "event_id",
            "x",
            "y",
            "weight",
            "reason",
            "nearest_distance",
            "candidate_count",
        ],
    )
    report_issues: list[DataIssue] = []
    if rejected_rows:
        report_issues.append(
            DataIssue(
                "warning",
                "events_rejected",
                "Some events exceeded the maximum snapping distance.",
                {"count": len(rejected_rows)},
            )
        )
    ambiguous_count = int(sum(status == "ambiguous_nearest" for status in statuses))
    if ambiguous_count:
        report_issues.append(
            DataIssue(
                "warning",
                "ambiguous_nearest_edges",
                "Some events were equally close to multiple edges; the lowest edge index was selected.",
                {"count": ambiguous_count, "tie_tolerance": tie_tolerance},
            )
        )
    report = DataValidationReport(
        tuple(report_issues),
        {
            "n_input": events.n_events,
            "n_accepted": len(accepted_indices),
            "n_rejected": len(rejected_rows),
            "ambiguous_count": ambiguous_count,
            "max_accepted_distance": (
                None if not snap_distances else float(max(snap_distances))
            ),
        },
    )
    return SnapResult(
        events=accepted,
        rejected=rejected,
        report=report,
        parameters={
            "max_distance": max_distance,
            "tie_tolerance": tie_tolerance,
            "endpoint_tolerance": endpoint_tolerance,
        },
    )
