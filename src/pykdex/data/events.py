# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Immutable spatial event data objects.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np
import pandas as pd

from pykdex.data._utils import (
    normalize_crs,
    normalize_names,
    normalize_unit,
    readonly_array,
    stable_fingerprint,
)
from pykdex.data.provenance import DataProvenance
from pykdex.data.validation import DataIssue, DataValidationReport


@dataclass(frozen=True)
class SpatialEvents:
    """A validated, immutable collection of weighted spatial events.

    Args:
        coordinates: Event coordinates with shape ``(n_events, dimension)``.
        weights: Optional non-negative event weights. Defaults to one.
        ids: Optional unique event identifiers.
        coordinate_names: Optional coordinate column names.
        crs: Optional coordinate reference system label.
        spatial_unit: Optional coordinate unit label.
        marks: Optional one-dimensional event labels.
        provenance: Source and transformation metadata.
    """

    coordinates: np.ndarray
    weights: np.ndarray | None = None
    ids: np.ndarray | None = None
    coordinate_names: tuple[str, ...] | None = None
    crs: str | None = None
    spatial_unit: str | None = None
    marks: np.ndarray | None = None
    provenance: DataProvenance = field(default_factory=DataProvenance)

    def __post_init__(self) -> None:
        coordinates = readonly_array(
            self.coordinates,
            dtype=float,
            ndim=2,
            name="coordinates",
        )
        if coordinates.shape[0] == 0 or coordinates.shape[1] == 0:
            raise ValueError(
                "coordinates must contain at least one event and dimension."
            )
        if not np.all(np.isfinite(coordinates)):
            raise ValueError("coordinates must contain only finite values.")
        n_events, dimension = coordinates.shape

        if self.weights is None:
            weights = readonly_array(
                np.ones(n_events, dtype=float), ndim=1, name="weights"
            )
        else:
            weights = readonly_array(
                self.weights,
                dtype=float,
                ndim=1,
                name="weights",
            )
        if weights.shape[0] != n_events:
            raise ValueError("weights must contain one value per event.")
        if not np.all(np.isfinite(weights)) or np.any(weights < 0.0):
            raise ValueError("weights must be finite and non-negative.")
        if not np.any(weights > 0.0):
            raise ValueError("weights must contain at least one positive value.")

        if self.ids is None:
            ids = readonly_array(
                np.arange(n_events, dtype=np.int64), ndim=1, name="ids"
            )
        else:
            ids = readonly_array(self.ids, ndim=1, name="ids")
        if ids.shape[0] != n_events:
            raise ValueError("ids must contain one value per event.")
        if len({repr(value) for value in ids.tolist()}) != n_events:
            raise ValueError("ids must be unique.")

        marks = None
        if self.marks is not None:
            marks = readonly_array(self.marks, ndim=1, name="marks")
            if marks.shape[0] != n_events:
                raise ValueError("marks must contain one value per event.")

        object.__setattr__(self, "coordinates", coordinates)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "ids", ids)
        object.__setattr__(
            self,
            "coordinate_names",
            normalize_names(self.coordinate_names, dimension=dimension),
        )
        object.__setattr__(self, "crs", normalize_crs(self.crs))
        object.__setattr__(
            self,
            "spatial_unit",
            normalize_unit(self.spatial_unit, name="spatial_unit"),
        )
        object.__setattr__(self, "marks", marks)

    @property
    def n_events(self) -> int:
        """Number of events."""
        return int(self.coordinates.shape[0])

    @property
    def dimension(self) -> int:
        """Coordinate dimension."""
        return int(self.coordinates.shape[1])

    @property
    def weight_sum(self) -> float:
        """Total event weight."""
        assert self.weights is not None
        return float(np.sum(self.weights))

    @property
    def fingerprint(self) -> str:
        """Deterministic content fingerprint."""
        return stable_fingerprint(
            self.coordinates,
            self.weights,
            self.ids,
            self.coordinate_names,
            self.crs,
            self.spatial_unit,
            self.marks,
            self.provenance.fingerprint,
        )

    def validate(self) -> DataValidationReport:
        """Return non-fatal quality warnings and descriptive statistics."""
        unique_coordinates = np.unique(self.coordinates, axis=0).shape[0]
        duplicate_count = self.n_events - unique_coordinates
        issues: list[DataIssue] = []
        if duplicate_count:
            issues.append(
                DataIssue(
                    "warning",
                    "duplicate_coordinates",
                    "Multiple events share identical coordinates.",
                    {"duplicate_event_count": duplicate_count},
                )
            )
        if self.crs is None:
            issues.append(
                DataIssue(
                    "warning",
                    "missing_crs",
                    "No CRS is attached; bandwidths are interpreted in raw coordinate units.",
                )
            )
        return DataValidationReport(
            tuple(issues),
            {
                "n_events": self.n_events,
                "dimension": self.dimension,
                "weight_sum": self.weight_sum,
                "duplicate_event_count": duplicate_count,
            },
        )

    def to_frame(self) -> pd.DataFrame:
        """Return event attributes as a pandas DataFrame."""
        names = self.coordinate_names or tuple(
            f"coord_{index}" for index in range(self.dimension)
        )
        frame = pd.DataFrame(self.coordinates, columns=list(names))
        frame.insert(0, "event_id", self.ids)
        frame["weight"] = self.weights
        if self.marks is not None:
            frame["mark"] = self.marks
        return frame

    def to_geodataframe(self) -> Any:
        """Return a GeoDataFrame for one- or two-dimensional coordinates."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "GeoDataFrame export requires the 'geo' optional dependencies."
            ) from exc
        if self.dimension > 2:
            raise ValueError("GeoDataFrame export supports at most two dimensions.")
        if self.dimension == 1:
            geometry = [Point(float(x), 0.0) for x in self.coordinates[:, 0]]
        else:
            geometry = [Point(float(x), float(y)) for x, y in self.coordinates]
        return gpd.GeoDataFrame(self.to_frame(), geometry=geometry, crs=self.crs)

    @classmethod
    def from_array(
        cls,
        coordinates: Any,
        *,
        weights: Any | None = None,
        ids: Any | None = None,
        coordinate_names: Iterable[str] | None = None,
        crs: Any | None = None,
        spatial_unit: str | None = None,
        marks: Any | None = None,
        provenance: DataProvenance | None = None,
    ) -> "SpatialEvents":
        """Construct events from array-like coordinates."""
        return cls(
            coordinates=np.asarray(coordinates),
            weights=None if weights is None else np.asarray(weights),
            ids=None if ids is None else np.asarray(ids),
            coordinate_names=(
                None if coordinate_names is None else tuple(coordinate_names)
            ),
            crs=normalize_crs(crs),
            spatial_unit=spatial_unit,
            marks=None if marks is None else np.asarray(marks),
            provenance=provenance or DataProvenance(),
        )

    @classmethod
    def from_dataframe(
        cls,
        frame: pd.DataFrame,
        *,
        coordinate_columns: Iterable[str],
        weight_column: str | None = None,
        id_column: str | None = None,
        mark_column: str | None = None,
        crs: Any | None = None,
        spatial_unit: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "SpatialEvents":
        """Construct events from named DataFrame columns."""
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("frame must be a pandas DataFrame.")
        columns = tuple(coordinate_columns)
        if not columns:
            raise ValueError("coordinate_columns must contain at least one column.")
        missing = [column for column in columns if column not in frame.columns]
        for optional in (weight_column, id_column, mark_column):
            if optional is not None and optional not in frame.columns:
                missing.append(optional)
        if missing:
            raise ValueError(f"DataFrame is missing columns: {sorted(set(missing))}.")
        return cls(
            coordinates=frame.loc[:, list(columns)].to_numpy(),
            weights=(
                None if weight_column is None else frame[weight_column].to_numpy()
            ),
            ids=None if id_column is None else frame[id_column].to_numpy(),
            coordinate_names=columns,
            crs=normalize_crs(crs),
            spatial_unit=spatial_unit,
            marks=None if mark_column is None else frame[mark_column].to_numpy(),
            provenance=provenance or DataProvenance(),
        )

    @classmethod
    def from_geodataframe(
        cls,
        frame: Any,
        *,
        weight_column: str | None = None,
        id_column: str | None = None,
        mark_column: str | None = None,
        spatial_unit: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "SpatialEvents":
        """Construct events from a point GeoDataFrame."""
        try:
            import geopandas as gpd
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "GeoDataFrame input requires the 'geo' optional dependencies."
            ) from exc
        if not isinstance(frame, gpd.GeoDataFrame):
            raise TypeError("frame must be a GeoDataFrame.")
        if frame.empty:
            raise ValueError("frame must contain at least one event.")
        if frame.geometry.isna().any() or frame.geometry.is_empty.any():
            raise ValueError("event geometries must be non-empty points.")
        if not frame.geometry.geom_type.eq("Point").all():
            raise ValueError("event geometries must all be Point geometries.")
        coordinates = np.column_stack([frame.geometry.x, frame.geometry.y])
        return cls(
            coordinates=coordinates,
            weights=(
                None if weight_column is None else frame[weight_column].to_numpy()
            ),
            ids=None if id_column is None else frame[id_column].to_numpy(),
            coordinate_names=("x", "y"),
            crs=normalize_crs(frame.crs),
            spatial_unit=spatial_unit,
            marks=None if mark_column is None else frame[mark_column].to_numpy(),
            provenance=provenance or DataProvenance(),
        )
