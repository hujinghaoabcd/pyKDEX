"""Tests for boundaries and structured dataset bundles."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import (
    GridSupport,
    KDEDataset,
    PointSupport,
    SpatialBoundary,
    SpatialEvents,
    load_bounded_square,
)


def test_boundary_covers_points_and_reports_outside_locations():
    boundary = SpatialBoundary.from_bounds(
        (0.0, 0.0, 1.0, 1.0),
        crs="EPSG:3857",
        spatial_unit="m",
    )
    coordinates = np.array([[0.0, 0.0], [0.5, 0.5], [2.0, 2.0]])
    assert boundary.area == 1.0
    assert boundary.covers(coordinates).tolist() == [True, True, False]
    report = boundary.validate_points(coordinates)
    assert report.valid
    assert report.statistics["outside_count"] == 1
    assert report.warnings[0].code == "points_outside_boundary"
    np.testing.assert_allclose(
        boundary.distance_to_edge(np.array([[0.5, 0.5]])),
        [0.5],
    )


def test_dataset_validation_detects_crs_and_dimension_mismatch():
    events = SpatialEvents.from_array(
        [[0.0, 0.0], [1.0, 1.0]],
        crs="EPSG:3857",
        spatial_unit="m",
    )
    support = PointSupport.from_array(
        [[0.0], [1.0]],
        crs="EPSG:4326",
        spatial_unit="degree",
    )
    dataset = KDEDataset(name="invalid", events=events, support=support)
    report = dataset.validate()
    assert not report.valid
    assert {issue.code for issue in report.errors} == {
        "dimension_mismatch",
        "crs_mismatch",
        "spatial_unit_mismatch",
    }
    with pytest.raises(ValueError, match="Data validation failed"):
        report.raise_for_errors()


def test_dataset_summary_and_fingerprint_are_stable():
    first = load_bounded_square()
    second = load_bounded_square()
    assert first.fingerprint == second.fingerprint
    summary = first.summary()
    assert summary["name"] == "bounded_square"
    assert summary["n_events"] == 5
    assert summary["n_support"] == 2500
    assert summary["has_boundary"]
    assert summary["valid"]


def test_dataset_rejects_wrong_component_types():
    events = SpatialEvents.from_array([[0.0, 0.0]])
    with pytest.raises(TypeError, match="support"):
        KDEDataset(name="bad", events=events, support=np.zeros((1, 2)))  # type: ignore[arg-type]
    grid = GridSupport.from_bounds((0.0, 0.0, 1.0, 1.0), resolution=0.5)
    dataset = KDEDataset(name="valid", events=events, support=grid)
    assert dataset.validate().valid
