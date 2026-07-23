# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Temporal-domain contracts for ordinary and periodic time."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from pykdex.data._utils import stable_fingerprint


class BaseTimeDomain(ABC):
    """Base contract for temporal coordinates and pairwise distances."""

    name: str

    @abstractmethod
    def canonicalize(self, values: np.ndarray) -> np.ndarray:
        """Return finite coordinates in the domain's canonical representation."""

    @abstractmethod
    def distances_from_offsets(self, offsets: np.ndarray) -> np.ndarray:
        """Return non-negative distances from signed target-source offsets."""

    def pairwise(self, target: np.ndarray, source: np.ndarray) -> np.ndarray:
        """Return target-by-source temporal distances."""
        left = np.asarray(target, dtype=float)
        right = np.asarray(source, dtype=float)
        if left.ndim != 1 or right.ndim != 1:
            raise ValueError("target and source times must be one-dimensional.")
        if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
            raise ValueError("temporal coordinates must contain finite values.")
        offsets = left[:, None] - right[None, :]
        return self.distances_from_offsets(offsets)

    @property
    @abstractmethod
    def fingerprint(self) -> str:
        """Deterministic temporal-domain fingerprint."""


@dataclass(frozen=True)
class LinearTimeDomain(BaseTimeDomain):
    """Unbounded linear time with absolute-difference distance."""

    name = "linear"

    def canonicalize(self, values: np.ndarray) -> np.ndarray:
        array = np.asarray(values, dtype=float)
        if not np.all(np.isfinite(array)):
            raise ValueError("temporal coordinates must contain finite values.")
        return np.asarray(array, dtype=float)

    def distances_from_offsets(self, offsets: np.ndarray) -> np.ndarray:
        values = np.asarray(offsets, dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError("temporal offsets must contain finite values.")
        return np.abs(values)

    @property
    def fingerprint(self) -> str:
        return stable_fingerprint(self.name)


@dataclass(frozen=True)
class CyclicTimeDomain(BaseTimeDomain):
    """Periodic time represented on ``[origin, origin + period)``."""

    period: float
    origin: float = 0.0

    name = "cyclic"

    def __post_init__(self) -> None:
        if isinstance(self.period, (bool, np.bool_)):
            raise TypeError("period must not be boolean.")
        period = float(self.period)
        origin = float(self.origin)
        if not np.isfinite(period) or period <= 0.0:
            raise ValueError("period must be finite and positive.")
        if not np.isfinite(origin):
            raise ValueError("origin must be finite.")
        object.__setattr__(self, "period", period)
        object.__setattr__(self, "origin", origin)

    def canonicalize(self, values: np.ndarray) -> np.ndarray:
        array = np.asarray(values, dtype=float)
        if not np.all(np.isfinite(array)):
            raise ValueError("temporal coordinates must contain finite values.")
        return self.origin + np.mod(array - self.origin, self.period)

    def distances_from_offsets(self, offsets: np.ndarray) -> np.ndarray:
        values = np.asarray(offsets, dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError("temporal offsets must contain finite values.")
        wrapped = np.mod(np.abs(values), self.period)
        return np.minimum(wrapped, self.period - wrapped)

    @property
    def fingerprint(self) -> str:
        return stable_fingerprint(self.name, self.period, self.origin)
