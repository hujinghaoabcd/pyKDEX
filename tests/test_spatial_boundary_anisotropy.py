"""Tests for spatial boundary correction, matrix, and balloon bandwidths."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import multivariate_normal
from shapely.geometry import Polygon

from pykdex import (
    BalloonKNNBandwidth,
    BandwidthMatrix,
    GridSupport,
    KNNBandwidth,
    PointSupport,
    ReflectionCorrection,
    RenormalizationCorrection,
    SpatialBoundary,
    SpatialKDE,
)
from pykdex.kernels import GaussianKernel
from pykdex.metrics import EuclideanMetric


def test_bandwidth_matrix_validates_spd_and_dimension():
    with pytest.raises(ValueError, match="symmetric"):
        BandwidthMatrix(np.array([[1.0, 2.0], [0.0, 1.0]]))
    with pytest.raises(ValueError, match="positive definite"):
        BandwidthMatrix(np.array([[1.0, 2.0], [2.0, 1.0]]))
    strategy = BandwidthMatrix(np.diag([4.0, 0.25]))
    with pytest.raises(ValueError, match="dimension"):
        strategy.resolve(np.zeros((3, 1)))


def test_matrix_gaussian_matches_scipy_multivariate_normal():
    covariance = np.array([[1.2, 0.35], [0.35, 0.6]])
    event = np.array([[0.2, -0.1]])
    support = np.array([[-0.4, 0.3], [0.2, -0.1], [1.0, 0.5]])
    model = SpatialKDE(
        kernel="gaussian",
        bandwidth=BandwidthMatrix(covariance),
    ).fit(event)
    expected = multivariate_normal.pdf(support, mean=event[0], cov=covariance)
    np.testing.assert_allclose(model.evaluate(support), expected, rtol=1e-12, atol=1e-14)
    assert model.fit_metadata_["bandwidth_kind"] == "matrix"


def test_isotropic_matrix_equals_scalar_bandwidth():
    events = np.array([[-0.5, 0.2], [0.8, -0.1]])
    support = np.array([[0.0, 0.0], [1.0, 1.0]])
    scalar = SpatialKDE(bandwidth=0.7).fit(events).evaluate(support)
    matrix = SpatialKDE(
        bandwidth=BandwidthMatrix(np.eye(2) * 0.7**2)
    ).fit(events).evaluate(support)
    np.testing.assert_allclose(matrix, scalar, rtol=1e-13, atol=1e-15)


def test_anisotropic_matrix_has_expected_orientation():
    model = SpatialKDE(
        bandwidth=BandwidthMatrix(np.diag([4.0, 0.25]))
    ).fit(np.array([[0.0, 0.0]]))
    values = model.evaluate(np.array([[1.5, 0.0], [0.0, 1.5]]))
    assert values[0] > values[1] * 20.0


def test_balloon_knn_matches_ranked_support_distances_and_result_metadata():
    events = np.array([[0.0], [2.0], [5.0]])
    support = PointSupport.from_array([[1.0], [4.0]])
    strategy = BalloonKNNBandwidth(2)
    bandwidths = strategy.resolve_support(
        support.coordinates,
        events,
        metric=EuclideanMetric(),
    )
    np.testing.assert_allclose(bandwidths, [1.0, 2.0])
    result = SpatialKDE(bandwidth=strategy).fit_predict(events, support)
    np.testing.assert_allclose(result.bandwidth, [1.0, 2.0])
    assert result.metadata["bandwidth_kind"] == "support"
    assert result.values.shape == (2,)


def test_balloon_knn_requires_floor_for_coincident_first_rank():
    events = np.array([[0.0], [2.0]])
    model = SpatialKDE(bandwidth=BalloonKNNBandwidth(1)).fit(events)
    with pytest.raises(ValueError, match="minimum_bandwidth"):
        model.evaluate(np.array([[0.0]]))
    floored = SpatialKDE(
        bandwidth=BalloonKNNBandwidth(1, minimum_bandwidth=0.2)
    ).fit(events)
    assert np.isfinite(floored.evaluate(np.array([[0.0]]))).all()
    with pytest.raises(ValueError, match="cannot exceed"):
        SpatialKDE(bandwidth=BalloonKNNBandwidth(3)).fit(events)


def test_rectangular_gaussian_renormalization_restores_boundary_mass():
    boundary = SpatialBoundary.from_bounds((0.0, 0.0, 1.0, 1.0))
    grid = GridSupport.from_bounds(boundary.bounds, resolution=0.01)
    event = np.array([[0.04, 0.5]])
    plain = SpatialKDE(bandwidth=0.12, boundary=boundary).fit_predict(event, grid)
    corrected = SpatialKDE(
        bandwidth=0.12,
        boundary=boundary,
        boundary_correction="renormalization",
    ).fit_predict(event, grid)
    assert plain.integral() < 0.7
    np.testing.assert_allclose(corrected.integral(), 1.0, rtol=2e-3, atol=2e-3)
    assert corrected.metadata["boundary_correction"] == "renormalization"


def test_polygon_renormalization_uses_deterministic_measured_quadrature():
    polygon = Polygon([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)])
    boundary = SpatialBoundary(polygon)
    correction = RenormalizationCorrection(cells_per_axis=80)
    events = np.array([[0.08, 0.08], [0.3, 0.2]])
    state = correction.prepare(
        events,
        boundary=boundary,
        kernel=GaussianKernel(),
        metric=EuclideanMetric(),
        bandwidth=0.15,
    )
    assert state.masses is not None
    assert np.all(state.masses > 0.45)
    assert np.all(state.masses < 1.0)
    repeated = correction.prepare(
        events,
        boundary=boundary,
        kernel=GaussianKernel(),
        metric=EuclideanMetric(),
        bandwidth=0.15,
    )
    np.testing.assert_array_equal(repeated.masses, state.masses)


def test_reflection_increases_near_edge_density_and_approximately_preserves_mass():
    boundary = SpatialBoundary.from_bounds((0.0, 0.0, 1.0, 1.0))
    event = np.array([[0.04, 0.5]])
    query = np.array([[0.0, 0.5]])
    plain = SpatialKDE(bandwidth=0.08, boundary=boundary).fit(event)
    reflected = SpatialKDE(
        bandwidth=0.08,
        boundary=boundary,
        boundary_correction=ReflectionCorrection(),
    ).fit(event)
    assert reflected.evaluate(query)[0] > 1.9 * plain.evaluate(query)[0]
    grid = GridSupport.from_bounds(boundary.bounds, resolution=0.005)
    result = reflected.predict_result(grid)
    np.testing.assert_allclose(result.integral(), 1.0, rtol=3e-3, atol=3e-3)


def test_reflection_rejects_nonrectangular_boundary_and_full_matrix():
    triangle = SpatialBoundary(Polygon([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]))
    with pytest.raises(ValueError, match="rectangular"):
        SpatialKDE(
            bandwidth=0.2,
            boundary=triangle,
            boundary_correction="reflection",
        ).fit(np.array([[0.2, 0.2]]))
    rectangle = SpatialBoundary.from_bounds((0.0, 0.0, 1.0, 1.0))
    with pytest.raises(ValueError, match="full matrices"):
        SpatialKDE(
            bandwidth=BandwidthMatrix(np.array([[0.04, 0.01], [0.01, 0.04]])),
            boundary=rectangle,
            boundary_correction="reflection",
        ).fit(np.array([[0.2, 0.2]]))


def test_boundary_context_and_atomic_failure_contracts():
    boundary = SpatialBoundary.from_bounds((0.0, 0.0, 1.0, 1.0))
    model = SpatialKDE(
        bandwidth=0.2,
        boundary=boundary,
        boundary_correction="renormalization",
    )
    with pytest.raises(ValueError, match="outside"):
        model.fit(np.array([[2.0, 2.0]]))
    assert not model.is_fitted_
    fitted = SpatialKDE(bandwidth=0.2, boundary=boundary).fit(
        np.array([[0.5, 0.5]])
    )
    with pytest.raises(ValueError, match="support"):
        fitted.evaluate(np.array([[2.0, 2.0]]))
    with pytest.raises(ValueError, match="cannot yet be combined"):
        SpatialKDE(
            bandwidth=BalloonKNNBandwidth(1, minimum_bandwidth=0.1),
            boundary=boundary,
            boundary_correction="renormalization",
        ).fit(np.array([[0.5, 0.5]]))


def test_new_spatial_strategy_constructor_validation():
    with pytest.raises(TypeError, match="positive integer"):
        BalloonKNNBandwidth(True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="greater than zero"):
        BalloonKNNBandwidth(0)
    with pytest.raises(ValueError, match="multiplier"):
        BalloonKNNBandwidth(1, multiplier=0.0)
    with pytest.raises(ValueError, match="minimum_bandwidth"):
        BalloonKNNBandwidth(1, minimum_bandwidth=0.0)
    with pytest.raises(ValueError, match="square"):
        BandwidthMatrix(np.ones((2, 3)))
    with pytest.raises(ValueError, match="finite"):
        BandwidthMatrix(np.array([[1.0, np.nan], [np.nan, 1.0]]))
    with pytest.raises(TypeError, match="positive integer"):
        RenormalizationCorrection(cells_per_axis=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="at least 8"):
        RenormalizationCorrection(cells_per_axis=4)
    with pytest.raises(ValueError, match="mass_floor"):
        RenormalizationCorrection(mass_floor=0.0)


def test_balloon_support_validation_and_boundary_correction_names():
    strategy = BalloonKNNBandwidth(1, minimum_bandwidth=0.1)
    with pytest.raises(ValueError, match="two-dimensional"):
        strategy.resolve_support(
            np.array([0.0]),
            np.array([[0.0]]),
            metric=EuclideanMetric(),
        )
    with pytest.raises(ValueError, match="requires a SpatialBoundary"):
        SpatialKDE(boundary_correction="renormalization").fit(
            np.array([[0.0, 0.0]])
        )
    with pytest.raises(ValueError, match="Unknown boundary correction"):
        SpatialKDE(boundary_correction="invented").fit(np.array([[0.0, 0.0]]))
    with pytest.raises(TypeError, match="boundary_correction"):
        SpatialKDE(boundary_correction=1).fit(  # type: ignore[arg-type]
            np.array([[0.0, 0.0]])
        )


def test_full_matrix_gaussian_rectangle_renormalization_is_supported():
    boundary = SpatialBoundary.from_bounds((-1.0, -1.0, 1.0, 1.0))
    covariance = np.array([[0.25, 0.08], [0.08, 0.16]])
    model = SpatialKDE(
        bandwidth=BandwidthMatrix(covariance),
        boundary=boundary,
        boundary_correction=RenormalizationCorrection(),
    ).fit(np.array([[0.75, 0.0]]))
    state = model.boundary_correction_state_
    assert state is not None and state.masses is not None
    assert 0.5 < state.masses[0] < 1.0
    assert not state.masses.flags.writeable


def test_diagonal_matrix_reflection_and_event_bandwidth_reflection_are_supported():
    boundary = SpatialBoundary.from_bounds((0.0, 0.0, 1.0, 1.0))
    matrix_model = SpatialKDE(
        bandwidth=BandwidthMatrix(np.diag([0.04, 0.09])),
        boundary=boundary,
        boundary_correction="reflection",
    ).fit(np.array([[0.2, 0.3]]))
    assert np.isfinite(matrix_model.evaluate(np.array([[0.2, 0.3]]))).all()
    event_model = SpatialKDE(
        bandwidth=KNNBandwidth(1, minimum_bandwidth=0.1),
        boundary=boundary,
        boundary_correction="reflection",
    ).fit(np.array([[0.2, 0.3], [0.8, 0.7]]))
    state = event_model.boundary_correction_state_
    assert state is not None and state.expanded_bandwidth is not None
    assert np.asarray(state.expanded_bandwidth).shape == (18,)


def test_spatial_boundary_requires_planar_coordinates():
    boundary = SpatialBoundary.from_bounds((0.0, 0.0, 1.0, 1.0))
    with pytest.raises(ValueError, match="two-dimensional"):
        SpatialKDE(boundary=boundary).fit(np.array([[0.5]]))
