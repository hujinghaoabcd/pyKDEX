# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import numpy as np
import pytest

from pykdex import (
    GridSupport,
    HeatNetworkKDE,
    NetworkKDE,
    NetworkTimeWorkspace,
    NetworkWorkspace,
    SpatialEvents,
    SpatialKDE,
    SpatiotemporalEvents,
    SpatiotemporalGridSupport,
    SpatiotemporalKDE,
    TemporalCoordinates,
    TemporalNetworkKDE,
    load_t_junction,
)
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, BootstrapResult, bootstrap_kde


_FAMILIES = ("spatial", "network", "heat_network", "spatiotemporal", "network_time")


def _plan(*, variant: bool) -> BootstrapPlan:
    execution = (
        ExecutionPlan(
            replicate_chunk_size=1,
            n_jobs=2,
            backend="thread",
        )
        if variant
        else ExecutionPlan(n_jobs=1, backend="sequential")
    )
    return BootstrapPlan(
        n_resamples=2,
        confidence_level=0.8,
        random_state=19,
        execution_plan=execution,
    )


def _spatial_result(*, variant: bool, changed: bool = False) -> BootstrapResult:
    support = GridSupport.from_bounds(
        (0.0, 0.0, 2.0, 1.0),
        resolution=0.5,
        spatial_unit="km",
    )
    coordinates = (
        [[0.25, 0.25], [1.25, 0.75], [1.75, 0.25]]
        if variant
        else [[0.25, 0.75], [0.75, 0.25], [1.25, 0.75]]
    )
    events = SpatialEvents.from_array(coordinates, spatial_unit="km")
    return bootstrap_kde(
        SpatialKDE(
            bandwidth=0.7 if changed else 0.6,
            kernel="epanechnikov",
            metric="euclidean",
            target="density",
        ),
        events,
        support,
        plan=_plan(variant=variant),
    )


def _network_workspace(*, variant: bool) -> NetworkWorkspace:
    network = load_t_junction().network
    coordinates = (
        [[-0.25, 0.0], [0.0, 0.75]]
        if variant
        else [[-0.75, 0.0], [0.50, 0.0]]
    )
    events = SpatialEvents.from_array(
        coordinates,
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    return NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=0.5,
        max_snap_distance=0.05,
    )


def _network_result(*, variant: bool, changed: bool = False) -> BootstrapResult:
    workspace = _network_workspace(variant=variant)
    return bootstrap_kde(
        NetworkKDE(
            bandwidth=0.8,
            kernel="triangular" if changed else "epanechnikov",
            junction_policy="simple",
            target="density",
        ),
        workspace,
        plan=_plan(variant=variant),
    )


def _heat_result(*, variant: bool, changed: bool = False) -> BootstrapResult:
    workspace = _network_workspace(variant=variant)
    return bootstrap_kde(
        HeatNetworkKDE(
            diffusion_time=0.09 if changed else 0.08,
            mesh_size=0.5,
            target="density",
        ),
        workspace,
        plan=_plan(variant=variant),
    )


def _spatiotemporal_result(*, variant: bool, changed: bool = False) -> BootstrapResult:
    spatial = GridSupport.from_bounds(
        (0.0, 0.0, 2.0, 1.0),
        resolution=1.0,
        spatial_unit="km",
    )
    support = SpatiotemporalGridSupport.from_spatial_grid(
        spatial,
        temporal_resolution=1.0,
        temporal_unit="hours",
        temporal_bounds=(0.0, 2.0),
        temporal_origin="study-hour-zero",
        timezone="UTC",
    )
    coordinates = (
        [[0.5, 0.5], [1.5, 0.5], [0.5, 0.5]]
        if variant
        else [[0.5, 0.5], [0.5, 0.5], [1.5, 0.5]]
    )
    times = [0.25, 1.25, 1.75] if variant else [0.25, 0.75, 1.25]
    spatial_events = SpatialEvents.from_array(coordinates, spatial_unit="km")
    temporal = TemporalCoordinates.from_array(
        times,
        temporal_unit="hours",
        temporal_origin="study-hour-zero",
        timezone="UTC",
    )
    events = SpatiotemporalEvents(spatial=spatial_events, temporal=temporal)
    return bootstrap_kde(
        SpatiotemporalKDE(
            spatial_bandwidth=0.8,
            temporal_bandwidth=0.7 if changed else 0.6,
            spatial_kernel="epanechnikov",
            temporal_kernel="gaussian",
            spatial_metric="euclidean",
            target="density",
        ),
        events,
        support,
        plan=_plan(variant=variant),
    )


def _network_time_result(*, variant: bool, changed: bool = False) -> BootstrapResult:
    network = load_t_junction().network
    coordinates = (
        [[-0.25, 0.0], [0.0, 0.75]]
        if variant
        else [[-0.75, 0.0], [0.50, 0.0]]
    )
    times = [0.75, 1.25] if variant else [0.25, 1.75]
    events = SpatialEvents.from_array(
        coordinates,
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    workspace = NetworkTimeWorkspace.prepare(
        network,
        events,
        times,
        temporal_unit="hours",
        lixel_length=0.5,
        temporal_resolution=1.0,
        temporal_bounds=(0.0, 2.0),
        temporal_origin="study-hour-zero",
        timezone="UTC",
        max_snap_distance=0.05,
    )
    return bootstrap_kde(
        TemporalNetworkKDE(
            spatial_bandwidth=0.8,
            temporal_bandwidth=0.7 if changed else 0.6,
            spatial_kernel="epanechnikov",
            temporal_kernel="gaussian",
            junction_policy="simple",
            target="density",
        ),
        workspace,
        plan=_plan(variant=variant),
    )


def _result(family: str, *, variant: bool, changed: bool = False) -> BootstrapResult:
    builders = {
        "spatial": _spatial_result,
        "network": _network_result,
        "heat_network": _heat_result,
        "spatiotemporal": _spatiotemporal_result,
        "network_time": _network_time_result,
    }
    return builders[family](variant=variant, changed=changed)


def _contract(result: BootstrapResult) -> tuple[Mapping[str, Any], str]:
    contract = result.metadata["relative_risk_contract"]
    fingerprint = result.metadata["relative_risk_contract_fingerprint"]
    assert isinstance(contract, Mapping)
    assert isinstance(fingerprint, str)
    return contract, fingerprint


@pytest.mark.parametrize("family", _FAMILIES)
def test_all_density_families_expose_one_read_only_serializable_contract(
    family: str,
) -> None:
    result = _result(family, variant=False)
    contract, fingerprint = _contract(result)

    assert result.ensemble.metadata["relative_risk_contract"] is contract
    assert (
        result.ensemble.metadata["relative_risk_contract_fingerprint"] == fingerprint
    )
    assert contract["schema_version"] == 1
    assert contract["result_family"] == family
    assert contract["target"] == "density"
    assert contract["support_fingerprint"] == result.ensemble.descriptor.fingerprint
    assert json.loads(json.dumps(dict(contract), sort_keys=True))["result_family"] == family
    with pytest.raises(TypeError):
        contract["new_key"] = "not allowed"  # type: ignore[index]


@pytest.mark.parametrize("family", _FAMILIES)
def test_event_data_and_execution_changes_do_not_change_shared_contract(
    family: str,
) -> None:
    first = _result(family, variant=False)
    second = _result(family, variant=True)
    first_contract, first_fingerprint = _contract(first)
    second_contract, second_fingerprint = _contract(second)

    assert dict(first_contract) == dict(second_contract)
    assert first_fingerprint == second_fingerprint
    assert first.metadata["source_event_fingerprint"] != second.metadata["source_event_fingerprint"]
    assert first.ensemble.execution_metadata != second.ensemble.execution_metadata


@pytest.mark.parametrize("family", _FAMILIES)
def test_meaningful_estimator_changes_change_shared_contract(family: str) -> None:
    baseline = _result(family, variant=False)
    changed = _result(family, variant=False, changed=True)
    baseline_contract, baseline_fingerprint = _contract(baseline)
    changed_contract, changed_fingerprint = _contract(changed)

    assert dict(baseline_contract) != dict(changed_contract)
    assert baseline_fingerprint != changed_fingerprint


def test_shared_contract_metadata_does_not_change_numerical_outputs() -> None:
    result = _spatial_result(variant=False)
    estimator = SpatialKDE(
        bandwidth=0.6,
        kernel="epanechnikov",
        metric="euclidean",
        target="density",
    )
    support = result.ensemble.support
    events = SpatialEvents.from_array(
        [[0.25, 0.75], [0.75, 0.25], [1.25, 0.75]],
        spatial_unit="km",
    )
    expected = estimator.fit_predict(events, support)

    np.testing.assert_array_equal(result.ensemble.observed_values, expected.values)
    assert np.all(np.isfinite(result.ensemble.replicate_values))
