# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Network-time data, support, distance, and workspace contracts."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import (
    ArixelSupport,
    CyclicTimeDomain,
    NetworkTimeEvents,
    NetworkTimeWorkspace,
    SpatialEvents,
    TemporalCoordinates,
    build_network_time_distance_asset,
    load_t_junction,
)


def _workspace(
    coordinates=((-0.75, 0.0), (0.5, 0.0)),
    times=(0.25, 2.25),
    *,
    weights=None,
    lixel_length: float = 0.4,
) -> NetworkTimeWorkspace:
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        coordinates,
        weights=weights,
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    return NetworkTimeWorkspace.prepare(
        network,
        events,
        times,
        temporal_unit="hours",
        lixel_length=lixel_length,
        temporal_resolution=1.0,
        temporal_bounds=(0.0, 2.5),
        max_snap_distance=0.05,
    )


def test_network_time_events_are_paired_read_only_and_auditable() -> None:
    workspace = _workspace(times=(1.0, 1.0))
    events = workspace.events

    assert events.n_events == 2
    np.testing.assert_allclose(events.times, [1.0, 1.0])
    assert not events.times.flags.writeable
    assert events.to_frame()["time"].tolist() == [1.0, 1.0]
    assert "duplicate_times" in {
        issue.code for issue in events.validate(workspace.network).warnings
    }
    with pytest.raises(ValueError):
        events.times[0] = 9.0
    with pytest.raises(ValueError, match="equal length"):
        NetworkTimeEvents(
            events.network_events,
            TemporalCoordinates.from_array(
                [1.0],
                temporal_unit="hours",
            ),
        )


def test_prepare_filters_rejected_event_times_by_stable_event_id() -> None:
    network = load_t_junction().network
    raw = SpatialEvents.from_array(
        [[-0.75, 0.0], [10.0, 10.0], [0.5, 0.0]],
        ids=["accepted-left", "rejected", "accepted-right"],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )

    workspace = NetworkTimeWorkspace.prepare(
        network,
        raw,
        [2.0, 99.0, 7.0],
        temporal_unit="hours",
        lixel_length=0.4,
        temporal_resolution=1.0,
        temporal_bounds=(0.0, 8.0),
        max_snap_distance=0.05,
    )

    assert workspace.events.event_ids.tolist() == [
        "accepted-left",
        "accepted-right",
    ]
    np.testing.assert_allclose(workspace.events.times, [2.0, 7.0])
    assert workspace.network_workspace.snap_result.n_rejected == 1


def test_arixels_preserve_spatial_and_temporal_remainder_measure() -> None:
    workspace = _workspace()
    support = workspace.arixels

    assert support.shape == (3, 9)
    assert support.n_arixels == 27
    np.testing.assert_allclose(support.time_widths, [1.0, 1.0, 0.5])
    assert support.total_measure == pytest.approx(7.5)
    assert support.to_frame().shape[0] == support.n_arixels
    np.testing.assert_array_equal(
        support.reshape(np.arange(support.n_arixels)).shape,
        support.shape,
    )
    with pytest.raises(ValueError, match="one value per arixel"):
        support.reshape(np.arange(3))


def test_cyclic_arixels_cover_exactly_one_period() -> None:
    lixels = _workspace().lixels
    domain = CyclicTimeDomain(period=24.0, origin=0.0)
    support = ArixelSupport.from_lixels(
        lixels,
        temporal_resolution=5.0,
        temporal_unit="hours",
        time_domain=domain,
    )

    np.testing.assert_allclose(support.time_widths, [5.0, 5.0, 5.0, 5.0, 4.0])
    assert support.total_measure == pytest.approx(24.0 * 3.0)
    with pytest.raises(ValueError, match="complete period"):
        ArixelSupport(
            lixels=lixels,
            time_edges=np.array([0.0, 12.0]),
            time_domain=domain,
            temporal_unit="hours",
        )


def test_factorized_asset_preserves_signed_offsets_and_sparse_network_pairs() -> None:
    workspace = _workspace().with_distances(cutoff=0.8)
    asset = workspace.distance_asset
    assert asset is not None

    assert asset.arixel_shape == workspace.arixels.shape
    assert asset.temporal_offsets.shape == (3, 2)
    np.testing.assert_allclose(asset.temporal_offsets[0], [0.25, -1.75])
    np.testing.assert_allclose(asset.temporal_distances, np.abs(asset.temporal_offsets))
    assert asset.network_distances.n_pairs < (asset.n_events * asset.n_lixels)
    assert not asset.temporal_offsets.flags.writeable
    asset.validate_for(
        workspace.network_workspace,
        workspace.events,
        workspace.arixels,
        directed=False,
    )


def test_distance_builder_rejects_metadata_and_directed_type_mismatches() -> None:
    workspace = _workspace()
    incompatible = NetworkTimeEvents(
        workspace.events.network_events,
        TemporalCoordinates.from_array(
            workspace.events.times,
            temporal_unit="days",
        ),
    )

    with pytest.raises(ValueError, match="temporal units"):
        build_network_time_distance_asset(
            workspace.network_workspace,
            incompatible,
            workspace.arixels,
        )
    with pytest.raises(TypeError, match="directed"):
        build_network_time_distance_asset(
            workspace.network_workspace,
            workspace.events,
            workspace.arixels,
            directed="yes",  # type: ignore[arg-type]
        )


def test_workspace_summary_and_distance_copy_are_deterministic() -> None:
    workspace = _workspace()
    prepared = workspace.with_distances()

    assert workspace.distance_asset is None
    assert prepared.distance_asset is not None
    assert prepared.summary()["valid"] is True
    assert prepared.summary()["n_arixels"] == prepared.arixels.n_arixels
    assert prepared.fingerprint != workspace.fingerprint
    assert prepared.with_distances().distance_asset.fingerprint == (
        prepared.distance_asset.fingerprint
    )
