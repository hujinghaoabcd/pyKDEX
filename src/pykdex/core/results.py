# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Structured result objects for pyKDEX estimators."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SpatialKDEResult:
    """Spatial KDE values evaluated at explicit support coordinates.

    Args:
        values: Estimated density or intensity values.
        support: Evaluation coordinates.
        bandwidth: Scalar bandwidth or one bandwidth per fitted event.
        target: Either ``"density"`` or ``"intensity"``.
        kernel: Canonical kernel name.
        metric: Canonical metric name.
        coordinate_names: Optional support coordinate column names.
        metadata: Additional immutable-by-convention estimation metadata.
    """

    values: np.ndarray
    support: np.ndarray
    bandwidth: float | np.ndarray
    target: str
    kernel: str
    metric: str
    coordinate_names: Optional[Tuple[str, ...]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        values = np.asarray(self.values, dtype=float)
        support = np.asarray(self.support, dtype=float)
        if values.ndim != 1:
            raise ValueError("values must be one-dimensional.")
        if support.ndim != 2:
            raise ValueError("support must be two-dimensional.")
        if values.shape[0] != support.shape[0]:
            raise ValueError("values and support must contain the same number of rows.")
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("values must be finite and non-negative.")
        object.__setattr__(self, "values", values.copy())
        object.__setattr__(self, "support", support.copy())
        if isinstance(self.bandwidth, np.ndarray):
            object.__setattr__(self, "bandwidth", self.bandwidth.copy())

    def to_frame(self) -> pd.DataFrame:
        """Return support coordinates and estimates as a DataFrame."""
        names = self.coordinate_names or tuple(
            f"coord_{index}" for index in range(self.support.shape[1])
        )
        frame = pd.DataFrame(self.support, columns=list(names))
        frame[self.target] = self.values
        return frame

    def to_geodataframe(self, crs: Optional[str | int] = None) -> Any:
        """Return a GeoDataFrame for one- or two-dimensional support.

        One-dimensional support is mapped to ``(x, 0)``. Support with more than
        two coordinate columns cannot be represented as planar point geometry.
        """
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "GeoDataFrame export requires the 'geo' optional dependencies."
            ) from exc
        if self.support.shape[1] > 2:
            raise ValueError(
                "GeoDataFrame export supports only one- or two-dimensional support."
            )
        frame = self.to_frame()
        if self.support.shape[1] == 1:
            geometry = [Point(float(x), 0.0) for x in self.support[:, 0]]
        else:
            geometry = [Point(float(x), float(y)) for x, y in self.support]
        return gpd.GeoDataFrame(frame, geometry=geometry, crs=crs)
