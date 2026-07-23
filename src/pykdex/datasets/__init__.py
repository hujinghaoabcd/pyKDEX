# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Deterministic datasets and synthetic generators."""

from pykdex.datasets.network import (
    load_cross_network,
    load_disconnected_network,
    load_osmnx_fixture,
    load_ring_network,
    load_t_junction,
    make_grid_network,
)
from pykdex.datasets.synthetic import (
    load_bimodal_points,
    load_bounded_square,
    make_bimodal_events,
    make_moving_hotspot_events,
)

__all__ = [
    "make_bimodal_events",
    "make_moving_hotspot_events",
    "load_bimodal_points",
    "load_bounded_square",
    "load_t_junction",
    "load_cross_network",
    "load_ring_network",
    "load_disconnected_network",
    "load_osmnx_fixture",
    "make_grid_network",
]
