# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Euclidean pairwise distance metric."""

from __future__ import annotations

import numpy as np
from scipy.spatial.distance import cdist

from pykdex.metrics.base import BaseMetric


class EuclideanMetric(BaseMetric):
    """Euclidean distance in an arbitrary finite-dimensional coordinate space."""

    name = "euclidean"

    def pairwise(self, left: np.ndarray, right: np.ndarray) -> np.ndarray:
        if left.ndim != 2 or right.ndim != 2:
            raise ValueError("left and right must be two-dimensional arrays.")
        if left.shape[1] != right.shape[1]:
            raise ValueError("left and right must have the same coordinate dimension.")
        distances = np.asarray(cdist(left, right, metric="euclidean"), dtype=float)
        if not np.all(np.isfinite(distances)):
            raise ValueError("distance computation produced non-finite values.")
        return distances


def get_metric(metric: str | BaseMetric) -> BaseMetric:
    """Resolve a metric name or object."""
    if isinstance(metric, BaseMetric):
        return metric
    if not isinstance(metric, str) or not metric.strip():
        raise TypeError("metric must be a non-empty string or BaseMetric instance.")
    name = metric.strip().lower()
    if name != "euclidean":
        raise ValueError(
            "Only the 'euclidean' metric is available in the first baseline."
        )
    return EuclideanMetric()
