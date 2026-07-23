# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Geometric linear-network data, distance, and propagation foundations."""

from pykdex.network.dataset import NetworkDataset
from pykdex.network.distance import (
    NetworkDistanceAsset,
    NetworkLocations,
    TraversalResult,
    TraversalState,
    build_event_event_distances,
    build_event_lixel_distances,
    build_network_distance_asset,
    truncated_traversal,
)
from pykdex.network.events import NetworkEvents, SnapResult, snap_events
from pykdex.network.heat import (
    HeatComputePlan,
    NetworkHeatOperator,
    build_heat_compute_plan,
    build_network_heat_operator,
)
from pykdex.network.linear_network import LinearNetwork
from pykdex.network.propagation import (
    ContinuousJunctionPolicy,
    DiscontinuousJunctionPolicy,
    JunctionPolicy,
    PropagationRecord,
    PropagationTrace,
    SimpleJunctionPolicy,
    get_junction_policy,
    trace_network_propagation,
)
from pykdex.network.support import LixelSupport
from pykdex.network.workspace import NetworkWorkspace

__all__ = [
    "LinearNetwork",
    "NetworkEvents",
    "NetworkHeatOperator",
    "HeatComputePlan",
    "build_network_heat_operator",
    "build_heat_compute_plan",
    "SnapResult",
    "snap_events",
    "LixelSupport",
    "NetworkWorkspace",
    "NetworkDataset",
    "NetworkLocations",
    "NetworkDistanceAsset",
    "build_network_distance_asset",
    "build_event_event_distances",
    "build_event_lixel_distances",
    "TraversalState",
    "TraversalResult",
    "truncated_traversal",
    "JunctionPolicy",
    "SimpleJunctionPolicy",
    "DiscontinuousJunctionPolicy",
    "ContinuousJunctionPolicy",
    "get_junction_policy",
    "PropagationRecord",
    "PropagationTrace",
    "trace_network_propagation",
]
