# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Low-level Euclidean KDE evaluation helpers.

Author:
    Jinghao Hu
"""

from __future__ import annotations

import numpy as np

from pykdex.kernels import BaseKernel
from pykdex.metrics import BaseMetric


def validate_spatial_bandwidth(
    bandwidth: float | np.ndarray,
    *,
    n_events: int,
    dimension: int,
) -> float | np.ndarray:
    """Validate scalar, event-specific scalar, or global matrix bandwidths."""
    array = np.asarray(bandwidth, dtype=float)
    if array.ndim == 0:
        value = float(array)
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError("resolved bandwidth must be finite and positive.")
        return value
    if array.ndim == 1:
        if array.shape[0] != n_events:
            raise ValueError(
                "event-specific bandwidth must contain one value per event."
            )
        if not np.all(np.isfinite(array)) or np.any(array <= 0.0):
            raise ValueError("resolved bandwidth values must be finite and positive.")
        owned = np.ascontiguousarray(array.copy())
        owned.setflags(write=False)
        return owned
    if array.ndim == 2:
        if array.shape != (dimension, dimension):
            raise ValueError(
                "bandwidth matrix must have shape (dimension, dimension)."
            )
        if not np.all(np.isfinite(array)):
            raise ValueError("bandwidth matrix must contain finite values.")
        if not np.allclose(array, array.T, rtol=1e-10, atol=1e-12):
            raise ValueError("bandwidth matrix must be symmetric.")
        try:
            np.linalg.cholesky(array)
        except np.linalg.LinAlgError as exc:
            raise ValueError("bandwidth matrix must be positive definite.") from exc
        owned = np.ascontiguousarray(array.copy())
        owned.setflags(write=False)
        return owned
    raise ValueError(
        "resolved bandwidth must be scalar, one-dimensional per event, or a "
        "global positive-definite matrix."
    )


def bandwidth_kind(bandwidth: float | np.ndarray) -> str:
    """Return the canonical bandwidth representation name."""
    array = np.asarray(bandwidth)
    if array.ndim == 0:
        return "scalar"
    if array.ndim == 1:
        return "event"
    return "matrix"


def evaluate_sample_point_kernel(
    support: np.ndarray,
    events: np.ndarray,
    *,
    kernel: BaseKernel,
    metric: BaseMetric,
    bandwidth: float | np.ndarray,
) -> np.ndarray:
    """Evaluate scalar, sample-point, or matrix kernels by source event."""
    dimension = int(events.shape[1])
    array = np.asarray(bandwidth, dtype=float)
    if array.ndim == 2:
        if metric.name != "euclidean":
            raise ValueError(
                "bandwidth matrices require the Euclidean metric because their "
                "orientation is defined in coordinate space."
            )
        chol = np.linalg.cholesky(array)
        differences = support[:, None, :] - events[None, :, :]
        flattened = differences.reshape(-1, dimension).T
        transformed = np.linalg.solve(chol, flattened).T
        distances = np.linalg.norm(transformed, axis=1).reshape(
            support.shape[0], events.shape[0]
        )
        determinant_scale = float(np.prod(np.diag(chol)))
        return kernel(distances, dimension) / determinant_scale

    distances = metric.pairwise(support, events)
    if array.ndim == 1:
        standardized = distances / array[None, :]
        return kernel(standardized, dimension) / (
            array[None, :] ** dimension
        )
    h = float(array)
    return kernel(distances / h, dimension) / h**dimension


def evaluate_balloon_kernel(
    support: np.ndarray,
    events: np.ndarray,
    *,
    kernel: BaseKernel,
    metric: BaseMetric,
    support_bandwidths: np.ndarray,
) -> np.ndarray:
    """Evaluate a query-centred scalar balloon kernel."""
    bandwidths = np.asarray(support_bandwidths, dtype=float)
    if bandwidths.ndim != 1 or bandwidths.shape[0] != support.shape[0]:
        raise ValueError("support_bandwidths must contain one value per support row.")
    if not np.all(np.isfinite(bandwidths)) or np.any(bandwidths <= 0.0):
        raise ValueError("support bandwidths must be finite and positive.")
    dimension = int(events.shape[1])
    distances = metric.pairwise(support, events)
    standardized = distances / bandwidths[:, None]
    return kernel(standardized, dimension) / (
        bandwidths[:, None] ** dimension
    )
