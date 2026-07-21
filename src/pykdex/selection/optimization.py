# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Deterministic one-dimensional optimization helpers."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy.optimize import minimize_scalar

from pykdex.core.results import BandwidthSelectionResult


def infer_bandwidth_bounds(distances: np.ndarray) -> tuple[float, float]:
    """Infer robust positive search bounds from pairwise event distances."""
    if distances.ndim != 2 or distances.shape[0] != distances.shape[1]:
        raise ValueError("distances must be a square pairwise matrix.")
    upper_triangle = distances[np.triu_indices(distances.shape[0], k=1)]
    positive = upper_triangle[np.isfinite(upper_triangle) & (upper_triangle > 0.0)]
    if positive.size == 0:
        raise ValueError(
            "automatic bandwidth bounds require at least two distinct event locations."
        )
    scale = float(np.median(positive))
    lower = max(float(np.quantile(positive, 0.05)) * 0.2, scale * 1e-6)
    upper = max(float(np.quantile(positive, 0.95)) * 2.0, lower * 10.0)
    return lower, upper


def validate_bounds(
    bounds: tuple[float, float] | None,
    distances: np.ndarray,
) -> tuple[float, float]:
    """Validate explicit bounds or infer them from pairwise distances."""
    if bounds is None:
        return infer_bandwidth_bounds(distances)
    if not isinstance(bounds, tuple) or len(bounds) != 2:
        raise TypeError("bounds must be a (lower, upper) tuple or None.")
    lower, upper = float(bounds[0]), float(bounds[1])
    if not np.isfinite(lower) or not np.isfinite(upper) or lower <= 0.0:
        raise ValueError("bounds must be finite and strictly positive.")
    if not lower < upper:
        raise ValueError("bounds must satisfy lower < upper.")
    return lower, upper


def minimize_bandwidth_objective(
    objective: Callable[[float], float],
    *,
    method: str,
    bounds: tuple[float, float],
    tolerance: float,
    maxiter: int,
) -> BandwidthSelectionResult:
    """Minimize an objective on log bandwidth and retain its full trace."""
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tolerance must be finite and positive.")
    if isinstance(maxiter, (bool, np.bool_)) or not isinstance(
        maxiter, (int, np.integer)
    ):
        raise TypeError("maxiter must be a positive integer.")
    if int(maxiter) <= 0:
        raise ValueError("maxiter must be greater than zero.")

    visited_bandwidths: list[float] = []
    visited_scores: list[float] = []

    def objective_log(log_bandwidth: float) -> float:
        bandwidth = float(np.exp(log_bandwidth))
        score = float(objective(bandwidth))
        if not np.isfinite(score):
            score = float(np.finfo(float).max)
        visited_bandwidths.append(bandwidth)
        visited_scores.append(score)
        return score

    lower, upper = bounds
    result = minimize_scalar(
        objective_log,
        method="bounded",
        bounds=(float(np.log(lower)), float(np.log(upper))),
        options={"xatol": float(tolerance), "maxiter": int(maxiter)},
    )
    bandwidth = float(np.exp(float(result.x)))
    score = float(result.fun)
    return BandwidthSelectionResult(
        bandwidth=bandwidth,
        score=score,
        method=method,
        bounds=bounds,
        n_evaluations=len(visited_bandwidths),
        success=bool(result.success),
        message=str(result.message),
        evaluated_bandwidths=np.asarray(visited_bandwidths, dtype=float),
        evaluated_scores=np.asarray(visited_scores, dtype=float),
    )
