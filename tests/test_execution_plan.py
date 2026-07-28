# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import time

import pytest

from pykdex.execution import ExecutionPlan
from pykdex.execution.chunks import execute_target_chunks, target_chunk_ranges
from pykdex.execution.plan import resolve_target_execution


def test_execution_plan_is_normalized_and_fingerprinted() -> None:
    plan = ExecutionPlan(
        memory_budget_bytes=1024,
        target_chunk_size=8,
        replicate_chunk_size=4,
        n_jobs=2,
        backend=" THREAD ",
    )

    assert plan.backend == "thread"
    assert plan.n_jobs == 2
    assert plan.fingerprint == plan.fingerprint
    assert plan.fingerprint != ExecutionPlan(
        memory_budget_bytes=1024,
        target_chunk_size=8,
        replicate_chunk_size=4,
        n_jobs=1,
        backend="thread",
    ).fingerprint


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"memory_budget_bytes": True}, TypeError),
        ({"memory_budget_bytes": 0}, ValueError),
        ({"target_chunk_size": 0}, ValueError),
        ({"replicate_chunk_size": False}, TypeError),
        ({"n_jobs": 0}, ValueError),
        ({"n_jobs": 2, "backend": "sequential"}, ValueError),
        ({"backend": "process"}, ValueError),
    ],
)
def test_execution_plan_rejects_invalid_requests(
    kwargs: dict[str, object],
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        ExecutionPlan(**kwargs)  # type: ignore[arg-type]


def test_budget_resolution_accounts_for_parallel_workers() -> None:
    resolved = resolve_target_execution(
        ExecutionPlan(
            memory_budget_bytes=1000,
            n_jobs=2,
            backend="thread",
        ),
        operation_name="toy",
        n_targets=20,
        n_sources=10,
        bytes_per_pair=8,
        fixed_overhead_bytes=200,
        safety_factor=1.0,
    )

    assert resolved.resolved_target_chunk_size == 5
    assert resolved.resolved_n_jobs == 2
    assert resolved.parallel_axis == "targets"
    assert resolved.estimated_peak_bytes == 1000
    assert resolved.n_target_chunks == 4
    assert resolved.to_metadata()["resolved_execution_fingerprint"] == (
        resolved.fingerprint
    )


def test_explicit_chunk_must_fit_the_memory_budget() -> None:
    with pytest.raises(MemoryError, match="target_chunk_size"):
        resolve_target_execution(
            ExecutionPlan(
                memory_budget_bytes=1000,
                target_chunk_size=6,
                n_jobs=2,
                backend="thread",
            ),
            operation_name="toy",
            n_targets=20,
            n_sources=10,
            bytes_per_pair=8,
            fixed_overhead_bytes=200,
            safety_factor=1.0,
        )


def test_legacy_chunk_and_plan_chunk_are_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="cannot both be set"):
        resolve_target_execution(
            ExecutionPlan(target_chunk_size=2),
            operation_name="toy",
            n_targets=10,
            n_sources=2,
            bytes_per_pair=8,
            legacy_target_chunk_size=3,
        )


def test_implicit_and_legacy_plans_preserve_unbounded_defaults() -> None:
    implicit = resolve_target_execution(
        None,
        operation_name="toy",
        n_targets=7,
        n_sources=3,
        bytes_per_pair=8,
    )
    legacy = resolve_target_execution(
        None,
        operation_name="toy",
        n_targets=7,
        n_sources=3,
        bytes_per_pair=8,
        legacy_target_chunk_size=2,
    )

    assert implicit.source == "implicit"
    assert implicit.memory_budget_bytes is None
    assert implicit.resolved_target_chunk_size == 7
    assert legacy.source == "legacy"
    assert legacy.resolved_target_chunk_size == 2


def test_nonchunkable_operations_reject_parallel_or_small_chunks() -> None:
    with pytest.raises(ValueError, match="threaded target axis"):
        resolve_target_execution(
            ExecutionPlan(n_jobs=2, backend="thread"),
            operation_name="fixed-solver",
            n_targets=10,
            n_sources=0,
            bytes_per_pair=0,
            fixed_overhead_bytes=100,
            chunkable=False,
        )
    with pytest.raises(ValueError, match="does not support target chunking"):
        resolve_target_execution(
            ExecutionPlan(target_chunk_size=5),
            operation_name="fixed-solver",
            n_targets=10,
            n_sources=0,
            bytes_per_pair=0,
            fixed_overhead_bytes=100,
            chunkable=False,
        )


def test_threaded_chunks_are_yielded_in_logical_order() -> None:
    resolved = resolve_target_execution(
        ExecutionPlan(
            memory_budget_bytes=None,
            target_chunk_size=1,
            n_jobs=3,
            backend="thread",
        ),
        operation_name="ordered",
        n_targets=4,
        n_sources=0,
        bytes_per_pair=0,
    )

    def worker(start: int, stop: int) -> int:
        time.sleep(0.003 * (4 - start))
        assert stop == start + 1
        return start

    observed = [
        (start, stop, value)
        for start, stop, value in execute_target_chunks(resolved, worker)
    ]
    assert observed == [(0, 1, 0), (1, 2, 1), (2, 3, 2), (3, 4, 3)]
    assert target_chunk_ranges(5, 2) == ((0, 2), (2, 4), (4, 5))
