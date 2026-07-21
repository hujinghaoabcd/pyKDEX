"""Tests for auditable event-to-network snapping."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import SpatialEvents, load_t_junction, snap_events


def test_snapping_records_offsets_coordinates_and_rejections():
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        [[-0.75, 0.05], [0.0, 0.0], [5.0, 5.0]],
        ids=["left", "junction", "far"],
        weights=[1.0, 2.0, 3.0],
        crs=network.crs,
        spatial_unit="m",
    )
    result = snap_events(network, events, max_distance=0.2)
    assert result.n_accepted == 2
    assert result.n_rejected == 1
    assert result.events is not None
    accepted = result.events
    assert accepted.event_ids.tolist() == ["left", "junction"]
    assert accepted.offsets[0] == pytest.approx(0.25)
    np.testing.assert_allclose(accepted.coordinates[0], [-0.75, 0.0])
    assert accepted.snap_status[1] in {"snapped_to_u", "snapped_to_v"}
    assert result.rejected.iloc[0]["event_id"] == "far"
    assert result.rejected.iloc[0]["reason"] == "beyond_max_distance"
    assert "events_rejected" in {issue.code for issue in result.report.warnings}
    assert accepted.validate(network).valid


def test_equal_nearest_edges_are_deterministic_and_audited():
    network = load_t_junction().network
    events = SpatialEvents.from_array([[0.05, 0.05]], crs=network.crs, spatial_unit="m")
    result = snap_events(network, events, tie_tolerance=1e-12)
    assert result.events is not None
    assert result.events.edge_indices.tolist() == [1]
    assert result.events.snap_status.tolist() == ["ambiguous_nearest"]
    assert result.report.statistics["ambiguous_count"] == 1


def test_snapping_rejects_crs_and_unit_mismatches():
    network = load_t_junction().network
    wrong_crs = SpatialEvents.from_array([[0.0, 0.0]], crs="EPSG:4326")
    with pytest.raises(ValueError, match="crs_mismatch"):
        snap_events(network, wrong_crs)
    wrong_unit = SpatialEvents.from_array(
        [[0.0, 0.0]], crs=network.crs, spatial_unit="km"
    )
    with pytest.raises(ValueError, match="spatial_unit_mismatch"):
        snap_events(network, wrong_unit)


def test_all_rejected_returns_none_events():
    network = load_t_junction().network
    events = SpatialEvents.from_array([[20.0, 20.0]], crs=network.crs, spatial_unit="m")
    result = snap_events(network, events, max_distance=0.1)
    assert result.events is None
    assert result.n_accepted == 0
    assert result.n_rejected == 1
