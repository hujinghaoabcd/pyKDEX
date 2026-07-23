# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Analytical fixed-bandwidth temporal network KDE tests."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import (
    CyclicTimeDomain,
    NetworkKDE,
    NetworkTimeWorkspace,
    SpatialEvents,
    TemporalNetworkKDE,
    load_osmnx_fixture,
    load_t_junction,
)


def _workspace(
    coordinates=((-0.7475, 0.0),),
    times=(0.0,),
    *,
    weights=None,
    lixel_length: float = 0.005,
    temporal_resolution: float = 1.0,
    temporal_bounds=(-0.5, 0.5),
    time_domain=None,
) -> NetworkTimeWorkspace:
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        coordinates,
        weights=weights,
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    return NetworkTimeWorkspace.prepare(
        network,
        events,
        times,
        temporal_unit="hours",
        lixel_length=lixel_length,
        temporal_resolution=temporal_resolution,
        temporal_bounds=temporal_bounds,
        time_domain=time_domain,
        max_snap_distance=0.05,
    )


def _lixel_index(workspace: NetworkTimeWorkspace, edge: int, offset: float) -> int:
    selected = np.flatnonzero(
        (workspace.lixels.edge_indices == edge)
        & np.isclose(workspace.lixels.center_offsets, offset)
    )
    assert selected.size == 1
    return int(selected[0])


def test_simple_product_kernel_matches_exact_zero_distance_value() -> None:
    workspace = _workspace()
    field = TemporalNetworkKDE(
        spatial_bandwidth=1.0,
        temporal_bandwidth=1.0,
        spatial_kernel="epanechnikov",
        temporal_kernel="gaussian",
        junction_policy="simple",
    ).fit_predict(workspace)

    source = _lixel_index(workspace, 0, 0.2525)
    expected = 0.75 / np.sqrt(2.0 * np.pi)
    assert field.to_grid()[0, source] == pytest.approx(expected)
    assert field.support_measure.shape == field.values.shape
    assert not field.values.flags.writeable


@pytest.mark.parametrize("policy", ["discontinuous", "continuous"])
def test_temporal_slice_is_spatial_network_field_times_temporal_factor(
    policy: str,
) -> None:
    workspace = _workspace()
    spatial = NetworkKDE(
        bandwidth=1.0,
        kernel="epanechnikov",
        junction_policy=policy,
    ).fit_predict(workspace.network_workspace)
    temporal = TemporalNetworkKDE(
        spatial_bandwidth=1.0,
        temporal_bandwidth=1.0,
        spatial_kernel="epanechnikov",
        temporal_kernel="gaussian",
        junction_policy=policy,
    ).fit_predict(workspace)

    np.testing.assert_allclose(
        temporal.to_grid()[0],
        spatial.values / np.sqrt(2.0 * np.pi),
        atol=1e-14,
    )


def test_weighted_intensity_is_weight_sum_times_weighted_density() -> None:
    workspace = _workspace(
        coordinates=((-0.75, 0.0), (0.5, 0.0)),
        times=(-0.2, 0.2),
        weights=(1.0, 3.0),
        lixel_length=0.02,
    )
    common = {
        "spatial_bandwidth": 0.6,
        "temporal_bandwidth": 0.4,
        "junction_policy": "continuous",
    }

    density = TemporalNetworkKDE(target="density", **common).fit_predict(workspace)
    intensity = TemporalNetworkKDE(target="intensity", **common).fit_predict(workspace)

    np.testing.assert_allclose(intensity.values, 4.0 * density.values)


def test_time_chunking_is_numerically_identical_and_reuses_distance_asset() -> None:
    workspace = _workspace(
        coordinates=((-0.75, 0.0), (0.5, 0.0)),
        times=(0.25, 2.25),
        lixel_length=0.05,
        temporal_resolution=0.5,
        temporal_bounds=(0.0, 3.0),
    ).with_distances(cutoff=0.8)
    common = {
        "spatial_bandwidth": 0.8,
        "temporal_bandwidth": 0.6,
        "junction_policy": "simple",
    }

    whole = TemporalNetworkKDE(**common).fit(workspace)
    chunked = TemporalNetworkKDE(time_chunk_size=2, **common).fit(workspace)

    np.testing.assert_allclose(chunked.evaluate(), whole.evaluate())
    assert whole.distance_asset_ is workspace.distance_asset
    assert chunked.distance_asset_ is workspace.distance_asset


def test_cyclic_time_wraps_at_period_boundary() -> None:
    domain = CyclicTimeDomain(period=24.0)
    workspace = _workspace(
        times=(0.0,),
        lixel_length=0.05,
        temporal_resolution=2.0,
        temporal_bounds=None,
        time_domain=domain,
    )
    field = TemporalNetworkKDE(
        spatial_bandwidth=0.5,
        temporal_bandwidth=1.0,
        junction_policy="continuous",
    ).fit_predict(workspace)

    np.testing.assert_allclose(field.to_grid()[0], field.to_grid()[-1])


def test_cyclic_network_time_density_conserves_total_mass() -> None:
    domain = CyclicTimeDomain(period=24.0)
    workspace = _workspace(
        times=(23.8,),
        lixel_length=0.005,
        temporal_resolution=0.2,
        temporal_bounds=None,
        time_domain=domain,
    )
    field = TemporalNetworkKDE(
        spatial_bandwidth=1.0,
        temporal_bandwidth=1.0,
        junction_policy="continuous",
    ).fit_predict(workspace)

    assert field.integral() == pytest.approx(1.0, abs=1e-3)


def test_directed_simple_policy_does_not_propagate_upstream() -> None:
    network = load_osmnx_fixture().network
    raw = SpatialEvents.from_array(
        [[0.4, 0.08]],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    workspace = NetworkTimeWorkspace.prepare(
        network,
        raw,
        [0.0],
        temporal_unit="hours",
        lixel_length=0.05,
        temporal_resolution=1.0,
        temporal_bounds=(-0.5, 0.5),
        max_snap_distance=0.05,
    )
    field = TemporalNetworkKDE(
        spatial_bandwidth=0.3,
        temporal_bandwidth=1.0,
        junction_policy="simple",
        directed=True,
    ).fit_predict(workspace)
    source_edge = int(workspace.events.edge_indices[0])
    source_offset = float(workspace.events.offsets[0])
    upstream = (workspace.lixels.edge_indices == source_edge) & (
        workspace.lixels.center_offsets < source_offset - 1e-9
    )

    assert np.any(upstream)
    np.testing.assert_allclose(field.to_grid()[0, upstream], 0.0)


def test_path_policy_rejects_gaussian_and_resets_state() -> None:
    workspace = _workspace()
    model = TemporalNetworkKDE(
        spatial_bandwidth=1.0,
        temporal_bandwidth=1.0,
        spatial_kernel="gaussian",
        junction_policy="continuous",
    )

    with pytest.raises(ValueError, match="finite-support"):
        model.fit(workspace)

    assert not model.is_fitted_
    assert model.workspace_ is None
    assert model.values_ is None


def test_field_exports_time_lixel_xarray() -> None:
    workspace = _workspace(lixel_length=0.1)
    field = TemporalNetworkKDE(
        spatial_bandwidth=0.5,
        temporal_bandwidth=1.0,
        junction_policy="continuous",
    ).fit_predict(workspace)
    array = field.to_xarray()

    assert array.dims == ("time", "lixel")
    assert array.shape == workspace.arixels.shape
    assert array.attrs["temporal_unit"] == "hours"
