"""Tests for measured lixels and reusable network workspaces."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import LixelSupport, NetworkWorkspace, load_ring_network, load_t_junction


def test_lixels_cover_exact_network_length_with_remainders():
    network = load_t_junction().network
    lixels = LixelSupport.from_network(network, length=0.4)
    assert lixels.n_lixels == 9
    assert lixels.total_length == pytest.approx(network.total_length)
    assert lixels.validate(network).valid
    assert np.count_nonzero(lixels.lengths < 0.4 - 1e-12) == 3
    for edge_index in range(network.n_edges):
        mask = lixels.edge_indices == edge_index
        assert lixels.start_offsets[mask][0] == pytest.approx(0.0)
        assert lixels.end_offsets[mask][-1] == pytest.approx(
            network.edge_lengths[edge_index]
        )


def test_lixel_geodataframe_preserves_line_geometry_and_crs():
    dataset = load_ring_network()
    assert dataset.lixels is not None
    frame = dataset.lixels.to_geodataframe()
    assert frame.crs.to_epsg() == 3857
    assert frame.geometry.geom_type.eq("LineString").all()
    assert frame["length"].sum() == pytest.approx(dataset.network.total_length)


def test_workspace_prepares_and_reuses_compatible_assets():
    dataset = load_t_junction()
    workspace = NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=0.25,
        max_snap_distance=0.2,
    )
    assert workspace.events is not None
    assert workspace.summary()["valid"] is True
    assert workspace.summary()["n_events"] == dataset.raw_events.n_events
    assert workspace.lixels.total_length == pytest.approx(
        workspace.network.total_length
    )
    assert (
        workspace.fingerprint
        == NetworkWorkspace.prepare(
            dataset.network,
            dataset.raw_events,
            lixel_length=0.25,
            max_snap_distance=0.2,
        ).fingerprint
    )
