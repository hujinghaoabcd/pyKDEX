# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Ordered sequential or threaded execution of independent index chunks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterator, TypeVar

from pykdex.execution.plan import ResolvedExecutionPlan

_ResultT = TypeVar("_ResultT")


def target_chunk_ranges(n_targets: int, chunk_size: int) -> tuple[tuple[int, int], ...]:
    """Return deterministic half-open target ranges."""
    if n_targets <= 0 or chunk_size <= 0:
        raise ValueError("n_targets and chunk_size must be positive.")
    return tuple(
        (start, min(start + chunk_size, n_targets))
        for start in range(0, n_targets, chunk_size)
    )


def execute_target_chunks(
    resolved: ResolvedExecutionPlan,
    worker: Callable[[int, int], _ResultT],
) -> Iterator[tuple[int, int, _ResultT]]:
    """Yield chunk results in logical range order.

    Threaded work is submitted in bounded batches no larger than the resolved
    worker count. Results are yielded by logical chunk index, never completion
    order, and callers write them into preassigned output slices.
    """
    if not isinstance(resolved, ResolvedExecutionPlan):
        raise TypeError("resolved must be a ResolvedExecutionPlan.")
    ranges = target_chunk_ranges(
        resolved.n_targets,
        resolved.resolved_target_chunk_size,
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
