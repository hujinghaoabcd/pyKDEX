"""Tests for the canonical geometric linear-network representation."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import LinearNetwork, load_disconnected_network, load_osmnx_fixture


def test_t_junction_topology_and_sparse_adjacency():
    from pykdex import load_t_junction

    network = load_t_junction().network
    assert network.n_nodes == 4
    assert network.n_edges == 3
    assert network.n_components == 1
    assert network.total_length == pytest.approx(3.0)
    adjacency = network.adjacency_matrix(weight="length")
    assert adjacency.shape == (4, 4)
    assert adjacency.nnz == 6
    assert network.validate().valid


def test_disconnected_network_reports_components():
    network = load_disconnected_network().network
    report = network.validate()
    assert report.valid
    assert report.statistics["n_components"] == 2
    assert {issue.code for issue in report.warnings} == {"disconnected_network"}


def test_osmnx_fixture_preserves_direction_parallel_edges_and_attributes():
    network = load_osmnx_fixture().network
    assert network.directed
    assert network.n_nodes == 3
    assert network.n_edges == 3
    assert network.metadata["source_adapter"] == "osmnx"
    assert network.metadata["osm_simplified"] is True
    assert network.validate().statistics["parallel_edge_count"] == 1
    assert network.edge_costs.tolist() == pytest.approx([0.1, 0.2, 0.1])
    assert network.edge_attributes["osmid"].tolist() == [100, 101, 102]
    adjacency = network.adjacency_matrix(weight="cost")
    assert adjacency[0, 1] == pytest.approx(0.1)
    assert adjacency[1, 0] == 0.0


def test_networkx_roundtrip_retains_multigraph_semantics():
    original = load_osmnx_fixture().network
    graph = original.to_networkx()
    restored = LinearNetwork.from_networkx(
        graph, cost_attribute="cost", spatial_unit="m"
    )
    assert restored.directed
    assert restored.n_edges == original.n_edges
    assert restored.n_nodes == original.n_nodes
    np.testing.assert_allclose(restored.edge_costs, original.edge_costs)
    assert len(set(restored.edge_keys.tolist())) == 2


def test_osmnx_geographic_graph_requires_explicit_projection():
    import networkx as nx

    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "EPSG:4326"
    graph.add_node(1, x=118.0, y=32.0)
    graph.add_node(2, x=118.01, y=32.0)
    graph.add_edge(1, 2, key=0, length=1000.0)
    with pytest.raises(ValueError, match="must be projected"):
        LinearNetwork.from_osmnx(graph)
    allowed = LinearNetwork.from_osmnx(graph, require_projected=False)
    assert "geographic_crs" in {issue.code for issue in allowed.validate().warnings}


def test_geodataframe_rejects_multilines_and_inconsistent_nodes():
    import geopandas as gpd
    from shapely.geometry import LineString, MultiLineString

    multi = gpd.GeoDataFrame(
        {"edge_id": [0]},
        geometry=[MultiLineString([[(0, 0), (1, 0)], [(1, 0), (2, 0)]])],
        crs="EPSG:3857",
    )
    with pytest.raises(ValueError, match="LineString"):
        LinearNetwork.from_geodataframe(multi)

    inconsistent = gpd.GeoDataFrame(
        {"u": [0, 0], "v": [1, 2]},
        geometry=[LineString([(0, 0), (1, 0)]), LineString([(0.1, 0), (0, 1)])],
        crs="EPSG:3857",
    )
    with pytest.raises(ValueError, match="inconsistent coordinates"):
        LinearNetwork.from_geodataframe(
            inconsistent, u_column="u", v_column="v", endpoint_tolerance=0.01
        )
