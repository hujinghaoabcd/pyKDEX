"""Heat-equation network KDE analytical and contract tests."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import sparse

from pykdex import (
    HeatNetworkKDE,
    NetworkHeatOperator,
    NetworkWorkspace,
    SpatialEvents,
    build_network_heat_operator,
    load_disconnected_network,
    load_osmnx_fixture,
    load_ring_network,
    load_t_junction,
)


def _workspace(network, coordinates, *, weights=None, lixel_length=0.05):
    events = SpatialEvents.from_array(
        coordinates,
        weights=weights,
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    return NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=lixel_length,
        max_snap_distance=0.05,
    )


def _interval_neumann_average(
    starts, ends, *, source: float, time: float, terms: int = 200
):
    starts = np.asarray(starts, dtype=float)
    ends = np.asarray(ends, dtype=float)
    result = np.ones_like(starts)
    for order in range(1, terms + 1):
        frequency = order * np.pi
        cell_cosine = (np.sin(frequency * ends) - np.sin(frequency * starts)) / (
            frequency * (ends - starts)
        )
        result += (
            2.0
            * np.cos(frequency * source)
            * np.exp(-(frequency**2) * time)
            * cell_cosine
        )
    return result


def _ring_average(
    starts, ends, *, source: float, time: float, length: float = 4.0, terms: int = 200
):
    starts = np.asarray(starts, dtype=float)
    ends = np.asarray(ends, dtype=float)
    result = np.full_like(starts, 1.0 / length)
    for order in range(1, terms + 1):
        frequency = 2.0 * np.pi * order / length
        cosine_integral = (
            np.sin(frequency * (ends - source)) - np.sin(frequency * (starts - source))
        ) / (frequency * (ends - starts))
        result += 2.0 / length * np.exp(-(frequency**2) * time) * cosine_integral
    return result


def test_heat_network_kde_matches_neumann_interval_reference():
    network = load_disconnected_network().network
    workspace = _workspace(network, [[0.5, 0.0]], lixel_length=0.05)
    first_component = workspace.lixels.edge_indices == 0
    time = 0.025

    field = HeatNetworkKDE(
        diffusion_time=time,
        mesh_size=0.0125,
    ).fit_predict(workspace)
    expected = _interval_neumann_average(
        workspace.lixels.start_offsets[first_component],
        workspace.lixels.end_offsets[first_component],
        source=0.5,
        time=time,
    )

    np.testing.assert_allclose(
        field.values[first_component], expected, rtol=4e-3, atol=4e-3
    )
    assert np.all(field.values[~first_component] == 0.0)
    assert field.integral() == pytest.approx(1.0, abs=1e-12)


def test_heat_network_kde_matches_periodic_ring_reference():
    network = load_ring_network().network
    workspace = _workspace(network, [[0.5, 0.0]], lixel_length=0.05)
    arc_starts = (
        workspace.lixels.edge_indices.astype(float) + workspace.lixels.start_offsets
    )
    arc_ends = (
        workspace.lixels.edge_indices.astype(float) + workspace.lixels.end_offsets
    )
    time = 0.04

    field = HeatNetworkKDE(
        diffusion_time=time,
        mesh_size=0.0125,
    ).fit_predict(workspace)
    expected = _ring_average(
        arc_starts,
        arc_ends,
        source=0.5,
        time=time,
    )

    np.testing.assert_allclose(field.values, expected, rtol=4e-3, atol=4e-3)
    assert field.integral() == pytest.approx(1.0, abs=1e-12)


def test_heat_density_and_intensity_conserve_weight_by_component():
    network = load_disconnected_network().network
    workspace = _workspace(
        network,
        [[0.25, 0.0], [3.75, 0.0]],
        weights=[1.0, 3.0],
        lixel_length=0.1,
    )

    density = HeatNetworkKDE(diffusion_time=0.1).fit_predict(workspace)
    intensity = HeatNetworkKDE(diffusion_time=0.1, target="intensity").fit_predict(
        workspace
    )
    first = workspace.lixels.edge_indices == 0
    second = ~first

    assert np.dot(
        density.values[first], workspace.lixels.lengths[first]
    ) == pytest.approx(0.25, abs=1e-12)
    assert np.dot(
        density.values[second], workspace.lixels.lengths[second]
    ) == pytest.approx(0.75, abs=1e-12)
    assert intensity.integral() == pytest.approx(4.0, abs=1e-12)
    np.testing.assert_allclose(intensity.values, 4.0 * density.values)


def test_heat_operator_is_sparse_measured_and_places_events_exactly():
    network = load_t_junction().network
    workspace = _workspace(network, [[-0.733, 0.0]], lixel_length=0.2)

    operator = build_network_heat_operator(workspace, mesh_size=0.08)
    event_edge = int(workspace.events.edge_indices[0])
    event_offset = float(workspace.events.offsets[0])
    event_dof = int(operator.event_dofs[0])
    position = int(np.flatnonzero(operator.edge_dofs[event_edge] == event_dof)[0])

    assert isinstance(operator, NetworkHeatOperator)
    assert sparse.isspmatrix_csr(operator.stiffness)
    assert operator.edge_offsets[event_edge][position] == pytest.approx(event_offset)
    assert operator.n_dofs > network.n_nodes
    assert operator.n_segments >= workspace.lixels.n_lixels
    assert np.all(operator.mass > 0.0)
    assert (
        operator.fingerprint
        == build_network_heat_operator(workspace, mesh_size=0.08).fingerprint
    )
    with pytest.raises(ValueError):
        operator.mass[0] = 0.0


def test_t_junction_uses_shared_vertex_and_reports_exact_continuity():
    network = load_t_junction().network
    workspace = _workspace(network, [[-0.7, 0.0]], lixel_length=0.02)
    model = HeatNetworkKDE(diffusion_time=0.08, mesh_size=0.01).fit(workspace)
    operator = model.heat_operator_

    assert operator is not None
    junction = int(network.edge_v[0])
    incident_endpoint_dofs = [
        int(operator.edge_dofs[0][-1]),
        int(operator.edge_dofs[1][0]),
        int(operator.edge_dofs[2][0]),
    ]
    assert incident_endpoint_dofs == [junction, junction, junction]
    assert model.vertex_continuity_error_ == 0.0
    assert model.component_mass_error_ is not None
    assert model.component_mass_error_ < 1e-12
    assert model.predict_result().metadata["junction_policy"] == "kirchhoff"


def test_heat_model_state_result_metadata_and_copy_contracts():
    network = load_t_junction().network
    workspace = _workspace(network, [[-0.6, 0.0]], lixel_length=0.1)
    model = HeatNetworkKDE(diffusion_time=0.2)

    field = model.fit_predict(workspace)
    copied = model.evaluate()

    assert model.is_fitted_
    assert field.kernel == "heat"
    assert field.junction_policy == "kirchhoff"
    assert field.bandwidth == pytest.approx(np.sqrt(0.4))
    assert field.metadata["lixel_evaluation"] == "cell_average"
    assert field.metadata["terminal_boundary"] == "neumann"
    copied[0] = -1.0
    assert model.values_ is not None
    assert model.values_[0] >= 0.0
    with pytest.raises(ValueError):
        model.nodal_values_[0] = 0.0


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"diffusion_time": 0.0}, "diffusion_time"),
        ({"diffusion_time": np.inf}, "diffusion_time"),
        ({"mesh_size": 0.0}, "mesh_size"),
        ({"negative_tolerance": 0.0}, "negative_tolerance"),
    ],
)
def test_heat_model_validates_constructor(kwargs, match):
    with pytest.raises(ValueError, match=match):
        HeatNetworkKDE(**kwargs)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"diffusion_time": True}, "diffusion_time"),
        ({"mesh_size": True}, "mesh_size"),
        ({"negative_tolerance": True}, "negative_tolerance"),
    ],
)
def test_heat_model_rejects_boolean_numeric_parameters(kwargs, match):
    with pytest.raises(TypeError, match=match):
        HeatNetworkKDE(**kwargs)


def test_heat_operator_rejects_directed_network_and_resets_failed_fit():
    dataset = load_osmnx_fixture()
    workspace = _workspace(
        dataset.network,
        [[0.4, 0.08]],
        lixel_length=0.2,
    )
    model = HeatNetworkKDE(diffusion_time=0.1)

    with pytest.raises(ValueError, match="undirected"):
        model.fit(workspace)

    assert not model.is_fitted_
    assert model.workspace_ is None
    assert model.heat_operator_ is None
    assert model.values_ is None


def test_heat_operator_and_estimator_validate_workspace_type():
    with pytest.raises(TypeError, match="workspace"):
        build_network_heat_operator(object())
    with pytest.raises(TypeError, match="workspace"):
        HeatNetworkKDE().fit(object())


def test_heat_operator_rejects_boolean_mesh_size():
    network = load_t_junction().network
    workspace = _workspace(network, [[-0.6, 0.0]], lixel_length=0.1)

    with pytest.raises(TypeError, match="mesh_size"):
        build_network_heat_operator(workspace, mesh_size=True)
