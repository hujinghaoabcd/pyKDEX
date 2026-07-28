# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Cached bandwidth experiments for separable network-time KDE."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pykdex.core.network_time_results import (
    NetworkTimeBandwidthSelectionResult,
)
from pykdex.data._utils import readonly_array, stable_fingerprint
from pykdex.kernels import BaseKernel, get_kernel
from pykdex.network import (
    NetworkDistanceAsset,
    NetworkLocations,
    PropagationTrace,
    build_event_event_distances,
    build_event_lixel_distances,
    get_junction_policy,
    trace_network_propagation,
)
from pykdex.network.evaluation import (
    evaluate_distance_kernel_matrix,
    evaluate_propagation_kernel_matrix,
)
from pykdex.network.propagation import JunctionPolicy
from pykdex.network_time import NetworkTimeWorkspace
from pykdex.selection.objectives import validate_selection_weights
from pykdex.spatiotemporal import evaluate_temporal_kernel


def _candidates(values: object, *, name: str) -> np.ndarray:
    array = readonly_array(values, dtype=float, ndim=1, name=name)
    if array.size == 0 or not np.all(np.isfinite(array)) or np.any(array <= 0.0):
        raise ValueError(f"{name} must contain finite positive values.")
    if np.unique(array).size != array.size:
        raise ValueError(f"{name} must not contain duplicates.")
    return array


def _effective_directed(workspace: NetworkTimeWorkspace, directed: bool | None) -> bool:
    if directed is not None and not isinstance(directed, (bool, np.bool_)):
        raise TypeError("directed must be boolean or None.")
    return bool(
        workspace.network.directed
        if directed is None
        else bool(directed) and workspace.network.directed
    )


def _asset_usable(
    asset: NetworkDistanceAsset | None,
    *,
    source_fingerprint: str,
    target_fingerprint: str,
    directed: bool,
    cutoff: float | None,
) -> bool:
    if (
        asset is None
        or asset.source_fingerprint != source_fingerprint
        or asset.target_fingerprint != target_fingerprint
        or asset.weight != "length"
        or asset.directed != directed
    ):
        return False
    if cutoff is None:
        return asset.cutoff is None
    return asset.cutoff is None or asset.cutoff >= cutoff - 1e-12


@dataclass(frozen=True)
class NetworkTimeSelectionCache:
    """Reusable event, lixel, time, and propagation assets for candidate grids."""

    event_event_distances: NetworkDistanceAsset
    event_lixel_distances: NetworkDistanceAsset | None
    propagation_traces: tuple[PropagationTrace, ...] | None
    event_temporal_offsets: np.ndarray
    support_temporal_offsets: np.ndarray
    upper_spatial_bandwidth: float
    junction_policy: str
    directed: bool
    workspace_fingerprint: str

    def __post_init__(self) -> None:
        event_offsets = readonly_array(
            self.event_temporal_offsets,
            dtype=float,
            ndim=2,
            name="event_temporal_offsets",
        )
        support_offsets = readonly_array(
            self.support_temporal_offsets,
            dtype=float,
            ndim=2,
            name="support_temporal_offsets",
        )
        n_events = self.event_event_distances.shape[0]
        if self.event_event_distances.shape != (n_events, n_events):
            raise ValueError("event_event_distances must be square.")
        if event_offsets.shape != (n_events, n_events):
            raise ValueError("event temporal offsets must be event-by-event.")
        if support_offsets.shape[1] != n_events:
            raise ValueError("support temporal offsets must have one event column.")
        if (self.event_lixel_distances is None) == (self.propagation_traces is None):
            raise ValueError(
                "cache must contain exactly one spatial support representation."
            )
        upper = float(self.upper_spatial_bandwidth)
        if not np.isfinite(upper) or upper <= 0.0:
            raise ValueError("upper_spatial_bandwidth must be finite and positive.")
        object.__setattr__(self, "event_temporal_offsets", event_offsets)
        object.__setattr__(self, "support_temporal_offsets", support_offsets)
        object.__setattr__(self, "upper_spatial_bandwidth", upper)

    @property
    def fingerprint(self) -> str:
        """Deterministic identity of all reusable selection assets."""
        return stable_fingerprint(
            self.event_event_distances.fingerprint,
            (
                None
                if self.event_lixel_distances is None
                else self.event_lixel_distances.fingerprint
            ),
            (
                None
                if self.propagation_traces is None
                else tuple(trace.fingerprint for trace in self.propagation_traces)
            ),
            self.event_temporal_offsets,
            self.support_temporal_offsets,
            self.upper_spatial_bandwidth,
            self.junction_policy,
            self.directed,
            self.workspace_fingerprint,
        )


def _loo_densities(matrix: np.ndarray, weights: np.ndarray) -> np.ndarray:
    values = np.asarray(matrix, dtype=float).copy()
    if values.shape != (weights.size, weights.size):
        raise ValueError("LOO kernel matrix must be square over fitted events.")
    np.fill_diagonal(values, 0.0)
    denominators = float(np.sum(weights)) - weights
    if np.any(denominators <= 0.0):
        raise ValueError("LOO objectives require positive leave-one-out weight.")
    return (weights @ values) / denominators


class NetworkTimeBandwidthExperiment:
    """Grid-search scalar network and temporal bandwidth pairs."""

    def __init__(
        self,
        spatial_candidates: object,
        temporal_candidates: object,
        *,
        mode: str = "joint",
        objective: str = "likelihood",
        spatial_kernel: str | BaseKernel = "epanechnikov",
        temporal_kernel: str | BaseKernel = "gaussian",
        junction_policy: str | JunctionPolicy = "simple",
        directed: bool | None = None,
        density_floor: float = 1e-300,
        cyclic_tail_tolerance: float = 1e-12,
        coefficient_tolerance: float = 1e-12,
        max_records_per_event: int = 100_000,
    ) -> None:
        self.spatial_candidates = _candidates(
            spatial_candidates, name="spatial_candidates"
        )
        self.temporal_candidates = _candidates(
            temporal_candidates, name="temporal_candidates"
        )
        if mode not in {"joint", "separate"}:
            raise ValueError("mode must be 'joint' or 'separate'.")
        if objective not in {"likelihood", "least_squares"}:
            raise ValueError("objective must be 'likelihood' or 'least_squares'.")
        floor = float(density_floor)
        tail = float(cyclic_tail_tolerance)
        coefficient = float(coefficient_tolerance)
        if not np.isfinite(floor) or floor <= 0.0:
            raise ValueError("density_floor must be finite and positive.")
        if not np.isfinite(tail) or not 0.0 < tail < 1.0:
            raise ValueError(
                "cyclic_tail_tolerance must lie strictly between zero and one."
            )
        if not np.isfinite(coefficient) or coefficient <= 0.0:
            raise ValueError("coefficient_tolerance must be finite and positive.")
        if isinstance(max_records_per_event, bool) or not isinstance(
            max_records_per_event, (int, np.integer)
        ):
            raise TypeError("max_records_per_event must be a positive integer.")
        if int(max_records_per_event) <= 0:
            raise ValueError("max_records_per_event must be greater than zero.")
        self.mode = mode
        self.objective = objective
        self.spatial_kernel = spatial_kernel
        self.temporal_kernel = temporal_kernel
        self.junction_policy = junction_policy
        self.directed = directed
        self.density_floor = floor
        self.cyclic_tail_tolerance = tail
        self.coefficient_tolerance = coefficient
        self.max_records_per_event = int(max_records_per_event)
        self.cache_: NetworkTimeSelectionCache | None = None
        self.result_: NetworkTimeBandwidthSelectionResult | None = None

    def _prepare_cache(
        self,
        workspace: NetworkTimeWorkspace,
        spatial_kernel: BaseKernel,
    ) -> tuple[NetworkTimeSelectionCache, JunctionPolicy]:
        if not isinstance(workspace, NetworkTimeWorkspace):
            raise TypeError("workspace must be NetworkTimeWorkspace.")
        workspace.validate().raise_for_errors()
        events = workspace.events
        if events.n_events < 2:
            raise ValueError("network-time selection requires at least two events.")
        policy = get_junction_policy(self.junction_policy)
        directed = _effective_directed(workspace, self.directed)
        if directed and not policy.supports_directed:
            raise ValueError(
                f"The '{policy.name}' junction policy requires an undirected network."
            )
        if policy.path_based and not spatial_kernel.finite_support:
            raise ValueError(
                "Path-based network-time selection requires a finite-support "
                "spatial kernel."
            )
        event_locations = NetworkLocations.from_events(events.network_events)
        event_asset = workspace.network_workspace.event_distance_asset
        if not _asset_usable(
            event_asset,
            source_fingerprint=event_locations.fingerprint,
            target_fingerprint=event_locations.fingerprint,
            directed=directed,
            cutoff=None,
        ):
            event_asset = build_event_event_distances(
                workspace.network,
                events.network_events,
                weight="length",
                directed=directed,
            )
        assert event_asset is not None
        upper = float(np.max(self.spatial_candidates))
        lixel_asset: NetworkDistanceAsset | None = None
        traces: tuple[PropagationTrace, ...] | None = None
        if policy.path_based:
            traces = tuple(
                trace_network_propagation(
                    workspace.network,
                    int(events.edge_indices[index]),
                    float(events.offsets[index]),
                    cutoff=upper,
                    junction_policy=policy,
                    directed=directed,
                    coefficient_tolerance=self.coefficient_tolerance,
                    max_records=self.max_records_per_event,
                    source_id=events.event_ids[index],
                )
                for index in range(events.n_events)
            )
        else:
            lixel_locations = NetworkLocations.from_lixels(workspace.lixels)
            cutoff = upper if spatial_kernel.finite_support else None
            candidate_asset = (
                None
                if workspace.distance_asset is None
                else workspace.distance_asset.network_distances
            )
            if _asset_usable(
                candidate_asset,
                source_fingerprint=event_locations.fingerprint,
                target_fingerprint=lixel_locations.fingerprint,
                directed=directed,
                cutoff=cutoff,
            ):
                lixel_asset = candidate_asset
            else:
                lixel_asset = build_event_lixel_distances(
                    workspace.network,
                    events.network_events,
                    workspace.lixels,
                    cutoff=cutoff,
                    weight="length",
                    directed=directed,
                )
        cache = NetworkTimeSelectionCache(
            event_event_distances=event_asset,
            event_lixel_distances=lixel_asset,
            propagation_traces=traces,
            event_temporal_offsets=events.times[None, :] - events.times[:, None],
            support_temporal_offsets=(
                workspace.arixels.time_centers[:, None] - events.times[None, :]
            ),
            upper_spatial_bandwidth=upper,
            junction_policy=policy.name,
            directed=directed,
            workspace_fingerprint=workspace.fingerprint,
        )
        self.cache_ = cache
        return cache, policy

    @staticmethod
    def _spatial_matrices(
        workspace: NetworkTimeWorkspace,
        cache: NetworkTimeSelectionCache,
        kernel: BaseKernel,
        bandwidth: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        if cache.propagation_traces is not None:
            return (
                evaluate_propagation_kernel_matrix(
                    cache.propagation_traces,
                    NetworkLocations.from_events(workspace.events.network_events),
                    kernel,
                    bandwidth,
                ),
                evaluate_propagation_kernel_matrix(
                    cache.propagation_traces,
                    NetworkLocations.from_lixels(workspace.lixels),
                    kernel,
                    bandwidth,
                ),
            )
        if cache.event_lixel_distances is None:
            raise RuntimeError("network-time cache lacks spatial support distances.")
        return (
            evaluate_distance_kernel_matrix(
                cache.event_event_distances, kernel, bandwidth
            ),
            evaluate_distance_kernel_matrix(
                cache.event_lixel_distances, kernel, bandwidth
            ),
        )

    def run(
        self, workspace: NetworkTimeWorkspace
    ) -> NetworkTimeBandwidthSelectionResult:
        """Evaluate the candidate grid using one reusable factorized cache."""
        self.cache_ = None
        self.result_ = None
        spatial_kernel = get_kernel(self.spatial_kernel)
        temporal_kernel = get_kernel(self.temporal_kernel)
        cache, _ = self._prepare_cache(workspace, spatial_kernel)
        events = workspace.events
        weights = validate_selection_weights(events.weights, events.n_events)
        normalized = weights / float(np.sum(weights))
        spatial_values = [
            self._spatial_matrices(workspace, cache, spatial_kernel, float(h))
            for h in self.spatial_candidates
        ]
        temporal_values = [
            (
                evaluate_temporal_kernel(
                    cache.event_temporal_offsets,
                    domain=events.temporal.domain,
                    kernel=temporal_kernel,
                    bandwidth=float(h),
                    tail_tolerance=self.cyclic_tail_tolerance,
                ),
                evaluate_temporal_kernel(
                    cache.support_temporal_offsets,
                    domain=events.temporal.domain,
                    kernel=temporal_kernel,
                    bandwidth=float(h),
                    tail_tolerance=self.cyclic_tail_tolerance,
                ),
            )
            for h in self.temporal_candidates
        ]
        scores = np.empty(
            (self.spatial_candidates.size, self.temporal_candidates.size),
            dtype=float,
        )
        for spatial_index, (event_spatial, lixel_spatial) in enumerate(spatial_values):
            for temporal_index, (event_temporal, support_temporal) in enumerate(
                temporal_values
            ):
                loo = _loo_densities(event_spatial * event_temporal, weights)
                if self.objective == "likelihood":
                    scores[spatial_index, temporal_index] = -float(
                        np.dot(
                            normalized,
                            np.log(np.maximum(loo, self.density_floor)),
                        )
                    )
                else:
                    density = (support_temporal * normalized[None, :]) @ lixel_spatial
                    integrated_square = float(
                        np.dot(density.ravel() ** 2, workspace.arixels.measure)
                    )
                    scores[spatial_index, temporal_index] = (
                        integrated_square - 2.0 * float(np.dot(normalized, loo))
                    )
        if self.mode == "joint":
            spatial_index, temporal_index = np.unravel_index(
                int(np.argmin(scores)), scores.shape
            )
        else:
            spatial_scores = np.empty(self.spatial_candidates.size, dtype=float)
            for index, (event_matrix, lixel_matrix) in enumerate(spatial_values):
                loo = _loo_densities(event_matrix, weights)
                if self.objective == "likelihood":
                    spatial_scores[index] = -float(
                        np.dot(
                            normalized,
                            np.log(np.maximum(loo, self.density_floor)),
                        )
                    )
                else:
                    density = normalized @ lixel_matrix
                    spatial_scores[index] = float(
                        np.dot(density**2, workspace.lixels.measure)
                        - 2.0 * np.dot(normalized, loo)
                    )
            temporal_scores = np.empty(self.temporal_candidates.size, dtype=float)
            for index, (event_matrix, support_matrix) in enumerate(temporal_values):
                loo = _loo_densities(event_matrix, weights)
                if self.objective == "likelihood":
                    temporal_scores[index] = -float(
                        np.dot(
                            normalized,
                            np.log(np.maximum(loo, self.density_floor)),
                        )
                    )
                else:
                    density = support_matrix @ normalized
                    temporal_scores[index] = float(
                        np.dot(density**2, workspace.arixels.time_widths)
                        - 2.0 * np.dot(normalized, loo)
                    )
            spatial_index = int(np.argmin(spatial_scores))
            temporal_index = int(np.argmin(temporal_scores))
        result = NetworkTimeBandwidthSelectionResult(
            spatial_bandwidth=float(self.spatial_candidates[spatial_index]),
            temporal_bandwidth=float(self.temporal_candidates[temporal_index]),
            score=float(scores[spatial_index, temporal_index]),
            mode=self.mode,
            objective=(
                "loo_likelihood"
                if self.objective == "likelihood"
                else "least_squares_cv"
            ),
            spatial_candidates=self.spatial_candidates,
            temporal_candidates=self.temporal_candidates,
            score_matrix=scores,
            cache_fingerprint=cache.fingerprint,
        )
        self.result_ = result
        return result
