# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""NetworkX adapter for pyKDEX linear networks.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from typing import Any

from pykdex.data import DataProvenance
from pykdex.network.linear_network import LinearNetwork


def from_networkx_graph(
    graph: Any,
    *,
    cost_attribute: str = "length",
    spatial_unit: str | None = None,
    provenance: DataProvenance | None = None,
) -> LinearNetwork:
    """Convert a NetworkX graph to pyKDEX's canonical network representation."""
    return LinearNetwork.from_networkx(
        graph,
        cost_attribute=cost_attribute,
        spatial_unit=spatial_unit,
        provenance=provenance,
    )
