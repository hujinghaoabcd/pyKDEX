# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Cross-validation objectives for scalar spatial KDE bandwidths."""

from __future__ import annotations

from math import sqrt

import numpy as np

from pykdex.kernels import BaseKernel, GaussianKernel


def validate_selection_weights(
    weights: np.ndarray | None,
    n_events: int,
) -> np.ndarray:
    """Return finite non-negative selector weights with at least two positives."""
    if weights is None:
        values = np.ones(n_events, dtype=float)
    else:
        values = np.asarray(weights, dtype=float)
        if values.ndim != 1 or values.shape[0] != n_events:
            raise ValueError("weights must contain one value per event.")
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("weights must be finite and non-negative.")
        values = values.copy()
    if np.count_nonzero(values > 0.0) < 2:
        raise ValueError("bandwidth selection requires at least two positive weights.")
    return values


def likelihood_cv_score(
    bandwidth: float,
    distances: np.ndarray,
    weights: np.ndarray,
    kernel: BaseKernel,
    dimension: int,
    *,
    density_floor: float,
) -> float:
    """Return weighted negative leave-one-out log likelihood."""
    h = float(bandwidth)
    values = kernel(distances / h, dimension) / h**dimension
    values = np.asarray(values, dtype=float)
    np.fill_diagonal(values, 0.0)
    weight_sum = float(np.sum(weights))
    denominators = weight_sum - weights
    if np.any((weights > 0.0) & (denominators <= 0.0)):
        return float(np.finfo(float).max)
    densities = np.divide(
        values @ weights,
        denominators,
        out=np.zeros_like(weights, dtype=float),
        where=denominators > 0.0,
    )
    densities = np.maximum(densities, density_floor)
    normalized = weights / weight_sum
    score = -float(np.dot(normalized, np.log(densities)))
    return score if np.isfinite(score) else float(np.finfo(float).max)


def least_squares_cv_score(
    bandwidth: float,
    distances: np.ndarray,
    weights: np.ndarray,
    dimension: int,
) -> float:
    """Return exact weighted Gaussian least-squares CV score.

    The integrated squared density term uses the Gaussian convolution identity,
    while the second term is a weighted leave-one-out density average.
    """
    h = float(bandwidth)
    gaussian = GaussianKernel()
    weight_sum = float(np.sum(weights))
    normalized = weights / weight_sum

    convolution_scale = sqrt(2.0) * h
    convolution = gaussian(distances / convolution_scale, dimension) / (
        convolution_scale**dimension
    )
    integrated_square = float(normalized @ convolution @ normalized)

    leave_one_out = gaussian(distances / h, dimension) / h**dimension
    leave_one_out = np.asarray(leave_one_out, dtype=float)
    np.fill_diagonal(leave_one_out, 0.0)
    denominators = weight_sum - weights
    densities = np.divide(
        leave_one_out @ weights,
        denominators,
        out=np.zeros_like(weights, dtype=float),
        where=denominators > 0.0,
    )
    score = integrated_square - 2.0 * float(np.dot(normalized, densities))
    return score if np.isfinite(score) else float(np.finfo(float).max)
