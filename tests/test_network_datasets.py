"""Tests for deterministic network fixtures and generators."""

from __future__ import annotations

import pytest

from pykdex import (
    load_cross_network,
    load_disconnected_network,
    load_osmnx_fixture,
    load_ring_network,
    load_t_junction,
    make_grid_network,
)


@pytest.mark.parametrize(
    "loader",
    [
        load_t_junction,
        load_cross_network,
        load_ring_network,
        load_disconnected_network,
        load_osmnx_fixture,
    ],
)
def test_network_dataset_loaders_are_complete_and_deterministic(loader):
    first = loader()
    second = loader()
    assert first.fingerprint == second.fingerprint
    assert first.network_events is not None
    assert first.lixels is not None
    assert first.validate().valid
    assert first.expected["total_network_length"] == pytest.approx(
        first.network.total_length
    )


def test_grid_network_generator_counts_and_length():
    network = make_grid_network(2, 3, spacing=10.0)
    assert network.n_nodes == 12
    assert network.n_edges == 17
    assert network.total_length == pytest.approx(170.0)
    assert network.n_components == 1


def test_grid_network_generator_validation():
    with pytest.raises(ValueError, match="rows"):
        make_grid_network(0, 2)
    with pytest.raises(ValueError, match="columns"):
        make_grid_network(2, 0)
    with pytest.raises(ValueError, match="spacing"):
        make_grid_network(2, 2, spacing=0.0)
