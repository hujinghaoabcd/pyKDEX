# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Structured results for ordinary space-time estimation."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
import pandas as pd

from pykdex.data._utils import readonly_array
from pykdex.data.spatiotemporal import (
    SpatiotemporalGridSupport,
    SpatiotemporalPointSupport,
)


@dataclass(frozen=True)
class SpatiotemporalKDEResult:
    """Space-time density or intensity evaluated on explicit support."""

    values: np.ndarray
    support: SpatiotemporalPointSupport | SpatiotemporalGridSupport
    spatial_bandwidth: float
    temporal_bandwidth: float
    target: str
    spatial_kernel: str
    temporal_kernel: str
    spatial_metric: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(
            self.support, (SpatiotemporalPointSupport, SpatiotemporalGridSupport)
        ):
            raise TypeError("support must be a space-time support object.")
        values = readonly_array(self.values, dtype=float, ndim=1, name="values")
        if values.shape != (self.support.n_points,):
            raise ValueError("values must contain one estimate per support point.")
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("values must be finite and non-negative.")
        spatial_bandwidth = float(self.spatial_bandwidth)
        temporal_bandwidth = float(self.temporal_bandwidth)
        if (
            not np.isfinite(spatial_bandwidth)
            or spatial_bandwidth <= 0.0
            or not np.isfinite(temporal_bandwidth)
            or temporal_bandwidth <= 0.0
        ):
            raise ValueError("bandwidths must be finite and positive.")
        if self.target not in {"density", "intensity"}:
            raise ValueError("target must be 'density' or 'intensity'.")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "spatial_bandwidth", spatial_bandwidth)
        object.__setattr__(self, "temporal_bandwidth", temporal_bandwidth)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def support_measure(self) -> np.ndarray | None:
        """Per-location spatial-by-temporal integration measure."""
        return self.support.measure

    def integral(self) -> float:
        """Approximate the space-time integral on measured support."""
        if self.support_measure is None:
            raise ValueError(
                "This result has no support measure; use measured point support "
                "or SpatiotemporalGridSupport."
            )
        return float(np.dot(self.values, self.support_measure))

    def to_frame(self) -> pd.DataFrame:
        """Return coordinates, time, measure, and estimates."""
        frame = self.support.to_frame()
        frame[self.target] = self.values
        return frame

    def to_grid(self) -> np.ndarray:
        """Reshape values to ``(time, y, x)`` on grid support."""
        if not isinstance(self.support, SpatiotemporalGridSupport):
            raise ValueError("to_grid requires SpatiotemporalGridSupport.")
        return self.support.reshape(self.values)

    def to_xarray(self) -> Any:
        """Return an xarray DataArray without making xarray a core dependency."""
        try:
            import xarray as xr
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "xarray export requires the 'xarray' optional dependency."
            ) from exc
        if isinstance(self.support, SpatiotemporalGridSupport):
            spatial = self.support.spatial
            if spatial.dimension != 2:
                raise ValueError("grid xarray export currently requires 2D space.")
            names = tuple(spatial.coordinate_names)
            x_values = np.unique(spatial.coordinates[:, 0])
            y_values = np.unique(spatial.coordinates[:, 1])
            return xr.DataArray(
                self.to_grid(),
                dims=("time", names[1], names[0]),
                coords={
                    "time": self.support.time_centers,
                    names[1]: y_values,
                    names[0]: x_values,
                },
                name=self.target,
                attrs={
                    "spatial_unit": spatial.spatial_unit,
                    "temporal_unit": self.support.temporal_unit,
                    "spatial_bandwidth": self.spatial_bandwidth,
                    "temporal_bandwidth": self.temporal_bandwidth,
                },
            )
            names = self.support.spatial.coordinate_names or ("x", "y")
        coordinates: dict[str, Any] = {
            "observation": np.arange(self.support.n_points),
            "time": ("observation", self.support.times),
        }
        for index, name in enumerate(names):
            coordinates[name] = (
                "observation",
                self.support.spatial_coordinates[:, index],
            )
        return xr.DataArray(
            self.values,
            dims=("observation",),
            coords=coordinates,
            name=self.target,
        )


@dataclass(frozen=True)
class SpatiotemporalBandwidthSelectionResult:
    """Immutable result of a joint or separate bandwidth grid experiment."""

    spatial_bandwidth: float
    temporal_bandwidth: float
    score: float
    mode: str
    objective: str
    spatial_candidates: np.ndarray
    temporal_candidates: np.ndarray
    score_matrix: np.ndarray
    distance_asset_fingerprint: str

    def __post_init__(self) -> None:
        spatial_candidates = readonly_array(
            self.spatial_candidates,
            dtype=float,
            ndim=1,
            name="spatial_candidates",
        )
        temporal_candidates = readonly_array(
            self.temporal_candidates,
            dtype=float,
            ndim=1,
            name="temporal_candidates",
        )
        scores = readonly_array(
            self.score_matrix,
            dtype=float,
            ndim=2,
            name="score_matrix",
        )
        if scores.shape != (spatial_candidates.size, temporal_candidates.size):
            raise ValueError("score_matrix shape must match candidate grid.")
        if (
            spatial_candidates.size == 0
            or temporal_candidates.size == 0
            or not np.all(np.isfinite(spatial_candidates))
            or np.any(spatial_candidates <= 0.0)
            or not np.all(np.isfinite(temporal_candidates))
            or np.any(temporal_candidates <= 0.0)
            or not np.all(np.isfinite(scores))
        ):
            raise ValueError("candidate grid and scores must contain valid values.")
        spatial_bandwidth = float(self.spatial_bandwidth)
        temporal_bandwidth = float(self.temporal_bandwidth)
        score = float(self.score)
        if not np.any(np.isclose(spatial_candidates, spatial_bandwidth)):
            raise ValueError("selected spatial bandwidth must be a candidate.")
        if not np.any(np.isclose(temporal_candidates, temporal_bandwidth)):
            raise ValueError("selected temporal bandwidth must be a candidate.")
        if not np.isfinite(score):
            raise ValueError("score must be finite.")
        if self.mode not in {"joint", "separate"}:
            raise ValueError("mode must be 'joint' or 'separate'.")
        if self.objective != "loo_likelihood":
            raise ValueError("objective must be 'loo_likelihood'.")
        if (
            not isinstance(self.distance_asset_fingerprint, str)
            or not self.distance_asset_fingerprint
        ):
            raise ValueError("distance_asset_fingerprint must be non-empty.")
        object.__setattr__(self, "spatial_bandwidth", spatial_bandwidth)
        object.__setattr__(self, "temporal_bandwidth", temporal_bandwidth)
        object.__setattr__(self, "score", score)
        object.__setattr__(self, "spatial_candidates", spatial_candidates)
        object.__setattr__(self, "temporal_candidates", temporal_candidates)
        object.__setattr__(self, "score_matrix", scores)

    def to_frame(self) -> pd.DataFrame:
        """Return every candidate pair and joint objective score."""
        spatial, temporal = np.meshgrid(
            self.spatial_candidates,
            self.temporal_candidates,
            indexing="ij",
        )
        return pd.DataFrame(
            {
                "spatial_bandwidth": spatial.ravel(),
                "temporal_bandwidth": temporal.ravel(),
                "score": self.score_matrix.ravel(),
            }
        )
