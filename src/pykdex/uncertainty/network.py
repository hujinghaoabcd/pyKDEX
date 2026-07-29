# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Closed ordinary-Bootstrap adapter for prepared radial network KDE fields."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from numbers import Real
from typing import Any

import numpy as np

from pykdex.core.network_results import NetworkField
from pykdex.data._utils import stable_fingerprint
from pykdex.estimators.network_kde import NetworkKDE
from pykdex.execution import ExecutionPlan
from pykdex.execution.replicates import (
    ResolvedReplicateExecution,
    execute_replicate_chunks,
    resolve_replicate_execution,
)
from pykdex.kernels import get_kernel
from pykdex.network.distance import NetworkDistanceAsset, NetworkLocations
from pykdex.network.events import NetworkEvents, SnapResult
from pykdex.network.propagation import get_junction_policy
from pykdex.network.workspace import NetworkWorkspace
from pykdex.uncertainty.contracts import build_relative_risk_contract
from pykdex.uncertainty.fields import FieldEnsemble, pointwise_percentile_interval
from pykdex.uncertainty.plan import BootstrapPlan
from pykdex.uncertainty.results import BootstrapResult
from pykdex.uncertainty.seeds import SeedLedger, build_seed_ledger


@dataclass(frozen=True)
class _NetworkBootstrapContract:
    kernel: str
    bandwidth: float
    junction_policy: str
    target: str
    directed: bool | None
    effective_directed: bool
    coefficient_tolerance: float
    max_records_per_event: int
    store_propagation: bool
    network_fingerprint: str
    support_fingerprint: str

    @property
    def fingerprint(self) -> str:
        return stable_fingerprint(
            "NetworkBootstrapContract",
            self.kernel,
            self.bandwidth,
            self.junction_policy,
            self.target,
            self.directed,
            self.effective_directed,
            self.coefficient_tolerance,
            self.max_records_per_event,
            self.store_propagation,
            self.network_fingerprint,
            self.support_fingerprint,
        )


@dataclass(frozen=True)
class _NetworkMemoryModel:
    ensemble_bytes: int
    input_bytes: int
    one_worker_bytes: int
    event_lixel_pair_bound: int
    event_event_pair_bound: int
    propagation_record_bound: int
    requested_concurrent_workers: int
    target_chunk_rows: int

    def to_metadata(self) -> dict[str, int]:
        return {
            "ensemble_bytes": self.ensemble_bytes,
            "input_bytes": self.input_bytes,
            "one_worker_bytes": self.one_worker_bytes,
            "event_lixel_pair_bound": self.event_lixel_pair_bound,
            "event_event_pair_bound": self.event_event_pair_bound,
            "propagation_record_bound": self.propagation_record_bound,
            "requested_concurrent_workers": self.requested_concurrent_workers,
            "target_chunk_rows": self.target_chunk_rows,
        }


def _direct_array_bytes(value: object) -> int:
    total = 0
    try:
        attributes = vars(value).values()
    except TypeError:
        return 0
    for attribute in attributes:
        if isinstance(attribute, np.ndarray):
            total += int(attribute.nbytes)
    return total


def _distance_asset_bytes(asset: NetworkDistanceAsset | None) -> int:
    if asset is None:
        return 0
    return _direct_array_bytes(asset)


def _require_unit_weights(events: NetworkEvents) -> None:
    if not np.array_equal(events.weights, np.ones(events.n_events, dtype=float)):
        raise ValueError(
            "network bootstrap_kde initially requires unit accepted-event weights; "
            "weighted Bootstrap semantics are not implemented."
        )


def _require_fixed_scalar_bandwidth(estimator: NetworkKDE) -> float:
    value = estimator.bandwidth
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (Real, np.integer, np.floating),
    ):
        raise ValueError(
            "network bootstrap_kde requires NetworkKDE bandwidth to be a fixed "
            "numeric scalar; selectors and event-specific bandwidths are not supported."
        )
    bandwidth = float(value)
    if not np.isfinite(bandwidth) or bandwidth <= 0.0:
        raise ValueError("network bootstrap_kde bandwidth must be finite and positive.")
    return bandwidth


def _build_contract(
    estimator: NetworkKDE,
    workspace: NetworkWorkspace,
) -> _NetworkBootstrapContract:
    bandwidth = _require_fixed_scalar_bandwidth(estimator)
    for name, value in (
        ("kernel", estimator.kernel),
        ("junction_policy", estimator.junction_policy),
    ):
        if not isinstance(value, str):
            raise ValueError(
                "network bootstrap_kde initially requires built-in string names "
                f"for kernel and junction_policy; {name} was an object."
            )
    kernel = get_kernel(estimator.kernel)
    policy = get_junction_policy(estimator.junction_policy)
    effective_directed = bool(
        workspace.network.directed
        if estimator.directed is None
        else estimator.directed and workspace.network.directed
    )
    if effective_directed and not policy.supports_directed:
        raise ValueError(
            f"The '{policy.name}' junction policy requires an undirected network."
        )
    if policy.path_based and not kernel.finite_support:
        raise ValueError(
            "Path-based network bootstrap_kde requires a finite-support kernel."
        )
    return _NetworkBootstrapContract(
        kernel=kernel.name,
        bandwidth=bandwidth,
        junction_policy=policy.name,
        target=estimator.target,
        directed=estimator.directed,
        effective_directed=effective_directed,
        coefficient_tolerance=estimator.coefficient_tolerance,
        max_records_per_event=estimator.max_records_per_event,
        store_propagation=estimator.store_propagation,
        network_fingerprint=workspace.network.fingerprint,
        support_fingerprint=workspace.lixels.fingerprint,
    )


def _target_execution_plan(plan: BootstrapPlan) -> ExecutionPlan:
    requested = plan.execution_plan or ExecutionPlan()
    return ExecutionPlan(
        memory_budget_bytes=None,
        target_chunk_size=requested.target_chunk_size,
        n_jobs=1,
        backend="sequential",
    )


def _new_estimator(
    contract: _NetworkBootstrapContract,
    target_execution: ExecutionPlan,
) -> NetworkKDE:
    return NetworkKDE(
        kernel=contract.kernel,
        bandwidth=contract.bandwidth,
        junction_policy=contract.junction_policy,
        target=contract.target,
        directed=contract.directed,
        coefficient_tolerance=contract.coefficient_tolerance,
        max_records_per_event=contract.max_records_per_event,
        store_propagation=contract.store_propagation,
        execution_plan=target_execution,
    )


def _resample_network_events(
    events: NetworkEvents,
    sampled_indices: np.ndarray,
    *,
    replicate_index: int,
) -> NetworkEvents:
    sampled = np.asarray(sampled_indices, dtype=np.int64)
    if sampled.shape != (events.n_events,):
        raise ValueError("sampled indices must preserve the accepted event count.")
    if np.any(sampled < 0) or np.any(sampled >= events.n_events):
        raise IndexError("sampled accepted-event index is outside the source events.")
    marks = None if events.marks is None else events.marks[sampled]
    provenance = events.provenance.with_transformation(
        "ordinary_bootstrap_resample",
        replicate_index=int(replicate_index),
        sampled_source_indices=sampled.tolist(),
        source_event_fingerprint=events.fingerprint,
        resampling_stage="after_accepted_event_snapping",
    )
    return NetworkEvents(
        event_ids=np.arange(events.n_events, dtype=np.int64),
        edge_indices=events.edge_indices[sampled],
        edge_ids=events.edge_ids[sampled],
        offsets=events.offsets[sampled],
        coordinates=events.coordinates[sampled],
        original_coordinates=events.original_coordinates[sampled],
        weights=np.ones(events.n_events, dtype=float),
        snap_distances=events.snap_distances[sampled],
        snap_status=events.snap_status[sampled],
        network_fingerprint=events.network_fingerprint,
        crs=events.crs,
        spatial_unit=events.spatial_unit,
        marks=marks,
        provenance=provenance,
    )


def _asset_metadata(
    asset: NetworkDistanceAsset,
    *,
    replicate_index: int,
    sampled_indices: np.ndarray,
    axis_contract: str,
) -> dict[str, Any]:
    metadata = dict(asset.metadata)
    metadata.update(
        {
            "bootstrap_reindexed": True,
            "bootstrap_replicate_index": int(replicate_index),
            "bootstrap_sampled_source_indices": sampled_indices.tolist(),
            "bootstrap_axis_contract": axis_contract,
            "source_asset_fingerprint": asset.fingerprint,
        }
    )
    return metadata


def _reindex_event_lixel_asset(
    asset: NetworkDistanceAsset | None,
    source_events: NetworkEvents,
    replicate_events: NetworkEvents,
    sampled_indices: np.ndarray,
    workspace: NetworkWorkspace,
    *,
    replicate_index: int,
) -> NetworkDistanceAsset | None:
    if asset is None:
        return None
    if asset.shape != (source_events.n_events, workspace.lixels.n_lixels):
        raise ValueError(
            "workspace event-to-lixel distance asset has an unexpected shape."
        )
    rows: list[np.ndarray] = []
    columns: list[np.ndarray] = []
    distances: list[np.ndarray] = []
    for new_index, source_index in enumerate(sampled_indices.tolist()):
        selected = asset.row_indices == int(source_index)
        pair_count = int(np.count_nonzero(selected))
        if pair_count == 0:
            continue
        rows.append(np.full(pair_count, new_index, dtype=np.int64))
        columns.append(asset.column_indices[selected])
        distances.append(asset.distances[selected])
    row_values = np.concatenate(rows) if rows else np.empty(0, dtype=np.int64)
    column_values = np.concatenate(columns) if columns else np.empty(0, dtype=np.int64)
    distance_values = (
        np.concatenate(distances) if distances else np.empty(0, dtype=float)
    )
    sources = NetworkLocations.from_events(replicate_events)
    targets = NetworkLocations.from_lixels(workspace.lixels)
    return NetworkDistanceAsset(
        source_ids=replicate_events.event_ids,
        target_ids=workspace.lixels.lixel_ids,
        row_indices=row_values,
        column_indices=column_values,
        distances=distance_values,
        network_fingerprint=asset.network_fingerprint,
        source_fingerprint=sources.fingerprint,
        target_fingerprint=targets.fingerprint,
        weight=asset.weight,
        directed=asset.directed,
        cutoff=asset.cutoff,
        metadata=_asset_metadata(
            asset,
            replicate_index=replicate_index,
            sampled_indices=sampled_indices,
            axis_contract="sampled_event_rows_fixed_lixel_columns",
        ),
    )


def _reindex_event_event_asset(
    asset: NetworkDistanceAsset | None,
    source_events: NetworkEvents,
    replicate_events: NetworkEvents,
    sampled_indices: np.ndarray,
    *,
    replicate_index: int,
) -> NetworkDistanceAsset | None:
    if asset is None:
        return None
    expected = (source_events.n_events, source_events.n_events)
    if asset.shape != expected:
        raise ValueError(
            "workspace event-to-event distance asset has an unexpected shape."
        )
    inverse = tuple(
        np.flatnonzero(sampled_indices == source_index)
        for source_index in range(source_events.n_events)
    )
    rows: list[np.ndarray] = []
    columns: list[np.ndarray] = []
    distances: list[np.ndarray] = []
    for source_row, source_column, distance in zip(
        asset.row_indices,
        asset.column_indices,
        asset.distances,
        strict=True,
    ):
        new_rows = inverse[int(source_row)]
        new_columns = inverse[int(source_column)]
        if new_rows.size == 0 or new_columns.size == 0:
            continue
        pair_count = int(new_rows.size * new_columns.size)
        rows.append(np.repeat(new_rows, new_columns.size))
        columns.append(np.tile(new_columns, new_rows.size))
        distances.append(np.full(pair_count, float(distance), dtype=float))
    row_values = np.concatenate(rows) if rows else np.empty(0, dtype=np.int64)
    column_values = np.concatenate(columns) if columns else np.empty(0, dtype=np.int64)
    distance_values = (
        np.concatenate(distances) if distances else np.empty(0, dtype=float)
    )
    locations = NetworkLocations.from_events(replicate_events)
    return NetworkDistanceAsset(
        source_ids=replicate_events.event_ids,
        target_ids=replicate_events.event_ids,
        row_indices=row_values,
        column_indices=column_values,
        distances=distance_values,
        network_fingerprint=asset.network_fingerprint,
        source_fingerprint=locations.fingerprint,
        target_fingerprint=locations.fingerprint,
        weight=asset.weight,
        directed=asset.directed,
        cutoff=asset.cutoff,
        metadata=_asset_metadata(
            asset,
            replicate_index=replicate_index,
            sampled_indices=sampled_indices,
            axis_contract="sampled_event_rows_and_columns",
        ),
    )


def _resample_network_workspace(
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
    distance_asset = _reindex_event_lixel_asset(
        workspace.distance_asset,
        source_events,
        replicate_events,
        sampled_indices,
        workspace,
        replicate_index=replicate_index,
    )
    event_distance_asset = _reindex_event_event_asset(
        workspace.event_distance_asset,
        source_events,
        replicate_events,
        sampled_indices,
        replicate_index=replicate_index,
    )
    return NetworkWorkspace(
        network=workspace.network,
        snap_result=snap_result,
        lixels=workspace.lixels,
        distance_asset=distance_asset,
        event_distance_asset=event_distance_asset,
    )


def _network_result_fingerprint(result: NetworkField) -> str:
    metadata = dict(result.metadata)
    return stable_fingerprint(
        "BootstrapNetworkKDEResult",
        result.values,
        result.support.fingerprint,
        result.bandwidth,
        result.target,
        result.kernel,
        result.junction_policy,
        result.directed,
        result.network_fingerprint,
        metadata.get("path_based"),
        metadata.get("bandwidth_strategy"),
    )


def _resolve_network_replicate_execution(
    workspace: NetworkWorkspace,
    contract: _NetworkBootstrapContract,
    plan: BootstrapPlan,
) -> tuple[ResolvedReplicateExecution, ExecutionPlan, _NetworkMemoryModel]:
    events = workspace.events
    if events is None:
        raise ValueError("workspace contains no accepted network events.")
    requested = plan.execution_plan or ExecutionPlan()
    target_execution = _target_execution_plan(plan)
    target_rows = min(
        workspace.lixels.n_lixels,
        requested.target_chunk_size or workspace.lixels.n_lixels,
    )
    concurrent_workers = requested.n_jobs if requested.backend == "thread" else 1
    ensemble_bytes = (
        plan.n_resamples * workspace.lixels.n_lixels * 8
        + workspace.lixels.n_lixels * 8
        + workspace.lixels.n_lixels
    )
    rejected_bytes = int(
        workspace.snap_result.rejected.memory_usage(index=True, deep=True).sum()
    )
    input_bytes = (
        _direct_array_bytes(workspace.network)
        + _direct_array_bytes(events)
        + _direct_array_bytes(workspace.lixels)
        + _distance_asset_bytes(workspace.distance_asset)
        + _distance_asset_bytes(workspace.event_distance_asset)
        + rejected_bytes
    )
    event_lixel_pair_bound = events.n_events * workspace.lixels.n_lixels
    event_event_pair_bound = (
        events.n_events * events.n_events
        if workspace.event_distance_asset is not None
        else 0
    )
    event_array_bytes = _direct_array_bytes(events) + events.n_events * 16
    reindexed_asset_bytes = (
        event_lixel_pair_bound * 24
        + events.n_events * 8
        + workspace.lixels.n_lixels * 8
        + event_event_pair_bound * 24
        + event_event_pair_bound * 0
        + events.n_events * 16
    )
    propagation_record_bound = 0
    if contract.junction_policy != "simple":
        propagation_record_bound = events.n_events * contract.max_records_per_event
    inner_working_bytes = (
        target_rows * events.n_events * 64
        + workspace.lixels.n_lixels * 8
        + events.n_events * 16
        + event_lixel_pair_bound * 16
        + propagation_record_bound * 96
    )
    one_worker_bytes = (
        events.n_events * 8
        + event_array_bytes
        + reindexed_asset_bytes
        + workspace.lixels.n_lixels * 8
        + inner_working_bytes
    )
    fixed_overhead = int(
        ensemble_bytes
        + input_bytes
        + ceil(one_worker_bytes * 1.25 * concurrent_workers)
    )
    resolved = resolve_replicate_execution(
        plan.execution_plan,
        operation_name=f"bootstrap_kde.network.{contract.junction_policy}",
        n_replicates=plan.n_resamples,
        bytes_per_replicate=workspace.lixels.n_lixels * 8,
        fixed_overhead_bytes=fixed_overhead,
    )
    model = _NetworkMemoryModel(
        ensemble_bytes=int(ensemble_bytes),
        input_bytes=int(input_bytes),
        one_worker_bytes=int(one_worker_bytes),
        event_lixel_pair_bound=int(event_lixel_pair_bound),
        event_event_pair_bound=int(event_event_pair_bound),
        propagation_record_bound=int(propagation_record_bound),
        requested_concurrent_workers=int(concurrent_workers),
        target_chunk_rows=int(target_rows),
    )
    return resolved, target_execution, model


def _validate_inputs(
    estimator: NetworkKDE,
    workspace: NetworkWorkspace,
    plan: BootstrapPlan | None,
) -> tuple[BootstrapPlan, _NetworkBootstrapContract]:
    if not isinstance(estimator, NetworkKDE):
        raise TypeError("estimator must be a NetworkKDE.")
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
    contract = _build_contract(estimator, workspace)
    return bootstrap_plan, contract


def bootstrap_network_kde(
    estimator: NetworkKDE,
    workspace: NetworkWorkspace,
    *,
    plan: BootstrapPlan | None = None,
) -> BootstrapResult:
    """Ordinary pointwise Bootstrap for a fixed prepared radial network field."""
    bootstrap_plan, contract = _validate_inputs(estimator, workspace, plan)
    events = workspace.events
    if events is None:
        raise ValueError("workspace contains no accepted network events.")
    resolved, target_execution, memory_model = _resolve_network_replicate_execution(
        workspace,
        contract,
        bootstrap_plan,
    )
    seed_ledger: SeedLedger = build_seed_ledger(
        bootstrap_plan.random_state,
        bootstrap_plan.n_resamples,
    )
    observed_result = _new_estimator(contract, target_execution).fit_predict(workspace)
    if observed_result.support.fingerprint != workspace.lixels.fingerprint:
        raise RuntimeError("observed network Bootstrap support fingerprint changed.")
    observed_fingerprint = _network_result_fingerprint(observed_result)
    replicate_values = np.empty(
        (bootstrap_plan.n_resamples, workspace.lixels.n_lixels),
        dtype=float,
    )
    replicate_fingerprints: list[str | None] = [None] * bootstrap_plan.n_resamples
    replicate_workspace_fingerprints: list[str | None] = [
        None
    ] * bootstrap_plan.n_resamples

    def worker(
        start: int, stop: int
    ) -> tuple[np.ndarray, tuple[str, ...], tuple[str, ...]]:
        block = np.empty((stop - start, workspace.lixels.n_lixels), dtype=float)
        event_fingerprints: list[str] = []
        workspace_fingerprints: list[str] = []
        for local_index, replicate_index in enumerate(range(start, stop)):
            generator = seed_ledger.generator(replicate_index)
            sampled_indices = generator.integers(
                0,
                events.n_events,
                size=events.n_events,
                dtype=np.int64,
            )
            replicate_workspace = _resample_network_workspace(
                workspace,
                sampled_indices,
                replicate_index=replicate_index,
            )
            replicate_result = _new_estimator(
                contract,
                target_execution,
            ).fit_predict(replicate_workspace)
            if replicate_result.support.fingerprint != workspace.lixels.fingerprint:
                raise RuntimeError(
                    "network Bootstrap replicate support fingerprint changed."
                )
            block[local_index] = replicate_result.values
            replicate_events = replicate_workspace.events
            if replicate_events is None:
                raise RuntimeError("network Bootstrap replicate lost accepted events.")
            event_fingerprints.append(replicate_events.fingerprint)
            workspace_fingerprints.append(replicate_workspace.fingerprint)
        return block, tuple(event_fingerprints), tuple(workspace_fingerprints)

    for start, stop, chunk_result in execute_replicate_chunks(resolved, worker):
        block, event_fingerprints, workspace_fingerprints = chunk_result
        replicate_values[start:stop] = block
        replicate_fingerprints[start:stop] = event_fingerprints
        replicate_workspace_fingerprints[start:stop] = workspace_fingerprints

    if any(value is None for value in replicate_fingerprints):
        raise RuntimeError("network Bootstrap event fingerprints are incomplete.")
    if any(value is None for value in replicate_workspace_fingerprints):
        raise RuntimeError("network Bootstrap workspace fingerprints are incomplete.")
    completed_event_fingerprints = tuple(
        str(value) for value in replicate_fingerprints if value is not None
    )
    completed_workspace_fingerprints = tuple(
        str(value) for value in replicate_workspace_fingerprints if value is not None
    )
    relative_risk_contract, relative_risk_contract_fingerprint = (
        build_relative_risk_contract(
            result_family="network",
            support_fingerprint=contract.support_fingerprint,
            target=contract.target,
            bandwidths=(contract.bandwidth,),
            components={
                "kernel": contract.kernel,
                "junction_policy": contract.junction_policy,
                "directed": contract.effective_directed,
                "network_fingerprint": contract.network_fingerprint,
                "path_based": contract.junction_policy != "simple",
                "coefficient_tolerance": contract.coefficient_tolerance,
                "max_records_per_event": contract.max_records_per_event,
            },
        )
    )
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
            "estimator_family": "network",
            "estimator_contract_fingerprint": contract.fingerprint,
            "relative_risk_contract": relative_risk_contract,
            "relative_risk_contract_fingerprint": relative_risk_contract_fingerprint,
            "source_workspace_fingerprint": workspace.fingerprint,
            "source_event_fingerprint": events.fingerprint,
            "network_fingerprint": workspace.network.fingerprint,
            "support_fingerprint": workspace.lixels.fingerprint,
            "conditional_on_observed_event_count": True,
            "resampling_stage": "after_accepted_event_snapping",
            "unit_event_weights": True,
            "n_events": events.n_events,
            "n_rejected_fixed": workspace.snap_result.n_rejected,
            "junction_policy": contract.junction_policy,
            "directed": contract.effective_directed,
            "replicate_workspace_fingerprints": completed_workspace_fingerprints,
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
        estimator_family="network",
        seed_metadata=seed_ledger.to_metadata(),
        metadata={
            "estimator_contract_fingerprint": contract.fingerprint,
            "relative_risk_contract": relative_risk_contract,
            "relative_risk_contract_fingerprint": relative_risk_contract_fingerprint,
            "observed_result_fingerprint": observed_fingerprint,
            "source_workspace_fingerprint": workspace.fingerprint,
            "source_event_fingerprint": events.fingerprint,
            "network_fingerprint": workspace.network.fingerprint,
            "support_fingerprint": workspace.lixels.fingerprint,
            "conditional_on_observed_event_count": True,
            "resampling_stage": "after_accepted_event_snapping",
            "junction_policy": contract.junction_policy,
            "directed": contract.effective_directed,
        },
    )
