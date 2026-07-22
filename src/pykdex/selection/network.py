# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Bandwidth selection for kernel estimation on linear networks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from pykdex.core.results import BandwidthSelectionResult
from pykdex.kernels import BaseKernel
from pykdex.network.distance import (
    NetworkDistanceAsset,
    NetworkLocations,
    build_event_event_distances,
    build_event_lixel_distances,
)
from pykdex.network.evaluation import (
    evaluate_distance_kernel_matrix,
    evaluate_propagation_kernel_matrix,
)
from pykdex.network.propagation import (
    JunctionPolicy,
    PropagationTrace,
    get_junction_policy,
    trace_network_propagation,
)
from pykdex.network.workspace import NetworkWorkspace
from pykdex.selection.objectives import validate_selection_weights
from pykdex.selection.optimization import minimize_bandwidth_objective


def _effective_directed(workspace: NetworkWorkspace, directed: bool | None) -> bool:
    if directed is not None and not isinstance(directed, (bool, np.bool_)):
        raise TypeError("directed must be boolean or None.")
    requested = workspace.network.directed if directed is None else bool(directed)
    return bool(requested and workspace.network.directed)


def _validate_bounds(
    bounds: tuple[float, float] | None,
    distances: np.ndarray,
) -> tuple[float, float]:
    if bounds is not None:
        if not isinstance(bounds, tuple) or len(bounds) != 2:
            raise TypeError("bounds must be a (lower, upper) tuple or None.")
        lower, upper = float(bounds[0]), float(bounds[1])
        if not np.isfinite(lower) or not np.isfinite(upper) or lower <= 0.0:
            raise ValueError("bounds must be finite and strictly positive.")
        if not lower < upper:
            raise ValueError("bounds must satisfy lower < upper.")
        return lower, upper

    matrix = np.asarray(distances, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("network event distances must be a square matrix.")
    mask = ~np.eye(matrix.shape[0], dtype=bool)
    positive = matrix[mask & np.isfinite(matrix) & (matrix > 0.0)]
    if positive.size == 0:
        raise ValueError(
            "automatic network bandwidth bounds require at least two distinct "
            "mutually reachable event locations."
        )
    scale = float(np.median(positive))
    lower = max(float(np.quantile(positive, 0.05)) * 0.2, scale * 1e-6)
    upper = max(float(np.quantile(positive, 0.95)) * 2.0, lower * 10.0)
    return lower, upper


def _distance_asset_usable(
    asset: NetworkDistanceAsset | None,
    *,
    source_fingerprint: str,
    target_fingerprint: str,
    directed: bool,
    cutoff: float | None,
) -> bool:
    if asset is None:
        return False
    if asset.source_fingerprint != source_fingerprint:
        return False
    if asset.target_fingerprint != target_fingerprint:
        return False
    if asset.weight != "length" or asset.directed != directed:
        return False
    if cutoff is None:
        return asset.cutoff is None
    return asset.cutoff is None or asset.cutoff >= cutoff - 1e-12


@dataclass(frozen=True)
class NetworkSelectionCache:
    """Reusable distances and propagation traces for network CV objectives."""

    event_event_distances: NetworkDistanceAsset
    event_lixel_distances: NetworkDistanceAsset | None
    propagation_traces: tuple[PropagationTrace, ...] | None
    upper_bandwidth: float
    junction_policy: str
    directed: bool
    workspace_fingerprint: str


class _BaseNetworkSelector:
    def __init__(
        self,
        *,
        bounds: tuple[float, float] | None = None,
        tolerance: float = 1e-5,
        maxiter: int = 200,
    ) -> None:
        self.bounds = bounds
        self.tolerance = float(tolerance)
        self.maxiter = maxiter
        self.cache_: Optional[NetworkSelectionCache] = None

    def _prepare_cache(
        self,
        workspace: NetworkWorkspace,
        *,
        kernel: BaseKernel,
        junction_policy: str | JunctionPolicy,
        directed: bool | None,
        coefficient_tolerance: float,
        max_records_per_event: int,
    ) -> tuple[
        NetworkSelectionCache,
        tuple[float, float],
        np.ndarray,
        JunctionPolicy,
    ]:
        if not isinstance(workspace, NetworkWorkspace):
            raise TypeError("workspace must be a NetworkWorkspace instance.")
        workspace.validate().raise_for_errors()
        events = workspace.events
        if events is None:
            raise ValueError("workspace contains no accepted network events.")
        if events.n_events < 2:
            raise ValueError("network bandwidth selection requires at least two events.")
        policy = get_junction_policy(junction_policy)
        effective_directed = _effective_directed(workspace, directed)
        if effective_directed and not policy.supports_directed:
            raise ValueError(
                f"The '{policy.name}' junction policy requires an undirected network."
            )
        if policy.path_based and not kernel.finite_support:
            raise ValueError(
                "Path-based network bandwidth selection requires a finite-support "
                "kernel."
            )

        event_locations = NetworkLocations.from_events(events)
        event_asset = workspace.event_distance_asset
        if not _distance_asset_usable(
            event_asset,
            source_fingerprint=event_locations.fingerprint,
            target_fingerprint=event_locations.fingerprint,
            directed=effective_directed,
            cutoff=None,
        ):
            event_asset = build_event_event_distances(
                workspace.network,
                events,
                cutoff=None,
                weight="length",
                directed=effective_directed,
            )
        assert event_asset is not None
        dense_event_distances = event_asset.to_dense()
        bounds = _validate_bounds(self.bounds, dense_event_distances)
        upper = float(bounds[1])

        event_lixel_asset: NetworkDistanceAsset | None = None
        traces: tuple[PropagationTrace, ...] | None = None
        if policy.path_based:
            traces = tuple(
                trace_network_propagation(
                    workspace.network,
                    int(events.edge_indices[index]),
                    float(events.offsets[index]),
                    cutoff=upper,
                    junction_policy=policy,
                    directed=effective_directed,
                    coefficient_tolerance=coefficient_tolerance,
                    max_records=max_records_per_event,
                    source_id=events.event_ids[index],
                )
                for index in range(events.n_events)
            )
        else:
            lixel_locations = NetworkLocations.from_lixels(workspace.lixels)
            cutoff = upper if kernel.finite_support else None
            event_lixel_asset = workspace.distance_asset
            if not _distance_asset_usable(
                event_lixel_asset,
                source_fingerprint=event_locations.fingerprint,
                target_fingerprint=lixel_locations.fingerprint,
                directed=effective_directed,
                cutoff=cutoff,
            ):
                event_lixel_asset = build_event_lixel_distances(
                    workspace.network,
                    events,
                    workspace.lixels,
                    cutoff=cutoff,
                    weight="length",
                    directed=effective_directed,
                )

        cache = NetworkSelectionCache(
            event_event_distances=event_asset,
            event_lixel_distances=event_lixel_asset,
            propagation_traces=traces,
            upper_bandwidth=upper,
            junction_policy=policy.name,
            directed=effective_directed,
            workspace_fingerprint=workspace.fingerprint,
        )
        self.cache_ = cache
        return cache, bounds, dense_event_distances, policy


def _kernel_matrices(
    workspace: NetworkWorkspace,
    cache: NetworkSelectionCache,
    kernel: BaseKernel,
    bandwidth: float,
) -> tuple[np.ndarray, np.ndarray]:
    events = workspace.events
    if events is None:
        raise RuntimeError("workspace events became unavailable.")
    if cache.propagation_traces is not None:
        event_matrix = evaluate_propagation_kernel_matrix(
            cache.propagation_traces,
            NetworkLocations.from_events(events),
            kernel,
            bandwidth,
        )
        lixel_matrix = evaluate_propagation_kernel_matrix(
            cache.propagation_traces,
            NetworkLocations.from_lixels(workspace.lixels),
            kernel,
            bandwidth,
        )
        return event_matrix, lixel_matrix

    if cache.event_lixel_distances is None:
        raise RuntimeError("simple network selection cache lacks lixel distances.")
    event_matrix = evaluate_distance_kernel_matrix(
        cache.event_event_distances,
        kernel,
        bandwidth,
    )
    lixel_matrix = evaluate_distance_kernel_matrix(
        cache.event_lixel_distances,
        kernel,
        bandwidth,
    )
    return event_matrix, lixel_matrix


def _loo_densities(kernel_matrix: np.ndarray, weights: np.ndarray) -> np.ndarray:
    matrix = np.asarray(kernel_matrix, dtype=float).copy()
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("event kernel matrix must be square.")
    np.fill_diagonal(matrix, 0.0)
    weight_sum = float(np.sum(weights))
    denominators = weight_sum - weights
    numerators = weights @ matrix
    return np.divide(
        numerators,
        denominators,
        out=np.zeros_like(weights, dtype=float),
        where=denominators > 0.0,
    )


class NetworkLikelihoodCV(_BaseNetworkSelector):
    """Select a scalar network bandwidth by weighted LOO likelihood."""

    def __init__(
        self,
        *,
        bounds: tuple[float, float] | None = None,
        tolerance: float = 1e-5,
        maxiter: int = 200,
        density_floor: float = 1e-300,
    ) -> None:
        super().__init__(bounds=bounds, tolerance=tolerance, maxiter=maxiter)
        floor = float(density_floor)
        if not np.isfinite(floor) or floor <= 0.0:
            raise ValueError("density_floor must be finite and positive.")
        self.density_floor = floor

    def select(
        self,
        workspace: NetworkWorkspace,
        *,
        kernel: BaseKernel,
        junction_policy: str | JunctionPolicy = "simple",
        directed: bool | None = None,
        coefficient_tolerance: float = 1e-12,
        max_records_per_event: int = 100_000,
    ) -> BandwidthSelectionResult:
        """Select and return a complete network optimization result."""
        events = workspace.events
        if events is None:
            raise ValueError("workspace contains no accepted network events.")
        weights = validate_selection_weights(events.weights, events.n_events)
        cache, bounds, _, _ = self._prepare_cache(
            workspace,
            kernel=kernel,
            junction_policy=junction_policy,
            directed=directed,
            coefficient_tolerance=coefficient_tolerance,
            max_records_per_event=max_records_per_event,
        )
        normalized = weights / float(np.sum(weights))

        def objective(h: float) -> float:
            event_matrix, _ = _kernel_matrices(workspace, cache, kernel, h)
            densities = np.maximum(
                _loo_densities(event_matrix, weights), self.density_floor
            )
            score = -float(np.dot(normalized, np.log(densities)))
            return score if np.isfinite(score) else float(np.finfo(float).max)

        return minimize_bandwidth_objective(
            objective,
            method="network_likelihood_cv",
            bounds=bounds,
            tolerance=self.tolerance,
            maxiter=self.maxiter,
        )


class NetworkLeastSquaresCV(_BaseNetworkSelector):
    """Select a scalar network bandwidth by lixel-integrated LSCV."""

    def select(
        self,
        workspace: NetworkWorkspace,
        *,
        kernel: BaseKernel,
        junction_policy: str | JunctionPolicy = "simple",
        directed: bool | None = None,
        coefficient_tolerance: float = 1e-12,
        max_records_per_event: int = 100_000,
    ) -> BandwidthSelectionResult:
        """Select bandwidth using measured lixels for the squared-density integral."""
        events = workspace.events
        if events is None:
            raise ValueError("workspace contains no accepted network events.")
        weights = validate_selection_weights(events.weights, events.n_events)
        cache, bounds, _, _ = self._prepare_cache(
            workspace,
            kernel=kernel,
            junction_policy=junction_policy,
            directed=directed,
            coefficient_tolerance=coefficient_tolerance,
            max_records_per_event=max_records_per_event,
        )
        normalized = weights / float(np.sum(weights))

        def objective(h: float) -> float:
            event_matrix, lixel_matrix = _kernel_matrices(
                workspace, cache, kernel, h
            )
            density = normalized @ lixel_matrix
            integrated_square = float(
                np.dot(density * density, workspace.lixels.measure)
            )
            loo = _loo_densities(event_matrix, weights)
            score = integrated_square - 2.0 * float(np.dot(normalized, loo))
            return score if np.isfinite(score) else float(np.finfo(float).max)

        return minimize_bandwidth_objective(
            objective,
            method="network_least_squares_cv",
            bounds=bounds,
            tolerance=self.tolerance,
            maxiter=self.maxiter,
        )
