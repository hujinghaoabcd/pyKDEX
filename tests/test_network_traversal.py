"""Traversal-state tests for directed, undirected, and parallel edges."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import load_osmnx_fixture, load_t_junction, truncated_traversal


def test_t_junction_traversal_reaches_each_branch_fraction():
    network = load_t_junction().network

    result = truncated_traversal(network, 1, cutoff=0.5)

    assert len(result.states) == 3
    assert {state.edge_index for state in result.states} == {0, 1, 2}
    np.testing.assert_allclose(
        [state.start_distance for state in result.states],
        [0.0, 0.0, 0.0],
    )
    np.testing.assert_allclose(
        [state.reached_fraction for state in result.states],
        [0.5, 0.5, 0.5],
    )
    assert not any(state.reversed and state.start_distance == 0.0 for state in result.states)


def test_directed_osm_traversal_keeps_parallel_edges_as_distinct_states():
    network = load_osmnx_fixture().network

    result = truncated_traversal(
        network,
        10,
        cutoff=0.15,
        weight="cost",
        directed=True,
    )

    states_by_edge = {state.edge_index: state for state in result.states}
    assert set(states_by_edge) == {0, 1, 2}
    np.testing.assert_allclose(states_by_edge[0].reached_fraction, 1.0)
    np.testing.assert_allclose(states_by_edge[1].reached_fraction, 0.75)
    np.testing.assert_allclose(states_by_edge[2].reached_fraction, 0.5)
    assert not any(state.reversed for state in result.states)
    assert result.to_frame().shape[0] == 3


def test_undirected_override_emits_reverse_orientations():
    network = load_osmnx_fixture().network

    result = truncated_traversal(
        network,
        20,
        cutoff=0.05,
        weight="cost",
        directed=False,
    )

    assert any(state.reversed for state in result.states)
    assert any(not state.reversed for state in result.states)


def test_unknown_source_node_and_invalid_cutoff_are_rejected():
    network = load_t_junction().network

    with pytest.raises(KeyError, match="Unknown source node"):
        truncated_traversal(network, "missing", cutoff=1.0)
    with pytest.raises(ValueError, match="cutoff"):
        truncated_traversal(network, 1, cutoff=-1.0)
