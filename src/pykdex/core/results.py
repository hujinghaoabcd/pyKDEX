# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Structured result objects for pyKDEX estimators and selectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BandwidthSelectionResult:
    """Immutable summary of a one-dimensional bandwidth search.

    Args:
        bandwidth: Selected positive scalar bandwidth.
        score: Objective value at the selected bandwidth.
        method: Canonical selector name.
        bounds: Lower and upper search bounds.
        n_evaluations: Number of objective evaluations.
        success: Whether the optimizer reported convergence.
        message: Optimizer status message.
        evaluated_bandwidths: Bandwidth values visited by the optimizer.
        evaluated_scores: Objective values corresponding to visited bandwidths.
    """

    bandwidth: float
    score: float
    method: str
    bounds: Tuple[float, float]
    n_evaluations: int
    success: bool
    message: str
    evaluated_bandwidths: np.ndarray = field(repr=False)
    evaluated_scores: np.ndarray = field(repr=False)

    def __post_init__(self) -> None:
        bandwidth = float(self.bandwidth)
        score = float(self.score)
        lower, upper = (float(self.bounds[0]), float(self.bounds[1]))
        bandwidths = np.asarray(self.evaluated_bandwidths, dtype=float)
        scores = np.asarray(self.evaluated_scores, dtype=float)
        if not np.isfinite(bandwidth) or bandwidth <= 0.0:
            raise ValueError("bandwidth must be finite and positive.")
        if not np.isfinite(score):
            raise ValueError("score must be finite.")
        if not np.isfinite(lower) or not np.isfinite(upper) or not lower < upper:
            raise ValueError("bounds must contain finite increasing values.")
        if not lower <= bandwidth <= upper:
            raise ValueError("bandwidth must lie within bounds.")
        if bandwidths.ndim != 1 or scores.ndim != 1:
            raise ValueError("evaluation histories must be one-dimensional.")
        if bandwidths.shape != scores.shape:
            raise ValueError("evaluation histories must have matching shapes.")
        if bandwidths.size != int(self.n_evaluations):
            raise ValueError("n_evaluations must match the history length.")
        if not np.all(np.isfinite(bandwidths)) or np.any(bandwidths <= 0.0):
            raise ValueError("evaluated bandwidths must be finite and positive.")
        if not np.all(np.isfinite(scores)):
            raise ValueError("evaluated scores must be finite.")
        object.__setattr__(self, "bandwidth", bandwidth)
        object.__setattr__(self, "score", score)
        object.__setattr__(self, "bounds", (lower, upper))
        object.__setattr__(self, "n_evaluations", int(self.n_evaluations))
        object.__setattr__(self, "success", bool(self.success))
        object.__setattr__(self, "evaluated_bandwidths", bandwidths.copy())
        object.__setattr__(self, "evaluated_scores", scores.copy())

    def to_frame(self) -> pd.DataFrame:
        """Return the complete optimization trace as a DataFrame."""
        return pd.DataFrame(
            {
                "bandwidth": self.evaluated_bandwidths,
                "score": self.evaluated_scores,
            }
        )


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
