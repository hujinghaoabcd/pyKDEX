# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Geometric linear-network data and distance foundations."""

from pykdex.network.dataset import NetworkDataset
from pykdex.network.distance import (
    NetworkDistanceAsset,
    NetworkLocations,
    TraversalResult,
    TraversalState,
    build_event_lixel_distances,
    build_network_distance_asset,
    truncated_traversal,
)
from pykdex.network.events import NetworkEvents, SnapResult, snap_events
from pykdex.network.linear_network import LinearNetwork
from pykdex.network.support import LixelSupport
from pykdex.network.workspace import NetworkWorkspace

__all__ = [
    "LinearNetwork",
    "NetworkEvents",
    "SnapResult",
    "snap_events",
    "LixelSupport",
    "NetworkWorkspace",
    "NetworkDataset",
    "NetworkLocations",
    "NetworkDistanceAsset",
    "build_network_distance_asset",
    "build_event_lixel_distances",
    "TraversalState",
    "TraversalResult",
    "truncated_traversal",
]
