# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Batched diffusion-time experiments for metric-graph heat KDE."""

from __future__ import annotations

from typing import Optional

import numpy as np

from pykdex.core.heat_results import HeatNetworkBatchResult
from pykdex.core.network_results import NetworkField
from pykdex.network.heat import (
    HeatComputePlan,
    build_heat_compute_plan,
    normalize_heat_solution,
)
from pykdex.network.workspace import NetworkWorkspace


class HeatNetworkExperiment:
    """Evaluate several heat diffusion times with one reusable compute plan.

    Requested time order and duplicates are retained in the returned batch.
    Dense plans reuse one eigendecomposition; sparse plans reuse one assembled
    generator and apply deterministic Krylov exponential products.
    """

    def __init__(
        self,
        diffusion_times: np.ndarray | list[float] | tuple[float, ...],
        *,
        mesh_size: float | None = None,
        target: str = "density",
        dense_threshold: int = 1_024,
        negative_tolerance: float = 1e-10,
        random_state: Optional[int] = None,
    ) -> None:
        raw_times = np.asarray(diffusion_times)
        if raw_times.dtype.kind == "b":
            raise TypeError("diffusion_times must not contain boolean values.")
        times = np.asarray(diffusion_times, dtype=float)
        if times.ndim != 1 or times.size == 0:
            raise ValueError(
                "diffusion_times must be a non-empty one-dimensional array."
            )
        if not np.all(np.isfinite(times)) or np.any(times <= 0.0):
            raise ValueError("diffusion_times must contain finite positive values.")
        if mesh_size is not None:
            if isinstance(mesh_size, (bool, np.bool_)):
                raise TypeError("mesh_size must not be boolean.")
            resolved_mesh = float(mesh_size)
            if not np.isfinite(resolved_mesh) or resolved_mesh <= 0.0:
                raise ValueError("mesh_size must be finite and positive or None.")
        else:
            resolved_mesh = None
        resolved_target = str(target).strip().lower()
        if resolved_target not in {"density", "intensity"}:
            raise ValueError("target must be either 'density' or 'intensity'.")
        if isinstance(dense_threshold, (bool, np.bool_)) or not isinstance(
            dense_threshold, (int, np.integer)
        ):
            raise TypeError("dense_threshold must be a positive integer.")
        if int(dense_threshold) <= 0:
            raise ValueError("dense_threshold must be greater than zero.")
        if isinstance(negative_tolerance, (bool, np.bool_)):
            raise TypeError("negative_tolerance must not be boolean.")
        tolerance = float(negative_tolerance)
        if not np.isfinite(tolerance) or tolerance <= 0.0:
            raise ValueError("negative_tolerance must be finite and positive.")

        owned = np.ascontiguousarray(times.copy())
        owned.setflags(write=False)
        self.diffusion_times = owned
        self.mesh_size = resolved_mesh
        self.target = resolved_target
        self.dense_threshold = int(dense_threshold)
        self.negative_tolerance = tolerance
        self.random_state = random_state
        self.compute_plan_: HeatComputePlan | None = None
        self.result_: HeatNetworkBatchResult | None = None

    def run(
        self,
        workspace: NetworkWorkspace,
        *,
        compute_plan: HeatComputePlan | None = None,
    ) -> HeatNetworkBatchResult:
        """Evaluate every requested time and return immutable measured fields."""
        if not isinstance(workspace, NetworkWorkspace):
            raise TypeError("workspace must be a NetworkWorkspace instance.")
        workspace.validate().raise_for_errors()
        events = workspace.events
        if events is None:
            raise ValueError("workspace contains no accepted network events.")
        plan = (
            build_heat_compute_plan(
                workspace,
                mesh_size=self.mesh_size,
                dense_threshold=self.dense_threshold,
            )
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
                "compute_plan mesh_size does not match the experiment mesh_size."
            )

        coefficients = (
            events.weights / events.weight_sum
            if self.target == "density"
            else events.weights
        )
        source_mass = np.zeros(plan.operator.n_dofs, dtype=float)
        np.add.at(source_mass, plan.operator.event_dofs, coefficients)
        raw_batch = plan.evolve(source_mass, self.diffusion_times)[:, :, 0]
        fields: list[NetworkField] = []
        component_errors: list[float] = []
        raw_minima: list[float] = []
        for time, raw_values in zip(self.diffusion_times, raw_batch, strict=True):
            nodal, component_error, raw_minimum = normalize_heat_solution(
                plan.operator,
                raw_values,
                coefficients,
                negative_tolerance=self.negative_tolerance,
            )
            lixel_values = plan.operator.lixel_averages(nodal, workspace)
            equivalent_bandwidth = float(np.sqrt(2.0 * float(time)))
            metadata = {
                "kernel": "heat",
                "target": self.target,
                "junction_policy": "kirchhoff",
                "diffusion_time": float(time),
                "equivalent_gaussian_bandwidth": equivalent_bandwidth,
                "mesh_size": plan.operator.mesh_size,
                "n_heat_dofs": plan.operator.n_dofs,
                "n_heat_segments": plan.operator.n_segments,
                "heat_operator_fingerprint": plan.operator.fingerprint,
                "heat_compute_plan_fingerprint": plan.fingerprint,
                "heat_compute_plan_memory_bytes": plan.memory_bytes,
                "solver": plan.solver,
                "raw_minimum_before_clipping": raw_minimum,
                "component_mass_error_before_normalization": component_error,
                "lixel_evaluation": "cell_average",
                "terminal_boundary": "neumann",
                "batch_evaluation": True,
            }
            fields.append(
                NetworkField(
                    values=lixel_values,
                    support=workspace.lixels,
                    bandwidth=equivalent_bandwidth,
                    target=self.target,
                    kernel="heat",
                    junction_policy="kirchhoff",
                    directed=False,
                    network_fingerprint=workspace.network.fingerprint,
                    event_fingerprint=events.fingerprint,
                    metadata=metadata,
                )
            )
            component_errors.append(component_error)
            raw_minima.append(raw_minimum)

        result = HeatNetworkBatchResult(
            diffusion_times=self.diffusion_times,
            fields=tuple(fields),
            compute_plan_fingerprint=plan.fingerprint,
            metadata={
                "solver": plan.solver,
                "mesh_size": plan.operator.mesh_size,
                "n_heat_dofs": plan.operator.n_dofs,
                "n_heat_segments": plan.operator.n_segments,
                "heat_compute_plan_memory_bytes": plan.memory_bytes,
                "max_component_mass_error_before_normalization": max(
                    component_errors, default=0.0
                ),
                "minimum_raw_value": min(raw_minima, default=0.0),
            },
        )
        self.compute_plan_ = plan
        self.result_ = result
        return result
