# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Scalar bandwidth selectors for spatial KDE."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pykdex.core.results import BandwidthSelectionResult
from pykdex.kernels import BaseKernel
from pykdex.metrics import BaseMetric
from pykdex.selection.objectives import (
    least_squares_cv_score,
    likelihood_cv_score,
    validate_selection_weights,
)
from pykdex.selection.optimization import (
    minimize_bandwidth_objective,
    validate_bounds,
)


@dataclass(frozen=True)
class LikelihoodCV:
    """Select a scalar bandwidth by weighted leave-one-out log likelihood."""

    bounds: tuple[float, float] | None = None
    tolerance: float = 1e-5
    maxiter: int = 200
    density_floor: float = 1e-300

    def select(
        self,
        events: np.ndarray,
        *,
        weights: np.ndarray | None,
        kernel: BaseKernel,
        metric: BaseMetric,
    ) -> BandwidthSelectionResult:
        """Select and return a complete optimization result."""
        if not np.isfinite(self.density_floor) or self.density_floor <= 0.0:
            raise ValueError("density_floor must be finite and positive.")
        selector_weights = validate_selection_weights(weights, events.shape[0])
        distances = metric.pairwise(events, events)
        bounds = validate_bounds(self.bounds, distances)
        dimension = int(events.shape[1])
        return minimize_bandwidth_objective(
            lambda h: likelihood_cv_score(
                h,
                distances,
                selector_weights,
                kernel,
                dimension,
                density_floor=float(self.density_floor),
            ),
            method="likelihood_cv",
            bounds=bounds,
            tolerance=float(self.tolerance),
            maxiter=self.maxiter,
        )


@dataclass(frozen=True)
class LeastSquaresCV:
    """Select an exact scalar Gaussian bandwidth by least-squares CV."""

    bounds: tuple[float, float] | None = None
    tolerance: float = 1e-5
    maxiter: int = 200

    def select(
        self,
        events: np.ndarray,
        *,
        weights: np.ndarray | None,
        kernel: BaseKernel,
        metric: BaseMetric,
    ) -> BandwidthSelectionResult:
        """Select and return a complete optimization result."""
        if kernel.name != "gaussian":
            raise ValueError(
                "LeastSquaresCV currently has an exact implementation only for the "
                "Gaussian kernel."
            )
        selector_weights = validate_selection_weights(weights, events.shape[0])
        distances = metric.pairwise(events, events)
        bounds = validate_bounds(self.bounds, distances)
        dimension = int(events.shape[1])
        return minimize_bandwidth_objective(
            lambda h: least_squares_cv_score(
                h,
                distances,
                selector_weights,
                dimension,
            ),
            method="least_squares_cv",
            bounds=bounds,
            tolerance=float(self.tolerance),
            maxiter=self.maxiter,
        )
