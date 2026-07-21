# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Base class for normalized radial kernels."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class BaseKernel(ABC):
    """Normalized radial kernel evaluated on standardized distances."""

    name: str
    finite_support: bool

    @abstractmethod
    def evaluate(self, standardized_distance: np.ndarray, dimension: int) -> np.ndarray:
        """Evaluate the normalized radial kernel."""

    def __call__(self, standardized_distance: np.ndarray, dimension: int) -> np.ndarray:
        distances = np.asarray(standardized_distance, dtype=float)
        if distances.ndim == 0:
            distances = distances.reshape(1)
        if not isinstance(dimension, (int, np.integer)) or dimension <= 0:
            raise ValueError("dimension must be a positive integer.")
        if not np.all(np.isfinite(distances)) or np.any(distances < 0.0):
            raise ValueError(
                "standardized_distance must contain finite non-negative values."
            )
        values = np.asarray(self.evaluate(distances, int(dimension)), dtype=float)
        if values.shape != distances.shape:
            raise ValueError("kernel evaluation returned an unexpected shape.")
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("kernel evaluation returned invalid values.")
        return values
