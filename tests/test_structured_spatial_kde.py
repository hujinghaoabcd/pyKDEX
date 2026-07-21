"""Integration tests for structured data objects and SpatialKDE."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import GridSupport, PointSupport, SpatialEvents, SpatialKDE


def test_spatial_kde_uses_owned_event_weights_and_grid_metadata():
    events = SpatialEvents.from_array(
        [[-0.5, 0.0], [0.5, 0.0]],
        weights=[1.0, 3.0],
        crs="EPSG:3857",
        spatial_unit="m",
    )
    grid = GridSupport.from_bounds(
        (-4.0, -4.0, 4.0, 4.0),
        resolution=0.08,
        crs="EPSG:3857",
        spatial_unit="m",
    )
    result = SpatialKDE(bandwidth=0.5).fit_predict(events, grid)
    assert result.crs == "EPSG:3857"
    assert result.spatial_unit == "m"
    assert result.support_ids is not None
    assert result.support_measure is not None
    assert result.support_fingerprint == grid.fingerprint
    assert result.to_grid().shape == grid.shape
    np.testing.assert_allclose(result.integral(), 1.0, rtol=2e-5, atol=2e-5)
    assert result.metadata["event_fingerprint"] == events.fingerprint


def test_spatial_kde_rejects_separate_weights_for_spatial_events():
    events = SpatialEvents.from_array([[0.0], [1.0]], weights=[1.0, 2.0])
    with pytest.raises(ValueError, match="must be omitted"):
        SpatialKDE().fit(events, weights=[1.0, 2.0])


def test_spatial_kde_checks_structured_crs_and_units():
    events = SpatialEvents.from_array(
        [[0.0, 0.0], [1.0, 1.0]],
        crs="EPSG:3857",
        spatial_unit="m",
    )
    wrong_crs = PointSupport.from_array(
        [[0.0, 0.0]],
        crs="EPSG:4326",
        spatial_unit="m",
    )
    wrong_unit = PointSupport.from_array(
        [[0.0, 0.0]],
        crs="EPSG:3857",
        spatial_unit="km",
    )
    model = SpatialKDE().fit(events)
    with pytest.raises(ValueError, match="does not match support CRS"):
        model.evaluate(wrong_crs)
    with pytest.raises(ValueError, match="spatial_unit"):
        model.evaluate(wrong_unit)


def test_spatial_kde_preserves_point_support_ids_without_measure():
    events = SpatialEvents.from_array([[0.0, 0.0], [1.0, 1.0]])
    support = PointSupport.from_array(
        [[0.5, 0.5], [2.0, 2.0]],
        ids=["centre", "far"],
    )
    result = SpatialKDE(bandwidth=1.0).fit(events).predict_result(support)
    assert result.to_frame()["support_id"].tolist() == ["centre", "far"]
    with pytest.raises(ValueError, match="no support_measure"):
        result.integral()
    with pytest.raises(ValueError, match="not evaluated on a GridSupport"):
        result.to_grid()


def test_structured_coordinate_names_must_match():
    events = SpatialEvents.from_array(
        [[0.0, 0.0], [1.0, 1.0]],
        coordinate_names=("east", "north"),
    )
    support = PointSupport.from_array(
        [[0.0, 0.0]],
        coordinate_names=("x", "y"),
    )
    with pytest.raises(ValueError, match="coordinate names"):
        SpatialKDE().fit(events).evaluate(support)
