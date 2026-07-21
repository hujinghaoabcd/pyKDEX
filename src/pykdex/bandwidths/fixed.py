# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Fixed scalar bandwidth strategy."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pykdex.bandwidths.base import BaseBandwidth


@dataclass(frozen=True)
class FixedBandwidth(BaseBandwidth):
    """Use one positive distance bandwidth for every event."""

    value: float

    def __post_init__(self) -> None:
        if isinstance(self.value, (bool, np.bool_)):
            raise TypeError("bandwidth must not be boolean.")
        try:
            numeric = float(self.value)
        except (TypeError, ValueError) as exc:
            raise TypeError("bandwidth must be numeric.") from exc
        if not np.isfinite(numeric) or numeric <= 0.0:
            raise ValueError("bandwidth must be finite and greater than zero.")
        object.__setattr__(self, "value", numeric)

    def resolve(self, events: np.ndarray) -> float:
        if events.ndim != 2 or events.shape[0] == 0:
            raise ValueError("events must be a non-empty two-dimensional array.")
        return self.value


def get_bandwidth(bandwidth: float | BaseBandwidth) -> BaseBandwidth:
    """Resolve a numeric or strategy bandwidth."""
    if isinstance(bandwidth, BaseBandwidth):
        return bandwidth
    return FixedBandwidth(bandwidth)
