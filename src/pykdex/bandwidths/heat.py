# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Fixed and cross-validated diffusion-time strategies for heat KDE."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from pykdex.core.results import BandwidthSelectionResult
from pykdex.network.heat import HeatComputePlan
from pykdex.network.workspace import NetworkWorkspace
from pykdex.selection.heat import HeatLeastSquaresCV, HeatLikelihoodCV


class BaseHeatTime(ABC):
    """Strategy resolving the positive diffusion time of ``HeatNetworkKDE``."""

    @property
    def selection_result(self) -> BandwidthSelectionResult | None:
        """Return the most recent selection result, when applicable."""
        return None

    @abstractmethod
    def resolve(
        self,
        workspace: NetworkWorkspace,
        *,
        compute_plan: HeatComputePlan,
    ) -> float:
        """Resolve one positive diffusion time for a prepared workspace."""


class FixedHeatTime(BaseHeatTime):
    """Use one explicitly supplied positive diffusion time."""

    def __init__(self, value: float | int | np.floating) -> None:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError("diffusion_time must not be boolean.")
        numeric = float(value)
        if not np.isfinite(numeric) or numeric <= 0.0:
            raise ValueError("diffusion_time must be finite and positive.")
        self.value = numeric

    def resolve(
        self,
        workspace: NetworkWorkspace,
        *,
        compute_plan: HeatComputePlan,
    ) -> float:
        if not isinstance(workspace, NetworkWorkspace):
            raise TypeError("workspace must be a NetworkWorkspace instance.")
        compute_plan.validate_workspace(workspace)
        return self.value


class HeatLikelihoodCVTime(BaseHeatTime):
    """Resolve diffusion time by heat-kernel leave-one-out likelihood."""

    def __init__(
        self,
        *,
        bounds: tuple[float, float] | None = None,
        tolerance: float = 1e-5,
        maxiter: int = 200,
        density_floor: float = 1e-300,
        negative_tolerance: float = 1e-10,
    ) -> None:
        self.selector = HeatLikelihoodCV(
            bounds=bounds,
            tolerance=tolerance,
            maxiter=maxiter,
            density_floor=density_floor,
            negative_tolerance=negative_tolerance,
        )
        self.result_: Optional[BandwidthSelectionResult] = None

    @property
    def selection_result(self) -> BandwidthSelectionResult | None:
        """Return the most recent likelihood-CV result."""
        return self.result_

    def resolve(
        self,
        workspace: NetworkWorkspace,
        *,
        compute_plan: HeatComputePlan,
    ) -> float:
        self.result_ = self.selector.select(workspace, compute_plan=compute_plan)
        return self.result_.bandwidth


class HeatLeastSquaresCVTime(BaseHeatTime):
    """Resolve diffusion time by exact finite-element least-squares CV."""

    def __init__(
        self,
        *,
        bounds: tuple[float, float] | None = None,
        tolerance: float = 1e-5,
        maxiter: int = 200,
        negative_tolerance: float = 1e-10,
    ) -> None:
        self.selector = HeatLeastSquaresCV(
            bounds=bounds,
            tolerance=tolerance,
            maxiter=maxiter,
            negative_tolerance=negative_tolerance,
        )
        self.result_: Optional[BandwidthSelectionResult] = None

    @property
    def selection_result(self) -> BandwidthSelectionResult | None:
        """Return the most recent least-squares-CV result."""
        return self.result_

    def resolve(
        self,
        workspace: NetworkWorkspace,
        *,
        compute_plan: HeatComputePlan,
    ) -> float:
        self.result_ = self.selector.select(workspace, compute_plan=compute_plan)
        return self.result_.bandwidth


def get_heat_time(
    diffusion_time: float | int | np.floating | BaseHeatTime,
) -> BaseHeatTime:
    """Resolve a numeric value or heat-specific diffusion-time strategy."""
    if isinstance(diffusion_time, BaseHeatTime):
        return diffusion_time
    return FixedHeatTime(diffusion_time)
