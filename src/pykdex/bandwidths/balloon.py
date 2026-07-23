# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Query-centred balloon bandwidth strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from pykdex.metrics import BaseMetric


class BaseBalloonBandwidth(ABC):
    """Base class for support-dependent scalar bandwidth strategies."""

    @abstractmethod
    def resolve_support(
        self,
        support: np.ndarray,
        events: np.ndarray,
        *,
        metric: BaseMetric,
    ) -> np.ndarray:
        """Return one positive bandwidth per support row."""

    def validate_events(self, events: np.ndarray) -> None:
        """Validate fitted events before support-dependent evaluation."""
        if events.ndim != 2 or events.shape[0] == 0:
            raise ValueError("events must be a non-empty two-dimensional array.")


class BalloonKNNBandwidth(BaseBalloonBandwidth):
    """Use each support point's k-th event distance as a balloon bandwidth.

    Args:
        k: One-based event rank. Unlike sample-point kNN, no event is excluded
            because support locations are query points rather than source events.
        multiplier: Positive multiplier applied to the ranked distance.
        minimum_bandwidth: Optional positive floor for coincident support/events.
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
        if minimum_bandwidth is not None and (
            not np.isfinite(minimum_bandwidth) or float(minimum_bandwidth) <= 0.0
        ):
            raise ValueError("minimum_bandwidth must be finite and positive.")
        self.k = int(k)
        self.multiplier = float(multiplier)
        self.minimum_bandwidth = (
            None if minimum_bandwidth is None else float(minimum_bandwidth)
        )

    def validate_events(self, events: np.ndarray) -> None:
        super().validate_events(events)
        if self.k > events.shape[0]:
            raise ValueError(f"k cannot exceed n_events = {events.shape[0]}.")

    def resolve_support(
        self,
        support: np.ndarray,
        events: np.ndarray,
        *,
        metric: BaseMetric,
    ) -> np.ndarray:
        self.validate_events(events)
        if support.ndim != 2 or support.shape[1] != events.shape[1]:
            raise ValueError(
                "support must be two-dimensional with the fitted event dimension."
            )
        distances = np.asarray(metric.pairwise(support, events), dtype=float)
        ranked = np.partition(distances, self.k - 1, axis=1)[:, self.k - 1]
        bandwidths = ranked * self.multiplier
        if self.minimum_bandwidth is not None:
            bandwidths = np.maximum(bandwidths, self.minimum_bandwidth)
        if not np.all(np.isfinite(bandwidths)) or np.any(bandwidths <= 0.0):
            raise ValueError(
                "balloon kNN produced non-positive bandwidths, usually because a "
                "support point coincides with an event. Set minimum_bandwidth."
            )
        return np.ascontiguousarray(bandwidths)
