# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Closed ordinary-Bootstrap adapter for measured temporal-network KDE fields."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any

import numpy as np

from pykdex.core.network_time_results import NetworkTimeField
from pykdex.data import TemporalCoordinates
from pykdex.data._utils import stable_fingerprint
from pykdex.estimators.temporal_network_kde import TemporalNetworkKDE
from pykdex.execution import ExecutionPlan
from pykdex.execution.replicates import (
    ResolvedReplicateExecution,
    execute_replicate_chunks,
    resolve_replicate_execution,
)
from pykdex.kernels import get_kernel
from pykdex.network.propagation import get_junction_policy
from pykdex.network_time.distance import NetworkTimeDistanceAsset
from pykdex.network_time.events import NetworkTimeEvents
from pykdex.network_time.workspace import NetworkTimeWorkspace
from pykdex.uncertainty.contracts import build_relative_risk_contract
from pykdex.uncertainty.fields import FieldEnsemble, pointwise_percentile_interval
from pykdex.uncertainty.network import (
    _direct_array_bytes,
    _distance_asset_bytes,
    _reindex_event_lixel_asset,
    _require_unit_weights,
    _resample_network_workspace,
)
from pykdex.uncertainty.plan import BootstrapPlan
from pykdex.uncertainty.results import BootstrapResult
from pykdex.uncertainty.seeds import SeedLedger, build_seed_ledger


@dataclass(frozen=True)
class _TemporalNetworkBootstrapContract:
    spatial_bandwidth: float
    temporal_bandwidth: float
    spatial_kernel: str
    temporal_kernel: str
    junction_policy: str
    target: str
    requested_directed: bool | None
    effective_directed: bool
    cyclic_tail_tolerance: float
    coefficient_tolerance: float
    max_records_per_event: int
    network_fingerprint: str
    support_fingerprint: str
    time_domain_fingerprint: str

    @property
    def fingerprint(self) -> str:
        return stable_fingerprint(
            "TemporalNetworkBootstrapContract",
            self.spatial_bandwidth,
            self.temporal_bandwidth,
            self.spatial_kernel,
            self.temporal_kernel,
            self.junction_policy,
            self.target,
            self.requested_directed,
            self.effective_directed,
            self.cyclic_tail_tolerance,
            self.coefficient_tolerance,
            self.max_records_per_event,
            self.network_fingerprint,
            self.support_fingerprint,
            self.time_domain_fingerprint,
        )


@dataclass(frozen=True)
class _TemporalNetworkMemoryModel:
    ensemble_bytes: int
    input_bytes: int
    one_worker_bytes: int
    event_lixel_pair_bound: int
    propagation_record_bound: int
    requested_concurrent_workers: int
    time_chunk_rows: int

    def to_metadata(self) -> dict[str, int]:
        return {
            "ensemble_bytes": self.ensemble_bytes,
            "input_bytes": self.input_bytes,
            "one_worker_bytes": self.one_worker_bytes,
            "event_lixel_pair_bound": self.event_lixel_pair_bound,
            "propagation_record_bound": self.propagation_record_bound,
            "requested_concurrent_workers": self.requested_concurrent_workers,
            "time_chunk_rows": self.time_chunk_rows,
        }


def _network_time_asset_bytes(asset: NetworkTimeDistanceAsset | None) -> int:
    if asset is None:
        return 0
    return int(
        _distance_asset_bytes(asset.network_distances)
        + asset.temporal_offsets.nbytes
        + asset.temporal_distances.nbytes
    )


def _require_scalar(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must not be boolean.")
    array = np.asarray(value, dtype=float)
    if array.ndim != 0:
        raise ValueError(
            f"temporal-network bootstrap_kde requires {name} to be a fixed numeric "
            "scalar; adaptive arrays are not supported."
        )
    scalar = float(array)
    if not np.isfinite(scalar) or scalar <= 0.0:
        raise ValueError(f"{name} must be finite and positive.")
    return scalar


def _build_contract(
    estimator: TemporalNetworkKDE,
    workspace: NetworkTimeWorkspace,
) -> _TemporalNetworkBootstrapContract:
    if estimator.bandwidths is not None:
        raise ValueError(
            "temporal-network bootstrap_kde requires fixed constructor bandwidths; "
            "bandwidth strategy objects are not supported."
        )
    for name, value in (
        ("spatial_kernel", estimator.spatial_kernel),
        ("temporal_kernel", estimator.temporal_kernel),
        ("junction_policy", estimator.junction_policy),
    ):
        if not isinstance(value, str):
            raise ValueError(
                "temporal-network bootstrap_kde initially requires built-in string "
                f"names; {name} was an object."
            )
    spatial_bandwidth = _require_scalar(
        estimator.spatial_bandwidth,
        name="spatial_bandwidth",
    )
    temporal_bandwidth = _require_scalar(
        estimator.temporal_bandwidth,
        name="temporal_bandwidth",
    )
    spatial_kernel = get_kernel(estimator.spatial_kernel)
    temporal_kernel = get_kernel(estimator.temporal_kernel)
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
    if policy.path_based and not spatial_kernel.finite_support:
        raise ValueError(
            "Path-based temporal-network Bootstrap requires a finite-support "
            "spatial kernel."
        )
    return _TemporalNetworkBootstrapContract(
        spatial_bandwidth=spatial_bandwidth,
        temporal_bandwidth=temporal_bandwidth,
        spatial_kernel=spatial_kernel.name,
        temporal_kernel=temporal_kernel.name,
        junction_policy=policy.name,
        target=estimator.target,
        requested_directed=estimator.directed,
        effective_directed=effective_directed,
        cyclic_tail_tolerance=estimator.cyclic_tail_tolerance,
        coefficient_tolerance=estimator.coefficient_tolerance,
        max_records_per_event=estimator.max_records_per_event,
        network_fingerprint=workspace.network.fingerprint,
        support_fingerprint=workspace.arixels.fingerprint,
        time_domain_fingerprint=workspace.events.temporal.domain.fingerprint,
    )


def _target_execution_plan(
    estimator: TemporalNetworkKDE,
    plan: BootstrapPlan,
) -> ExecutionPlan:
    requested = plan.execution_plan or ExecutionPlan()
    target_chunk_size = requested.target_chunk_size
    if target_chunk_size is None:
        target_chunk_size = estimator.time_chunk_size
    return ExecutionPlan(
        memory_budget_bytes=None,
        target_chunk_size=target_chunk_size,
        n_jobs=1,
        backend="sequential",
    )


def _new_estimator(
    contract: _TemporalNetworkBootstrapContract,
    target_execution: ExecutionPlan,
) -> TemporalNetworkKDE:
    return TemporalNetworkKDE(
        spatial_bandwidth=contract.spatial_bandwidth,
        temporal_bandwidth=contract.temporal_bandwidth,
        spatial_kernel=contract.spatial_kernel,
        temporal_kernel=contract.temporal_kernel,
        junction_policy=contract.junction_policy,
        target=contract.target,
        directed=contract.requested_directed,
        time_chunk_size=None,
        execution_plan=target_execution,
        cyclic_tail_tolerance=contract.cyclic_tail_tolerance,
        coefficient_tolerance=contract.coefficient_tolerance,
        max_records_per_event=contract.max_records_per_event,
        store_propagation=False,
    )


def _resample_network_time_events(
    events: NetworkTimeEvents,
    replicate_network_events: Any,
    sampled_indices: np.ndarray,
    *,
    replicate_index: int,
) -> NetworkTimeEvents:
    sampled = np.asarray(sampled_indices, dtype=np.int64)
    if sampled.shape != (events.n_events,):
        raise ValueError("sampled indices must preserve the accepted event count.")
    if np.any(sampled < 0) or np.any(sampled >= events.n_events):
        raise IndexError(
            "sampled network-time event index is outside the source events."
        )
    metadata = {
        "replicate_index": int(replicate_index),
        "sampled_source_indices": sampled.tolist(),
        "source_event_fingerprint": events.fingerprint,
        "resampling_unit": "paired_snapped_network_time_event_identity",
        "resampling_stage": "after_accepted_event_snapping",
    }
    temporal = TemporalCoordinates(
        values=events.temporal.values[sampled],
        domain=events.temporal.domain,
        temporal_unit=events.temporal.temporal_unit,
        temporal_origin=events.temporal.temporal_origin,
        timezone=events.temporal.timezone,
        provenance=events.temporal.provenance.with_transformation(
            "ordinary_bootstrap_resample",
            **metadata,
        ),
    )
    return NetworkTimeEvents(
        network_events=replicate_network_events,
        temporal=temporal,
        provenance=events.provenance.with_transformation(
            "ordinary_bootstrap_resample",
            **metadata,
        ),
    )


def _reindex_network_time_asset(
    asset: NetworkTimeDistanceAsset | None,
    source_workspace: NetworkTimeWorkspace,
    replicate_workspace: Any,
    replicate_events: NetworkTimeEvents,
    sampled_indices: np.ndarray,
    *,
    replicate_index: int,
) -> NetworkTimeDistanceAsset | None:
    if asset is None:
        return None
    replicate_network_events = replicate_workspace.events
    if replicate_network_events is None:
        raise RuntimeError("replicate base workspace lost accepted events.")
    network_distances = _reindex_event_lixel_asset(
        asset.network_distances,
        source_workspace.events.network_events,
        replicate_network_events,
        sampled_indices,
        source_workspace.network_workspace,
        replicate_index=replicate_index,
    )
    if network_distances is None:
        raise RuntimeError("factorized network-time distance rows were not rebuilt.")
    return NetworkTimeDistanceAsset(
        network_distances=network_distances,
        temporal_offsets=asset.temporal_offsets[:, sampled_indices],
        temporal_distances=asset.temporal_distances[:, sampled_indices],
        event_fingerprint=replicate_events.fingerprint,
        support_fingerprint=source_workspace.arixels.fingerprint,
        time_domain_fingerprint=replicate_events.temporal.domain.fingerprint,
        workspace_fingerprint=replicate_workspace.fingerprint,
    )


def _resample_network_time_workspace(
    workspace: NetworkTimeWorkspace,
    sampled_indices: np.ndarray,
    *,
    replicate_index: int,
) -> NetworkTimeWorkspace:
    replicate_base = _resample_network_workspace(
        workspace.network_workspace,
        sampled_indices,
        replicate_index=replicate_index,
    )
    replicate_network_events = replicate_base.events
    if replicate_network_events is None:
        raise RuntimeError("replicate base workspace lost accepted events.")
    replicate_events = _resample_network_time_events(
        workspace.events,
        replicate_network_events,
        sampled_indices,
        replicate_index=replicate_index,
    )
    distance_asset = _reindex_network_time_asset(
        workspace.distance_asset,
        workspace,
        replicate_base,
        replicate_events,
        sampled_indices,
        replicate_index=replicate_index,
    )
    return NetworkTimeWorkspace(
        network_workspace=replicate_base,
        events=replicate_events,
        arixels=workspace.arixels,
        distance_asset=distance_asset,
    )


def _result_fingerprint(
    result: NetworkTimeField,
    contract: _TemporalNetworkBootstrapContract,
) -> str:
    return stable_fingerprint(
        "BootstrapTemporalNetworkKDEResult",
        contract.fingerprint,
        result.event_fingerprint,
        result.network_fingerprint,
        result.support.fingerprint,
    )


def _resolve_replicate_execution(
    estimator: TemporalNetworkKDE,
    workspace: NetworkTimeWorkspace,
    contract: _TemporalNetworkBootstrapContract,
    plan: BootstrapPlan,
) -> tuple[
    ResolvedReplicateExecution,
    ExecutionPlan,
    _TemporalNetworkMemoryModel,
]:
    events = workspace.events
    requested = plan.execution_plan or ExecutionPlan()
    target_execution = _target_execution_plan(estimator, plan)
    time_chunk_rows = min(
        workspace.arixels.n_times,
        target_execution.target_chunk_size or workspace.arixels.n_times,
    )
    concurrent_workers = requested.n_jobs if requested.backend == "thread" else 1
    n_events = events.n_events
    n_lixels = workspace.arixels.lixels.n_lixels
    n_arixels = workspace.arixels.n_arixels
    ensemble_bytes = int(plan.n_resamples * n_arixels * 8 + n_arixels * 8 + n_arixels)
    rejected_bytes = int(
        workspace.network_workspace.snap_result.rejected.memory_usage(
            index=True,
            deep=True,
        ).sum()
    )
    input_bytes = int(
        _direct_array_bytes(workspace.network)
        + _direct_array_bytes(events.network_events)
        + events.temporal.values.nbytes
        + _direct_array_bytes(workspace.arixels.lixels)
        + workspace.arixels.time_edges.nbytes
        + workspace.arixels.time_centers.nbytes
        + workspace.arixels.time_widths.nbytes
        + workspace.arixels.measure.nbytes
        + _distance_asset_bytes(workspace.network_workspace.distance_asset)
        + _distance_asset_bytes(workspace.network_workspace.event_distance_asset)
        + _network_time_asset_bytes(workspace.distance_asset)
        + rejected_bytes
    )
    event_lixel_pair_bound = n_events * n_lixels
    reindexed_base_assets = int(
        event_lixel_pair_bound * 24
        + n_events * 8
        + n_lixels * 8
        + (
            n_events * n_events * 24
            if workspace.network_workspace.event_distance_asset is not None
            else 0
        )
    )
    factorized_asset_bytes = int(
        event_lixel_pair_bound * 24
        + workspace.arixels.n_times * n_events * 16
        + n_events * 8
        + n_lixels * 8
    )
    propagation_record_bound = 0
    if contract.junction_policy != "simple":
        propagation_record_bound = n_events * contract.max_records_per_event
    one_worker_bytes = int(
        n_events * 8
        + _direct_array_bytes(events.network_events)
        + events.temporal.values.nbytes
        + n_events * 24
        + rejected_bytes
        + reindexed_base_assets
        + factorized_asset_bytes
        + n_events * n_lixels * 8
        + time_chunk_rows * n_events * 16
        + time_chunk_rows * n_lixels * 8
        + n_arixels * 8
        + propagation_record_bound * 96
    )
    fixed_overhead = int(
        ensemble_bytes
        + input_bytes
        + ceil(one_worker_bytes * 1.25 * concurrent_workers)
    )
    resolved = resolve_replicate_execution(
        plan.execution_plan,
        operation_name=(f"bootstrap_kde.temporal_network.{contract.junction_policy}"),
        n_replicates=plan.n_resamples,
        bytes_per_replicate=n_arixels * 8,
        fixed_overhead_bytes=fixed_overhead,
    )
    memory_model = _TemporalNetworkMemoryModel(
        ensemble_bytes=ensemble_bytes,
        input_bytes=input_bytes,
        one_worker_bytes=one_worker_bytes,
        event_lixel_pair_bound=event_lixel_pair_bound,
        propagation_record_bound=propagation_record_bound,
        requested_concurrent_workers=int(concurrent_workers),
        time_chunk_rows=int(time_chunk_rows),
    )
    return resolved, target_execution, memory_model


def _validate_inputs(
    estimator: TemporalNetworkKDE,
    workspace: NetworkTimeWorkspace,
    plan: BootstrapPlan | None,
) -> tuple[BootstrapPlan, _TemporalNetworkBootstrapContract]:
    if not isinstance(estimator, TemporalNetworkKDE):
        raise TypeError("estimator must be a TemporalNetworkKDE.")
    if not isinstance(workspace, NetworkTimeWorkspace):
        raise TypeError("workspace must be a NetworkTimeWorkspace.")
    if plan is not None and not isinstance(plan, BootstrapPlan):
        raise TypeError("plan must be a BootstrapPlan or None.")
    workspace.validate().raise_for_errors()
    _require_unit_weights(workspace.events.network_events)
    bootstrap_plan = BootstrapPlan() if plan is None else plan
    contract = _build_contract(estimator, workspace)
    return bootstrap_plan, contract


def bootstrap_temporal_network_kde(
    estimator: TemporalNetworkKDE,
    workspace: NetworkTimeWorkspace,
    *,
    plan: BootstrapPlan | None = None,
) -> BootstrapResult:
    """Ordinary pointwise Bootstrap for a fixed temporal-network KDE field."""
    bootstrap_plan, contract = _validate_inputs(estimator, workspace, plan)
    events = workspace.events
    resolved, target_execution, memory_model = _resolve_replicate_execution(
        estimator,
        workspace,
        contract,
        bootstrap_plan,
    )
    seed_ledger: SeedLedger = build_seed_ledger(
        bootstrap_plan.random_state,
        bootstrap_plan.n_resamples,
    )
    observed_result = _new_estimator(contract, target_execution).fit_predict(workspace)
    if observed_result.support.fingerprint != workspace.arixels.fingerprint:
        raise RuntimeError(
            "observed temporal-network Bootstrap support fingerprint changed."
        )
    observed_fingerprint = _result_fingerprint(observed_result, contract)
    replicate_values = np.empty(
        (bootstrap_plan.n_resamples, workspace.arixels.n_arixels),
        dtype=float,
    )
    replicate_fingerprints: list[str | None] = [None] * bootstrap_plan.n_resamples
    replicate_workspace_fingerprints: list[str | None] = [
        None
    ] * bootstrap_plan.n_resamples

    def worker(
        start: int,
        stop: int,
    ) -> tuple[np.ndarray, tuple[str, ...], tuple[str, ...]]:
        block = np.empty((stop - start, workspace.arixels.n_arixels), dtype=float)
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
            replicate_workspace = _resample_network_time_workspace(
                workspace,
                sampled_indices,
                replicate_index=replicate_index,
            )
            replicate_result = _new_estimator(
                contract,
                target_execution,
            ).fit_predict(replicate_workspace)
            if replicate_result.support.fingerprint != workspace.arixels.fingerprint:
                raise RuntimeError(
                    "temporal-network Bootstrap replicate support fingerprint changed."
                )
            if (
                replicate_workspace.events.temporal.domain.fingerprint
                != contract.time_domain_fingerprint
            ):
                raise RuntimeError(
                    "temporal-network Bootstrap replicate time domain changed."
                )
            block[local_index] = replicate_result.values
            event_fingerprints.append(replicate_workspace.events.fingerprint)
            workspace_fingerprints.append(replicate_workspace.fingerprint)
        return block, tuple(event_fingerprints), tuple(workspace_fingerprints)

    for start, stop, chunk_result in execute_replicate_chunks(resolved, worker):
        block, event_fingerprints, workspace_fingerprints = chunk_result
        replicate_values[start:stop] = block
        replicate_fingerprints[start:stop] = event_fingerprints
        replicate_workspace_fingerprints[start:stop] = workspace_fingerprints

    if any(value is None for value in replicate_fingerprints):
        raise RuntimeError(
            "temporal-network Bootstrap event fingerprints are incomplete."
        )
    if any(value is None for value in replicate_workspace_fingerprints):
        raise RuntimeError(
            "temporal-network Bootstrap workspace fingerprints are incomplete."
        )
    completed_event_fingerprints = tuple(
        str(value) for value in replicate_fingerprints if value is not None
    )
    completed_workspace_fingerprints = tuple(
        str(value) for value in replicate_workspace_fingerprints if value is not None
    )
    relative_risk_contract, relative_risk_contract_fingerprint = (
        build_relative_risk_contract(
            result_family="network_time",
            support_fingerprint=contract.support_fingerprint,
            target=contract.target,
            bandwidths=(contract.spatial_bandwidth, contract.temporal_bandwidth),
            components={
                "spatial_kernel": contract.spatial_kernel,
                "temporal_kernel": contract.temporal_kernel,
                "junction_policy": contract.junction_policy,
                "directed": contract.effective_directed,
                "network_fingerprint": contract.network_fingerprint,
                "path_based": contract.junction_policy != "simple",
                "cyclic_tail_tolerance": contract.cyclic_tail_tolerance,
                "coefficient_tolerance": contract.coefficient_tolerance,
                "max_records_per_event": contract.max_records_per_event,
                "time_domain_fingerprint": contract.time_domain_fingerprint,
            },
        )
    )
    common_metadata: dict[str, Any] = {
        "estimator_contract_fingerprint": contract.fingerprint,
        "relative_risk_contract": relative_risk_contract,
        "relative_risk_contract_fingerprint": relative_risk_contract_fingerprint,
        "source_workspace_fingerprint": workspace.fingerprint,
        "source_event_fingerprint": events.fingerprint,
        "network_fingerprint": workspace.network.fingerprint,
        "support_fingerprint": workspace.arixels.fingerprint,
        "time_domain_fingerprint": events.temporal.domain.fingerprint,
        "time_domain": events.temporal.domain.name,
        "temporal_unit": events.temporal.temporal_unit,
        "temporal_origin": events.temporal.temporal_origin,
        "timezone": events.temporal.timezone,
        "conditional_on_observed_event_count": True,
        "resampling_stage": "after_accepted_event_snapping",
        "resampling_unit": "paired_snapped_network_time_event_identity",
        "unit_event_weights": True,
        "n_events": events.n_events,
        "n_rejected_fixed": workspace.network_workspace.snap_result.n_rejected,
        "junction_policy": contract.junction_policy,
        "directed": contract.effective_directed,
    }
    ensemble = FieldEnsemble(
        replicate_values=replicate_values,
        observed_values=observed_result.values,
        support=workspace.arixels,
        field_family=contract.target,
        observed_field_fingerprint=observed_fingerprint,
        replicate_source_fingerprints=completed_event_fingerprints,
        resampling_method=bootstrap_plan.method,
        seed_ledger_fingerprint=seed_ledger.fingerprint,
        execution_metadata=resolved.to_metadata(),
        metadata={
            "estimator_family": "temporal_network",
            **common_metadata,
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
        estimator_family="temporal_network",
        seed_metadata=seed_ledger.to_metadata(),
        metadata={
            **common_metadata,
            "observed_result_fingerprint": observed_fingerprint,
        },
    )
