# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Geometric linear-network data foundations."""

from pykdex.network.dataset import NetworkDataset
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
]
