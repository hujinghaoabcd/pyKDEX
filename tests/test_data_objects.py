"""Tests for immutable event, support, and provenance data objects."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pykdex import (
    DataProvenance,
    GridSupport,
    PointSupport,
    SpatialEvents,
)


def test_spatial_events_are_owned_read_only_and_fingerprinted():
    coordinates = np.array([[0.0, 1.0], [2.0, 3.0]])
    weights = np.array([1.0, 2.0])
    events = SpatialEvents.from_array(
        coordinates,
        weights=weights,
        ids=["a", "b"],
        crs="EPSG:3857",
        spatial_unit="m",
    )
    baseline = events.coordinates.copy()
    coordinates[:] = 99.0
    weights[:] = 99.0
    np.testing.assert_array_equal(events.coordinates, baseline)
    assert not events.coordinates.flags.writeable
    assert not events.weights.flags.writeable
    assert not events.ids.flags.writeable
    assert events.coordinate_names == ("x", "y")
    assert events.weight_sum == 3.0
    assert len(events.fingerprint) == 40
    with pytest.raises(ValueError):
        events.coordinates[0, 0] = 2.0


def test_spatial_events_dataframe_constructor_and_validation_report():
    frame = pd.DataFrame(
        {
            "east": [0.0, 0.0, 1.0],
            "north": [0.0, 0.0, 1.0],
            "severity": [1.0, 2.0, 3.0],
            "identifier": [10, 11, 12],
            "type": ["a", "a", "b"],
        }
    )
    events = SpatialEvents.from_dataframe(
        frame,
        coordinate_columns=("east", "north"),
        weight_column="severity",
        id_column="identifier",
        mark_column="type",
    )
    report = events.validate()
    assert report.valid
    assert report.statistics["duplicate_event_count"] == 1
    assert {issue.code for issue in report.warnings} == {
        "duplicate_coordinates",
        "missing_crs",
    }
    assert list(events.to_frame().columns) == [
        "event_id",
        "east",
        "north",
        "weight",
        "mark",
    ]


def test_spatial_events_reject_invalid_ids_and_weights():
    with pytest.raises(ValueError, match="unique"):
        SpatialEvents.from_array([[0.0], [1.0]], ids=[1, 1])
    with pytest.raises(ValueError, match="non-negative"):
        SpatialEvents.from_array([[0.0], [1.0]], weights=[1.0, -1.0])
    with pytest.raises(ValueError, match="positive"):
        SpatialEvents.from_array([[0.0], [1.0]], weights=[0.0, 0.0])


def test_point_support_dataframe_roundtrip():
    frame = pd.DataFrame({"x": [0.0, 1.0], "y": [2.0, 3.0], "id": [4, 5]})
    support = PointSupport.from_dataframe(
        frame,
        coordinate_columns=("x", "y"),
        id_column="id",
        crs="EPSG:3857",
        spatial_unit="m",
    )
    assert support.n_points == 2
    assert support.dimension == 2
    assert support.measure is None
    assert list(support.to_frame().columns) == ["support_id", "x", "y"]
    assert support.to_frame()["support_id"].tolist() == [4, 5]


def test_grid_support_handles_remainder_cells_and_measure():
    grid = GridSupport.from_bounds(
        (0.0, 0.0, 1.0, 1.0),
        resolution=0.4,
        spatial_unit="m",
    )
    assert grid.shape == (3, 3)
    assert grid.n_points == 9
    np.testing.assert_allclose(np.sum(grid.measure), 1.0)
    np.testing.assert_allclose(grid.reshape(np.arange(9)).shape, (3, 3))
    assert np.min(grid.measure) < 0.16
    with pytest.raises(ValueError, match="one value per grid cell"):
        grid.reshape(np.arange(8))


def test_provenance_is_immutable_and_fingerprint_changes():
    first = DataProvenance(source="demo", metadata={"version": 1})
    second = first.with_transformation("reprojected", crs="EPSG:3857")
    assert first.transformations == ()
    assert second.transformations == ("reprojected",)
    assert first.fingerprint != second.fingerprint
    with pytest.raises(TypeError):
        first.metadata["x"] = 1  # type: ignore[index]
