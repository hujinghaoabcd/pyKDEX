# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Structural protocols used by the composition-oriented public API."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class KernelProtocol(Protocol):
    """Protocol for normalized radial kernels."""

    name: str
    finite_support: bool

    def evaluate(self, standardized_distance: np.ndarray, dimension: int) -> np.ndarray:
        """Evaluate the normalized kernel at non-negative radial distances."""


@runtime_checkable
class BandwidthProtocol(Protocol):
    """Protocol for bandwidth strategies."""

    def resolve(self, events: np.ndarray) -> float | np.ndarray:
        """Return a scalar or one positive bandwidth per event."""


@runtime_checkable
class MetricProtocol(Protocol):
    """Protocol for pairwise metrics."""

    name: str

    def pairwise(self, left: np.ndarray, right: np.ndarray) -> np.ndarray:
        """Return pairwise distances with shape ``(len(left), len(right))``."""
