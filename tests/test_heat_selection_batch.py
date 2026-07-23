"""Reusable heat plans, batch experiments, and diffusion-time selection."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import (
    FixedHeatTime,
    HeatComputePlan,
    HeatLeastSquaresCV,
    HeatLeastSquaresCVTime,
    HeatLikelihoodCV,
    HeatLikelihoodCVTime,
    HeatNetworkExperiment,
    HeatNetworkKDE,
    NetworkWorkspace,
    SpatialEvents,
    build_heat_compute_plan,
    load_ring_network,
    load_t_junction,
)


def _workspace(*, lixel_length: float = 0.1) -> NetworkWorkspace:
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        [[-0.8, 0.0], [-0.35, 0.0], [0.45, 0.0], [0.0, 0.7]],
        weights=[1.0, 2.0, 1.5, 0.5],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    return NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=lixel_length,
        max_snap_distance=0.05,
    )


def test_dense_heat_compute_plan_is_reusable_immutable_and_fingerprinted():
    workspace = _workspace()
    first = build_heat_compute_plan(workspace, mesh_size=0.05)
    second = build_heat_compute_plan(workspace, mesh_size=0.05)

    assert isinstance(first, HeatComputePlan)
    assert first.solver == "dense_symmetric_eigendecomposition"
    assert first.fingerprint == second.fingerprint
    assert first.memory_bytes > 0
    assert first.eigenvalues is not None
    assert first.eigenvectors is not None
    with pytest.raises(ValueError):
        first.eigenvalues[0] = 1.0

    other = _workspace(lixel_length=0.2)
    with pytest.raises(ValueError, match="lixel support"):
        first.validate_workspace(other)


def test_heat_plan_batch_evolution_retains_order_and_duplicates():
    workspace = _workspace()
    plan = build_heat_compute_plan(workspace, mesh_size=0.05)
    assert workspace.events is not None
    coefficients = workspace.events.weights / workspace.events.weight_sum
    source = np.zeros(plan.operator.n_dofs)
    np.add.at(source, plan.operator.event_dofs, coefficients)
    times = np.asarray([0.15, 0.03, 0.15])

    batch = plan.evolve(source, times)
    single = plan.evolve(source, 0.03)

    assert batch.shape == (3, plan.operator.n_dofs, 1)
    np.testing.assert_allclose(batch[0], batch[2], atol=1e-14)
    np.testing.assert_allclose(batch[1], single[0], atol=1e-14)


def test_sparse_and_dense_heat_plans_agree():
    workspace = _workspace(lixel_length=0.2)
    dense = build_heat_compute_plan(
        workspace,
        mesh_size=0.1,
        dense_threshold=1_024,
    )
    sparse_plan = build_heat_compute_plan(
        workspace,
        mesh_size=0.1,
        dense_threshold=1,
    )
    assert workspace.events is not None
    source = np.zeros(dense.operator.n_dofs)
    np.add.at(
        source,
        dense.operator.event_dofs,
        workspace.events.weights / workspace.events.weight_sum,
    )

    expected = dense.evolve(source, [0.04, 0.2])
    actual = sparse_plan.evolve(source, [0.04, 0.2])

    assert sparse_plan.solver == "sparse_expm_multiply"
    assert sparse_plan.eigenvalues is None
    np.testing.assert_allclose(actual, expected, rtol=2e-10, atol=2e-11)


def test_event_heat_kernel_matrix_is_symmetric():
    plan = build_heat_compute_plan(_workspace(), mesh_size=0.05)

    matrix = plan.event_kernel_matrix(0.08)

    np.testing.assert_allclose(matrix, matrix.T, rtol=1e-12, atol=1e-12)
    assert np.all(np.diag(matrix) > 0.0)


def test_exact_piecewise_linear_squared_integral():
    plan = build_heat_compute_plan(_workspace(lixel_length=0.2), mesh_size=0.2)
    constant = np.full(plan.operator.n_dofs, 2.0)
    network_length = float(np.sum(_workspace(lixel_length=0.2).lixels.measure))

    assert plan.operator.integrate_squared(constant) == pytest.approx(
        4.0 * network_length
    )
    with pytest.raises(ValueError, match="heat DOF"):
        plan.operator.integrate_squared(np.ones(2))


def test_heat_network_experiment_matches_independent_fits_and_long_frame():
    workspace = _workspace()
    plan = build_heat_compute_plan(workspace, mesh_size=0.05)
    times = [0.12, 0.03, 0.12]
    experiment = HeatNetworkExperiment(times, mesh_size=0.05)

    result = experiment.run(workspace, compute_plan=plan)

    assert result.n_times == 3
    assert result.compute_plan_fingerprint == plan.fingerprint
    assert result.fields[0] is result.at_index(0)
    np.testing.assert_allclose(result.fields[0].values, result.fields[2].values)
    for time, field in zip(times, result.fields, strict=True):
        expected = HeatNetworkKDE(
            diffusion_time=time,
            mesh_size=0.05,
        ).fit_predict(workspace, compute_plan=plan)
        np.testing.assert_allclose(field.values, expected.values, atol=1e-14)
        assert field.integral() == pytest.approx(1.0, abs=1e-12)
    frame = result.to_frame()
    assert frame.shape[0] == 3 * workspace.lixels.n_lixels
    assert list(frame["diffusion_time"].unique()) == [0.12, 0.03]
    with pytest.raises(ValueError):
        result.diffusion_times[0] = 1.0


def test_heat_likelihood_cv_is_deterministic_and_reuses_plan():
    workspace = _workspace()
    plan = build_heat_compute_plan(workspace, mesh_size=0.05)
    first_selector = HeatLikelihoodCV(bounds=(0.01, 0.4), maxiter=35)

    first = first_selector.select(workspace, compute_plan=plan)
    second = HeatLikelihoodCV(bounds=(0.01, 0.4), maxiter=35).select(
        workspace,
        compute_plan=plan,
    )

    assert first.success
    assert first.method == "heat_likelihood_cv"
    assert 0.01 <= first.bandwidth <= 0.4
    assert first.bandwidth == pytest.approx(second.bandwidth)
    assert first.score == pytest.approx(second.score)
    assert first_selector.cache_ is not None
    assert first_selector.cache_.compute_plan is plan


def test_heat_lscv_and_time_strategies_integrate_with_estimator():
    workspace = _workspace()
    plan = build_heat_compute_plan(workspace, mesh_size=0.05)
    selector = HeatLeastSquaresCV(bounds=(0.01, 0.4), maxiter=35)

    selected = selector.select(workspace, compute_plan=plan)
    likelihood_strategy = HeatLikelihoodCVTime(bounds=(0.01, 0.4), maxiter=30)
    likelihood_model = HeatNetworkKDE(
        diffusion_time=likelihood_strategy,
        mesh_size=0.05,
    ).fit(workspace, compute_plan=plan)
    least_squares_model = HeatNetworkKDE(
        diffusion_time=HeatLeastSquaresCVTime(bounds=(0.01, 0.4), maxiter=30),
        mesh_size=0.05,
    ).fit(workspace, compute_plan=plan)

    assert selected.success
    assert selected.method == "heat_least_squares_cv"
    assert selector.cache_ is not None
    assert likelihood_model.diffusion_time_selection_ is likelihood_strategy.result_
    assert likelihood_model.fit_metadata_["diffusion_time_selected"] is True
    assert least_squares_model.diffusion_time_selection_ is not None
    assert least_squares_model.predict_result().integral() == pytest.approx(
        1.0, abs=1e-12
    )


def test_fixed_heat_time_and_automatic_selection_bounds():
    workspace = _workspace()
    plan = HeatComputePlan.from_workspace(workspace, mesh_size=0.05)

    assert FixedHeatTime(0.2).resolve(
        workspace,
        compute_plan=plan,
    ) == pytest.approx(0.2)
    result = HeatLikelihoodCV(maxiter=20).select(
        workspace,
        compute_plan=plan,
    )
    assert result.bounds[0] > 0.0
    assert result.bounds[0] <= result.bandwidth <= result.bounds[1]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: HeatNetworkExperiment([]),
        lambda: HeatNetworkExperiment([0.0]),
        lambda: HeatNetworkExperiment([True]),
        lambda: HeatNetworkExperiment([0.1], dense_threshold=0),
        lambda: FixedHeatTime(True),
        lambda: HeatLikelihoodCV(bounds=(0.2, 0.1)),
        lambda: HeatLeastSquaresCV(maxiter=0),
    ],
)
def test_heat_batch_and_selection_validate_parameters(factory):
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_heat_plan_rejects_event_pattern_mismatch():
    workspace = _workspace()
    plan = build_heat_compute_plan(workspace)
    network = load_ring_network().network
    events = SpatialEvents.from_array(
        [[0.5, 0.0]],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    other = NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=0.1,
        max_snap_distance=0.05,
    )

    with pytest.raises(ValueError, match="network"):
        HeatNetworkExperiment([0.1]).run(other, compute_plan=plan)
