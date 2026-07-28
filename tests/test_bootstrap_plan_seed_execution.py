# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

from time import sleep

import numpy as np
import pytest

from pykdex.execution import ExecutionPlan
from pykdex.execution.replicates import (
    execute_replicate_chunks,
    replicate_chunk_ranges,
    resolve_replicate_execution,
)
from pykdex.uncertainty import BootstrapPlan
from pykdex.uncertainty.seeds import SeedLedger, build_seed_ledger


def test_bootstrap_plan_normalizes_and_fingerprints() -> None:
    execution = ExecutionPlan(
        memory_budget_bytes=None,
        replicate_chunk_size=3,
        n_jobs=2,
        backend="thread",
    )
    plan = BootstrapPlan(
        n_resamples=np.int64(9),
        confidence_level=np.float64(0.9),
        random_state=np.int64(17),
        method=" ORDINARY ",
        execution_plan=execution,
    )

    assert plan.n_resamples == 9
    assert plan.confidence_level == pytest.approx(0.9)
    assert plan.random_state == 17
    assert plan.method == "ordinary"
    assert plan.store_replicates is True
    assert (
        plan.fingerprint
        == BootstrapPlan(
            n_resamples=9,
            confidence_level=0.9,
            random_state=17,
            execution_plan=execution,
        ).fingerprint
    )


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"n_resamples": True}, TypeError),
        ({"n_resamples": 1}, ValueError),
        ({"confidence_level": True}, TypeError),
        ({"confidence_level": 1.0}, ValueError),
        ({"random_state": True}, TypeError),
        ({"random_state": -1}, ValueError),
        ({"method": "bayesian"}, ValueError),
        ({"store_replicates": 1}, TypeError),
        ({"store_replicates": False}, ValueError),
        ({"execution_plan": "thread"}, TypeError),
    ],
)
def test_bootstrap_plan_rejects_unsupported_requests(
    kwargs: dict[str, object],
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        BootstrapPlan(**kwargs)  # type: ignore[arg-type]


def test_seed_ledger_assigns_stable_streams_by_logical_index() -> None:
    first = build_seed_ledger(20260728, 8)
    second = build_seed_ledger(20260728, 8)

    assert isinstance(first, SeedLedger)
    assert first.fingerprint == second.fingerprint
    assert first.to_metadata() == second.to_metadata()
    for index in range(first.n_logical_tasks):
        np.testing.assert_array_equal(
            first.generator(index).integers(0, 10_000, size=20),
            second.generator(index).integers(0, 10_000, size=20),
        )
    assert not np.array_equal(
        first.generator(0).integers(0, 10_000, size=20),
        first.generator(1).integers(0, 10_000, size=20),
    )


def test_generated_entropy_can_replay_a_none_seed_ledger() -> None:
    generated = build_seed_ledger(None, 4)
    replayed = build_seed_ledger(generated.root_entropy, 4)

    assert generated.fingerprint == replayed.fingerprint
    np.testing.assert_array_equal(
        generated.generator(3).random(10),
        replayed.generator(3).random(10),
    )


def test_seed_ledger_rejects_invalid_indices_and_entropy() -> None:
    ledger = build_seed_ledger(1, 2)

    with pytest.raises(TypeError):
        ledger.generator(True)
    with pytest.raises(IndexError):
        ledger.generator(2)
    with pytest.raises(ValueError):
        build_seed_ledger((-1,), 2)
    with pytest.raises(TypeError):
        build_seed_ledger(1, True)


def test_replicate_resolution_accounts_for_workers_and_budget() -> None:
    plan = ExecutionPlan(
        memory_budget_bytes=700,
        n_jobs=2,
        backend="thread",
    )
    resolved = resolve_replicate_execution(
        plan,
        operation_name="bootstrap_kde",
        n_replicates=10,
        bytes_per_replicate=100,
        fixed_overhead_bytes=100,
        safety_factor=1.0,
    )

    assert resolved.resolved_replicate_chunk_size == 3
    assert resolved.resolved_n_jobs == 2
    assert resolved.parallel_axis == "replicates"
    assert resolved.n_replicate_chunks == 4
    assert resolved.estimated_peak_bytes == 700
    assert resolved.to_metadata()["n_replicate_chunks"] == 4


def test_implicit_replicate_execution_uses_default_budget() -> None:
    resolved = resolve_replicate_execution(
        None,
        operation_name="bootstrap_kde",
        n_replicates=5,
        bytes_per_replicate=8,
    )

    assert resolved.source == "implicit"
    assert resolved.memory_budget_bytes == 256 * 1024 * 1024
    assert resolved.backend == "sequential"
    assert resolved.resolved_replicate_chunk_size == 5


def test_explicit_replicate_chunk_must_fit_budget() -> None:
    with pytest.raises(MemoryError, match="replicate_chunk_size"):
        resolve_replicate_execution(
            ExecutionPlan(
                memory_budget_bytes=500,
                replicate_chunk_size=3,
                n_jobs=2,
                backend="thread",
            ),
            operation_name="bootstrap_kde",
            n_replicates=10,
            bytes_per_replicate=100,
            fixed_overhead_bytes=100,
            safety_factor=1.0,
        )


def test_replicate_fixed_overhead_and_single_task_fail_early() -> None:
    with pytest.raises(MemoryError, match="fixed overhead"):
        resolve_replicate_execution(
            ExecutionPlan(memory_budget_bytes=100),
            operation_name="bootstrap_kde",
            n_replicates=3,
            bytes_per_replicate=1,
            fixed_overhead_bytes=100,
        )
    with pytest.raises(MemoryError, match="one replicate"):
        resolve_replicate_execution(
            ExecutionPlan(memory_budget_bytes=150),
            operation_name="bootstrap_kde",
            n_replicates=3,
            bytes_per_replicate=100,
            fixed_overhead_bytes=100,
            safety_factor=1.0,
        )


def test_replicate_chunks_are_yielded_in_logical_order() -> None:
    resolved = resolve_replicate_execution(
        ExecutionPlan(
            memory_budget_bytes=None,
            replicate_chunk_size=2,
            n_jobs=3,
            backend="thread",
        ),
        operation_name="bootstrap_kde",
        n_replicates=6,
        bytes_per_replicate=1,
    )

    def worker(start: int, stop: int) -> tuple[int, int]:
        sleep(0.002 * (6 - start))
        return start, stop

    observed = list(execute_replicate_chunks(resolved, worker))

    assert replicate_chunk_ranges(6, 2) == ((0, 2), (2, 4), (4, 6))
    assert [(start, stop) for start, stop, _ in observed] == [
        (0, 2),
        (2, 4),
        (4, 6),
    ]
    assert [value for _, _, value in observed] == [(0, 2), (2, 4), (4, 6)]


def test_seed_identity_is_independent_of_replicate_schedule() -> None:
    ledger = build_seed_ledger(99, 12)

    def run(execution: ExecutionPlan) -> np.ndarray:
        resolved = resolve_replicate_execution(
            execution,
            operation_name="bootstrap_kde",
            n_replicates=12,
            bytes_per_replicate=8,
        )
        values = np.empty(12, dtype=np.int64)

        def worker(start: int, stop: int) -> np.ndarray:
            return np.asarray(
                [
                    ledger.generator(index).integers(0, 2**31)
                    for index in range(start, stop)
                ],
                dtype=np.int64,
            )

        for start, stop, chunk in execute_replicate_chunks(resolved, worker):
            values[start:stop] = chunk
        return values

    sequential = run(
        ExecutionPlan(
            memory_budget_bytes=None,
            replicate_chunk_size=5,
        )
    )
    threaded = run(
        ExecutionPlan(
            memory_budget_bytes=None,
            replicate_chunk_size=2,
            n_jobs=4,
            backend="thread",
        )
    )

    np.testing.assert_array_equal(threaded, sequential)
