# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Closed ordinary-Bootstrap adapter for spatial KDE fields."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from numbers import Real

import numpy as np

from pykdex.corrections import get_boundary_correction
from pykdex.data import GridSupport, SpatialBoundary, SpatialEvents
from pykdex.data._utils import stable_fingerprint
from pykdex.estimators.spatial_kde import SpatialKDE
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
class _SpatialBootstrapContract:
    kernel: str
    bandwidth: float
    metric: str
    target: str
    boundary: SpatialBoundary | None
    boundary_correction: str
    support_fingerprint: str

    @property
    def fingerprint(self) -> str:
        return stable_fingerprint(
            "SpatialBootstrapContract",
            self.kernel,
            self.bandwidth,
            self.metric,
            self.target,
            None if self.boundary is None else self.boundary.fingerprint,
            self.boundary_correction,
            self.support_fingerprint,
        )


def _require_unit_weights(events: SpatialEvents) -> None:
    assert events.weights is not None
    if not np.array_equal(events.weights, np.ones(events.n_events, dtype=float)):
        raise ValueError(
            "bootstrap_kde initially requires unit event weights; weighted "
            "Bootstrap semantics are not implemented."
        )


def _require_fixed_scalar_bandwidth(estimator: SpatialKDE) -> float:
    value = estimator.bandwidth
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (Real, np.integer, np.floating),
    ):
        raise ValueError(
            "bootstrap_kde requires SpatialKDE bandwidth to be a fixed numeric "
            "scalar; selectors, adaptive vectors, matrices, and balloon bandwidths "
            "are not supported."
        )
    bandwidth = float(value)
    if not np.isfinite(bandwidth) or bandwidth <= 0.0:
        raise ValueError("bootstrap_kde bandwidth must be finite and positive.")
    return bandwidth


def _build_contract(
    estimator: SpatialKDE,
    support: GridSupport,
) -> _SpatialBootstrapContract:
    bandwidth = _require_fixed_scalar_bandwidth(estimator)
    for name, value in (
        ("kernel", estimator.kernel),
        ("metric", estimator.metric),
        ("boundary_correction", estimator.boundary_correction),
    ):
        if not isinstance(value, str):
            raise ValueError(
                "bootstrap_kde initially requires built-in string names for "
                f"kernel, metric, and boundary_correction; {name} was an object."
            )
    kernel = get_kernel(estimator.kernel)
    metric = get_metric(estimator.metric)
    correction = get_boundary_correction(estimator.boundary_correction)
    boundary = estimator.boundary
    if boundary is not None and not isinstance(boundary, SpatialBoundary):
        raise TypeError("SpatialKDE boundary must be a SpatialBoundary or None.")
    if boundary is None and correction.name != "none":
        raise ValueError("boundary correction requires a fixed SpatialBoundary.")
    return _SpatialBootstrapContract(
        kernel=kernel.name,
        bandwidth=bandwidth,
        metric=metric.name,
        target=estimator.target,
        boundary=boundary,
        boundary_correction=correction.name,
        support_fingerprint=support.fingerprint,
    )


def _target_execution_plan(
    plan: BootstrapPlan,
) -> ExecutionPlan:
    requested = plan.execution_plan or ExecutionPlan()
    return ExecutionPlan(
        memory_budget_bytes=None,
        target_chunk_size=requested.target_chunk_size,
        n_jobs=1,
        backend="sequential",
    )


def _new_estimator(
    contract: _SpatialBootstrapContract,
    target_execution: ExecutionPlan,
) -> SpatialKDE:
    return SpatialKDE(
        kernel=contract.kernel,
        bandwidth=contract.bandwidth,
        metric=contract.metric,
        target=contract.target,
        boundary=contract.boundary,
        boundary_correction=contract.boundary_correction,
        execution_plan=target_execution,
    )


def _resample_spatial_events(
    events: SpatialEvents,
    indices: np.ndarray,
    *,
    replicate_index: int,
) -> SpatialEvents:
    sampled = np.asarray(indices, dtype=np.int64)
    if sampled.shape != (events.n_events,):
        raise ValueError("sampled indices must preserve the observed event count.")
    marks = None if events.marks is None else events.marks[sampled]
    provenance = events.provenance.with_transformation(
        "ordinary_bootstrap_resample",
        replicate_index=int(replicate_index),
        sampled_source_indices=sampled.tolist(),
        source_event_fingerprint=events.fingerprint,
    )
    return SpatialEvents(
        coordinates=events.coordinates[sampled],
        weights=np.ones(events.n_events, dtype=float),
        ids=np.arange(events.n_events, dtype=np.int64),
        coordinate_names=events.coordinate_names,
        crs=events.crs,
        spatial_unit=events.spatial_unit,
        marks=marks,
        provenance=provenance,
    )


def _spatial_result_fingerprint(result: object) -> str:
    from pykdex.core.results import SpatialKDEResult

    if not isinstance(result, SpatialKDEResult):
        raise TypeError("result must be a SpatialKDEResult.")
    metadata = dict(result.metadata)
    return stable_fingerprint(
        "BootstrapSpatialKDEResult",
        result.values,
        result.support_fingerprint,
        result.bandwidth,
        result.target,
        result.kernel,
        result.metric,
        result.crs,
        result.spatial_unit,
        metadata.get("boundary_correction"),
        metadata.get("boundary_fingerprint"),
    )


def _array_bytes(value: np.ndarray | None) -> int:
    return 0 if value is None else int(value.nbytes)


def _resolve_spatial_replicate_execution(
    events: SpatialEvents,
    support: GridSupport,
    plan: BootstrapPlan,
) -> tuple[ResolvedReplicateExecution, ExecutionPlan, dict[str, int]]:
    requested = plan.execution_plan or ExecutionPlan()
    target_execution = _target_execution_plan(plan)
    target_rows = min(
        support.n_points,
        requested.target_chunk_size or support.n_points,
    )
    concurrent_workers = requested.n_jobs if requested.backend == "thread" else 1
    ensemble_bytes = (
        plan.n_resamples * support.n_points * 8
        + support.n_points * 8
        + support.n_points
    )
    input_bytes = (
        events.coordinates.nbytes
        + _array_bytes(events.weights)
        + _array_bytes(events.ids)
        + _array_bytes(events.marks)
        + support.coordinates.nbytes
        + support.measure.nbytes
        + _array_bytes(support.ids)
    )
    one_worker_bytes = (
        events.n_events * 8
        + events.n_events * events.dimension * 8
        + events.n_events * 8
        + events.n_events * 8
        + _array_bytes(events.marks)
        + support.n_points * 8
        + target_rows * events.n_events * 96
    )
    fixed_overhead = int(
        ensemble_bytes
        + input_bytes
        + ceil(one_worker_bytes * 1.25 * concurrent_workers)
    )
    resolved = resolve_replicate_execution(
        plan.execution_plan,
        operation_name="bootstrap_kde.spatial",
        n_replicates=plan.n_resamples,
        bytes_per_replicate=support.n_points * 8,
        fixed_overhead_bytes=fixed_overhead,
    )
    memory_metadata = {
        "ensemble_bytes": int(ensemble_bytes),
        "input_bytes": int(input_bytes),
        "one_worker_bytes": int(one_worker_bytes),
        "requested_concurrent_workers": int(concurrent_workers),
        "target_chunk_rows": int(target_rows),
    }
    return resolved, target_execution, memory_metadata


def _validate_inputs(
    estimator: SpatialKDE,
    events: SpatialEvents,
    support: GridSupport,
    plan: BootstrapPlan | None,
) -> tuple[BootstrapPlan, _SpatialBootstrapContract]:
    if not isinstance(estimator, SpatialKDE):
        raise TypeError("estimator must be a SpatialKDE.")
    if not isinstance(events, SpatialEvents):
        raise TypeError("events must be a SpatialEvents object.")
    if not isinstance(support, GridSupport):
        raise TypeError("support must be a GridSupport.")
    if plan is not None and not isinstance(plan, BootstrapPlan):
        raise TypeError("plan must be a BootstrapPlan or None.")
    bootstrap_plan = BootstrapPlan() if plan is None else plan
    _require_unit_weights(events)
    contract = _build_contract(estimator, support)
    return bootstrap_plan, contract


def bootstrap_kde(
    estimator: SpatialKDE,
    events: SpatialEvents,
    support: GridSupport,
    *,
    plan: BootstrapPlan | None = None,
) -> BootstrapResult:
    """Ordinary pointwise Bootstrap for fixed-contract spatial KDE fields.

    The initial adapter is deliberately closed to ``SpatialEvents``,
    ``GridSupport``, and ``SpatialKDE`` with unit weights and a fixed scalar
    numeric bandwidth. Event count, support, and estimator configuration remain
    fixed in every replicate.
    """
    bootstrap_plan, contract = _validate_inputs(estimator, events, support, plan)
    resolved, target_execution, memory_metadata = _resolve_spatial_replicate_execution(
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
    if observed_result.support_fingerprint != support.fingerprint:
        raise RuntimeError("observed Bootstrap support fingerprint changed.")
    observed_fingerprint = _spatial_result_fingerprint(observed_result)
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
            replicate_events = _resample_spatial_events(
                events,
                sampled_indices,
                replicate_index=replicate_index,
            )
            replicate_result = _new_estimator(
                contract,
                target_execution,
            ).fit_predict(replicate_events, support)
            if replicate_result.support_fingerprint != support.fingerprint:
                raise RuntimeError("Bootstrap replicate support fingerprint changed.")
            block[local_index] = replicate_result.values
            fingerprints.append(replicate_events.fingerprint)
        return block, tuple(fingerprints)

    for start, stop, chunk_result in execute_replicate_chunks(resolved, worker):
        block, fingerprints = chunk_result
        replicate_values[start:stop] = block
        replicate_fingerprints[start:stop] = fingerprints

    if any(value is None for value in replicate_fingerprints):
        raise RuntimeError("Bootstrap replicate fingerprints are incomplete.")
    completed_fingerprints = tuple(
        str(value) for value in replicate_fingerprints if value is not None
    )
    relative_risk_contract, relative_risk_contract_fingerprint = (
        build_relative_risk_contract(
            result_family="spatial",
            support_fingerprint=contract.support_fingerprint,
            target=contract.target,
            bandwidths=(contract.bandwidth,),
            components={
                "kernel": contract.kernel,
                "metric": contract.metric,
                "boundary_correction": contract.boundary_correction,
                "boundary_fingerprint": (
                    None if contract.boundary is None else contract.boundary.fingerprint
                ),
            },
        )
    )
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
            "estimator_family": "spatial",
            "estimator_contract_fingerprint": contract.fingerprint,
            "relative_risk_contract": relative_risk_contract,
            "relative_risk_contract_fingerprint": relative_risk_contract_fingerprint,
            "source_event_fingerprint": events.fingerprint,
            "support_fingerprint": support.fingerprint,
            "conditional_on_observed_event_count": True,
            "unit_event_weights": True,
            "n_events": events.n_events,
            "memory_model": memory_metadata,
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
        estimator_family="spatial",
        seed_metadata=seed_ledger.to_metadata(),
        metadata={
            "estimator_contract_fingerprint": contract.fingerprint,
            "relative_risk_contract": relative_risk_contract,
            "relative_risk_contract_fingerprint": relative_risk_contract_fingerprint,
            "observed_result_fingerprint": observed_fingerprint,
            "source_event_fingerprint": events.fingerprint,
            "support_fingerprint": support.fingerprint,
            "conditional_on_observed_event_count": True,
        },
    )
