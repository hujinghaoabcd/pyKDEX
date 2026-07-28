# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import numpy as np
import pytest

from pykdex import NetworkKDE, NetworkWorkspace, SpatialEvents, load_t_junction
from pykdex.execution import ExecutionPlan


def _workspace(*, lixel_length: float = 0.1) -> NetworkWorkspace:
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        [[-0.75, 0.0], [0.5, 0.0]],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    return NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=lixel_length,
        max_snap_distance=0.05,
    )


@pytest.mark.parametrize("junction_policy", ["simple", "discontinuous", "continuous"])
def test_threaded_network_plan_matches_sequential_values(
    junction_policy: str,
) -> None:
    workspace = _workspace()
    expected_model = NetworkKDE(
        bandwidth=0.8,
        junction_policy=junction_policy,
        store_propagation=True,
    ).fit(workspace)
    actual_model = NetworkKDE(
        bandwidth=0.8,
        junction_policy=junction_policy,
        store_propagation=True,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=None,
            target_chunk_size=5,
            n_jobs=2,
            backend="thread",
        ),
    ).fit(workspace)

    np.testing.assert_allclose(actual_model.evaluate(), expected_model.evaluate())
    assert actual_model.last_execution_ is not None
    execution = actual_model.predict_result().metadata["execution"]
    assert execution["resolved_target_chunk_size"] == 5
    assert execution["resolved_n_jobs"] == 2
    assert execution["parallel_axis"] == "targets"
    assert execution["operation_name"] == f"NetworkKDE.{junction_policy}"

    if junction_policy == "simple":
        assert actual_model.distance_asset_ is not None
        assert expected_model.distance_asset_ is not None
        assert (
            actual_model.distance_asset_.fingerprint
            == expected_model.distance_asset_.fingerprint
        )
        assert actual_model.propagation_traces_ is None
    else:
        assert actual_model.propagation_traces_ is not None
        assert expected_model.propagation_traces_ is not None
        assert tuple(
            trace.fingerprint for trace in actual_model.propagation_traces_
        ) == tuple(trace.fingerprint for trace in expected_model.propagation_traces_)


def test_network_default_execution_preserves_single_target_task() -> None:
    workspace = _workspace()
    model = NetworkKDE(
        bandwidth=0.8,
        junction_policy="simple",
    ).fit(workspace)

    assert model.last_execution_ is not None
    assert model.last_execution_.source == "implicit"
    assert model.last_execution_.resolved_target_chunk_size == workspace.lixels.n_lixels
    assert model.last_execution_.resolved_n_jobs == 1
    assert model.last_execution_.parallel_axis == "none"


def test_network_execution_budget_rejects_before_chunk_evaluation() -> None:
    workspace = _workspace()
    model = NetworkKDE(
        bandwidth=0.8,
        junction_policy="simple",
        execution_plan=ExecutionPlan(memory_budget_bytes=100),
    )

    with pytest.raises(MemoryError, match="fixed overhead"):
        model.fit(workspace)
    assert not model.is_fitted_
    assert model.values_ is None
    assert model.last_execution_ is None


def test_network_rejects_non_execution_plan_object() -> None:
    with pytest.raises(TypeError, match="ExecutionPlan"):
        NetworkKDE(execution_plan="thread")  # type: ignore[arg-type]
