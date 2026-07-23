# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

import numpy as np
import pytest

from pykdex import (
    CyclicTimeDomain,
    GridSupport,
    LinearTimeDomain,
    SpatiotemporalEvents,
    SpatiotemporalGridSupport,
    SpatiotemporalPointSupport,
    TemporalCoordinates,
    build_spatiotemporal_distance_asset,
)


def test_linear_and_cyclic_time_domains_are_explicit() -> None:
    linear = LinearTimeDomain()
    cyclic = CyclicTimeDomain(period=24.0, origin=0.0)
    offsets = np.array([-25.0, -23.0, 1.0, 25.0])

    np.testing.assert_allclose(
        linear.distances_from_offsets(offsets), [25.0, 23.0, 1.0, 25.0]
    )
    np.testing.assert_allclose(
        cyclic.distances_from_offsets(offsets), [1.0, 1.0, 1.0, 1.0]
    )
    np.testing.assert_allclose(cyclic.canonicalize([-1.0, 24.0]), [23.0, 0.0])
    assert cyclic.fingerprint != linear.fingerprint


def test_invalid_time_domain_parameters_are_rejected() -> None:
    with pytest.raises(TypeError, match="boolean"):
        CyclicTimeDomain(True)
    with pytest.raises(ValueError, match="positive"):
        CyclicTimeDomain(0.0)
    with pytest.raises(ValueError, match="origin"):
        CyclicTimeDomain(24.0, origin=np.inf)


def test_temporal_coordinates_are_read_only_and_datetime_aware() -> None:
    temporal = TemporalCoordinates.from_datetime(
        ["2026-01-01 00:00", "2026-01-01 06:00"],
        timezone="UTC",
        temporal_origin="2026-01-01 00:00",
        temporal_unit="hours",
    )

    np.testing.assert_allclose(temporal.values, [0.0, 6.0])
    assert temporal.timezone == "UTC"
    assert temporal.temporal_origin == "2026-01-01T00:00:00+00:00"
    assert not temporal.values.flags.writeable
    with pytest.raises(ValueError, match="timezone"):
        TemporalCoordinates.from_datetime(["2026-01-01 00:00"])


def test_spatiotemporal_events_keep_spatial_and_temporal_units_separate() -> None:
    events = SpatiotemporalEvents.from_arrays(
        [[0.0, 1.0], [2.0, 3.0]],
        [1.0, 1.0],
        weights=[1.0, 2.0],
        spatial_unit="km",
        temporal_unit="hours",
    )

    assert events.spatial.spatial_unit == "km"
    assert events.temporal.temporal_unit == "hours"
    assert events.weight_sum == 3.0
    assert "duplicate_times" in {issue.code for issue in events.validate().warnings}
    assert list(events.to_frame()["time"]) == [1.0, 1.0]


def test_spatiotemporal_point_support_validates_measure() -> None:
    support = SpatiotemporalPointSupport.from_arrays(
        [[0.0], [1.0]],
        [0.0, 1.0],
        support_measure=[0.5, 0.5],
        spatial_unit="m",
        temporal_unit="seconds",
    )
    np.testing.assert_allclose(support.measure, [0.5, 0.5])
    assert not support.measure.flags.writeable

    with pytest.raises(ValueError, match="positive"):
        SpatiotemporalPointSupport.from_arrays(
            [[0.0]],
            [0.0],
            support_measure=[0.0],
            temporal_unit="seconds",
        )


def test_spatiotemporal_grid_uses_actual_remainder_cell_measure() -> None:
    spatial = GridSupport.from_bounds(
        (0.0, 0.0, 2.5, 1.0),
        resolution=1.0,
        spatial_unit="m",
    )
    support = SpatiotemporalGridSupport.from_spatial_grid(
        spatial,
        temporal_bounds=(0.0, 2.5),
        temporal_resolution=1.0,
        temporal_unit="hours",
    )

    assert support.shape == (3, 1, 3)
    np.testing.assert_allclose(support.time_widths, [1.0, 1.0, 0.5])
    assert np.isclose(np.sum(support.measure), 6.25)
    np.testing.assert_array_equal(
        support.reshape(np.arange(support.n_points)).shape, support.shape
    )


def test_cyclic_grid_requires_one_complete_period() -> None:
    spatial = GridSupport.from_bounds((0, 0, 1, 1), resolution=1.0)
    domain = CyclicTimeDomain(24.0)
    support = SpatiotemporalGridSupport.from_spatial_grid(
        spatial,
        temporal_resolution=5.0,
        temporal_unit="hours",
        time_domain=domain,
    )
    assert np.isclose(np.sum(support.time_widths), 24.0)
    with pytest.raises(ValueError, match="complete period"):
        SpatiotemporalGridSupport(
            spatial=spatial,
            time_edges=np.array([0.0, 12.0]),
            time_domain=domain,
            temporal_unit="hours",
        )


def test_distance_asset_preserves_signed_offsets_and_cyclic_distance() -> None:
    domain = CyclicTimeDomain(24.0)
    events = SpatiotemporalEvents.from_arrays(
        [[0.0], [2.0]],
        [23.0, 3.0],
        spatial_unit="km",
        temporal_unit="hours",
        time_domain=domain,
    )
    support = SpatiotemporalPointSupport.from_arrays(
        [[1.0]],
        [1.0],
        spatial_unit="km",
        temporal_unit="hours",
        time_domain=domain,
    )
    asset = build_spatiotemporal_distance_asset(events, support)

    np.testing.assert_allclose(asset.spatial_distances, [[1.0, 1.0]])
    np.testing.assert_allclose(asset.temporal_offsets, [[-22.0, -2.0]])
    np.testing.assert_allclose(asset.temporal_distances, [[2.0, 2.0]])
    assert not asset.spatial_distances.flags.writeable


def test_distance_asset_rejects_temporal_metadata_mismatch() -> None:
    events = SpatiotemporalEvents.from_arrays(
        [[0.0]], [0.0], temporal_unit="hours", temporal_origin="origin-a"
    )
    support = SpatiotemporalPointSupport.from_arrays(
        [[0.0]], [0.0], temporal_unit="days", temporal_origin="origin-b"
    )
    with pytest.raises(ValueError, match="temporal units"):
        build_spatiotemporal_distance_asset(events, support)
