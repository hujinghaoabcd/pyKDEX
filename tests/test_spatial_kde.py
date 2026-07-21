"""Behavioural and numerical tests for SpatialKDE."""

import inspect

import numpy as np
import pandas as pd
import pytest
from scipy.integrate import trapezoid

from pykdex import GaussianKernel, SpatialKDE


def test_constructor_has_no_backend_parameter():
    assert "backend" not in inspect.signature(SpatialKDE).parameters
    model = SpatialKDE()
    assert not hasattr(model, "backend")
    assert not hasattr(model, "device")


def test_single_event_matches_closed_form_gaussian():
    model = SpatialKDE(kernel="gaussian", bandwidth=2.0)
    model.fit(np.array([[0.0, 0.0]]))
    support = np.array([[0.0, 0.0], [2.0, 0.0]])
    actual = model.evaluate(support)
    expected = np.array(
        [
            1.0 / (2.0 * np.pi * 2.0**2),
            np.exp(-0.5) / (2.0 * np.pi * 2.0**2),
        ]
    )
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)


def test_density_approximately_integrates_to_one(events_2d):
    x = np.linspace(-5.0, 5.0, 301)
    y = np.linspace(-5.0, 5.0, 301)
    xx, yy = np.meshgrid(x, y)
    support = np.column_stack([xx.ravel(), yy.ravel()])
    values = SpatialKDE(bandwidth=0.55).fit(events_2d).evaluate(support)
    grid = values.reshape(y.size, x.size)
    integral_x = trapezoid(grid, x=x, axis=1)
    integral = trapezoid(integral_x, x=y)
    np.testing.assert_allclose(integral, 1.0, rtol=2e-4, atol=2e-4)


def test_intensity_approximately_integrates_to_weight_sum(events_2d):
    weights = np.array([1.0, 2.0, 3.0, 4.0])
    x = np.linspace(-5.0, 5.0, 251)
    y = np.linspace(-5.0, 5.0, 251)
    xx, yy = np.meshgrid(x, y)
    support = np.column_stack([xx.ravel(), yy.ravel()])
    values = (
        SpatialKDE(bandwidth=0.6, target="intensity")
        .fit(events_2d, weights=weights)
        .evaluate(support)
    )
    grid = values.reshape(y.size, x.size)
    integral = trapezoid(trapezoid(grid, x=x, axis=1), x=y)
    np.testing.assert_allclose(integral, weights.sum(), rtol=3e-4, atol=3e-4)


def test_weighted_density_is_invariant_to_common_weight_scale(events_2d):
    support = np.array([[0.0, 0.0], [1.0, 1.0]])
    weights = np.array([1.0, 2.0, 3.0, 4.0])
    first = SpatialKDE(bandwidth=0.5).fit(events_2d, weights).evaluate(support)
    second = SpatialKDE(bandwidth=0.5).fit(events_2d, 7 * weights).evaluate(support)
    np.testing.assert_allclose(first, second)


def test_training_arrays_are_copied(events_2d):
    events = events_2d.copy()
    weights = np.arange(1.0, 5.0)
    model = SpatialKDE(bandwidth=0.5).fit(events, weights)
    baseline = model.evaluate(np.array([[0.0, 0.0]]))
    events[:] = 999.0
    weights[:] = 999.0
    repeated = model.evaluate(np.array([[0.0, 0.0]]))
    np.testing.assert_allclose(repeated, baseline)


def test_failed_refit_clears_previous_state(events_2d):
    model = SpatialKDE(bandwidth=0.5).fit(events_2d)
    assert model.is_fitted_
    with pytest.raises(ValueError):
        model.fit(events_2d, weights=np.ones(2))
    assert not model.is_fitted_
    assert model.events_ is None
    assert model.bandwidth_ is None


def test_dataframe_schema_is_recorded_and_checked(events_2d):
    events = pd.DataFrame(events_2d, columns=["x", "y"])
    model = SpatialKDE(bandwidth=0.5).fit(events)
    assert model.coordinate_names_in_.tolist() == ["x", "y"]
    with pytest.raises(ValueError, match="same order"):
        model.evaluate(pd.DataFrame([[0.0, 0.0]], columns=["y", "x"]))


def test_chunked_evaluation_matches_full(events_2d):
    support = np.linspace(-1.0, 1.0, 40).reshape(20, 2)
    full = SpatialKDE(bandwidth=0.4).fit(events_2d).evaluate(support)
    chunked = SpatialKDE(bandwidth=0.4, chunk_size=3).fit(events_2d).evaluate(support)
    np.testing.assert_allclose(chunked, full)


def test_custom_kernel_object_is_supported(events_2d):
    model = SpatialKDE(kernel=GaussianKernel(), bandwidth=0.5).fit(events_2d)
    assert model.kernel_.name == "gaussian"
