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
class NetworkTimeField:
    """Density or intensity represented on measured arixel support."""

    values: np.ndarray
    support: ArixelSupport
    spatial_bandwidth: float
    temporal_bandwidth: float
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
            attrs={
                "spatial_bandwidth": self.spatial_bandwidth,
                "temporal_bandwidth": self.temporal_bandwidth,
                "spatial_unit": lixels.spatial_unit,
                "temporal_unit": self.support.temporal_unit,
                "junction_policy": self.junction_policy,
                "directed": self.directed,
            },
        )
