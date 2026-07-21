# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Point and regular-grid evaluation support objects.

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


@dataclass(frozen=True)
class PointSupport:
    """Immutable point locations where an estimator is evaluated."""

    coordinates: np.ndarray
    ids: np.ndarray | None = None
    coordinate_names: tuple[str, ...] | None = None
    crs: str | None = None
    spatial_unit: str | None = None
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
                "coordinates must contain at least one point and dimension."
            )
        if not np.all(np.isfinite(coordinates)):
            raise ValueError("coordinates must contain only finite values.")
        n_points, dimension = coordinates.shape
        ids = (
            readonly_array(np.arange(n_points, dtype=np.int64), ndim=1, name="ids")
            if self.ids is None
            else readonly_array(self.ids, ndim=1, name="ids")
        )
        if ids.shape[0] != n_points:
            raise ValueError("ids must contain one value per support point.")
        if len({repr(value) for value in ids.tolist()}) != n_points:
            raise ValueError("ids must be unique.")
        object.__setattr__(self, "coordinates", coordinates)
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

    @property
    def n_points(self) -> int:
        """Number of support points."""
        return int(self.coordinates.shape[0])

    @property
    def dimension(self) -> int:
        """Coordinate dimension."""
        return int(self.coordinates.shape[1])

    @property
    def measure(self) -> None:
        """Point supports have no integration measure."""
        return None

    @property
    def fingerprint(self) -> str:
        """Deterministic content fingerprint."""
        return stable_fingerprint(
            self.coordinates,
            self.ids,
            self.coordinate_names,
            self.crs,
            self.spatial_unit,
            self.provenance.fingerprint,
        )

    def to_frame(self) -> pd.DataFrame:
        """Return support coordinates and identifiers as a DataFrame."""
        names = self.coordinate_names or tuple(
            f"coord_{index}" for index in range(self.dimension)
        )
        frame = pd.DataFrame(self.coordinates, columns=list(names))
        frame.insert(0, "support_id", self.ids)
        return frame

    @classmethod
    def from_array(
        cls,
        coordinates: Any,
        *,
        ids: Any | None = None,
        coordinate_names: Iterable[str] | None = None,
        crs: Any | None = None,
        spatial_unit: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "PointSupport":
        """Construct point support from array-like coordinates."""
        return cls(
            coordinates=np.asarray(coordinates),
            ids=None if ids is None else np.asarray(ids),
            coordinate_names=(
                None if coordinate_names is None else tuple(coordinate_names)
            ),
            crs=normalize_crs(crs),
            spatial_unit=spatial_unit,
            provenance=provenance or DataProvenance(),
        )

    @classmethod
    def from_dataframe(
        cls,
        frame: pd.DataFrame,
        *,
        coordinate_columns: Iterable[str],
        id_column: str | None = None,
        crs: Any | None = None,
        spatial_unit: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "PointSupport":
        """Construct point support from named DataFrame columns."""
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("frame must be a pandas DataFrame.")
        columns = tuple(coordinate_columns)
        if not columns:
            raise ValueError("coordinate_columns must contain at least one column.")
        missing = [column for column in columns if column not in frame.columns]
        if id_column is not None and id_column not in frame.columns:
            missing.append(id_column)
        if missing:
            raise ValueError(f"DataFrame is missing columns: {sorted(set(missing))}.")
        return cls(
            coordinates=frame.loc[:, list(columns)].to_numpy(),
            ids=None if id_column is None else frame[id_column].to_numpy(),
            coordinate_names=columns,
            crs=normalize_crs(crs),
            spatial_unit=spatial_unit,
            provenance=provenance or DataProvenance(),
        )

    @classmethod
    def from_geodataframe(
        cls,
        frame: Any,
        *,
        id_column: str | None = None,
        spatial_unit: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "PointSupport":
        """Construct point support from a point GeoDataFrame."""
        try:
            import geopandas as gpd
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "GeoDataFrame input requires the 'geo' optional dependencies."
            ) from exc
        if not isinstance(frame, gpd.GeoDataFrame):
            raise TypeError("frame must be a GeoDataFrame.")
        if frame.empty or frame.geometry.isna().any() or frame.geometry.is_empty.any():
            raise ValueError("support geometries must be non-empty points.")
        if not frame.geometry.geom_type.eq("Point").all():
            raise ValueError("support geometries must all be Point geometries.")
        coordinates = np.column_stack([frame.geometry.x, frame.geometry.y])
        ids = None if id_column is None else frame[id_column].to_numpy()
        return cls(
            coordinates=coordinates,
            ids=ids,
            coordinate_names=("x", "y"),
            crs=normalize_crs(frame.crs),
            spatial_unit=spatial_unit,
            provenance=provenance or DataProvenance(),
        )


@dataclass(frozen=True)
class GridSupport:
    """Regular two-dimensional grid represented by cell centres and areas."""

    coordinates: np.ndarray
    cell_measure: np.ndarray
    shape: tuple[int, int]
    bounds: tuple[float, float, float, float]
    resolution: tuple[float, float]
    ids: np.ndarray | None = None
    coordinate_names: tuple[str, str] = ("x", "y")
    crs: str | None = None
    spatial_unit: str | None = None
    provenance: DataProvenance = field(default_factory=DataProvenance)

    def __post_init__(self) -> None:
        coordinates = readonly_array(
            self.coordinates,
            dtype=float,
            ndim=2,
            name="coordinates",
        )
        if coordinates.shape[1] != 2 or coordinates.shape[0] == 0:
            raise ValueError("GridSupport coordinates must have shape (n_cells, 2).")
        if not np.all(np.isfinite(coordinates)):
            raise ValueError("coordinates must contain only finite values.")
        measure = readonly_array(
            self.cell_measure,
            dtype=float,
            ndim=1,
            name="cell_measure",
        )
        if measure.shape[0] != coordinates.shape[0]:
            raise ValueError("cell_measure must contain one value per grid cell.")
        if not np.all(np.isfinite(measure)) or np.any(measure <= 0.0):
            raise ValueError("cell_measure must be finite and positive.")
        rows, columns = int(self.shape[0]), int(self.shape[1])
        if rows <= 0 or columns <= 0 or rows * columns != coordinates.shape[0]:
            raise ValueError("shape must match the number of grid cells.")
        xmin, ymin, xmax, ymax = (float(value) for value in self.bounds)
        if not all(np.isfinite([xmin, ymin, xmax, ymax])) or not (
            xmin < xmax and ymin < ymax
        ):
            raise ValueError("bounds must be finite and increasing.")
        dx, dy = (float(value) for value in self.resolution)
        if not np.isfinite(dx) or not np.isfinite(dy) or dx <= 0.0 or dy <= 0.0:
            raise ValueError("resolution values must be finite and positive.")
        ids = (
            readonly_array(
                np.arange(coordinates.shape[0], dtype=np.int64),
                ndim=1,
                name="ids",
            )
            if self.ids is None
            else readonly_array(self.ids, ndim=1, name="ids")
        )
        if ids.shape[0] != coordinates.shape[0]:
            raise ValueError("ids must contain one value per grid cell.")
        object.__setattr__(self, "coordinates", coordinates)
        object.__setattr__(self, "cell_measure", measure)
        object.__setattr__(self, "shape", (rows, columns))
        object.__setattr__(self, "bounds", (xmin, ymin, xmax, ymax))
        object.__setattr__(self, "resolution", (dx, dy))
        object.__setattr__(self, "ids", ids)
        object.__setattr__(
            self,
            "coordinate_names",
            normalize_names(self.coordinate_names, dimension=2),
        )
        object.__setattr__(self, "crs", normalize_crs(self.crs))
        object.__setattr__(
            self,
            "spatial_unit",
            normalize_unit(self.spatial_unit, name="spatial_unit"),
        )

    @property
    def n_points(self) -> int:
        """Number of grid cells."""
        return int(self.coordinates.shape[0])

    @property
    def dimension(self) -> int:
        """Grid coordinate dimension."""
        return 2

    @property
    def measure(self) -> np.ndarray:
        """Per-cell integration measures."""
        return self.cell_measure

    @property
    def fingerprint(self) -> str:
        """Deterministic content fingerprint."""
        return stable_fingerprint(
            self.coordinates,
            self.cell_measure,
            self.shape,
            self.bounds,
            self.resolution,
            self.ids,
            self.crs,
            self.spatial_unit,
            self.provenance.fingerprint,
        )

    def reshape(self, values: Any) -> np.ndarray:
        """Reshape one value per cell to ``shape``."""
        array = np.asarray(values)
        if array.ndim != 1 or array.shape[0] != self.n_points:
            raise ValueError("values must contain one value per grid cell.")
        return array.reshape(self.shape)

    def to_frame(self) -> pd.DataFrame:
        """Return cell centres, areas, and identifiers as a DataFrame."""
        frame = pd.DataFrame(self.coordinates, columns=list(self.coordinate_names))
        frame.insert(0, "support_id", self.ids)
        frame["cell_measure"] = self.cell_measure
        return frame

    @classmethod
    def from_bounds(
        cls,
        bounds: Iterable[float],
        *,
        resolution: float | tuple[float, float],
        crs: Any | None = None,
        spatial_unit: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "GridSupport":
        """Create a regular grid, retaining smaller remainder cells at boundaries."""
        bounds_tuple = tuple(float(value) for value in bounds)
        if len(bounds_tuple) != 4:
            raise ValueError("bounds must contain (xmin, ymin, xmax, ymax).")
        xmin, ymin, xmax, ymax = bounds_tuple
        if not all(np.isfinite(bounds_tuple)) or not (xmin < xmax and ymin < ymax):
            raise ValueError("bounds must be finite and increasing.")
        if isinstance(resolution, tuple):
            resolution_tuple = tuple(float(value) for value in resolution)
            if len(resolution_tuple) != 2:
                raise ValueError("resolution must be a scalar or (dx, dy).")
            dx, dy = resolution_tuple
        else:
            dx = dy = float(resolution)
        if not np.isfinite(dx) or not np.isfinite(dy) or dx <= 0.0 or dy <= 0.0:
            raise ValueError("resolution values must be finite and positive.")
        x_edges = _axis_edges(xmin, xmax, dx)
        y_edges = _axis_edges(ymin, ymax, dy)
        x_centres = 0.5 * (x_edges[:-1] + x_edges[1:])
        y_centres = 0.5 * (y_edges[:-1] + y_edges[1:])
        xx, yy = np.meshgrid(x_centres, y_centres)
        widths = np.diff(x_edges)
        heights = np.diff(y_edges)
        cell_measure = np.outer(heights, widths).ravel()
        return cls(
            coordinates=np.column_stack([xx.ravel(), yy.ravel()]),
            cell_measure=cell_measure,
            shape=(y_centres.size, x_centres.size),
            bounds=(xmin, ymin, xmax, ymax),
            resolution=(dx, dy),
            crs=normalize_crs(crs),
            spatial_unit=spatial_unit,
            provenance=(provenance or DataProvenance()).with_transformation(
                "created_regular_grid",
                bounds=(xmin, ymin, xmax, ymax),
                resolution=(dx, dy),
            ),
        )


def _axis_edges(lower: float, upper: float, step: float) -> np.ndarray:
    full_count = int(np.floor((upper - lower) / step))
    edges = lower + np.arange(full_count + 1, dtype=float) * step
    if edges.size == 0 or not np.isclose(edges[-1], upper):
        edges = np.append(edges, upper)
    else:
        edges[-1] = upper
    if edges.size < 2:
        edges = np.array([lower, upper], dtype=float)
    return edges
