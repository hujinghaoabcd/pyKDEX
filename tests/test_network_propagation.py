"""Junction-policy and path-propagation tests."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import (
    ContinuousJunctionPolicy,
    DiscontinuousJunctionPolicy,
    SimpleJunctionPolicy,
    load_osmnx_fixture,
    load_ring_network,
    load_t_junction,
    trace_network_propagation,
)


def test_junction_policy_weights_match_equal_split_definitions():
    simple = SimpleJunctionPolicy()
    discontinuous = DiscontinuousJunctionPolicy()
    continuous = ContinuousJunctionPolicy()

    np.testing.assert_allclose(simple.transition_weights(3, 0), [0.0, 1.0, 1.0])
    np.testing.assert_allclose(
        discontinuous.initial_weights(3),
        [2.0 / 3.0] * 3,
    )
    np.testing.assert_allclose(
        discontinuous.transition_weights(3, 0),
        [0.0, 0.5, 0.5],
    )
    np.testing.assert_allclose(
        continuous.transition_weights(3, 0),
        [-1.0 / 3.0, 2.0 / 3.0, 2.0 / 3.0],
    )


def test_discontinuous_trace_splits_t_junction_into_two_equal_branches():
    network = load_t_junction().network

    trace = trace_network_propagation(
        network,
        source_edge_index=0,
        source_offset=0.25,
        cutoff=1.0,
        junction_policy="discontinuous",
        source_id="event",
    )

    branch_records = [record for record in trace.records if record.edge_index in {1, 2}]
    assert len(branch_records) == 2
    np.testing.assert_allclose(
        [record.coefficient for record in branch_records],
        [0.5, 0.5],
    )
    assert all(record.start_distance == pytest.approx(0.75) for record in branch_records)
    assert trace.to_frame().shape[0] == trace.n_records


def test_continuous_trace_adds_signed_reflection_at_degree_three_node():
    network = load_t_junction().network

    trace = trace_network_propagation(
        network,
        source_edge_index=0,
        source_offset=0.25,
        cutoff=1.0,
        junction_policy="continuous",
    )

    corrected = [record for record in trace.records if record.depth == 1]
    coefficients = sorted(record.coefficient for record in corrected)
    np.testing.assert_allclose(coefficients, [-1.0 / 3.0, 2.0 / 3.0, 2.0 / 3.0])


def test_continuous_policy_rejects_directed_metric_graphs():
    network = load_osmnx_fixture().network

    with pytest.raises(ValueError, match="requires an undirected network"):
        trace_network_propagation(
            network,
            source_edge_index=0,
            source_offset=0.25,
            cutoff=1.0,
            junction_policy="continuous",
            directed=True,
        )


def test_path_safety_limit_fails_explicitly_on_repeated_ring_walks():
    network = load_ring_network().network

    with pytest.raises(RuntimeError, match="max_records"):
        trace_network_propagation(
            network,
            source_edge_index=0,
            source_offset=0.5,
            cutoff=10.0,
            junction_policy="continuous",
            max_records=5,
        )
