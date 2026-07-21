# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Event-specific adaptive bandwidth strategies."""

from __future__ import annotations

from typing import Optional

import numpy as np

from pykdex.bandwidths.base import BaseBandwidth
from pykdex.bandwidths.fixed import get_bandwidth
from pykdex.kernels import BaseKernel
from pykdex.metrics import BaseMetric, EuclideanMetric


class KNNBandwidth(BaseBandwidth):
    """Use each event's distance to its k-th other event as its bandwidth.

    Args:
        k: One-based neighbour rank, excluding the event itself.
        multiplier: Positive multiplier applied to every neighbour distance.
        minimum_bandwidth: Optional positive floor used for duplicate locations.
    """

    def __init__(
        self,
        k: int,
        *,
        multiplier: float = 1.0,
        minimum_bandwidth: float | None = None,
    ) -> None:
        if isinstance(k, (bool, np.bool_)) or not isinstance(k, (int, np.integer)):
            raise TypeError("k must be a positive integer.")
        if int(k) <= 0:
            raise ValueError("k must be greater than zero.")
        if not np.isfinite(multiplier) or float(multiplier) <= 0.0:
            raise ValueError("multiplier must be finite and positive.")
        if minimum_bandwidth is not None:
            if not np.isfinite(minimum_bandwidth) or float(minimum_bandwidth) <= 0.0:
                raise ValueError("minimum_bandwidth must be finite and positive.")
        self.k = int(k)
        self.multiplier = float(multiplier)
        self.minimum_bandwidth = (
            float(minimum_bandwidth) if minimum_bandwidth is not None else None
        )

    def resolve(
        self,
        events: np.ndarray,
        *,
        weights: np.ndarray | None = None,
        metric: BaseMetric | None = None,
        kernel: BaseKernel | None = None,
    ) -> np.ndarray:
        if events.ndim != 2 or events.shape[0] < 2:
            raise ValueError("kNN bandwidth requires at least two events.")
        if self.k > events.shape[0] - 1:
            raise ValueError(f"k cannot exceed n_events - 1 = {events.shape[0] - 1}.")
        resolved_metric = metric or EuclideanMetric()
        distances = np.asarray(resolved_metric.pairwise(events, events), dtype=float)
        np.fill_diagonal(distances, np.inf)
        kth = np.partition(distances, self.k - 1, axis=1)[:, self.k - 1]
        bandwidths = kth * self.multiplier
        if self.minimum_bandwidth is not None:
            bandwidths = np.maximum(bandwidths, self.minimum_bandwidth)
        if not np.all(np.isfinite(bandwidths)) or np.any(bandwidths <= 0.0):
            raise ValueError(
                "kNN bandwidth produced non-positive values, usually because of "
                "duplicate locations. Set minimum_bandwidth to a meaningful data-unit "
                "floor."
            )
        return np.ascontiguousarray(bandwidths)


class AbramsonBandwidth(BaseBandwidth):
    r"""Abramson sample-point adaptive bandwidths.

    The local bandwidth is

    .. math::

        h_i = h_0 \left(\tilde f(x_i) / g\right)^{-\alpha},

    where ``h_0`` is a scalar pilot bandwidth and ``g`` is the weighted geometric
    mean of pilot densities.

    Args:
        pilot_bandwidth: Positive scalar or scalar bandwidth strategy.
        alpha: Positive sensitivity exponent; the square-root law uses ``0.5``.
        density_floor: Positive floor applied before logarithms and ratios.
        clip: Optional lower and upper multipliers relative to the pilot bandwidth.
    """

    def __init__(
        self,
        pilot_bandwidth: float | int | np.floating | BaseBandwidth = 1.0,
        *,
        alpha: float = 0.5,
        density_floor: float = 1e-12,
        clip: tuple[float, float] | None = (0.2, 5.0),
    ) -> None:
        if not np.isfinite(alpha) or float(alpha) <= 0.0:
            raise ValueError("alpha must be finite and positive.")
        if not np.isfinite(density_floor) or float(density_floor) <= 0.0:
            raise ValueError("density_floor must be finite and positive.")
        if clip is not None:
            if not isinstance(clip, tuple) or len(clip) != 2:
                raise TypeError("clip must be a (lower, upper) tuple or None.")
            lower, upper = float(clip[0]), float(clip[1])
            if not np.isfinite(lower) or not np.isfinite(upper) or lower <= 0.0:
                raise ValueError("clip values must be finite and positive.")
            if not lower < upper:
                raise ValueError("clip must satisfy lower < upper.")
            clip = (lower, upper)
        self.pilot_bandwidth = pilot_bandwidth
        self.alpha = float(alpha)
        self.density_floor = float(density_floor)
        self.clip = clip
        self.pilot_bandwidth_: Optional[float] = None
        self.pilot_density_: Optional[np.ndarray] = None
        self.geometric_mean_: Optional[float] = None

    def resolve(
        self,
        events: np.ndarray,
        *,
        weights: np.ndarray | None = None,
        metric: BaseMetric | None = None,
        kernel: BaseKernel | None = None,
    ) -> np.ndarray:
        if events.ndim != 2 or events.shape[0] == 0:
            raise ValueError("events must be a non-empty two-dimensional array.")
        if metric is None or kernel is None:
            raise ValueError("Abramson bandwidth requires a metric and kernel context.")
        event_weights = (
            np.ones(events.shape[0], dtype=float)
            if weights is None
            else np.asarray(weights, dtype=float)
        )
        if event_weights.ndim != 1 or event_weights.shape[0] != events.shape[0]:
            raise ValueError("weights must contain one value per event.")
        if not np.all(np.isfinite(event_weights)) or np.any(event_weights < 0.0):
            raise ValueError("weights must be finite and non-negative.")
        weight_sum = float(np.sum(event_weights))
        if weight_sum <= 0.0:
            raise ValueError("weights must contain at least one positive value.")

        pilot_strategy = get_bandwidth(self.pilot_bandwidth)
        pilot_resolved = pilot_strategy.resolve(
            events,
            weights=event_weights,
            metric=metric,
            kernel=kernel,
        )
        pilot_array = np.asarray(pilot_resolved, dtype=float)
        if pilot_array.ndim != 0:
            raise ValueError("Abramson pilot_bandwidth must resolve to one scalar.")
        pilot = float(pilot_array)
        if not np.isfinite(pilot) or pilot <= 0.0:
            raise ValueError("pilot bandwidth must be finite and positive.")

        distances = metric.pairwise(events, events)
        dimension = int(events.shape[1])
        kernel_values = kernel(distances / pilot, dimension) / pilot**dimension
        normalized_weights = event_weights / weight_sum
        pilot_density = np.asarray(kernel_values @ normalized_weights, dtype=float)
        pilot_density = np.maximum(pilot_density, self.density_floor)
        positive = event_weights > 0.0
        geometric_mean = float(
            np.exp(
                np.dot(
                    normalized_weights[positive] / np.sum(normalized_weights[positive]),
                    np.log(pilot_density[positive]),
                )
            )
        )
        multipliers = (pilot_density / geometric_mean) ** (-self.alpha)
        if self.clip is not None:
            multipliers = np.clip(multipliers, self.clip[0], self.clip[1])
        bandwidths = pilot * multipliers
        if not np.all(np.isfinite(bandwidths)) or np.any(bandwidths <= 0.0):
            raise FloatingPointError("Abramson bandwidth produced invalid values.")

        self.pilot_bandwidth_ = pilot
        self.pilot_density_ = pilot_density.copy()
        self.geometric_mean_ = geometric_mean
        return np.ascontiguousarray(bandwidths)
