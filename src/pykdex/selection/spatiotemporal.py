# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Deterministic joint and separate space-time bandwidth experiments."""

from __future__ import annotations

import numpy as np

from pykdex.core.spatiotemporal_results import (
    SpatiotemporalBandwidthSelectionResult,
)
from pykdex.data import SpatiotemporalEvents
from pykdex.data._utils import readonly_array
from pykdex.kernels import BaseKernel, get_kernel
from pykdex.metrics import BaseMetric, get_metric
from pykdex.spatiotemporal import (
    SpatiotemporalDistanceAsset,
    build_spatiotemporal_distance_asset,
    evaluate_temporal_kernel,
)


def _candidates(values: object, *, name: str) -> np.ndarray:
    array = readonly_array(values, dtype=float, ndim=1, name=name)
    if array.size == 0 or not np.all(np.isfinite(array)) or np.any(array <= 0.0):
        raise ValueError(f"{name} must contain finite positive values.")
    if np.unique(array).size != array.size:
        raise ValueError(f"{name} must not contain duplicates.")
    return array


def _loo_score(
    kernel_values: np.ndarray,
    weights: np.ndarray,
    *,
    density_floor: float,
) -> float:
    matrix = np.asarray(kernel_values, dtype=float).copy()
    if matrix.shape != (weights.size, weights.size):
        raise ValueError("LOO kernel matrix must be square over fitted events.")
    np.fill_diagonal(matrix, 0.0)
    denominators = float(np.sum(weights)) - weights
    if np.any(denominators <= 0.0):
        raise ValueError("LOO likelihood requires positive leave-one-out weight.")
    estimates = (matrix @ weights) / denominators
    probabilities = weights / float(np.sum(weights))
    return float(-np.dot(probabilities, np.log(np.maximum(estimates, density_floor))))


class SpatiotemporalBandwidthExperiment:
    """Grid-search independent spatial and temporal scalar bandwidths.

    ``mode="joint"`` minimizes weighted product-kernel LOO negative
    log-likelihood over every candidate pair. ``mode="separate"`` minimizes
    spatial and temporal marginal objectives independently, then reports the
    product-kernel score at that deterministic pair.
    """

    def __init__(
        self,
        spatial_candidates: object,
        temporal_candidates: object,
        *,
        mode: str = "joint",
        spatial_kernel: str | BaseKernel = "gaussian",
        temporal_kernel: str | BaseKernel = "gaussian",
        spatial_metric: str | BaseMetric = "euclidean",
        density_floor: float = 1e-300,
        cyclic_tail_tolerance: float = 1e-12,
    ) -> None:
        self.spatial_candidates = _candidates(
            spatial_candidates, name="spatial_candidates"
        )
        self.temporal_candidates = _candidates(
            temporal_candidates, name="temporal_candidates"
        )
        if mode not in {"joint", "separate"}:
            raise ValueError("mode must be 'joint' or 'separate'.")
        floor = float(density_floor)
        tolerance = float(cyclic_tail_tolerance)
        if not np.isfinite(floor) or floor <= 0.0:
            raise ValueError("density_floor must be finite and positive.")
        if not np.isfinite(tolerance) or not 0.0 < tolerance < 1.0:
            raise ValueError(
                "cyclic_tail_tolerance must lie strictly between zero and one."
            )
        self.mode = mode
        self.spatial_kernel = spatial_kernel
        self.temporal_kernel = temporal_kernel
        self.spatial_metric = spatial_metric
        self.density_floor = floor
        self.cyclic_tail_tolerance = tolerance
        self.distance_asset_: SpatiotemporalDistanceAsset | None = None
        self.result_: SpatiotemporalBandwidthSelectionResult | None = None

    def run(
        self,
        events: SpatiotemporalEvents,
        *,
        distance_asset: SpatiotemporalDistanceAsset | None = None,
    ) -> SpatiotemporalBandwidthSelectionResult:
        """Evaluate the candidate grid with a reusable event-event asset."""
        self.distance_asset_ = None
        self.result_ = None
        if not isinstance(events, SpatiotemporalEvents):
            raise TypeError("events must be SpatiotemporalEvents.")
        if events.n_events < 2:
            raise ValueError("bandwidth selection requires at least two events.")
        spatial_kernel = get_kernel(self.spatial_kernel)
        temporal_kernel = get_kernel(self.temporal_kernel)
        metric = get_metric(self.spatial_metric)
        asset = distance_asset or build_spatiotemporal_distance_asset(
            events, events, spatial_metric=metric
        )
        asset.validate_for(events, events, spatial_metric=metric.name)
        weights = events.weights
        dimension = events.spatial.dimension
        spatial_values = [
            spatial_kernel(asset.spatial_distances / bandwidth, dimension)
            / bandwidth**dimension
            for bandwidth in self.spatial_candidates
        ]
        temporal_values = [
            evaluate_temporal_kernel(
                asset.temporal_offsets,
                domain=events.temporal.domain,
                kernel=temporal_kernel,
                bandwidth=bandwidth,
                tail_tolerance=self.cyclic_tail_tolerance,
            )
            for bandwidth in self.temporal_candidates
        ]
        scores = np.empty(
            (self.spatial_candidates.size, self.temporal_candidates.size),
            dtype=float,
        )
        for spatial_index, spatial_matrix in enumerate(spatial_values):
            for temporal_index, temporal_matrix in enumerate(temporal_values):
                scores[spatial_index, temporal_index] = _loo_score(
                    spatial_matrix * temporal_matrix,
                    weights,
                    density_floor=self.density_floor,
                )
        if self.mode == "joint":
            spatial_index, temporal_index = np.unravel_index(
                int(np.argmin(scores)), scores.shape
            )
        else:
            spatial_scores = np.asarray(
                [
                    _loo_score(value, weights, density_floor=self.density_floor)
                    for value in spatial_values
                ]
            )
            temporal_scores = np.asarray(
                [
                    _loo_score(value, weights, density_floor=self.density_floor)
                    for value in temporal_values
                ]
            )
            spatial_index = int(np.argmin(spatial_scores))
            temporal_index = int(np.argmin(temporal_scores))
        result = SpatiotemporalBandwidthSelectionResult(
            spatial_bandwidth=float(self.spatial_candidates[spatial_index]),
            temporal_bandwidth=float(self.temporal_candidates[temporal_index]),
            score=float(scores[spatial_index, temporal_index]),
            mode=self.mode,
            objective="loo_likelihood",
            spatial_candidates=self.spatial_candidates,
            temporal_candidates=self.temporal_candidates,
            score_matrix=scores,
            distance_asset_fingerprint=asset.fingerprint,
        )
        self.distance_asset_ = asset
        self.result_ = result
        return result
