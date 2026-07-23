# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Product-kernel evaluation on linear and periodic time domains."""

from __future__ import annotations

import math

import numpy as np

from pykdex.kernels import BaseKernel
from pykdex.temporal import BaseTimeDomain, CyclicTimeDomain


def _positive_bandwidth(value: float, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must not be boolean.")
    resolved = float(value)
    if not np.isfinite(resolved) or resolved <= 0.0:
        raise ValueError(f"{name} must be finite and positive.")
    return resolved


def _cyclic_image_count(
    kernel: BaseKernel,
    bandwidth: float,
    period: float,
    tolerance: float,
) -> int:
    if kernel.finite_support:
        radius = 1.0
    elif kernel.name == "gaussian":
        radius = math.sqrt(-2.0 * math.log(tolerance))
    elif kernel.name == "exponential":
        radius = -math.log(tolerance)
    else:
        raise ValueError(
            "Infinite-support custom temporal kernels on cyclic time require a "
            "known tail bound; use gaussian, exponential, or a finite-support kernel."
        )
    return max(1, int(math.ceil((radius * bandwidth + period) / period)))


def evaluate_temporal_kernel(
    offsets: np.ndarray,
    *,
    domain: BaseTimeDomain,
    kernel: BaseKernel,
    bandwidth: float | np.ndarray,
    tail_tolerance: float = 1e-12,
) -> np.ndarray:
    """Evaluate a normalized temporal kernel, including periodic image sums.

    A one-dimensional bandwidth array assigns one bandwidth to every source in
    the final axis of ``offsets``.
    """
    values = np.asarray(offsets, dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("temporal offsets must contain finite values.")
    raw_bandwidths = np.asarray(bandwidth, dtype=float)
    if raw_bandwidths.ndim == 0:
        resolved: float | np.ndarray = _positive_bandwidth(
            float(raw_bandwidths), name="temporal_bandwidth"
        )
    elif (
        raw_bandwidths.ndim == 1
        and values.ndim >= 1
        and raw_bandwidths.shape[0] == values.shape[-1]
    ):
        if not np.all(np.isfinite(raw_bandwidths)) or np.any(raw_bandwidths <= 0.0):
            raise ValueError("temporal_bandwidth values must be finite and positive.")
        resolved = np.ascontiguousarray(raw_bandwidths)
    else:
        raise ValueError(
            "temporal_bandwidth must be scalar or contain one value per source."
        )
    if not isinstance(domain, CyclicTimeDomain):
        distances = domain.distances_from_offsets(values)
        return kernel(distances / resolved, 1) / resolved
    tolerance = float(tail_tolerance)
    if not np.isfinite(tolerance) or not 0.0 < tolerance < 1.0:
        raise ValueError("tail_tolerance must lie strictly between zero and one.")
    canonical = domain.canonicalize(values + domain.origin) - domain.origin
    result = np.zeros_like(canonical, dtype=float)
    if np.ndim(resolved) == 0:
        scalar = float(resolved)
        count = _cyclic_image_count(kernel, scalar, domain.period, tolerance)
        for image in range(-count, count + 1):
            distance = np.abs(canonical + image * domain.period)
            result += kernel(distance / scalar, 1) / scalar
        return result
    bandwidths = np.asarray(resolved, dtype=float)
    for source, scalar in enumerate(bandwidths):
        count = _cyclic_image_count(kernel, float(scalar), domain.period, tolerance)
        for image in range(-count, count + 1):
            distance = np.abs(canonical[..., source] + image * domain.period)
            result[..., source] += kernel(distance / scalar, 1) / scalar
    return result


def evaluate_product_kernel(
    spatial_distances: np.ndarray,
    temporal_offsets: np.ndarray,
    *,
    dimension: int,
    spatial_kernel: BaseKernel,
    temporal_kernel: BaseKernel,
    spatial_bandwidth: float,
    temporal_bandwidth: float,
    time_domain: BaseTimeDomain,
    tail_tolerance: float = 1e-12,
) -> np.ndarray:
    """Evaluate a separable spatial-by-temporal product kernel."""
    spatial_h = _positive_bandwidth(spatial_bandwidth, name="spatial_bandwidth")
    temporal_h = _positive_bandwidth(temporal_bandwidth, name="temporal_bandwidth")
    spatial = np.asarray(spatial_distances, dtype=float)
    offsets = np.asarray(temporal_offsets, dtype=float)
    if spatial.shape != offsets.shape:
        raise ValueError("spatial distances and temporal offsets must have one shape.")
    if (
        not np.all(np.isfinite(spatial))
        or np.any(spatial < 0.0)
        or not np.all(np.isfinite(offsets))
    ):
        raise ValueError("distance arrays contain invalid values.")
    spatial_values = (
        spatial_kernel(spatial / spatial_h, dimension) / spatial_h**dimension
    )
    temporal_values = evaluate_temporal_kernel(
        offsets,
        domain=time_domain,
        kernel=temporal_kernel,
        bandwidth=temporal_h,
        tail_tolerance=tail_tolerance,
    )
    return np.asarray(spatial_values * temporal_values, dtype=float)
