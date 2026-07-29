# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Closed ordinary-Bootstrap adapter for measured space-time KDE fields."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import numpy as np

from pykdex.core.spatiotemporal_results import SpatiotemporalKDEResult
from pykdex.data import SpatialEvents
from pykdex.data._utils import stable_fingerprint
from pykdex.data.spatiotemporal import (
    SpatiotemporalEvents,
    SpatiotemporalGridSupport,
    TemporalCoordinates,
)
from pykdex.estimators.spatiotemporal_kde import SpatiotemporalKDE
from pykdex.execution import ExecutionPlan
from pykdex.execution.replicates import (
    ResolvedReplicateExecution,
    execute_replicate_chunks,
    resolve_replicate_execution,
)
from pykdex.kernels import get_kernel
from pykdex.metrics import get_metric
from pykdex.uncertainty.contracts import build_relative_risk_contract
from pykdex.uncertainty.fields import FieldEnsemble, pointwise_percentile_interval
from pykdex.uncertainty.plan import BootstrapPlan
from pykdex.uncertainty.results import BootstrapResult
from pykdex.uncertainty.seeds import SeedLedger, build_seed_ledger


@dataclass(frozen=True)
class _SpatiotemporalBootstrapContract:
    spatial_bandwidth: float
    temporal_bandwidth: float
    spatial_kernel: str
    temporal_kernel: str
    spatial_metric: str
    target: str
    cyclic_tail_tolerance: float
    event_time_domain_fingerprint: str
    support_fingerprint: str

    @property
    def fingerprint(self) -> str:
        return stable_fingerprint(
            "SpatiotemporalBootstrapContract",
            self.spatial_bandwidth,
            self.temporal_bandwidth,
            self.spatial_kernel,
            self.temporal_kernel,
            self.spatial_metric,
            self.target,
            self.cyclic_tail_tolerance,
            self.event_time_domain_fingerprint,
            self.support_fingerprint,
        )


@dataclass(frozen=True)
class _SpatiotemporalMemoryModel:
    ensemble_bytes: int
    input_bytes: int
    one_worker_bytes: int
    requested_concurrent_workers: int
    target_chunk_rows: int

    def to_metadata(self) -> dict[str, int]:
        return {
            "ensemble_bytes": self.ensemble_bytes,
            "input_bytes": self.input_bytes,
            "one_worker_bytes": self.one_worker_bytes,
            "requested_concurrent_workers": self.requested_concurrent_workers,
            "target_chunk_rows": self.target_chunk_rows,
        }


def _array_bytes(value: np.ndarray | None) -> int:
    return 0 if value is None else int(value.nbytes)


def _require_unit_weights(events: SpatiotemporalEvents) -> None:
    if not np.array_equal(events.weights, np.ones(events.n_events, dtype=float)):
        raise ValueError(
            "spatiotemporal bootstrap_kde initially requires unit event weights; "
            "weighted Bootstrap semantics are not implemented."
        )


def _validate_event_support_compatibility(
    events: SpatiotemporalEvents,
    support: SpatiotemporalGridSupport,
) -> None:
    if events.spatial.dimension != support.spatial.dimension:
        raise ValueError("event and support spatial dimensions differ.")
    if events.spatial.crs != support.spatial.crs:
        raise ValueError("event and support CRS labels differ.")
    if events.spatial.spatial_unit != support.spatial.spatial_unit:
        raise ValueError("event and support spatial units differ.")
    if events.temporal.temporal_unit != support.temporal_unit:
        raise ValueError("event and support temporal units differ.")
    if events.temporal.domain.fingerprint != support.time_domain.fingerprint:
        raise ValueError("event and support time-domain fingerprints differ.")
    if events.temporal.temporal_origin != support.temporal_origin:
        raise ValueError("event and support temporal origins differ.")
    if events.temporal.timezone != support.timezone:
        raise ValueError("event and support timezones differ.")


def _build_contract(
    estimator: SpatiotemporalKDE,
    events: SpatiotemporalEvents,
    support: SpatiotemporalGridSupport,
) -> _SpatiotemporalBootstrapContract:
    for name, value in (
        ("spatial_kernel", estimator.spatial_kernel),
        ("temporal_kernel", estimator.temporal_kernel),
        ("spatial_metric", estimator.spatial_metric),
    ):
        if not isinstance(value, str):
            raise ValueError(
                "spatiotemporal bootstrap_kde initially requires built-in string "
                f"names for kernels and metric; {name} was an object."
            )
    spatial_kernel = get_kernel(estimator.spatial_kernel)
    temporal_kernel = get_kernel(estimator.temporal_kernel)
    spatial_metric = get_metric(estimator.spatial_metric)
    return _SpatiotemporalBootstrapContract(
        spatial_bandwidth=float(estimator.spatial_bandwidth),
        temporal_bandwidth=float(estimator.temporal_bandwidth),
        spatial_kernel=spatial_kernel.name,
        temporal_kernel=temporal_kernel.name,
        spatial_metric=spatial_metric.name,
        target=estimator.target,
        cyclic_tail_tolerance=estimator.cyclic_tail_tolerance,
        event_time_domain_fingerprint=events.temporal.domain.fingerprint,
        support_fingerprint=support.fingerprint,
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
    contract: _SpatiotemporalBootstrapContract,
    target_execution: ExecutionPlan,
) -> SpatiotemporalKDE:
    return SpatiotemporalKDE(
        spatial_bandwidth=contract.spatial_bandwidth,
        temporal_bandwidth=contract.temporal_bandwidth,
        spatial_kernel=contract.spatial_kernel,
        temporal_kernel=contract.temporal_kernel,
        spatial_metric=contract.spatial_metric,
        target=contract.target,
        execution_plan=target_execution,
        cyclic_tail_tolerance=contract.cyclic_tail_tolerance,
    )


def _resample_spatiotemporal_events(
    events: SpatiotemporalEvents,
    sampled_indices: np.ndarray,
    *,
    replicate_index: int,
) -> SpatiotemporalEvents:
    sampled = np.asarray(sampled_indices, dtype=np.int64)
    if sampled.shape != (events.n_events,):
        raise ValueError("sampled indices must preserve the observed event count.")
    if np.any(sampled < 0) or np.any(sampled >= events.n_events):
        raise IndexError("sampled space-time event index is outside the source events.")
    common_metadata = {
        "replicate_index": int(replicate_index),
        "sampled_source_indices": sampled.tolist(),
        "source_event_fingerprint": events.fingerprint,
        "resampling_unit": "paired_space_time_event_identity",
    }
    spatial_provenance = events.spatial.provenance.with_transformation(
        "ordinary_bootstrap_resample",
        **common_metadata,
    )
    temporal_provenance = events.temporal.provenance.with_transformation(
        "ordinary_bootstrap_resample",
        **common_metadata,
    )
    joint_provenance = events.provenance.with_transformation(
        "ordinary_bootstrap_resample",
        **common_metadata,
    )
    marks = None if events.spatial.marks is None else events.spatial.marks[sampled]
    spatial = SpatialEvents(
        coordinates=events.spatial.coordinates[sampled],
        weights=np.ones(events.n_events, dtype=float),
        ids=np.arange(events.n_events, dtype=np.int64),
        coordinate_names=events.spatial.coordinate_names,
        crs=events.spatial.crs,
        spatial_unit=events.spatial.spatial_unit,
        marks=marks,
        provenance=spatial_provenance,
    )
    temporal = TemporalCoordinates(
        values=events.temporal.values[sampled],
        domain=events.temporal.domain,
        temporal_unit=events.temporal.temporal_unit,
        temporal_origin=events.temporal.temporal_origin,
        timezone=events.temporal.timezone,
        provenance=temporal_provenance,
    )
    return SpatiotemporalEvents(
        spatial=spatial,
        temporal=temporal,
        provenance=joint_provenance,
    )


def _result_fingerprint(result: SpatiotemporalKDEResult) -> str:
    metadata = dict(result.metadata)
    return stable_fingerprint(
        "BootstrapSpatiotemporalKDEResult",
        result.values,
        result.support.fingerprint,
        result.spatial_bandwidth,
        result.temporal_bandwidth,
        result.target,
        result.spatial_kernel,
        result.temporal_kernel,
        result.spatial_metric,
        metadata.get("time_domain"),
    )


def _resolve_replicate_execution(
    events: SpatiotemporalEvents,
    support: SpatiotemporalGridSupport,
    plan: BootstrapPlan,
) -> tuple[
    ResolvedReplicateExecution,
    ExecutionPlan,
    _SpatiotemporalMemoryModel,
]:
    requested = plan.execution_plan or ExecutionPlan()
    target_execution = _target_execution_plan(plan)
    target_rows = min(
        support.n_points,
        requested.target_chunk_size or support.n_points,
    )
    concurrent_workers = requested.n_jobs if requested.backend == "thread" else 1
    ensemble_bytes = int(
        plan.n_resamples * support.n_points * 8
        + support.n_points * 8
        + support.n_points
    )
    input_bytes = int(
        events.spatial.coordinates.nbytes
        + events.temporal.values.nbytes
        + events.weights.nbytes
        + events.ids.nbytes
        + _array_bytes(events.spatial.marks)
        + support.spatial.coordinates.nbytes
        + support.spatial.measure.nbytes
        + support.time_edges.nbytes
        + support.time_centers.nbytes
        + support.time_widths.nbytes
        + support.spatial_coordinates.nbytes
        + support.times.nbytes
        + support.measure.nbytes
        + support.ids.nbytes
    )
    one_worker_bytes = int(
        events.n_events * 8
        + events.n_events * events.spatial.dimension * 8
        + events.n_events * 8
        + events.n_events * 8
        + events.n_events * 8
        + _array_bytes(events.spatial.marks)
        + support.n_points * 8
        + target_rows * events.n_events * 96
        + target_rows * (events.spatial.dimension + 2) * 8
    )
    fixed_overhead = int(
        ensemble_bytes
        + input_bytes
        + ceil(one_worker_bytes * 1.25 * concurrent_workers)
    )
    resolved = resolve_replicate_execution(
        plan.execution_plan,
        operation_name="bootstrap_kde.spatiotemporal",
        n_replicates=plan.n_resamples,
        bytes_per_replicate=support.n_points * 8,
        fixed_overhead_bytes=fixed_overhead,
    )
    memory_model = _SpatiotemporalMemoryModel(
        ensemble_bytes=ensemble_bytes,
        input_bytes=input_bytes,
        one_worker_bytes=one_worker_bytes,
        requested_concurrent_workers=int(concurrent_workers),
        target_chunk_rows=int(target_rows),
    )
    return resolved, target_execution, memory_model


def _validate_inputs(
    estimator: SpatiotemporalKDE,
    events: SpatiotemporalEvents,
    support: SpatiotemporalGridSupport,
    plan: BootstrapPlan | None,
) -> tuple[BootstrapPlan, _SpatiotemporalBootstrapContract]:
    if not isinstance(estimator, SpatiotemporalKDE):
        raise TypeError("estimator must be a SpatiotemporalKDE.")
    if not isinstance(events, SpatiotemporalEvents):
        raise TypeError("events must be a SpatiotemporalEvents object.")
    if not isinstance(support, SpatiotemporalGridSupport):
        raise TypeError("support must be a SpatiotemporalGridSupport.")
    if plan is not None and not isinstance(plan, BootstrapPlan):
        raise TypeError("plan must be a BootstrapPlan or None.")
    events.validate().raise_for_errors()
    _require_unit_weights(events)
    _validate_event_support_compatibility(events, support)
    bootstrap_plan = BootstrapPlan() if plan is None else plan
    contract = _build_contract(estimator, events, support)
    return bootstrap_plan, contract


def bootstrap_spatiotemporal_kde(
    estimator: SpatiotemporalKDE,
    events: SpatiotemporalEvents,
    support: SpatiotemporalGridSupport,
    *,
    plan: BootstrapPlan | None = None,
) -> BootstrapResult:
    """Ordinary pointwise Bootstrap for fixed-contract measured space-time KDE."""
    bootstrap_plan, contract = _validate_inputs(estimator, events, support, plan)
    resolved, target_execution, memory_model = _resolve_replicate_execution(
        events,
        support,
        bootstrap_plan,
    )
    seed_ledger: SeedLedger = build_seed_ledger(
        bootstrap_plan.random_state,
        bootstrap_plan.n_resamples,
    )
    observed_result = _new_estimator(contract, target_execution).fit_predict(
        events,
        support,
    )
    if observed_result.support.fingerprint != support.fingerprint:
        raise RuntimeError("observed space-time Bootstrap support fingerprint changed.")
    observed_fingerprint = _result_fingerprint(observed_result)
    replicate_values = np.empty(
        (bootstrap_plan.n_resamples, support.n_points),
        dtype=float,
    )
    replicate_fingerprints: list[str | None] = [None] * bootstrap_plan.n_resamples

    def worker(start: int, stop: int) -> tuple[np.ndarray, tuple[str, ...]]:
        block = np.empty((stop - start, support.n_points), dtype=float)
        fingerprints: list[str] = []
        for local_index, replicate_index in enumerate(range(start, stop)):
            generator = seed_ledger.generator(replicate_index)
            sampled_indices = generator.integers(
                0,
                events.n_events,
                size=events.n_events,
                dtype=np.int64,
            )
            replicate_events = _resample_spatiotemporal_events(
                events,
                sampled_indices,
                replicate_index=replicate_index,
            )
            replicate_result = _new_estimator(
                contract,
                target_execution,
            ).fit_predict(replicate_events, support)
            if replicate_result.support.fingerprint != support.fingerprint:
                raise RuntimeError(
                    "space-time Bootstrap replicate support fingerprint changed."
                )
            if (
                replicate_events.temporal.domain.fingerprint
                != contract.event_time_domain_fingerprint
            ):
                raise RuntimeError(
                    "space-time Bootstrap replicate time domain changed."
                )
            block[local_index] = replicate_result.values
            fingerprints.append(replicate_events.fingerprint)
        return block, tuple(fingerprints)

    for start, stop, chunk_result in execute_replicate_chunks(resolved, worker):
        block, fingerprints = chunk_result
        replicate_values[start:stop] = block
        replicate_fingerprints[start:stop] = fingerprints

    if any(value is None for value in replicate_fingerprints):
        raise RuntimeError(
            "space-time Bootstrap replicate fingerprints are incomplete."
        )
    completed_fingerprints = tuple(
        str(value) for value in replicate_fingerprints if value is not None
    )
    relative_risk_contract, relative_risk_contract_fingerprint = (
        build_relative_risk_contract(
            result_family="spatiotemporal",
            support_fingerprint=contract.support_fingerprint,
            target=contract.target,
            bandwidths=(contract.spatial_bandwidth, contract.temporal_bandwidth),
            components={
                "spatial_kernel": contract.spatial_kernel,
                "temporal_kernel": contract.temporal_kernel,
                "spatial_metric": contract.spatial_metric,
                "cyclic_tail_tolerance": contract.cyclic_tail_tolerance,
                "time_domain_fingerprint": contract.event_time_domain_fingerprint,
            },
        )
    )
    common_metadata = {
        "estimator_contract_fingerprint": contract.fingerprint,
        "relative_risk_contract": relative_risk_contract,
        "relative_risk_contract_fingerprint": relative_risk_contract_fingerprint,
        "source_event_fingerprint": events.fingerprint,
        "support_fingerprint": support.fingerprint,
        "time_domain_fingerprint": events.temporal.domain.fingerprint,
        "time_domain": events.temporal.domain.name,
        "temporal_unit": events.temporal.temporal_unit,
        "temporal_origin": events.temporal.temporal_origin,
        "timezone": events.temporal.timezone,
        "conditional_on_observed_event_count": True,
        "resampling_unit": "paired_space_time_event_identity",
        "unit_event_weights": True,
        "n_events": events.n_events,
    }
    ensemble = FieldEnsemble(
        replicate_values=replicate_values,
        observed_values=observed_result.values,
        support=support,
        field_family=contract.target,
        observed_field_fingerprint=observed_fingerprint,
        replicate_source_fingerprints=completed_fingerprints,
        resampling_method=bootstrap_plan.method,
        seed_ledger_fingerprint=seed_ledger.fingerprint,
        execution_metadata=resolved.to_metadata(),
        metadata={
            "estimator_family": "spatiotemporal",
            **common_metadata,
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
        estimator_family="spatiotemporal",
        seed_metadata=seed_ledger.to_metadata(),
        metadata={
            **common_metadata,
            "observed_result_fingerprint": observed_fingerprint,
        },
    )
