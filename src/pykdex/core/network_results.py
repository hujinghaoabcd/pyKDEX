# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Structured fields evaluated on measured linear-network support.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
import pandas as pd

from pykdex.network.support import LixelSupport


@dataclass(frozen=True)
class NetworkField:
    """Density or intensity values evaluated at lixel centres.

    Args:
        values: One non-negative estimate per lixel.
        support: Measured lixel support used for evaluation and integration.
        bandwidth: Positive scalar or one positive value per source event.
        target: Either ``"density"`` or ``"intensity"``.
        kernel: Canonical radial-kernel name.
        junction_policy: Canonical network junction policy.
        directed: Whether edge direction constrained propagation.
        network_fingerprint: Fingerprint of the fitted network.
        event_fingerprint: Fingerprint of accepted snapped events.
        metadata: Additional immutable estimation metadata.
    """

    values: np.ndarray
    support: LixelSupport
    bandwidth: float | np.ndarray
    target: str
    kernel: str
    junction_policy: str
    directed: bool
    network_fingerprint: str
    event_fingerprint: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.support, LixelSupport):
            raise TypeError("support must be a LixelSupport instance.")
        values = np.asarray(self.values, dtype=float)
        if values.ndim != 1 or values.shape[0] != self.support.n_lixels:
            raise ValueError("values must contain one value per lixel.")
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("values must be finite and non-negative.")
        bandwidth_values = np.asarray(self.bandwidth, dtype=float)
        if bandwidth_values.ndim == 0:
            bandwidth: float | np.ndarray = float(bandwidth_values)
            if not np.isfinite(bandwidth) or bandwidth <= 0.0:
                raise ValueError("bandwidth must be finite and positive.")
        elif bandwidth_values.ndim == 1 and bandwidth_values.size > 0:
            if not np.all(np.isfinite(bandwidth_values)) or np.any(
                bandwidth_values <= 0.0
            ):
                raise ValueError("bandwidth values must be finite and positive.")
            owned_bandwidth = np.ascontiguousarray(bandwidth_values.copy())
            owned_bandwidth.setflags(write=False)
            bandwidth = owned_bandwidth
        else:
            raise ValueError(
                "bandwidth must be scalar or a non-empty one-dimensional array."
            )
        target = str(self.target).strip().lower()
        if target not in {"density", "intensity"}:
            raise ValueError("target must be either 'density' or 'intensity'.")
        kernel = str(self.kernel).strip()
        policy = str(self.junction_policy).strip()
        network_fingerprint = str(self.network_fingerprint).strip()
        event_fingerprint = str(self.event_fingerprint).strip()
        if not kernel or not policy:
            raise ValueError("kernel and junction_policy must be non-empty strings.")
        if not network_fingerprint or not event_fingerprint:
            raise ValueError("network and event fingerprints must be non-empty.")
        if self.support.network_fingerprint != network_fingerprint:
            raise ValueError("support belongs to a different network.")
        if not isinstance(self.directed, (bool, np.bool_)):
            raise TypeError("directed must be boolean.")
        owned = np.ascontiguousarray(values.copy())
        owned.setflags(write=False)
        object.__setattr__(self, "values", owned)
        object.__setattr__(self, "bandwidth", bandwidth)
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "kernel", kernel)
        object.__setattr__(self, "junction_policy", policy)
        object.__setattr__(self, "directed", bool(self.directed))
        object.__setattr__(self, "network_fingerprint", network_fingerprint)
        object.__setattr__(self, "event_fingerprint", event_fingerprint)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def adaptive(self) -> bool:
        """Whether the field used event-specific bandwidths."""
        return isinstance(self.bandwidth, np.ndarray)


    @property
    def n_lixels(self) -> int:
        """Number of evaluated lixels."""
        return self.support.n_lixels

    @property
    def support_measure(self) -> np.ndarray:
        """Actual lixel lengths used for network integration."""
        return self.support.measure

    def integral(self) -> float:
        """Approximate the field integral over the complete network."""
        return float(np.dot(self.values, self.support.measure))

    def to_frame(self) -> pd.DataFrame:
        """Return lixel attributes and estimates as a DataFrame."""
        frame = self.support.to_frame()
        frame[self.target] = self.values
        return frame

    def to_geodataframe(self) -> Any:
        """Return lixel line geometries and estimates as a GeoDataFrame."""
        frame = self.support.to_geodataframe()
        frame[self.target] = self.values
        return frame
