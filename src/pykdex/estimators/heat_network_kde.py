# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Heat-equation kernel density estimation on metric graphs."""

from __future__ import annotations

from typing import Optional

import numpy as np

from pykdex.bandwidths.heat import BaseHeatTime, get_heat_time
from pykdex.core.base import BaseKDE
from pykdex.core.network_results import NetworkField
from pykdex.core.results import BandwidthSelectionResult
from pykdex.network.events import NetworkEvents
from pykdex.network.heat import (
    HeatComputePlan,
    NetworkHeatOperator,
    build_heat_compute_plan,
    normalize_heat_solution,
)
from pykdex.network.support import LixelSupport
from pykdex.network.workspace import NetworkWorkspace


class HeatNetworkKDE(BaseKDE):
    r"""Heat-kernel density or intensity estimation on an undirected network.

    The estimator solves

    \[
    M \frac{du}{dt} + Ku = 0
    \]

    with a measured piecewise-linear finite-element discretization. Shared
    vertex degrees of freedom enforce continuity; the weak formulation enforces
    Kirchhoff flux balance and natural zero flux at terminal vertices.

    Args:
        diffusion_time: Positive heat diffusion time or a heat-time strategy.
        mesh_size: Maximum finite-element length. Defaults to the workspace
            lixel target length. Event offsets and lixel boundaries are always
            inserted, even when closer than this value.
        target: ``"density"`` or ``"intensity"``.
        negative_tolerance: Maximum tolerated negative solver roundoff.
        random_state: Reserved deterministic random seed.
        verbose: Print estimator progress.
    """

    def __init__(
        self,
        diffusion_time: float | BaseHeatTime = 1.0,
        *,
        mesh_size: float | None = None,
        target: str = "density",
        negative_tolerance: float = 1e-10,
        random_state: Optional[int] = None,
        verbose: bool = False,
    ) -> None:
        super().__init__(target=target, random_state=random_state, verbose=verbose)
        strategy = get_heat_time(diffusion_time)
        if mesh_size is not None:
            if isinstance(mesh_size, (bool, np.bool_)):
                raise TypeError("mesh_size must not be boolean.")
            size = float(mesh_size)
            if not np.isfinite(size) or size <= 0.0:
                raise ValueError("mesh_size must be finite and positive or None.")
        if isinstance(negative_tolerance, (bool, np.bool_)):
            raise TypeError("negative_tolerance must not be boolean.")
        tolerance = float(negative_tolerance)
        if not np.isfinite(tolerance) or tolerance <= 0.0:
            raise ValueError("negative_tolerance must be finite and positive.")
        self.diffusion_time = diffusion_time
        self.diffusion_time_strategy = strategy
        self.mesh_size = None if mesh_size is None else float(mesh_size)
        self.negative_tolerance = tolerance
        self._reset_fit_state()

    def _reset_fit_state(self) -> None:
        self._mark_unfitted()
        self._reset_common_state()
        self.workspace_: NetworkWorkspace | None = None
        self.network_events_: NetworkEvents | None = None
        self.lixels_: LixelSupport | None = None
        self.heat_operator_: NetworkHeatOperator | None = None
        self.heat_compute_plan_: HeatComputePlan | None = None
        self.diffusion_time_: float | None = None
        self.diffusion_time_selection_: BandwidthSelectionResult | None = None
        self.nodal_values_: np.ndarray | None = None
        self.values_: np.ndarray | None = None
        self.component_mass_error_: float | None = None
        self.raw_minimum_: float | None = None
        self.vertex_continuity_error_: float | None = None

    def fit(
        self,
        workspace: NetworkWorkspace,
        *,
        compute_plan: HeatComputePlan | None = None,
    ) -> "HeatNetworkKDE":
        """Fit and evaluate the heat kernel on a prepared workspace."""
        self._reset_fit_state()
        try:
            if not isinstance(workspace, NetworkWorkspace):
                raise TypeError("workspace must be a NetworkWorkspace instance.")
            workspace.validate().raise_for_errors()
            events = workspace.events
            if events is None:
                raise ValueError("workspace contains no accepted network events.")
            plan = (
                build_heat_compute_plan(workspace, mesh_size=self.mesh_size)
                if compute_plan is None
                else compute_plan
            )
            if not isinstance(plan, HeatComputePlan):
                raise TypeError("compute_plan must be a HeatComputePlan or None.")
            plan.validate_workspace(workspace)
            if self.mesh_size is not None and not np.isclose(
                plan.operator.mesh_size, self.mesh_size
            ):
                raise ValueError(
                    "compute_plan mesh_size does not match the estimator mesh_size."
                )
            operator = plan.operator
            diffusion_time = self.diffusion_time_strategy.resolve(
                workspace,
                compute_plan=plan,
            )
            self.diffusion_time_selection_ = (
                self.diffusion_time_strategy.selection_result
            )
            coefficients = (
                events.weights / events.weight_sum
                if self.target == "density"
                else events.weights
            )
            source_mass = np.zeros(operator.n_dofs, dtype=float)
            np.add.at(source_mass, operator.event_dofs, coefficients)
            raw_values = plan.evolve(source_mass, diffusion_time)[0, :, 0]
            nodal_values, component_error, raw_minimum = normalize_heat_solution(
                operator,
                raw_values,
                coefficients,
                negative_tolerance=self.negative_tolerance,
            )

            lixel_values = operator.lixel_averages(nodal_values, workspace)
            if not np.all(np.isfinite(lixel_values)) or np.any(lixel_values < 0.0):
                raise FloatingPointError(
                    "HeatNetworkKDE lixel integration produced invalid values."
                )
            owned_nodal = np.ascontiguousarray(nodal_values.copy())
            owned_nodal.setflags(write=False)
            owned_values = np.ascontiguousarray(lixel_values.copy())
            owned_values.setflags(write=False)
            bandwidth = float(np.sqrt(2.0 * diffusion_time))

            self.workspace_ = workspace
            self.network_events_ = events
            self.lixels_ = workspace.lixels
            self.heat_operator_ = operator
            self.heat_compute_plan_ = plan
            self.diffusion_time_ = diffusion_time
            self.nodal_values_ = owned_nodal
            self.values_ = owned_values
            self.component_mass_error_ = component_error
            self.raw_minimum_ = raw_minimum
            self.vertex_continuity_error_ = 0.0
            self.events_ = np.ascontiguousarray(events.coordinates.copy())
            self.weights_ = np.ascontiguousarray(events.weights.copy())
            self.n_events_ = events.n_events
            self.dimension_ = 1
            self.coordinate_names_in_ = np.asarray(["network_distance"], dtype=object)
            self.weight_sum_ = events.weight_sum
            self.bandwidth_ = bandwidth
            self.event_crs_ = events.crs
            self.spatial_unit_ = events.spatial_unit
            self.event_fingerprint_ = events.fingerprint
            self.fit_metadata_ = {
                "kernel": "heat",
                "target": self.target,
                "junction_policy": "kirchhoff",
                "diffusion_time": diffusion_time,
                "diffusion_time_selected": (self.diffusion_time_selection_ is not None),
                "equivalent_gaussian_bandwidth": bandwidth,
                "mesh_size": operator.mesh_size,
                "n_heat_dofs": operator.n_dofs,
                "n_heat_segments": operator.n_segments,
                "n_events": events.n_events,
                "n_lixels": workspace.lixels.n_lixels,
                "directed": False,
                "network_fingerprint": workspace.network.fingerprint,
                "event_fingerprint": events.fingerprint,
                "support_fingerprint": workspace.lixels.fingerprint,
                "heat_operator_fingerprint": operator.fingerprint,
                "heat_compute_plan_fingerprint": plan.fingerprint,
                "heat_compute_plan_memory_bytes": plan.memory_bytes,
                "raw_minimum_before_clipping": raw_minimum,
                "component_mass_error_before_normalization": (
                    self.component_mass_error_
                ),
                "vertex_continuity_error": self.vertex_continuity_error_,
                "lixel_evaluation": "cell_average",
                "terminal_boundary": "neumann",
                "solver": plan.solver,
            }
            self._mark_fitted()
            return self
        except Exception:
            self._reset_fit_state()
            raise

    def evaluate(self) -> np.ndarray:
        """Return fitted lixel-average heat density or intensity."""
        self._check_is_fitted()
        if self.values_ is None:
            raise RuntimeError("Fitted heat values are unavailable.")
        return self.values_.copy()

    predict = evaluate

    def predict_result(self) -> NetworkField:
        """Return the fitted heat solution as a measured network field."""
        self._check_is_fitted()
        if (
            self.values_ is None
            or self.lixels_ is None
            or self.workspace_ is None
            or self.event_fingerprint_ is None
            or self.bandwidth_ is None
        ):
            raise RuntimeError("Fitted estimator components are unavailable.")
        return NetworkField(
            values=self.values_,
            support=self.lixels_,
            bandwidth=self.bandwidth_,
            target=self.target,
            kernel="heat",
            junction_policy="kirchhoff",
            directed=False,
            network_fingerprint=self.workspace_.network.fingerprint,
            event_fingerprint=self.event_fingerprint_,
            metadata=dict(self.fit_metadata_ or {}),
        )

    def fit_predict(
        self,
        workspace: NetworkWorkspace,
        *,
        compute_plan: HeatComputePlan | None = None,
    ) -> NetworkField:
        """Fit a workspace and immediately return its heat network field."""
        return self.fit(workspace, compute_plan=compute_plan).predict_result()
