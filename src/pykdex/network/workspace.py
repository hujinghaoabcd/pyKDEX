# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Reusable prepared assets for network analysis.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pykdex.data import SpatialEvents
from pykdex.data._utils import stable_fingerprint
from pykdex.data.validation import DataValidationReport
from pykdex.network.events import NetworkEvents, SnapResult, snap_events
from pykdex.network.linear_network import LinearNetwork
from pykdex.network.support import LixelSupport


@dataclass(frozen=True)
class NetworkWorkspace:
    """Prepared network, snapped events, and measured lixel support.

    A workspace is deliberately estimator-independent. Multiple future NKDE,
    heat-kernel, or temporal-network estimators can reuse the same topology,
    snapping decisions, and lixel partition.
    """

    network: LinearNetwork
    snap_result: SnapResult
    lixels: LixelSupport

    def __post_init__(self) -> None:
        if not isinstance(self.network, LinearNetwork):
            raise TypeError("network must be a LinearNetwork instance.")
        if not isinstance(self.snap_result, SnapResult):
            raise TypeError("snap_result must be a SnapResult instance.")
        if not isinstance(self.lixels, LixelSupport):
            raise TypeError("lixels must be a LixelSupport instance.")
        self.validate().raise_for_errors()

    @property
    def events(self) -> NetworkEvents | None:
        """Accepted snapped events."""
        return self.snap_result.events

    @property
    def fingerprint(self) -> str:
        """Deterministic fingerprint of all reusable prepared assets."""
        return stable_fingerprint(
            self.network.fingerprint,
            None if self.events is None else self.events.fingerprint,
            self.lixels.fingerprint,
            dict(self.snap_result.parameters),
        )

    def validate(self) -> DataValidationReport:
        """Validate all workspace components against the same network."""
        report = self.network.validate()
        report = report.combine(self.lixels.validate(self.network))
        if self.events is not None:
            report = report.combine(self.events.validate(self.network))
        return report

    def summary(self) -> dict[str, Any]:
        """Return a compact serializable workspace summary."""
        validation = self.validate()
        return {
            "n_nodes": self.network.n_nodes,
            "n_edges": self.network.n_edges,
            "n_events": 0 if self.events is None else self.events.n_events,
            "n_rejected": self.snap_result.n_rejected,
            "n_lixels": self.lixels.n_lixels,
            "total_length": self.network.total_length,
            "valid": validation.valid,
            "n_warnings": len(validation.warnings),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def prepare(
        cls,
        network: LinearNetwork,
        events: SpatialEvents,
        *,
        lixel_length: float,
        max_snap_distance: float | None = None,
        tie_tolerance: float = 1e-9,
        endpoint_tolerance: float = 1e-9,
    ) -> "NetworkWorkspace":
        """Snap events and construct lixels once for later estimator reuse."""
        snapped = snap_events(
            network,
            events,
            max_distance=max_snap_distance,
            tie_tolerance=tie_tolerance,
            endpoint_tolerance=endpoint_tolerance,
        )
        lixels = LixelSupport.from_network(network, length=lixel_length)
        return cls(network=network, snap_result=snapped, lixels=lixels)
