# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Immutable execution plans and conservative memory resolution."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any

import numpy as np

from pykdex.data._utils import stable_fingerprint

_DEFAULT_MEMORY_BUDGET_BYTES = 256 * 1024 * 1024
_VALID_BACKENDS = frozenset({"sequential", "thread"})


def _positive_int_or_none(value: int | None, *, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be a positive integer or None.")
    resolved = int(value)
    if resolved <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return resolved


def _positive_int(value: int, *, name: str) -> int:
    resolved = _positive_int_or_none(value, name=name)
    if resolved is None:  # pragma: no cover - guarded by the type and helper
        raise TypeError(f"{name} must be a positive integer.")
    return resolved


@dataclass(frozen=True)
class ExecutionPlan:
    """Requested deterministic execution and memory contract.

    Args:
        memory_budget_bytes: Conservative peak-memory budget. ``None`` disables
            budget-based chunk resolution.
        target_chunk_size: Optional number of target rows per numerical task.
        replicate_chunk_size: Optional number of resampling replicates per task.
        n_jobs: Requested number of Python workers.
        backend: ``"sequential"`` or ``"thread"``.
    """

    memory_budget_bytes: int | None = _DEFAULT_MEMORY_BUDGET_BYTES
    target_chunk_size: int | None = None
    replicate_chunk_size: int | None = None
    n_jobs: int = 1
    backend: str = "sequential"

    def __post_init__(self) -> None:
        memory = _positive_int_or_none(
            self.memory_budget_bytes,
            name="memory_budget_bytes",
        )
        target = _positive_int_or_none(
            self.target_chunk_size,
            name="target_chunk_size",
        )
        replicate = _positive_int_or_none(
            self.replicate_chunk_size,
            name="replicate_chunk_size",
        )
        jobs = _positive_int(self.n_jobs, name="n_jobs")
        backend = str(self.backend).strip().lower()
        if backend not in _VALID_BACKENDS:
            raise ValueError("backend must be either 'sequential' or 'thread'.")
        if backend == "sequential" and jobs != 1:
            raise ValueError("backend='sequential' requires n_jobs=1.")
        object.__setattr__(self, "memory_budget_bytes", memory)
        object.__setattr__(self, "target_chunk_size", target)
        object.__setattr__(self, "replicate_chunk_size", replicate)
        object.__setattr__(self, "n_jobs", jobs)
        object.__setattr__(self, "backend", backend)

    @property
    def fingerprint(self) -> str:
        """Deterministic requested-plan fingerprint."""
        return stable_fingerprint(
            "ExecutionPlan",
            self.memory_budget_bytes,
            self.target_chunk_size,
            self.replicate_chunk_size,
            self.n_jobs,
            self.backend,
        )


@dataclass(frozen=True)
class ResolvedExecutionPlan:
    """Private operation-specific execution record."""

    operation_name: str
    source: str
    memory_budget_bytes: int | None
    requested_target_chunk_size: int | None
    resolved_target_chunk_size: int
    requested_replicate_chunk_size: int | None
    n_targets: int
    n_sources: int
    bytes_per_pair: int
    fixed_overhead_bytes: int
    safety_factor: float
    requested_n_jobs: int
    resolved_n_jobs: int
    backend: str
    parallel_axis: str
    estimated_peak_bytes: int
    execution_plan_fingerprint: str

    def __post_init__(self) -> None:
        if not str(self.operation_name).strip():
            raise ValueError("operation_name must be non-empty.")
        if self.source not in {"implicit", "legacy", "explicit"}:
            raise ValueError("source must be implicit, legacy, or explicit.")
        for value, name in (
            (self.resolved_target_chunk_size, "resolved_target_chunk_size"),
            (self.n_targets, "n_targets"),
            (self.requested_n_jobs, "requested_n_jobs"),
            (self.resolved_n_jobs, "resolved_n_jobs"),
        ):
            _positive_int(value, name=name)
        if self.n_sources < 0 or self.bytes_per_pair < 0 or self.fixed_overhead_bytes < 0:
            raise ValueError("source counts and byte estimates must be non-negative.")
        if not np.isfinite(self.safety_factor) or self.safety_factor < 1.0:
            raise ValueError("safety_factor must be finite and at least one.")
        if self.resolved_target_chunk_size > self.n_targets:
            raise ValueError("resolved_target_chunk_size cannot exceed n_targets.")
        if self.resolved_n_jobs > self.requested_n_jobs:
            raise ValueError("resolved_n_jobs cannot exceed requested_n_jobs.")
        if self.backend not in _VALID_BACKENDS:
            raise ValueError("resolved backend is invalid.")
        if self.parallel_axis not in {"none", "targets", "replicates"}:
            raise ValueError("parallel_axis is invalid.")
        if self.estimated_peak_bytes < 0:
            raise ValueError("estimated_peak_bytes must be non-negative.")
        if not str(self.execution_plan_fingerprint).strip():
            raise ValueError("execution_plan_fingerprint must be non-empty.")

    @property
    def n_target_chunks(self) -> int:
        """Number of logical target chunks."""
        return int(ceil(self.n_targets / self.resolved_target_chunk_size))

    @property
    def fingerprint(self) -> str:
        """Deterministic resolved-operation fingerprint."""
        return stable_fingerprint(
            "ResolvedExecutionPlan",
            self.operation_name,
            self.source,
            self.memory_budget_bytes,
            self.requested_target_chunk_size,
            self.resolved_target_chunk_size,
            self.requested_replicate_chunk_size,
            self.n_targets,
            self.n_sources,
            self.bytes_per_pair,
            self.fixed_overhead_bytes,
            self.safety_factor,
            self.requested_n_jobs,
            self.resolved_n_jobs,
            self.backend,
            self.parallel_axis,
            self.estimated_peak_bytes,
            self.execution_plan_fingerprint,
        )

    def to_metadata(self) -> dict[str, Any]:
        """Return a JSON-compatible execution audit record."""
        return {
            "operation_name": self.operation_name,
            "source": self.source,
            "memory_budget_bytes": self.memory_budget_bytes,
            "requested_target_chunk_size": self.requested_target_chunk_size,
            "resolved_target_chunk_size": self.resolved_target_chunk_size,
            "requested_replicate_chunk_size": self.requested_replicate_chunk_size,
            "n_targets": self.n_targets,
            "n_sources": self.n_sources,
            "bytes_per_pair": self.bytes_per_pair,
            "fixed_overhead_bytes": self.fixed_overhead_bytes,
            "safety_factor": self.safety_factor,
            "requested_n_jobs": self.requested_n_jobs,
            "resolved_n_jobs": self.resolved_n_jobs,
            "backend": self.backend,
            "parallel_axis": self.parallel_axis,
            "n_target_chunks": self.n_target_chunks,
            "estimated_peak_bytes": self.estimated_peak_bytes,
            "execution_plan_fingerprint": self.execution_plan_fingerprint,
            "resolved_execution_fingerprint": self.fingerprint,
        }


def resolve_target_execution(
    plan: ExecutionPlan | None,
    *,
    operation_name: str,
    n_targets: int,
    n_sources: int,
    bytes_per_pair: int,
    fixed_overhead_bytes: int = 0,
    safety_factor: float = 1.25,
    legacy_target_chunk_size: int | None = None,
    chunkable: bool = True,
) -> ResolvedExecutionPlan:
    """Resolve one target-axis execution contract before allocating pair blocks."""
    targets = _positive_int(n_targets, name="n_targets")
    if isinstance(n_sources, (bool, np.bool_)) or not isinstance(
        n_sources, (int, np.integer)
    ):
        raise TypeError("n_sources must be a non-negative integer.")
    sources = int(n_sources)
    if sources < 0:
        raise ValueError("n_sources must be non-negative.")
    if isinstance(bytes_per_pair, (bool, np.bool_)) or not isinstance(
        bytes_per_pair, (int, np.integer)
    ):
        raise TypeError("bytes_per_pair must be a non-negative integer.")
    pair_bytes = int(bytes_per_pair)
    if pair_bytes < 0:
        raise ValueError("bytes_per_pair must be non-negative.")
    if isinstance(fixed_overhead_bytes, (bool, np.bool_)) or not isinstance(
        fixed_overhead_bytes, (int, np.integer)
    ):
        raise TypeError("fixed_overhead_bytes must be a non-negative integer.")
    overhead = int(fixed_overhead_bytes)
    if overhead < 0:
        raise ValueError("fixed_overhead_bytes must be non-negative.")
    factor = float(safety_factor)
    if not np.isfinite(factor) or factor < 1.0:
        raise ValueError("safety_factor must be finite and at least one.")
    legacy = _positive_int_or_none(
        legacy_target_chunk_size,
        name="legacy_target_chunk_size",
    )
    if plan is not None and not isinstance(plan, ExecutionPlan):
        raise TypeError("execution_plan must be an ExecutionPlan or None.")

    if plan is None:
        effective = ExecutionPlan(memory_budget_bytes=None)
        source = "legacy" if legacy is not None else "implicit"
    else:
        effective = plan
        source = "explicit"
    if legacy is not None and effective.target_chunk_size is not None:
        raise ValueError(
            "legacy chunk size and execution_plan.target_chunk_size cannot both be set."
        )

    requested_chunk = (
        effective.target_chunk_size
        if effective.target_chunk_size is not None
        else legacy
    )
    requested_effective = (
        targets if requested_chunk is None else min(requested_chunk, targets)
    )
    requested_workers = effective.n_jobs
    concurrent_workers = requested_workers if effective.backend == "thread" else 1

    if not chunkable:
        if requested_chunk is not None and requested_effective < targets:
            raise ValueError(f"{operation_name} does not support target chunking.")
        if effective.backend == "thread" and requested_workers > 1:
            raise ValueError(f"{operation_name} does not expose a threaded target axis.")
        resolved_chunk = targets
        resolved_workers = 1
        parallel_axis = "none"
        estimated = int(
            ceil(overhead + targets * sources * pair_bytes * factor)
        )
    else:
        maximum_chunk = targets
        if effective.memory_budget_bytes is not None:
            available = effective.memory_budget_bytes - overhead
            if available <= 0:
                raise MemoryError(
                    f"{operation_name} fixed overhead exceeds memory_budget_bytes."
                )
            row_bytes = int(ceil(sources * pair_bytes * factor * concurrent_workers))
            if row_bytes > 0:
                maximum_chunk = min(targets, available // row_bytes)
                if maximum_chunk < 1:
                    raise MemoryError(
                        f"{operation_name} cannot fit one target row within the "
                        "requested memory budget."
                    )
        if requested_chunk is not None and requested_effective > maximum_chunk:
            raise MemoryError(
                f"{operation_name} target_chunk_size exceeds memory_budget_bytes."
            )
        resolved_chunk = (
            maximum_chunk if requested_chunk is None else requested_effective
        )
        n_chunks = int(ceil(targets / resolved_chunk))
        resolved_workers = min(concurrent_workers, n_chunks)
        parallel_axis = (
            "targets"
            if effective.backend == "thread" and resolved_workers > 1
            else "none"
        )
        estimated = int(
            ceil(
                overhead
                + resolved_chunk
                * sources
                * pair_bytes
                * factor
                * resolved_workers
            )
        )

    if (
        effective.memory_budget_bytes is not None
        and estimated > effective.memory_budget_bytes
    ):
        raise MemoryError(
            f"{operation_name} estimated peak memory exceeds memory_budget_bytes."
        )

    return ResolvedExecutionPlan(
        operation_name=str(operation_name).strip(),
        source=source,
        memory_budget_bytes=effective.memory_budget_bytes,
        requested_target_chunk_size=requested_chunk,
        resolved_target_chunk_size=resolved_chunk,
        requested_replicate_chunk_size=effective.replicate_chunk_size,
        n_targets=targets,
        n_sources=sources,
        bytes_per_pair=pair_bytes,
        fixed_overhead_bytes=overhead,
        safety_factor=factor,
        requested_n_jobs=requested_workers,
        resolved_n_jobs=resolved_workers,
        backend=effective.backend,
        parallel_axis=parallel_axis,
        estimated_peak_bytes=estimated,
        execution_plan_fingerprint=effective.fingerprint,
    )
