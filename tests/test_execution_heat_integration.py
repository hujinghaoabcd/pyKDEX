# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import numpy as np
import pytest

from pykdex import HeatNetworkKDE, NetworkWorkspace, SpatialEvents, load_t_junction
from pykdex.execution import ExecutionPlan


def _workspace() -> NetworkWorkspace:
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        [[-0.7, 0.0]],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    return NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=0.1,
        max_snap_distance=0.05,
    )


def test_heat_sequential_execution_plan_preserves_values_and_records_budget() -> None:
    workspace = _workspace()
    expected = HeatNetworkKDE(diffusion_time=0.08).fit(workspace)
    actual = HeatNetworkKDE(
        diffusion_time=0.08,
        execution_plan=ExecutionPlan(memory_budget_bytes=None),
    ).fit(workspace)

    np.testing.assert_allclose(actual.evaluate(), expected.evaluate())
    assert actual.last_execution_ is not None
    execution = actual.predict_result().metadata["execution"]
    assert execution["operation_name"] == "HeatNetworkKDE.evolve"
    assert execution["source"] == "explicit"
    assert execution["parallel_axis"] == "none"
    assert execution["resolved_n_jobs"] == 1
    assert execution["resolved_target_chunk_size"] == workspace.lixels.n_lixels
    assert execution["estimated_peak_bytes"] > 0


def test_heat_default_execution_is_implicit_and_unchunked() -> None:
    workspace = _workspace()
    model = HeatNetworkKDE(diffusion_time=0.08).fit(workspace)

    assert model.last_execution_ is not None
    assert model.last_execution_.source == "implicit"
    assert model.last_execution_.memory_budget_bytes is None
    assert model.last_execution_.parallel_axis == "none"


def test_heat_rejects_threaded_execution() -> None:
    workspace = _workspace()
    model = HeatNetworkKDE(
        diffusion_time=0.08,
        execution_plan=ExecutionPlan(n_jobs=2, backend="thread"),
    )

    with pytest.raises(ValueError, match="threaded target axis"):
        model.fit(workspace)
    assert not model.is_fitted_
    assert model.last_execution_ is None


def test_heat_rejects_target_chunking() -> None:
    workspace = _workspace()
    model = HeatNetworkKDE(
        diffusion_time=0.08,
        execution_plan=ExecutionPlan(target_chunk_size=1),
    )

    with pytest.raises(ValueError, match="does not support target chunking"):
        model.fit(workspace)
    assert not model.is_fitted_


def test_heat_budget_counts_compute_plan_and_solver_arrays() -> None:
    workspace = _workspace()
    model = HeatNetworkKDE(
        diffusion_time=0.08,
        execution_plan=ExecutionPlan(memory_budget_bytes=100),
    )

    with pytest.raises(MemoryError, match="estimated peak memory exceeds"):
        model.fit(workspace)
    assert not model.is_fitted_
    assert model.values_ is None


def test_heat_rejects_non_execution_plan_object() -> None:
    with pytest.raises(TypeError, match="ExecutionPlan"):
        HeatNetworkKDE(execution_plan="thread")  # type: ignore[arg-type]
