# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Closed ordinary-Bootstrap adapter for heat-equation network KDE fields."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from numbers import Real
from typing import Any

import numpy as np

from pykdex.core.network_results import NetworkField
from pykdex.data._utils import stable_fingerprint
from pykdex.estimators.heat_network_kde import HeatNetworkKDE
from pykdex.execution import ExecutionPlan
from pykdex.execution.replicates import (
    ResolvedReplicateExecution,
    execute_replicate_chunks,
    resolve_replicate_execution,
)
from pykdex.network.events import SnapResult
from pykdex.network.heat import (
    HeatComputePlan,
    NetworkHeatOperator,
    build_network_heat_operator,
)
from pykdex.network.workspace import NetworkWorkspace
from pykdex.uncertainty.fields import FieldEnsemble, pointwise_percentile_interval
from pykdex.uncertainty.network import (
    _direct_array_bytes,
    _distance_asset_bytes,
    _require_unit_weights,
    _resample_network_events,
)
from pykdex.uncertainty.plan import BootstrapPlan
from pykdex.uncertainty.results import BootstrapResult
from pykdex.uncertainty.seeds import SeedLedger, build_seed_ledger


_DEFAULT_DENSE_THRESHOLD = 1_024
_FORCE_SPARSE_THRESHOLD = 1


@dataclass(frozen=True)
class _HeatBootstrapContract:
    diffusion_time: float
    mesh_size: float | None
    target: str
    negative_tolerance: float
    dense_threshold: int
    solver: str
    max_n_dofs: int
    network_fingerprint: str
    support_fingerprint: str

    @property
    def fingerprint(self) -> str:
        return stable_fingerprint(
            "HeatBootstrapContract",
            self.diffusion_time,
            self.mesh_size,
            self.target,
            self.negative_tolerance,
            self.dense_threshold,
            self.solver,
            self.max_n_dofs,
            self.network_fingerprint,
            self.support_fingerprint,
        )


@dataclass(frozen=True)
class _HeatMemoryModel:
    ensemble_bytes: int
    input_bytes: int
    one_worker_bytes: int
    solver_state_upper_bytes: int
    solver_temporary_upper_bytes: int
    max_n_dofs: int
    requested_concurrent_workers: int

    def to_metadata(self) -> dict[str, int]:
        return {
            "ensemble_bytes": self.ensemble_bytes,
            "input_bytes": self.input_bytes,
            "one_worker_bytes": self.one_worker_bytes,
            "solver_state_upper_bytes": self.solver_state_upper_bytes,
            "solver_temporary_upper_bytes": self.solver_temporary_upper_bytes,
            "max_n_dofs": self.max_n_dofs,
            "requested_concurrent_workers": self.requested_concurrent_workers,
        }


def _require_fixed_diffusion_time(estimator: HeatNetworkKDE) -> float:
    value = estimator.diffusion_time
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (Real, np.integer, np.floating),
    ):
        raise ValueError(
            "heat-network bootstrap_kde requires diffusion_time to be a fixed "
            "numeric scalar; selection strategies are not supported."
        )
    diffusion_time = float(value)
    if not np.isfinite(diffusion_time) or diffusion_time <= 0.0:
        raise ValueError(
            "heat-network bootstrap_kde diffusion_time must be finite and positive."
        )
    return diffusion_time


def _input_bytes(workspace: NetworkWorkspace) -> int:
    events = workspace.events
    if events is None:
        raise ValueError("workspace contains no accepted network events.")
    rejected_bytes = int(
        workspace.snap_result.rejected.memory_usage(index=True, deep=True).sum()
    )
    return int(
        _direct_array_bytes(workspace.network)
        + _direct_array_bytes(events)
        + _direct_array_bytes(workspace.lixels)
        + _distance_asset_bytes(workspace.distance_asset)
        + _distance_asset_bytes(workspace.event_distance_asset)
        + rejected_bytes
    )


def _ensemble_bytes(workspace: NetworkWorkspace, plan: BootstrapPlan) -> int:
    n_lixels = workspace.lixels.n_lixels
    return int(plan.n_resamples * n_lixels * 8 + n_lixels * 8 + n_lixels)


def _minimum_worker_bytes(workspace: NetworkWorkspace) -> int:
    events = workspace.events
    if events is None:
        raise ValueError("workspace contains no accepted network events.")
    rejected_bytes = int(
        workspace.snap_result.rejected.memory_usage(index=True, deep=True).sum()
    )
    return int(
        events.n_events * 8
        + _direct_array_bytes(events)
        + events.n_events * 16
        + rejected_bytes
        + workspace.lixels.n_lixels * 8
    )


def _preflight_before_operator(
    workspace: NetworkWorkspace,
    plan: BootstrapPlan,
) -> tuple[int, int, int]:
    requested = plan.execution_plan or ExecutionPlan()
    concurrent_workers = requested.n_jobs if requested.backend == "thread" else 1
    ensemble_bytes = _ensemble_bytes(workspace, plan)
    input_bytes = _input_bytes(workspace)
    lower_bound = int(
        ensemble_bytes
        + input_bytes
        + ceil(_minimum_worker_bytes(workspace) * 1.25 * concurrent_workers)
    )
    budget = requested.memory_budget_bytes
    if budget is not None and lower_bound > budget:
        raise MemoryError(
            "bootstrap_kde.heat_network fixed overhead exceeds the requested "
            f"memory budget ({lower_bound} > {budget} bytes)."
        )
    return ensemble_bytes, input_bytes, concurrent_workers


def _operator_owned_bytes(operator: NetworkHeatOperator) -> int:
    stiffness = operator.stiffness
    return int(
        operator.mass.nbytes
        + stiffness.data.nbytes
        + stiffness.indices.nbytes
        + stiffness.indptr.nbytes
        + operator.event_dofs.nbytes
        + operator.dof_component_labels.nbytes
        + sum(values.nbytes for values in operator.edge_offsets)
        + sum(values.nbytes for values in operator.edge_dofs)
    )


def _plan_owned_bytes(plan: HeatComputePlan) -> int:
    return int(_operator_owned_bytes(plan.operator) + plan.memory_bytes)


def _solver_temporary_upper_bytes(plan: HeatComputePlan) -> int:
    n_dofs = plan.operator.n_dofs
    if plan.solver == "dense_symmetric_eigendecomposition":
        return int(4 * n_dofs * n_dofs * 8 + n_dofs * 8 * 16)
    generator = plan.generator
    sparse_bytes = (
        generator.data.nbytes
        + generator.indices.nbytes
        + generator.indptr.nbytes
    )
    return int(4 * sparse_bytes + n_dofs * 8 * 32)


def _build_source_plan(
    estimator: HeatNetworkKDE,
    workspace: NetworkWorkspace,
) -> tuple[_HeatBootstrapContract, HeatComputePlan]:
    diffusion_time = _require_fixed_diffusion_time(estimator)
    operator = build_network_heat_operator(workspace, mesh_size=estimator.mesh_size)
    dense_threshold = (
        _DEFAULT_DENSE_THRESHOLD
        if operator.n_dofs <= _DEFAULT_DENSE_THRESHOLD
        else _FORCE_SPARSE_THRESHOLD
    )
    plan = HeatComputePlan.from_operator(
        operator,
        dense_threshold=dense_threshold,
    )
    contract = _HeatBootstrapContract(
        diffusion_time=diffusion_time,
        mesh_size=estimator.mesh_size,
        target=estimator.target,
        negative_tolerance=estimator.negative_tolerance,
        dense_threshold=dense_threshold,
        solver=plan.solver,
        max_n_dofs=operator.n_dofs,
        network_fingerprint=workspace.network.fingerprint,
        support_fingerprint=workspace.lixels.fingerprint,
    )
    return contract, plan


def _inner_execution_plan() -> ExecutionPlan:
    return ExecutionPlan(
        memory_budget_bytes=None,
        target_chunk_size=None,
        n_jobs=1,
        backend="sequential",
    )


def _new_estimator(contract: _HeatBootstrapContract) -> HeatNetworkKDE:
    return HeatNetworkKDE(
        diffusion_time=contract.diffusion_time,
        mesh_size=contract.mesh_size,
        target=contract.target,
        negative_tolerance=contract.negative_tolerance,
        execution_plan=_inner_execution_plan(),
    )


def _resample_heat_workspace(
    workspace: NetworkWorkspace,
    sampled_indices: np.ndarray,
    *,
    replicate_index: int,
) -> NetworkWorkspace:
    source_events = workspace.events
    if source_events is None:
        raise ValueError("workspace contains no accepted network events.")
    replicate_events = _resample_network_events(
        source_events,
        sampled_indices,
        replicate_index=replicate_index,
    )
    snap_result = SnapResult(
        events=replicate_events,
        rejected=workspace.snap_result.rejected,
        report=workspace.snap_result.report,
        parameters=workspace.snap_result.parameters,
    )
    return NetworkWorkspace(
        network=workspace.network,
        snap_result=snap_result,
        lixels=workspace.lixels,
        distance_asset=None,
        event_distance_asset=None,
    )


def _build_replicate_plan(
    workspace: NetworkWorkspace,
    contract: _HeatBootstrapContract,
) -> HeatComputePlan:
    operator = build_network_heat_operator(workspace, mesh_size=contract.mesh_size)
    if operator.n_dofs > contract.max_n_dofs:
        raise RuntimeError(
            "heat Bootstrap replicate exceeded the source heat-mesh DOF upper bound."
        )
    plan = HeatComputePlan.from_operator(
        operator,
        dense_threshold=contract.dense_threshold,
    )
    if plan.solver != contract.solver:
        raise RuntimeError("heat Bootstrap replicate changed the fixed solver route.")
    return plan


def _heat_result_fingerprint(result: NetworkField) -> str:
    metadata = dict(result.metadata)
    return stable_fingerprint(
        "BootstrapHeatNetworkKDEResult",
        result.values,
        result.support.fingerprint,
        result.bandwidth,
        result.target,
        result.kernel,
        result.junction_policy,
        result.network_fingerprint,
        metadata.get("diffusion_time"),
        metadata.get("mesh_size"),
        metadata.get("solver"),
    )


def _resolve_heat_replicate_execution(
    workspace: NetworkWorkspace,
    contract: _HeatBootstrapContract,
    source_plan: HeatComputePlan,
    plan: BootstrapPlan,
    *,
    ensemble_bytes: int,
    input_bytes: int,
    concurrent_workers: int,
) -> tuple[ResolvedReplicateExecution, _HeatMemoryModel]:
    requested = plan.execution_plan or ExecutionPlan()
    if requested.target_chunk_size is not None:
        raise ValueError(
            "heat-network bootstrap_kde does not support target_chunk_size because "
            "each heat solve is global and unchunked."
        )
    events = workspace.events
    if events is None:
        raise ValueError("workspace contains no accepted network events.")
    rejected_bytes = int(
        workspace.snap_result.rejected.memory_usage(index=True, deep=True).sum()
    )
    solver_state = _plan_owned_bytes(source_plan)
    solver_temporary = _solver_temporary_upper_bytes(source_plan)
    replicate_workspace_bytes = (
        events.n_events * 8
        + _direct_array_bytes(events)
        + events.n_events * 16
        + rejected_bytes
    )
    numerical_arrays = (
        contract.max_n_dofs * 8 * 8
        + events.n_events * 8 * 3
        + workspace.lixels.n_lixels * 8
    )
    one_worker_bytes = int(
        replicate_workspace_bytes
        + solver_state
        + solver_temporary
        + numerical_arrays
    )
    fixed_overhead = int(
        ensemble_bytes
        + input_bytes
        + solver_state
        + ceil(one_worker_bytes * 1.25 * concurrent_workers)
    )
    resolved = resolve_replicate_execution(
        plan.execution_plan,
        operation_name="bootstrap_kde.heat_network",
        n_replicates=plan.n_resamples,
        bytes_per_replicate=workspace.lixels.n_lixels * 8,
        fixed_overhead_bytes=fixed_overhead,
    )
    memory_model = _HeatMemoryModel(
        ensemble_bytes=int(ensemble_bytes),
        input_bytes=int(input_bytes),
        one_worker_bytes=int(one_worker_bytes),
        solver_state_upper_bytes=int(solver_state),
        solver_temporary_upper_bytes=int(solver_temporary),
        max_n_dofs=int(contract.max_n_dofs),
        requested_concurrent_workers=int(concurrent_workers),
    )
    return resolved, memory_model


def _validate_inputs(
    estimator: HeatNetworkKDE,
    workspace: NetworkWorkspace,
    plan: BootstrapPlan | None,
) -> tuple[BootstrapPlan, int, int, int]:
    if not isinstance(estimator, HeatNetworkKDE):
        raise TypeError("estimator must be a HeatNetworkKDE.")
    if not isinstance(workspace, NetworkWorkspace):
        raise TypeError("workspace must be a NetworkWorkspace.")
    if plan is not None and not isinstance(plan, BootstrapPlan):
        raise TypeError("plan must be a BootstrapPlan or None.")
    workspace.validate().raise_for_errors()
    events = workspace.events
    if events is None:
        raise ValueError("workspace contains no accepted network events.")
    _require_unit_weights(events)
    bootstrap_plan = BootstrapPlan() if plan is None else plan
    ensemble_bytes, input_bytes, concurrent_workers = _preflight_before_operator(
        workspace,
        bootstrap_plan,
    )
    return bootstrap_plan, ensemble_bytes, input_bytes, concurrent_workers


def bootstrap_heat_network_kde(
    estimator: HeatNetworkKDE,
    workspace: NetworkWorkspace,
    *,
    plan: BootstrapPlan | None = None,
) -> BootstrapResult:
    """Ordinary pointwise Bootstrap for a fixed heat-equation network field."""
    (
        bootstrap_plan,
        ensemble_bytes,
        input_bytes,
        concurrent_workers,
    ) = _validate_inputs(estimator, workspace, plan)
    events = workspace.events
    if events is None:
        raise ValueError("workspace contains no accepted network events.")
    contract, source_plan = _build_source_plan(estimator, workspace)
    resolved, memory_model = _resolve_heat_replicate_execution(
        workspace,
        contract,
        source_plan,
        bootstrap_plan,
        ensemble_bytes=ensemble_bytes,
        input_bytes=input_bytes,
        concurrent_workers=concurrent_workers,
    )
    seed_ledger: SeedLedger = build_seed_ledger(
        bootstrap_plan.random_state,
        bootstrap_plan.n_resamples,
    )
    observed_estimator = _new_estimator(contract)
    observed_result = observed_estimator.fit_predict(
        workspace,
        compute_plan=source_plan,
    )
    if observed_result.support.fingerprint != workspace.lixels.fingerprint:
        raise RuntimeError("observed heat Bootstrap support fingerprint changed.")
    observed_fingerprint = _heat_result_fingerprint(observed_result)
    source_plan_fingerprint = source_plan.fingerprint
    del observed_estimator
    del source_plan

    replicate_values = np.empty(
        (bootstrap_plan.n_resamples, workspace.lixels.n_lixels),
        dtype=float,
    )
    replicate_fingerprints: list[str | None] = [None] * bootstrap_plan.n_resamples
    replicate_workspace_fingerprints: list[str | None] = [
        None
    ] * bootstrap_plan.n_resamples
    replicate_plan_fingerprints: list[str | None] = [
        None
    ] * bootstrap_plan.n_resamples

    def worker(
        start: int,
        stop: int,
    ) -> tuple[np.ndarray, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        block = np.empty((stop - start, workspace.lixels.n_lixels), dtype=float)
        event_fingerprints: list[str] = []
        workspace_fingerprints: list[str] = []
        plan_fingerprints: list[str] = []
        for local_index, replicate_index in enumerate(range(start, stop)):
            generator = seed_ledger.generator(replicate_index)
            sampled_indices = generator.integers(
                0,
                events.n_events,
                size=events.n_events,
                dtype=np.int64,
            )
            replicate_workspace = _resample_heat_workspace(
                workspace,
                sampled_indices,
                replicate_index=replicate_index,
            )
            replicate_plan = _build_replicate_plan(replicate_workspace, contract)
            replicate_result = _new_estimator(contract).fit_predict(
                replicate_workspace,
                compute_plan=replicate_plan,
            )
            if replicate_result.support.fingerprint != workspace.lixels.fingerprint:
                raise RuntimeError(
                    "heat Bootstrap replicate support fingerprint changed."
                )
            block[local_index] = replicate_result.values
            replicate_events = replicate_workspace.events
            if replicate_events is None:
                raise RuntimeError("heat Bootstrap replicate lost accepted events.")
            event_fingerprints.append(replicate_events.fingerprint)
            workspace_fingerprints.append(replicate_workspace.fingerprint)
            plan_fingerprints.append(replicate_plan.fingerprint)
        return (
            block,
            tuple(event_fingerprints),
            tuple(workspace_fingerprints),
            tuple(plan_fingerprints),
        )

    for start, stop, chunk_result in execute_replicate_chunks(resolved, worker):
        (
            block,
            event_fingerprints,
            workspace_fingerprints,
            plan_fingerprints,
        ) = chunk_result
        replicate_values[start:stop] = block
        replicate_fingerprints[start:stop] = event_fingerprints
        replicate_workspace_fingerprints[start:stop] = workspace_fingerprints
        replicate_plan_fingerprints[start:stop] = plan_fingerprints

    if any(value is None for value in replicate_fingerprints):
        raise RuntimeError("heat Bootstrap event fingerprints are incomplete.")
    if any(value is None for value in replicate_workspace_fingerprints):
        raise RuntimeError("heat Bootstrap workspace fingerprints are incomplete.")
    if any(value is None for value in replicate_plan_fingerprints):
        raise RuntimeError("heat Bootstrap plan fingerprints are incomplete.")
    completed_event_fingerprints = tuple(
        str(value) for value in replicate_fingerprints if value is not None
    )
    completed_workspace_fingerprints = tuple(
        str(value) for value in replicate_workspace_fingerprints if value is not None
    )
    completed_plan_fingerprints = tuple(
        str(value) for value in replicate_plan_fingerprints if value is not None
    )
    common_metadata: dict[str, Any] = {
        "estimator_contract_fingerprint": contract.fingerprint,
        "source_workspace_fingerprint": workspace.fingerprint,
        "source_event_fingerprint": events.fingerprint,
        "network_fingerprint": workspace.network.fingerprint,
        "support_fingerprint": workspace.lixels.fingerprint,
        "source_heat_compute_plan_fingerprint": source_plan_fingerprint,
        "conditional_on_observed_event_count": True,
        "resampling_stage": "after_accepted_event_snapping",
        "unit_event_weights": True,
        "n_events": events.n_events,
        "n_rejected_fixed": workspace.snap_result.n_rejected,
        "diffusion_time": contract.diffusion_time,
        "mesh_size": contract.mesh_size,
        "solver": contract.solver,
        "dense_threshold": contract.dense_threshold,
        "max_n_dofs": contract.max_n_dofs,
        "distance_assets_propagated": False,
    }
    ensemble = FieldEnsemble(
        replicate_values=replicate_values,
        observed_values=observed_result.values,
        support=workspace.lixels,
        field_family=contract.target,
        observed_field_fingerprint=observed_fingerprint,
        replicate_source_fingerprints=completed_event_fingerprints,
        resampling_method=bootstrap_plan.method,
        seed_ledger_fingerprint=seed_ledger.fingerprint,
        execution_metadata=resolved.to_metadata(),
        metadata={
            "estimator_family": "heat_network",
            **common_metadata,
            "replicate_workspace_fingerprints": completed_workspace_fingerprints,
            "replicate_heat_compute_plan_fingerprints": completed_plan_fingerprints,
            "memory_model": memory_model.to_metadata(),
        },
    )
    interval = pointwise_percentile_interval(
        ensemble,
        confidence_level=bootstrap_plan.confidence_level,
    )
    return BootstrapResult(
        ensemble=ensemble,
        interval=interval,
        plan=bootstrap_plan,
        operation="bootstrap_kde",
        estimator_family="heat_network",
        seed_metadata=seed_ledger.to_metadata(),
        metadata={
            **common_metadata,
            "observed_result_fingerprint": observed_fingerprint,
        },
    )
