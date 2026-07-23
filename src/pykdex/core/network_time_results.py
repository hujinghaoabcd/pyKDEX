# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Structured measured fields on lixel-by-time support."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
import pandas as pd

from pykdex.data._utils import readonly_array
from pykdex.network_time import ArixelSupport


@dataclass(frozen=True)
class NetworkTimeBandwidthSelectionResult:
    """Immutable result of a network-time bandwidth grid experiment."""

    spatial_bandwidth: float
    temporal_bandwidth: float
    score: float
    mode: str
    objective: str
    spatial_candidates: np.ndarray
    temporal_candidates: np.ndarray
    score_matrix: np.ndarray
    cache_fingerprint: str

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
            self.score_matrix, dtype=float, ndim=2, name="score_matrix"
        )
        if scores.shape != (spatial_candidates.size, temporal_candidates.size):
            raise ValueError("score_matrix shape must match the candidate grid.")
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
        if self.objective not in {"loo_likelihood", "least_squares_cv"}:
            raise ValueError(
                "objective must be 'loo_likelihood' or 'least_squares_cv'."
            )
        if not isinstance(self.cache_fingerprint, str) or not self.cache_fingerprint:
            raise ValueError("cache_fingerprint must be non-empty.")
        object.__setattr__(self, "spatial_bandwidth", spatial_bandwidth)
        object.__setattr__(self, "temporal_bandwidth", temporal_bandwidth)
        object.__setattr__(self, "score", score)
        object.__setattr__(self, "spatial_candidates", spatial_candidates)
        object.__setattr__(self, "temporal_candidates", temporal_candidates)
        object.__setattr__(self, "score_matrix", scores)

    def to_frame(self) -> pd.DataFrame:
        """Return every candidate pair and its joint objective score."""
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


@dataclass(frozen=True)
class NetworkTimeField:
    """Density or intensity represented on measured arixel support."""

    values: np.ndarray
    support: ArixelSupport
    spatial_bandwidth: float | np.ndarray
    temporal_bandwidth: float | np.ndarray
    target: str
    spatial_kernel: str
    temporal_kernel: str
    junction_policy: str
    directed: bool
    network_fingerprint: str
    event_fingerprint: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.support, ArixelSupport):
            raise TypeError("support must be ArixelSupport.")
        values = readonly_array(self.values, dtype=float, ndim=1, name="values")
        if values.shape != (self.support.n_arixels,):
            raise ValueError("values must contain one estimate per arixel.")
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("values must be finite and non-negative.")
        spatial_bandwidth = self._bandwidth(
            self.spatial_bandwidth, name="spatial_bandwidth"
        )
        temporal_bandwidth = self._bandwidth(
            self.temporal_bandwidth, name="temporal_bandwidth"
        )
        if self.target not in {"density", "intensity"}:
            raise ValueError("target must be 'density' or 'intensity'.")
        if not isinstance(self.directed, (bool, np.bool_)):
            raise TypeError("directed must be boolean.")
        if self.support.lixels.network_fingerprint != self.network_fingerprint:
            raise ValueError("support belongs to a different network.")
        for value, name in (
            (self.spatial_kernel, "spatial_kernel"),
            (self.temporal_kernel, "temporal_kernel"),
            (self.junction_policy, "junction_policy"),
            (self.network_fingerprint, "network_fingerprint"),
            (self.event_fingerprint, "event_fingerprint"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "spatial_bandwidth", spatial_bandwidth)
        object.__setattr__(self, "temporal_bandwidth", temporal_bandwidth)
        object.__setattr__(self, "directed", bool(self.directed))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def _bandwidth(self, value: float | np.ndarray, *, name: str) -> float | np.ndarray:
        array = np.asarray(value, dtype=float)
        if array.ndim == 0:
            scalar = float(array)
            if not np.isfinite(scalar) or scalar <= 0.0:
                raise ValueError(f"{name} must be finite and positive.")
            return scalar
        array = readonly_array(array, dtype=float, ndim=1, name=name)
        n_events = self.metadata.get("n_events")
        if n_events is not None and array.shape != (int(n_events),):
            raise ValueError(f"{name} must contain one value per event.")
        if array.size == 0 or not np.all(np.isfinite(array)) or np.any(array <= 0.0):
            raise ValueError(f"{name} must contain finite positive values.")
        return array

    @property
    def adaptive_spatial(self) -> bool:
        """Whether spatial bandwidth varies by source event."""
        return isinstance(self.spatial_bandwidth, np.ndarray)

    @property
    def adaptive_temporal(self) -> bool:
        """Whether temporal bandwidth varies by source event."""
        return isinstance(self.temporal_bandwidth, np.ndarray)

    @property
    def adaptive(self) -> bool:
        """Whether either bandwidth component varies by source event."""
        return self.adaptive_spatial or self.adaptive_temporal

    @property
    def support_measure(self) -> np.ndarray:
        """Length-times-time measure per arixel."""
        return self.support.measure

    def integral(self) -> float:
        """Approximate the complete network-time integral."""
        return float(np.dot(self.values, self.support.measure))

    def to_grid(self) -> np.ndarray:
        """Return time-by-lixel values."""
        return self.support.reshape(self.values)

    def to_frame(self) -> pd.DataFrame:
        """Return arixel attributes and estimates."""
        frame = self.support.to_frame()
        frame[self.target] = self.values
        return frame

    def to_geodataframe(self) -> Any:
        """Return repeated lixel geometries with time and estimates."""
        frame = self.support.to_geodataframe()
        frame[self.target] = self.values
        return frame

    def to_xarray(self) -> Any:
        """Return a time-by-lixel xarray DataArray."""
        try:
            import xarray as xr
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "xarray export requires the 'array' optional dependency."
            ) from exc
        lixels = self.support.lixels
        attrs: dict[str, Any] = {
            "adaptive_spatial_bandwidth": self.adaptive_spatial,
            "adaptive_temporal_bandwidth": self.adaptive_temporal,
            "spatial_bandwidth_min": float(np.min(self.spatial_bandwidth)),
            "spatial_bandwidth_max": float(np.max(self.spatial_bandwidth)),
            "temporal_bandwidth_min": float(np.min(self.temporal_bandwidth)),
            "temporal_bandwidth_max": float(np.max(self.temporal_bandwidth)),
            "spatial_unit": lixels.spatial_unit,
            "temporal_unit": self.support.temporal_unit,
            "junction_policy": self.junction_policy,
            "directed": self.directed,
        }
        if not self.adaptive_spatial:
            attrs["spatial_bandwidth"] = float(self.spatial_bandwidth)
        if not self.adaptive_temporal:
            attrs["temporal_bandwidth"] = float(self.temporal_bandwidth)
        return xr.DataArray(
            self.to_grid(),
            dims=("time", "lixel"),
            coords={
                "time": self.support.time_centers,
                "lixel": lixels.lixel_ids,
                "edge_index": ("lixel", lixels.edge_indices),
                "center_offset": ("lixel", lixels.center_offsets),
                "lixel_length": ("lixel", lixels.lengths),
            },
            name=self.target,
            attrs=attrs,
        )
