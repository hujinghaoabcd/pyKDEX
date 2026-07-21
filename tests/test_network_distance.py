"""Exact distance tests for arbitrary positions on linear networks."""

from __future__ import annotations

import numpy as np

from pykdex import (
    NetworkLocations,
    build_network_distance_asset,
    load_disconnected_network,
    load_osmnx_fixture,
    load_ring_network,
    load_t_junction,
)


def _locations(network, ids, edges, offsets, kind="test"):
    return NetworkLocations(
        location_ids=np.asarray(ids, dtype=object),
        edge_indices=np.asarray(edges, dtype=np.int64),
        offsets=np.asarray(offsets, dtype=float),
        network_fingerprint=network.fingerprint,
        kind=kind,
    )


def test_same_edge_and_t_junction_distances_match_analytical_values():
    network = load_t_junction().network
    sources = _locations(network, ["source"], [0], [0.3])
    targets = _locations(network, ["same", "branch"], [0, 1], [0.8, 0.5])

    asset = build_network_distance_asset(network, sources, targets)

    np.testing.assert_allclose(asset.to_dense(), [[0.5, 1.2]])
    assert asset.n_pairs == 2
    assert asset.validate(network, sources=sources, targets=targets).valid


def test_cutoff_produces_sparse_neighbourhood_without_losing_zero_pairs():
    network = load_t_junction().network
    sources = _locations(network, ["source"], [0], [0.3])
    targets = _locations(
        network, ["same", "source_copy", "far"], [0, 0, 2], [0.8, 0.3, 0.5]
    )

    asset = build_network_distance_asset(
        network,
        sources,
        targets,
        cutoff=0.6,
    )

    dense = asset.to_dense()
    np.testing.assert_allclose(dense[0, :2], [0.5, 0.0])
    assert np.isinf(dense[0, 2])
    target_indices, distances = asset.neighbors(0)
    np.testing.assert_array_equal(target_indices, [0, 1])
    np.testing.assert_allclose(distances, [0.5, 0.0])


def test_ring_distance_uses_the_shorter_network_route():
    network = load_ring_network().network
    sources = _locations(network, ["south"], [0], [0.5])
    targets = _locations(network, ["north"], [2], [0.5])

    asset = build_network_distance_asset(network, sources, targets)

    np.testing.assert_allclose(asset.to_dense(), [[2.0]])


def test_disconnected_location_pairs_are_omitted_as_unreachable():
    network = load_disconnected_network().network
    sources = _locations(network, ["left"], [0], [0.5])
    targets = _locations(network, ["right"], [1], [0.5])

    asset = build_network_distance_asset(network, sources, targets)

    assert asset.n_pairs == 0
    assert np.isinf(asset.to_dense()[0, 0])


def test_directed_and_undirected_osm_distances_preserve_orientation():
    network = load_osmnx_fixture().network
    forward = _locations(network, ["forward"], [0], [0.4])
    downstream = _locations(network, ["downstream"], [2], [0.7])

    directed = build_network_distance_asset(
        network,
        forward,
        downstream,
        directed=True,
        weight="length",
    )
    reverse = build_network_distance_asset(
        network,
        downstream,
        forward,
        directed=True,
        weight="length",
    )
    reverse_undirected = build_network_distance_asset(
        network,
        downstream,
        forward,
        directed=False,
        weight="length",
    )
    travel_time = build_network_distance_asset(
        network,
        forward,
        downstream,
        directed=True,
        weight="cost",
    )

    np.testing.assert_allclose(directed.to_dense(), [[1.3]])
    assert np.isinf(reverse.to_dense()[0, 0])
    np.testing.assert_allclose(reverse_undirected.to_dense(), [[1.3]])
    np.testing.assert_allclose(travel_time.to_dense(), [[0.13]])
