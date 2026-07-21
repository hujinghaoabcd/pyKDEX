# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Spatial study-boundary data objects.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from pykdex.data._utils import normalize_crs, normalize_unit, stable_fingerprint
from pykdex.data.provenance import DataProvenance
from pykdex.data.validation import DataIssue, DataValidationReport


@dataclass(frozen=True)
class SpatialBoundary:
    """Polygonal spatial study boundary with CRS and provenance metadata."""

    geometry: Any
    crs: str | None = None
    spatial_unit: str | None = None
    provenance: DataProvenance = field(default_factory=DataProvenance)

    def __post_init__(self) -> None:
        geometry = self.geometry
        if geometry is None or not hasattr(geometry, "geom_type"):
            raise TypeError("geometry must be a Shapely Polygon or MultiPolygon.")
        if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError("geometry must be a Polygon or MultiPolygon.")
        if geometry.is_empty:
            raise ValueError("geometry must not be empty.")
        if not geometry.is_valid:
            raise ValueError("geometry must be valid.")
        object.__setattr__(self, "crs", normalize_crs(self.crs))
        object.__setattr__(
            self,
            "spatial_unit",
            normalize_unit(self.spatial_unit, name="spatial_unit"),
        )

    @property
    def area(self) -> float:
        """Boundary area in squared coordinate units."""
        return float(self.geometry.area)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Boundary bounding box."""
        xmin, ymin, xmax, ymax = self.geometry.bounds
        return float(xmin), float(ymin), float(xmax), float(ymax)

    @property
    def fingerprint(self) -> str:
        """Deterministic content fingerprint."""
        return stable_fingerprint(
            self.geometry,
            self.crs,
            self.spatial_unit,
            self.provenance.fingerprint,
        )

    def covers(self, coordinates: Any) -> np.ndarray:
        """Return whether each planar coordinate lies in or on the boundary."""
        try:
            from shapely.geometry import Point
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "Boundary operations require the 'geo' optional dependencies."
            ) from exc
        array = np.asarray(coordinates, dtype=float)
        if array.ndim != 2 or array.shape[1] != 2:
            raise ValueError("coordinates must have shape (n_points, 2).")
        if not np.all(np.isfinite(array)):
            raise ValueError("coordinates must contain only finite values.")
        return np.asarray(
            [self.geometry.covers(Point(float(x), float(y))) for x, y in array],
            dtype=bool,
        )

    def distance_to_edge(self, coordinates: Any) -> np.ndarray:
        """Return Euclidean distance from each point to the boundary line."""
        try:
            from shapely.geometry import Point
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "Boundary operations require the 'geo' optional dependencies."
            ) from exc
        array = np.asarray(coordinates, dtype=float)
        if array.ndim != 2 or array.shape[1] != 2:
            raise ValueError("coordinates must have shape (n_points, 2).")
        return np.asarray(
            [
                self.geometry.boundary.distance(Point(float(x), float(y)))
                for x, y in array
            ],
            dtype=float,
        )

    def validate_points(self, coordinates: Any) -> DataValidationReport:
        """Report points falling outside the study boundary."""
        covered = self.covers(coordinates)
        outside = int(np.count_nonzero(~covered))
        issues: list[DataIssue] = []
        if outside:
            issues.append(
                DataIssue(
                    "warning",
                    "points_outside_boundary",
                    "Some points fall outside the study boundary.",
                    {"outside_count": outside},
                )
            )
        return DataValidationReport(
            tuple(issues),
            {"point_count": int(covered.size), "outside_count": outside},
        )

    @classmethod
    def from_bounds(
        cls,
        bounds: tuple[float, float, float, float],
        *,
        crs: Any | None = None,
        spatial_unit: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "SpatialBoundary":
        """Create a rectangular boundary from bounds."""
        try:
            from shapely.geometry import box
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "Boundary construction requires the 'geo' optional dependencies."
            ) from exc
        xmin, ymin, xmax, ymax = (float(value) for value in bounds)
        if not all(np.isfinite([xmin, ymin, xmax, ymax])) or not (
            xmin < xmax and ymin < ymax
        ):
            raise ValueError("bounds must be finite and increasing.")
        return cls(
            geometry=box(xmin, ymin, xmax, ymax),
            crs=normalize_crs(crs),
            spatial_unit=spatial_unit,
            provenance=(provenance or DataProvenance()).with_transformation(
                "created_rectangular_boundary",
                bounds=(xmin, ymin, xmax, ymax),
            ),
        )

    @classmethod
    def from_geodataframe(
        cls,
        frame: Any,
        *,
        spatial_unit: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "SpatialBoundary":
        """Create a dissolved boundary from polygon GeoDataFrame geometries."""
        try:
            import geopandas as gpd
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "GeoDataFrame input requires the 'geo' optional dependencies."
            ) from exc
        if not isinstance(frame, gpd.GeoDataFrame):
            raise TypeError("frame must be a GeoDataFrame.")
        if frame.empty or frame.geometry.isna().any() or frame.geometry.is_empty.any():
            raise ValueError("boundary geometries must be non-empty.")
        invalid_types = ~frame.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
        if invalid_types.any():
            raise ValueError("boundary geometries must be Polygon or MultiPolygon.")
        geometry = frame.geometry.union_all()
        return cls(
            geometry=geometry,
            crs=normalize_crs(frame.crs),
            spatial_unit=spatial_unit,
            provenance=provenance or DataProvenance(),
        )
