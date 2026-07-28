# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import numpy as np
import pytest

from pykdex import NetworkTimeWorkspace, SpatialEvents, TemporalNetworkKDE, load_t_junction
from pykdex.execution import ExecutionPlan


def _workspace() -> NetworkTimeWorkspace:
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        [[-0.75, 0.0], [0.5, 0.0]],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    return NetworkTimeWorkspace.prepare(
        network,
        events,
        [0.25, 2.25],
        temporal_unit="hours",
        lixel_length=0.05,
        temporal_resolution=0.5,
        temporal_bounds=(0.0, 3.0),
        max_snap_distance=0.05,
    )


@pytest.mark.parametrize("junction_policy", ["simple", "continuous"])
def test_threaded_network_time_plan_matches_legacy_time_chunks(
    junction_policy: str,
) -> None:
    workspace = _workspace()
    common = {
        "spatial_bandwidth": 0.8,
        "temporal_bandwidth": 0.6,
        "junction_policy": junction_policy,
        "store_propagation": True,
    }
    expected = TemporalNetworkKDE(time_chunk_size=2, **common).fit(workspace)
    actual = TemporalNetworkKDE(
        execution_plan=ExecutionPlan(
            memory_budget_bytes=None,
            target_chunk_size=2,
            n_jobs=2,
            backend="thread",
        ),
        **common,
    ).fit(workspace)

    np.testing.assert_allclose(actual.evaluate(), expected.evaluate())
    assert actual.last_execution_ is not None
    execution = actual.predict_result().metadata["execution"]
    assert execution["operation_name"] == f"TemporalNetworkKDE.{junction_policy}"
    assert execution["resolved_target_chunk_size"] == 2
    assert execution["resolved_n_jobs"] == 2
    assert execution["parallel_axis"] == "targets"
    assert execution["n_targets"] == workspace.arixels.n_times

    if junction_policy == "simple":
        assert actual.distance_asset_ is not None
        assert expected.distance_asset_ is not None
        assert actual.propagation_traces_ is None
    else:
        assert actual.distance_asset_ is None
        assert actual.propagation_traces_ is not None
        assert expected.propagation_traces_ is not None
        assert tuple(
            trace.fingerprint for trace in actual.propagation_traces_
        ) == tuple(trace.fingerprint for trace in expected.propagation_traces_)


def test_network_time_default_plan_preserves_single_time_task() -> None:
    workspace = _workspace()
    model = TemporalNetworkKDE(
        spatial_bandwidth=0.8,
        temporal_bandwidth=0.6,
        junction_policy="simple",
    ).fit(workspace)

    assert model.last_execution_ is not None
    assert model.last_execution_.source == "implicit"
    assert model.last_execution_.resolved_target_chunk_size == workspace.arixels.n_times
    assert model.last_execution_.parallel_axis == "none"


def test_network_time_legacy_and_plan_chunks_are_mutually_exclusive() -> None:
    workspace = _workspace()
    model = TemporalNetworkKDE(
        spatial_bandwidth=0.8,
        temporal_bandwidth=0.6,
        junction_policy="simple",
        time_chunk_size=2,
        execution_plan=ExecutionPlan(target_chunk_size=2),
    )

    with pytest.raises(ValueError, match="cannot both be set"):
        model.fit(workspace)
    assert not model.is_fitted_
    assert model.last_execution_ is None


def test_network_time_budget_counts_fixed_spatial_assets() -> None:
    workspace = _workspace()
    model = TemporalNetworkKDE(
        spatial_bandwidth=0.8,
        temporal_bandwidth=0.6,
        junction_policy="simple",
        execution_plan=ExecutionPlan(memory_budget_bytes=100),
    )

    with pytest.raises(MemoryError, match="fixed overhead"):
        model.fit(workspace)
    assert not model.is_fitted_
    assert model.values_ is None


def test_network_time_rejects_non_execution_plan_object() -> None:
    with pytest.raises(TypeError, match="ExecutionPlan"):
        TemporalNetworkKDE(execution_plan="thread")  # type: ignore[arg-type]
