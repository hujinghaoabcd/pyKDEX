"""Integration tests for reusable event-to-lixel distance assets."""

from __future__ import annotations

from pykdex import NetworkWorkspace, load_t_junction


def test_workspace_attaches_and_validates_event_lixel_distances():
    dataset = load_t_junction()
    workspace = NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=0.25,
        max_snap_distance=0.2,
    )

    prepared = workspace.with_event_lixel_distances(cutoff=0.8)

    assert prepared.distance_asset is not None
    assert prepared.distance_asset.n_pairs > 0
    assert prepared.distance_asset.cutoff == 0.8
    assert prepared.validate().valid
    assert prepared.summary()["n_distance_pairs"] == prepared.distance_asset.n_pairs
    assert prepared.fingerprint != workspace.fingerprint


def test_workspace_can_build_full_cost_distance_asset():
    dataset = load_t_junction()
    workspace = NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=0.5,
        max_snap_distance=0.2,
    )

    prepared = workspace.with_event_lixel_distances(weight="cost")

    assert prepared.distance_asset is not None
    assert prepared.distance_asset.weight == "cost"
    assert prepared.distance_asset.shape == (
        prepared.events.n_events,
        prepared.lixels.n_lixels,
    )
