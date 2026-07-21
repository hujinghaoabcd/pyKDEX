"""Fixed-bandwidth NetworkKDE analytical and state-safety tests."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import NetworkKDE, NetworkWorkspace, SpatialEvents, load_t_junction


def _t_workspace(
    coordinates,
    *,
    weights=None,
    lixel_length: float = 0.005,
):
    network = load_t_junction().network
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


def _lixel_index(workspace, edge_index: int, center_offset: float) -> int:
    selected = np.flatnonzero(
        (workspace.lixels.edge_indices == edge_index)
        & np.isclose(workspace.lixels.center_offsets, center_offset)
    )
    assert selected.size == 1
    return int(selected[0])


def _epanechnikov(distance: float, bandwidth: float = 1.0) -> float:
    standardized = distance / bandwidth
    if standardized > 1.0:
        return 0.0
    return 0.75 * (1.0 - standardized**2) / bandwidth


def test_simple_network_kde_matches_kernel_value_at_zero_distance():
    workspace = _t_workspace([[-0.7475, 0.0]])

    field = NetworkKDE(
        bandwidth=1.0,
        kernel="epanechnikov",
        junction_policy="simple",
    ).fit_predict(workspace)

    source_lixel = _lixel_index(workspace, 0, 0.2525)
    assert field.values[source_lixel] == pytest.approx(0.75)
    assert field.junction_policy == "simple"


def test_discontinuous_network_kde_has_exact_equal_split_branch_values():
    workspace = _t_workspace([[-0.7475, 0.0]])

    field = NetworkKDE(
        bandwidth=1.0,
        kernel="epanechnikov",
        junction_policy="discontinuous",
    ).fit_predict(workspace)

    branch_one = _lixel_index(workspace, 1, 0.1025)
    branch_two = _lixel_index(workspace, 2, 0.1025)
    expected = 0.5 * _epanechnikov(0.85)
    assert field.values[branch_one] == pytest.approx(expected)
    assert field.values[branch_two] == pytest.approx(expected)


def test_continuous_network_kde_matches_backward_correction_near_node():
    workspace = _t_workspace([[-0.7475, 0.0]])

    field = NetworkKDE(
        bandwidth=1.0,
        kernel="epanechnikov",
        junction_policy="continuous",
    ).fit_predict(workspace)

    incoming = _lixel_index(workspace, 0, 0.9975)
    outgoing_one = _lixel_index(workspace, 1, 0.0025)
    outgoing_two = _lixel_index(workspace, 2, 0.0025)
    expected_incoming = _epanechnikov(0.745) - _epanechnikov(0.75) / 3.0
    expected_outgoing = 2.0 * _epanechnikov(0.75) / 3.0
    assert field.values[incoming] == pytest.approx(expected_incoming)
    assert field.values[outgoing_one] == pytest.approx(expected_outgoing)
    assert field.values[outgoing_two] == pytest.approx(expected_outgoing)
    assert abs(field.values[incoming] - field.values[outgoing_one]) < 0.01


def test_continuous_network_field_conserves_mass_and_exports_measured_support():
    workspace = _t_workspace([[-0.7475, 0.0]])
    model = NetworkKDE(
        bandwidth=1.0,
        kernel="epanechnikov",
        junction_policy="continuous",
        store_propagation=True,
    ).fit(workspace)

    field = model.predict_result()
    assert field.integral() == pytest.approx(1.0, abs=5e-4)
    assert field.to_frame().shape[0] == workspace.lixels.n_lixels
    assert field.to_frame()["density"].to_numpy() == pytest.approx(field.values)
    assert model.propagation_traces_ is not None
    assert len(model.propagation_traces_) == 1
    with pytest.raises(ValueError):
        field.values[0] = 1.0


def test_weighted_intensity_is_weight_sum_times_weighted_density():
    workspace = _t_workspace(
        [[-0.7475, 0.0], [0.5025, 0.0]],
        weights=[1.0, 3.0],
        lixel_length=0.01,
    )

    density = NetworkKDE(
        bandwidth=0.5,
        junction_policy="continuous",
        target="density",
    ).fit_predict(workspace)
    intensity = NetworkKDE(
        bandwidth=0.5,
        junction_policy="continuous",
        target="intensity",
    ).fit_predict(workspace)

    np.testing.assert_allclose(intensity.values, 4.0 * density.values)


def test_path_policy_rejects_infinite_support_and_resets_fit_state():
    workspace = _t_workspace([[-0.7475, 0.0]])
    model = NetworkKDE(
        bandwidth=1.0,
        kernel="gaussian",
        junction_policy="discontinuous",
    )

    with pytest.raises(ValueError, match="finite-support"):
        model.fit(workspace)

    assert not model.is_fitted_
    assert model.values_ is None
    assert model.workspace_ is None


def test_simple_policy_accepts_gaussian_kernel():
    workspace = _t_workspace([[-0.7475, 0.0]], lixel_length=0.05)

    field = NetworkKDE(
        bandwidth=0.5,
        kernel="gaussian",
        junction_policy="simple",
    ).fit_predict(workspace)

    assert np.all(np.isfinite(field.values))
    assert np.all(field.values >= 0.0)
