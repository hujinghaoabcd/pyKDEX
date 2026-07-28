# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Repeatable benchmark for sequential and threaded target execution."""

from __future__ import annotations

from time import perf_counter

import numpy as np

from pykdex import GridSupport, SpatialKDE
from pykdex.execution import ExecutionPlan


def _run(events: np.ndarray, support: GridSupport, plan: ExecutionPlan) -> tuple[np.ndarray, float, dict]:
    started = perf_counter()
    model = SpatialKDE(
        bandwidth=65.0,
        kernel="epanechnikov",
        execution_plan=plan,
    )
    result = model.fit_predict(events, support)
    elapsed = perf_counter() - started
    return result.values, elapsed, dict(result.metadata["execution"])


def main() -> None:
    """Compare two execution plans on one deterministic spatial problem."""
    rng = np.random.default_rng(20260728)
    events = rng.uniform(0.0, 1000.0, size=(1000, 2))
    support = GridSupport.from_bounds(
        (0.0, 0.0, 1000.0, 1000.0),
        resolution=10.0,
        spatial_unit="m",
    )

    sequential_values, sequential_seconds, sequential_meta = _run(
        events,
        support,
        ExecutionPlan(
            memory_budget_bytes=None,
            target_chunk_size=500,
            n_jobs=1,
            backend="sequential",
        ),
    )
    threaded_values, threaded_seconds, threaded_meta = _run(
        events,
        support,
        ExecutionPlan(
            memory_budget_bytes=None,
            target_chunk_size=500,
            n_jobs=4,
            backend="thread",
        ),
    )

    np.testing.assert_allclose(threaded_values, sequential_values, rtol=1e-13, atol=1e-15)
    print(
        {
            "n_events": events.shape[0],
            "n_targets": support.n_points,
            "sequential_seconds": round(sequential_seconds, 3),
            "threaded_seconds": round(threaded_seconds, 3),
            "descriptive_speedup": round(sequential_seconds / threaded_seconds, 3),
            "sequential_chunks": sequential_meta["n_target_chunks"],
            "threaded_chunks": threaded_meta["n_target_chunks"],
            "threaded_workers": threaded_meta["resolved_n_jobs"],
            "threaded_peak_bytes": threaded_meta["estimated_peak_bytes"],
        }
    )


if __name__ == "__main__":
    main()
