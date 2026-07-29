# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Private deterministic execution for independent resampling replicates."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from math import ceil
from typing import Any, Callable, Iterator, TypeVar

import numpy as np

from pykdex.data._utils import stable_fingerprint
from pykdex.execution.plan import ExecutionPlan

_ResultT = TypeVar("_ResultT")


def _positive_int(value: int, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be a positive integer.")
    resolved = int(value)
    if resolved <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return resolved


def _nonnegative_int(value: int, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be a non-negative integer.")
    resolved = int(value)
    if resolved < 0:
        raise ValueError(f"{name} must be non-negative.")
    return resolved


@dataclass(frozen=True)
class ResolvedReplicateExecution:
    """Operation-specific private execution record for resampling tasks."""

    operation_name: str
    source: str
    memory_budget_bytes: int | None
    requested_replicate_chunk_size: int | None
    resolved_replicate_chunk_size: int
    n_replicates: int
    bytes_per_replicate: int
    fixed_overhead_bytes: int
    safety_factor: float
    requested_n_jobs: int
    resolved_n_jobs: int
    backend: str
    parallel_axis: str
    estimated_peak_bytes: int
    execution_plan_fingerprint: str

    def __post_init__(self) -> None:
        operation = str(self.operation_name).strip()
        if not operation:
            raise ValueError("operation_name must be non-empty.")
        if self.source not in {"implicit", "explicit"}:
            raise ValueError("source must be implicit or explicit.")
        chunk = _positive_int(
            self.resolved_replicate_chunk_size,
            name="resolved_replicate_chunk_size",
        )
        replicates = _positive_int(self.n_replicates, name="n_replicates")
        requested_jobs = _positive_int(self.requested_n_jobs, name="requested_n_jobs")
        resolved_jobs = _positive_int(self.resolved_n_jobs, name="resolved_n_jobs")
        if chunk > replicates:
            raise ValueError(
                "resolved_replicate_chunk_size cannot exceed n_replicates."
            )
        if resolved_jobs > requested_jobs:
            raise ValueError("resolved_n_jobs cannot exceed requested_n_jobs.")
        if self.backend not in {"sequential", "thread"}:
            raise ValueError("backend must be sequential or thread.")
        if self.parallel_axis not in {"none", "replicates"}:
            raise ValueError("parallel_axis must be none or replicates.")
        pair_bytes = _nonnegative_int(
            self.bytes_per_replicate,
            name="bytes_per_replicate",
        )
        overhead = _nonnegative_int(
            self.fixed_overhead_bytes,
            name="fixed_overhead_bytes",
        )
        estimated = _nonnegative_int(
            self.estimated_peak_bytes,
            name="estimated_peak_bytes",
        )
        factor = float(self.safety_factor)
        if not np.isfinite(factor) or factor < 1.0:
            raise ValueError("safety_factor must be finite and at least one.")
        fingerprint = str(self.execution_plan_fingerprint).strip()
        if not fingerprint:
            raise ValueError("execution_plan_fingerprint must be non-empty.")
        object.__setattr__(self, "operation_name", operation)
        object.__setattr__(self, "resolved_replicate_chunk_size", chunk)
        object.__setattr__(self, "n_replicates", replicates)
        object.__setattr__(self, "bytes_per_replicate", pair_bytes)
        object.__setattr__(self, "fixed_overhead_bytes", overhead)
        object.__setattr__(self, "safety_factor", factor)
        object.__setattr__(self, "requested_n_jobs", requested_jobs)
        object.__setattr__(self, "resolved_n_jobs", resolved_jobs)
        object.__setattr__(self, "estimated_peak_bytes", estimated)
        object.__setattr__(self, "execution_plan_fingerprint", fingerprint)

    @property
    def n_replicate_chunks(self) -> int:
        """Number of deterministic logical replicate chunks."""
        return int(ceil(self.n_replicates / self.resolved_replicate_chunk_size))

    @property
    def fingerprint(self) -> str:
        """Deterministic resolved-execution fingerprint."""
        return stable_fingerprint(
            "ResolvedReplicateExecution",
            self.operation_name,
            self.source,
            self.memory_budget_bytes,
            self.requested_replicate_chunk_size,
            self.resolved_replicate_chunk_size,
            self.n_replicates,
            self.bytes_per_replicate,
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
        """Return a JSON-compatible replicate execution audit record."""
        return {
            "operation_name": self.operation_name,
            "source": self.source,
            "memory_budget_bytes": self.memory_budget_bytes,
            "requested_replicate_chunk_size": self.requested_replicate_chunk_size,
            "resolved_replicate_chunk_size": self.resolved_replicate_chunk_size,
            "n_replicates": self.n_replicates,
            "bytes_per_replicate": self.bytes_per_replicate,
            "fixed_overhead_bytes": self.fixed_overhead_bytes,
            "safety_factor": self.safety_factor,
            "requested_n_jobs": self.requested_n_jobs,
            "resolved_n_jobs": self.resolved_n_jobs,
            "backend": self.backend,
            "parallel_axis": self.parallel_axis,
            "n_replicate_chunks": self.n_replicate_chunks,
            "estimated_peak_bytes": self.estimated_peak_bytes,
            "execution_plan_fingerprint": self.execution_plan_fingerprint,
            "resolved_execution_fingerprint": self.fingerprint,
        }


def resolve_replicate_execution(
    plan: ExecutionPlan | None,
    *,
    operation_name: str,
    n_replicates: int,
    bytes_per_replicate: int,
    fixed_overhead_bytes: int = 0,
    safety_factor: float = 1.25,
) -> ResolvedReplicateExecution:
    """Resolve deterministic replicate batches before ensemble allocation."""
    replicates = _positive_int(n_replicates, name="n_replicates")
    temporary_bytes = _nonnegative_int(
        bytes_per_replicate,
        name="bytes_per_replicate",
    )
    overhead = _nonnegative_int(
        fixed_overhead_bytes,
        name="fixed_overhead_bytes",
    )
    factor = float(safety_factor)
    if not np.isfinite(factor) or factor < 1.0:
        raise ValueError("safety_factor must be finite and at least one.")
    if plan is not None and not isinstance(plan, ExecutionPlan):
        raise TypeError("execution_plan must be an ExecutionPlan or None.")

    effective = ExecutionPlan() if plan is None else plan
    source = "implicit" if plan is None else "explicit"
    requested_chunk = effective.replicate_chunk_size
    requested_workers = effective.n_jobs
    concurrent_workers = requested_workers if effective.backend == "thread" else 1
    automatic_chunk = int(ceil(replicates / concurrent_workers))
    maximum_chunk = replicates

    if effective.memory_budget_bytes is not None:
        available = effective.memory_budget_bytes - overhead
        if available <= 0:
            raise MemoryError(
                f"{operation_name} fixed overhead exceeds memory_budget_bytes."
            )
        worker_bytes = int(ceil(temporary_bytes * factor * concurrent_workers))
        if worker_bytes > 0:
            maximum_chunk = min(replicates, available // worker_bytes)
            if maximum_chunk < 1:
                raise MemoryError(
                    f"{operation_name} cannot fit one replicate within the requested "
                    "memory budget."
                )

    if requested_chunk is not None:
        requested_effective = min(requested_chunk, replicates)
        if requested_effective > maximum_chunk:
            raise MemoryError(
                f"{operation_name} replicate_chunk_size exceeds memory_budget_bytes."
            )
        resolved_chunk = requested_effective
    else:
        resolved_chunk = min(automatic_chunk, maximum_chunk)

    n_chunks = int(ceil(replicates / resolved_chunk))
    resolved_workers = min(concurrent_workers, n_chunks)
    parallel_axis = (
        "replicates"
        if effective.backend == "thread" and resolved_workers > 1
        else "none"
    )
    estimated = int(
        ceil(overhead + resolved_chunk * temporary_bytes * factor * resolved_workers)
    )
    if (
        effective.memory_budget_bytes is not None
        and estimated > effective.memory_budget_bytes
    ):
        raise MemoryError(
            f"{operation_name} estimated peak memory exceeds memory_budget_bytes."
        )

    return ResolvedReplicateExecution(
        operation_name=operation_name,
        source=source,
        memory_budget_bytes=effective.memory_budget_bytes,
        requested_replicate_chunk_size=requested_chunk,
        resolved_replicate_chunk_size=resolved_chunk,
        n_replicates=replicates,
        bytes_per_replicate=temporary_bytes,
        fixed_overhead_bytes=overhead,
        safety_factor=factor,
        requested_n_jobs=requested_workers,
        resolved_n_jobs=resolved_workers,
        backend=effective.backend,
        parallel_axis=parallel_axis,
        estimated_peak_bytes=estimated,
        execution_plan_fingerprint=effective.fingerprint,
    )


def replicate_chunk_ranges(
    n_replicates: int,
    chunk_size: int,
) -> tuple[tuple[int, int], ...]:
    """Return deterministic half-open replicate ranges."""
    replicates = _positive_int(n_replicates, name="n_replicates")
    chunk = _positive_int(chunk_size, name="chunk_size")
    return tuple(
        (start, min(start + chunk, replicates)) for start in range(0, replicates, chunk)
    )


def execute_replicate_chunks(
    resolved: ResolvedReplicateExecution,
    worker: Callable[[int, int], _ResultT],
) -> Iterator[tuple[int, int, _ResultT]]:
    """Yield replicate-chunk results in logical range order."""
    if not isinstance(resolved, ResolvedReplicateExecution):
        raise TypeError("resolved must be a ResolvedReplicateExecution.")
    ranges = replicate_chunk_ranges(
        resolved.n_replicates,
        resolved.resolved_replicate_chunk_size,
    )
    if resolved.parallel_axis == "none" or resolved.resolved_n_jobs == 1:
        for start, stop in ranges:
            yield start, stop, worker(start, stop)
        return

    with ThreadPoolExecutor(max_workers=resolved.resolved_n_jobs) as executor:
        for batch_start in range(0, len(ranges), resolved.resolved_n_jobs):
            batch = ranges[batch_start : batch_start + resolved.resolved_n_jobs]
            futures = [executor.submit(worker, start, stop) for start, stop in batch]
            for (start, stop), future in zip(batch, futures, strict=True):
                yield start, stop, future.result()
