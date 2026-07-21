# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Common normalized radial kernels in arbitrary Euclidean dimension."""

from __future__ import annotations

from math import gamma, pi
from typing import Type

import numpy as np

from pykdex.kernels.base import BaseKernel


def _unit_ball_volume(dimension: int) -> float:
    return float(pi ** (dimension / 2.0) / gamma(dimension / 2.0 + 1.0))


class GaussianKernel(BaseKernel):
    """Standard multivariate Gaussian radial kernel."""

    name = "gaussian"
    finite_support = False

    def evaluate(self, standardized_distance: np.ndarray, dimension: int) -> np.ndarray:
        constant = (2.0 * pi) ** (-dimension / 2.0)
        return np.asarray(
            constant * np.exp(-0.5 * standardized_distance**2), dtype=float
        )


class EpanechnikovKernel(BaseKernel):
    """Compact Epanechnikov radial kernel."""

    name = "epanechnikov"
    finite_support = True

    def evaluate(self, standardized_distance: np.ndarray, dimension: int) -> np.ndarray:
        volume = _unit_ball_volume(dimension)
        constant = (dimension + 2.0) / (2.0 * volume)
        inside = standardized_distance <= 1.0
        values = np.zeros_like(standardized_distance, dtype=float)
        values[inside] = constant * (1.0 - standardized_distance[inside] ** 2)
        return values


class QuarticKernel(BaseKernel):
    """Compact quartic (biweight) radial kernel."""

    name = "quartic"
    finite_support = True

    def evaluate(self, standardized_distance: np.ndarray, dimension: int) -> np.ndarray:
        volume = _unit_ball_volume(dimension)
        constant = (dimension + 2.0) * (dimension + 4.0) / (8.0 * volume)
        inside = standardized_distance <= 1.0
        values = np.zeros_like(standardized_distance, dtype=float)
        base = 1.0 - standardized_distance[inside] ** 2
        values[inside] = constant * base**2
        return values


class TriangularKernel(BaseKernel):
    """Compact linearly decreasing radial kernel."""

    name = "triangular"
    finite_support = True

    def evaluate(self, standardized_distance: np.ndarray, dimension: int) -> np.ndarray:
        volume = _unit_ball_volume(dimension)
        constant = (dimension + 1.0) / volume
        inside = standardized_distance <= 1.0
        values = np.zeros_like(standardized_distance, dtype=float)
        values[inside] = constant * (1.0 - standardized_distance[inside])
        return values


class UniformKernel(BaseKernel):
    """Uniform radial kernel on the unit ball."""

    name = "uniform"
    finite_support = True

    def evaluate(self, standardized_distance: np.ndarray, dimension: int) -> np.ndarray:
        constant = 1.0 / _unit_ball_volume(dimension)
        return np.where(standardized_distance <= 1.0, constant, 0.0)


class ExponentialKernel(BaseKernel):
    """Normalized radial exponential kernel."""

    name = "exponential"
    finite_support = False

    def evaluate(self, standardized_distance: np.ndarray, dimension: int) -> np.ndarray:
        constant = 1.0 / (_unit_ball_volume(dimension) * gamma(dimension + 1.0))
        return np.asarray(constant * np.exp(-standardized_distance), dtype=float)


_KERNELS: dict[str, Type[BaseKernel]] = {
    "gaussian": GaussianKernel,
    "epanechnikov": EpanechnikovKernel,
    "quartic": QuarticKernel,
    "biweight": QuarticKernel,
    "triangular": TriangularKernel,
    "uniform": UniformKernel,
    "exponential": ExponentialKernel,
}


def get_kernel(kernel: str | BaseKernel) -> BaseKernel:
    """Resolve a canonical kernel instance from a name or object."""
    if isinstance(kernel, BaseKernel):
        return kernel
    if not isinstance(kernel, str) or not kernel.strip():
        raise TypeError("kernel must be a non-empty string or BaseKernel instance.")
    name = kernel.strip().lower()
    try:
        return _KERNELS[name]()
    except KeyError as exc:
        supported = ", ".join(sorted(_KERNELS))
        raise ValueError(
            f"Unknown kernel '{kernel}'. Supported kernels: {supported}."
        ) from exc
