# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Structured batch results for metric-graph heat experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
import pandas as pd

from pykdex.core.network_results import NetworkField


@dataclass(frozen=True)
class HeatNetworkBatchResult:
    """Network fields evaluated at an ordered collection of diffusion times."""

    diffusion_times: np.ndarray
    fields: tuple[NetworkField, ...]
    compute_plan_fingerprint: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        times = np.asarray(self.diffusion_times, dtype=float)
        if times.ndim != 1 or times.size == 0:
            raise ValueError(
                "diffusion_times must be a non-empty one-dimensional array."
            )
        if not np.all(np.isfinite(times)) or np.any(times <= 0.0):
            raise ValueError("diffusion_times must contain finite positive values.")
        fields = tuple(self.fields)
        if len(fields) != times.size or not all(
            isinstance(value, NetworkField) for value in fields
        ):
            raise ValueError("fields must contain one NetworkField per diffusion time.")
        first = fields[0]
        if any(
            value.network_fingerprint != first.network_fingerprint
            or value.event_fingerprint != first.event_fingerprint
            or value.support.fingerprint != first.support.fingerprint
            or value.target != first.target
            for value in fields[1:]
        ):
            raise ValueError("all batch fields must share data, support, and target.")
        fingerprint = str(self.compute_plan_fingerprint).strip()
        if not fingerprint:
            raise ValueError("compute_plan_fingerprint must be non-empty.")
        owned = np.ascontiguousarray(times.copy())
        owned.setflags(write=False)
        object.__setattr__(self, "diffusion_times", owned)
        object.__setattr__(self, "fields", fields)
        object.__setattr__(self, "compute_plan_fingerprint", fingerprint)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def n_times(self) -> int:
        """Number of requested diffusion times, including duplicates."""
        return int(self.diffusion_times.size)

    def at_index(self, index: int) -> NetworkField:
        """Return the field at one positional batch index."""
        if isinstance(index, (bool, np.bool_)) or not isinstance(
            index, (int, np.integer)
        ):
            raise TypeError("index must be an integer.")
        return self.fields[int(index)]

    def to_frame(self) -> pd.DataFrame:
        """Return all lixel fields in one long-form DataFrame."""
        frames: list[pd.DataFrame] = []
        for index, (time, field_value) in enumerate(
            zip(self.diffusion_times, self.fields, strict=True)
        ):
            frame = field_value.to_frame()
            frame.insert(0, "batch_index", index)
            frame.insert(1, "diffusion_time", float(time))
            frames.append(frame)
        return pd.concat(frames, ignore_index=True)
