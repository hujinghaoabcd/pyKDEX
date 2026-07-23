# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Diffusion-time selection for metric-graph heat KDE."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from pykdex.core.results import BandwidthSelectionResult
from pykdex.network.distance import build_event_event_distances
from pykdex.network.heat import HeatComputePlan, build_heat_compute_plan
from pykdex.network.workspace import NetworkWorkspace
from pykdex.selection.objectives import validate_selection_weights
from pykdex.selection.optimization import minimize_bandwidth_objective


def _validate_heat_bounds(
    bounds: tuple[float, float] | None,
    workspace: NetworkWorkspace,
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

    events = workspace.events
    if events is None:
        raise ValueError("workspace contains no accepted network events.")
    distances = build_event_event_distances(
        workspace.network,
        events,
        weight="length",
        directed=False,
    ).to_dense()
    mask = ~np.eye(events.n_events, dtype=bool)
    positive = distances[mask & np.isfinite(distances) & (distances > 0.0)]
    if positive.size == 0:
        raise ValueError(
            "automatic heat-time bounds require at least two distinct mutually "
            "reachable event locations."
        )
    scale = float(np.median(positive))
    lower_distance = max(
        float(np.quantile(positive, 0.05)) * 0.2,
        scale * 1e-6,
    )
    upper_distance = max(
        float(np.quantile(positive, 0.95)) * 2.0,
        lower_distance * np.sqrt(10.0),
    )
    return 0.5 * lower_distance**2, 0.5 * upper_distance**2


def _loo_densities(kernel_matrix: np.ndarray, weights: np.ndarray) -> np.ndarray:
    matrix = np.asarray(kernel_matrix, dtype=float).copy()
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("event heat-kernel matrix must be square.")
    np.fill_diagonal(matrix, 0.0)
    denominators = float(np.sum(weights)) - weights
    numerators = weights @ matrix
    return np.divide(
        numerators,
        denominators,
        out=np.zeros_like(weights, dtype=float),
        where=denominators > 0.0,
    )


@dataclass(frozen=True)
class HeatSelectionCache:
    """Reusable heat plan and immutable selection identity."""

    compute_plan: HeatComputePlan
    bounds: tuple[float, float]
    workspace_fingerprint: str


class _BaseHeatSelector:
    def __init__(
        self,
        *,
        bounds: tuple[float, float] | None = None,
        tolerance: float = 1e-5,
        maxiter: int = 200,
        negative_tolerance: float = 1e-10,
    ) -> None:
        if bounds is not None:
            if not isinstance(bounds, tuple) or len(bounds) != 2:
                raise TypeError("bounds must be a (lower, upper) tuple or None.")
            lower, upper = float(bounds[0]), float(bounds[1])
            if not np.isfinite(lower) or not np.isfinite(upper) or lower <= 0.0:
                raise ValueError("bounds must be finite and strictly positive.")
            if not lower < upper:
                raise ValueError("bounds must satisfy lower < upper.")
        if not np.isfinite(float(tolerance)) or float(tolerance) <= 0.0:
            raise ValueError("tolerance must be finite and positive.")
        if isinstance(maxiter, (bool, np.bool_)) or not isinstance(
            maxiter, (int, np.integer)
        ):
            raise TypeError("maxiter must be a positive integer.")
        if int(maxiter) <= 0:
            raise ValueError("maxiter must be greater than zero.")
        if isinstance(negative_tolerance, (bool, np.bool_)):
            raise TypeError("negative_tolerance must not be boolean.")
        resolved_negative = float(negative_tolerance)
        if not np.isfinite(resolved_negative) or resolved_negative <= 0.0:
            raise ValueError("negative_tolerance must be finite and positive.")
        self.bounds = bounds
        self.tolerance = float(tolerance)
        self.maxiter = int(maxiter)
        self.negative_tolerance = resolved_negative
        self.cache_: Optional[HeatSelectionCache] = None

    def _prepare(
        self,
        workspace: NetworkWorkspace,
        *,
        compute_plan: HeatComputePlan | None,
        mesh_size: float | None,
        dense_threshold: int,
    ) -> tuple[HeatSelectionCache, np.ndarray]:
        if not isinstance(workspace, NetworkWorkspace):
            raise TypeError("workspace must be a NetworkWorkspace instance.")
        workspace.validate().raise_for_errors()
        events = workspace.events
        if events is None:
            raise ValueError("workspace contains no accepted network events.")
        if events.n_events < 2:
            raise ValueError(
                "heat diffusion-time selection requires at least two events."
            )
        weights = validate_selection_weights(events.weights, events.n_events)
        plan = (
            build_heat_compute_plan(
                workspace,
                mesh_size=mesh_size,
                dense_threshold=dense_threshold,
            )
            if compute_plan is None
            else compute_plan
        )
        if not isinstance(plan, HeatComputePlan):
            raise TypeError("compute_plan must be a HeatComputePlan or None.")
        plan.validate_workspace(workspace)
        bounds = _validate_heat_bounds(self.bounds, workspace)
        cache = HeatSelectionCache(
            compute_plan=plan,
            bounds=bounds,
            workspace_fingerprint=workspace.fingerprint,
        )
        self.cache_ = cache
        return cache, weights

    def _heat_assets(
        self,
        cache: HeatSelectionCache,
        diffusion_time: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        nodal = cache.compute_plan.event_nodal_kernels(diffusion_time)
        minimum = float(np.min(nodal))
        if minimum < -self.negative_tolerance:
            raise FloatingPointError(
                "heat selection exceeded the configured negative roundoff tolerance."
            )
        nodal = np.maximum(nodal, 0.0)
        event_dofs = cache.compute_plan.operator.event_dofs
        event_matrix = np.asarray(nodal[event_dofs, :].T, dtype=float)
        return nodal, event_matrix


class HeatLikelihoodCV(_BaseHeatSelector):
    """Select heat diffusion time by weighted leave-one-out likelihood.

    The ``bandwidth`` field of the returned generic
    :class:`BandwidthSelectionResult` stores the selected diffusion time.
    """

    def __init__(
        self,
        *,
        bounds: tuple[float, float] | None = None,
        tolerance: float = 1e-5,
        maxiter: int = 200,
        density_floor: float = 1e-300,
        negative_tolerance: float = 1e-10,
    ) -> None:
        super().__init__(
            bounds=bounds,
            tolerance=tolerance,
            maxiter=maxiter,
            negative_tolerance=negative_tolerance,
        )
        floor = float(density_floor)
        if not np.isfinite(floor) or floor <= 0.0:
            raise ValueError("density_floor must be finite and positive.")
        self.density_floor = floor

    def select(
        self,
        workspace: NetworkWorkspace,
        *,
        compute_plan: HeatComputePlan | None = None,
        mesh_size: float | None = None,
        dense_threshold: int = 1_024,
    ) -> BandwidthSelectionResult:
        """Select one positive diffusion time."""
        cache, weights = self._prepare(
            workspace,
            compute_plan=compute_plan,
            mesh_size=mesh_size,
            dense_threshold=dense_threshold,
        )
        normalized = weights / float(np.sum(weights))

        def objective(diffusion_time: float) -> float:
            _, event_matrix = self._heat_assets(cache, diffusion_time)
            densities = np.maximum(
                _loo_densities(event_matrix, weights),
                self.density_floor,
            )
            score = -float(np.dot(normalized, np.log(densities)))
            return score if np.isfinite(score) else float(np.finfo(float).max)

        return minimize_bandwidth_objective(
            objective,
            method="heat_likelihood_cv",
            bounds=cache.bounds,
            tolerance=self.tolerance,
            maxiter=self.maxiter,
        )


class HeatLeastSquaresCV(_BaseHeatSelector):
    """Select heat diffusion time by exact finite-element LSCV."""

    def select(
        self,
        workspace: NetworkWorkspace,
        *,
        compute_plan: HeatComputePlan | None = None,
        mesh_size: float | None = None,
        dense_threshold: int = 1_024,
    ) -> BandwidthSelectionResult:
        """Select time using exact piecewise-linear squared-field integration."""
        cache, weights = self._prepare(
            workspace,
            compute_plan=compute_plan,
            mesh_size=mesh_size,
            dense_threshold=dense_threshold,
        )
        normalized = weights / float(np.sum(weights))

        def objective(diffusion_time: float) -> float:
            nodal, event_matrix = self._heat_assets(cache, diffusion_time)
            density = nodal @ normalized
            integrated_square = cache.compute_plan.operator.integrate_squared(density)
            loo = _loo_densities(event_matrix, weights)
            score = integrated_square - 2.0 * float(np.dot(normalized, loo))
            return score if np.isfinite(score) else float(np.finfo(float).max)

        return minimize_bandwidth_objective(
            objective,
            method="heat_least_squares_cv",
            bounds=cache.bounds,
            tolerance=self.tolerance,
            maxiter=self.maxiter,
        )
