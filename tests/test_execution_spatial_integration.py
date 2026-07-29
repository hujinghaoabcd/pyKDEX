# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import numpy as np
import pytest

from pykdex import (
    GridSupport,
    SpatialKDE,
    SpatiotemporalEvents,
    SpatiotemporalKDE,
    SpatiotemporalPointSupport,
    build_spatiotemporal_distance_asset,
)
from pykdex.execution import ExecutionPlan


def test_spatial_thread_plan_matches_legacy_chunking_and_records_metadata() -> None:
    events = np.array([[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]])
    support = GridSupport.from_bounds((0.0, 0.0, 1.0, 1.0), resolution=0.25)
    expected = SpatialKDE(bandwidth=0.4, chunk_size=2).fit_predict(events, support)

    model = SpatialKDE(
        bandwidth=0.4,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=None,
            target_chunk_size=2,
            n_jobs=2,
            backend="thread",
        ),
    )
    actual = model.fit_predict(events, support)

    np.testing.assert_allclose(actual.values, expected.values)
    assert model.last_execution_ is not None
    execution = actual.metadata["execution"]
    assert execution["source"] == "explicit"
    assert execution["resolved_target_chunk_size"] == 2
    assert execution["resolved_n_jobs"] == 2
    assert execution["parallel_axis"] == "targets"


def test_spatial_legacy_and_plan_chunks_are_mutually_exclusive() -> None:
    model = SpatialKDE(
        bandwidth=0.5,
        chunk_size=1,
        execution_plan=ExecutionPlan(target_chunk_size=1),
    ).fit([[0.0, 0.0], [1.0, 1.0]])

    with pytest.raises(ValueError, match="cannot both be set"):
        model.evaluate([[0.5, 0.5]])


def test_spatial_budget_rejects_before_pairwise_evaluation() -> None:
    model = SpatialKDE(
        bandwidth=0.5,
        execution_plan=ExecutionPlan(memory_budget_bytes=100),
    ).fit([[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]])

    with pytest.raises(MemoryError, match="cannot fit one target row"):
        model.evaluate([[0.25, 0.25], [0.75, 0.75]])


def _spatiotemporal_inputs() -> tuple[
    SpatiotemporalEvents,
    SpatiotemporalPointSupport,
]:
    events = SpatiotemporalEvents.from_arrays(
        [[0.0], [1.0], [2.0]],
        [0.0, 1.0, 2.0],
        spatial_unit="km",
        temporal_unit="hours",
    )
    support = SpatiotemporalPointSupport.from_arrays(
        [[0.25], [0.75], [1.25], [1.75]],
        [0.25, 0.75, 1.25, 1.75],
        spatial_unit="km",
        temporal_unit="hours",
    )
    return events, support


def test_spatiotemporal_thread_plan_matches_legacy_without_asset() -> None:
    events, support = _spatiotemporal_inputs()
    expected = SpatiotemporalKDE(0.7, 0.9, chunk_size=2).fit_predict(
        events,
        support,
    )
    model = SpatiotemporalKDE(
        0.7,
        0.9,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=None,
            target_chunk_size=2,
            n_jobs=2,
            backend="thread",
        ),
    )
    actual = model.fit_predict(events, support)

    np.testing.assert_allclose(actual.values, expected.values)
    execution = actual.metadata["execution"]
    assert execution["resolved_target_chunk_size"] == 2
    assert execution["resolved_n_jobs"] == 2
    assert execution["parallel_axis"] == "targets"


def test_spatiotemporal_thread_plan_reuses_full_distance_asset() -> None:
    events, support = _spatiotemporal_inputs()
    asset = build_spatiotemporal_distance_asset(events, support)
    expected = SpatiotemporalKDE(0.7, 0.9).fit_predict(
        events,
        support,
        distance_asset=asset,
    )
    actual = SpatiotemporalKDE(
        0.7,
        0.9,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=None,
            target_chunk_size=1,
            n_jobs=2,
            backend="thread",
        ),
    ).fit_predict(events, support, distance_asset=asset)

    np.testing.assert_allclose(actual.values, expected.values)
    assert actual.metadata["execution"]["n_target_chunks"] == support.n_points


def test_spatiotemporal_asset_memory_counts_against_budget() -> None:
    events, support = _spatiotemporal_inputs()
    asset = build_spatiotemporal_distance_asset(events, support)
    model = SpatiotemporalKDE(
        0.7,
        0.9,
        execution_plan=ExecutionPlan(memory_budget_bytes=100),
    ).fit(events)

    with pytest.raises(MemoryError, match="fixed overhead"):
        model.evaluate(support, distance_asset=asset)


def test_estimators_reject_non_execution_plan_objects() -> None:
    with pytest.raises(TypeError, match="ExecutionPlan"):
        SpatialKDE(execution_plan="thread")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="ExecutionPlan"):
        SpatiotemporalKDE(execution_plan="thread")  # type: ignore[arg-type]
