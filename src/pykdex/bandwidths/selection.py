# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Bandwidth strategies backed by cross-validation selectors."""

from __future__ import annotations

from typing import Optional

import numpy as np

from pykdex.bandwidths.base import BaseBandwidth
from pykdex.core.results import BandwidthSelectionResult
from pykdex.kernels import BaseKernel
from pykdex.metrics import BaseMetric
from pykdex.selection import LeastSquaresCV, LikelihoodCV


class LikelihoodCVBandwidth(BaseBandwidth):
    """Resolve one scalar bandwidth by leave-one-out likelihood CV."""

    def __init__(
        self,
        *,
        bounds: tuple[float, float] | None = None,
        tolerance: float = 1e-5,
        maxiter: int = 200,
        density_floor: float = 1e-300,
    ) -> None:
        self.selector = LikelihoodCV(
            bounds=bounds,
            tolerance=tolerance,
            maxiter=maxiter,
            density_floor=density_floor,
        )
        self.result_: Optional[BandwidthSelectionResult] = None

    def resolve(
        self,
        events: np.ndarray,
        *,
        weights: np.ndarray | None = None,
        metric: BaseMetric | None = None,
        kernel: BaseKernel | None = None,
    ) -> float:
        if metric is None or kernel is None:
            raise ValueError("likelihood CV requires a metric and kernel context.")
        self.result_ = self.selector.select(
            events,
            weights=weights,
            kernel=kernel,
            metric=metric,
        )
        return self.result_.bandwidth


class LeastSquaresCVBandwidth(BaseBandwidth):
    """Resolve one scalar Gaussian bandwidth by least-squares CV."""

    def __init__(
        self,
        *,
        bounds: tuple[float, float] | None = None,
        tolerance: float = 1e-5,
        maxiter: int = 200,
    ) -> None:
        self.selector = LeastSquaresCV(
            bounds=bounds,
            tolerance=tolerance,
            maxiter=maxiter,
        )
        self.result_: Optional[BandwidthSelectionResult] = None

    def resolve(
        self,
        events: np.ndarray,
        *,
        weights: np.ndarray | None = None,
        metric: BaseMetric | None = None,
        kernel: BaseKernel | None = None,
    ) -> float:
        if metric is None or kernel is None:
            raise ValueError("least-squares CV requires a metric and kernel context.")
        self.result_ = self.selector.select(
            events,
            weights=weights,
            kernel=kernel,
            metric=metric,
        )
        return self.result_.bandwidth
