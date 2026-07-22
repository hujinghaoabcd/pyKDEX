# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Reusable prepared assets for network analysis.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from pykdex.data import SpatialEvents
from pykdex.data._utils import stable_fingerprint
from pykdex.data.validation import DataValidationReport
from pykdex.network.distance import (
    NetworkDistanceAsset,
    NetworkLocations,
    build_event_event_distances,
    build_event_lixel_distances,
)
from pykdex.network.events import NetworkEvents, SnapResult, snap_events
from pykdex.network.linear_network import LinearNetwork
from pykdex.network.support import LixelSupport


@dataclass(frozen=True)
class NetworkWorkspace:
    """Prepared network, snapped events, lixels, and optional distances.

    A workspace is deliberately estimator-independent. Multiple future NKDE,
    heat-kernel, or temporal-network estimators can reuse the same topology,
    snapping decisions, lixel partition, and sparse distance neighbourhoods.
    """

    network: LinearNetwork
    snap_result: SnapResult
    lixels: LixelSupport
    distance_asset: NetworkDistanceAsset | None = None
    event_distance_asset: NetworkDistanceAsset | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.network, LinearNetwork):
            raise TypeError("network must be a LinearNetwork instance.")
        if not isinstance(self.snap_result, SnapResult):
            raise TypeError("snap_result must be a SnapResult instance.")
        if not isinstance(self.lixels, LixelSupport):
            raise TypeError("lixels must be a LixelSupport instance.")
        if self.distance_asset is not None and not isinstance(
            self.distance_asset, NetworkDistanceAsset
        ):
            raise TypeError("distance_asset must be NetworkDistanceAsset or None.")
        if self.event_distance_asset is not None and not isinstance(
            self.event_distance_asset, NetworkDistanceAsset
        ):
            raise TypeError(
                "event_distance_asset must be NetworkDistanceAsset or None."
            )
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
            None if self.distance_asset is None else self.distance_asset.fingerprint,
            (
                None
                if self.event_distance_asset is None
                else self.event_distance_asset.fingerprint
            ),
            dict(self.snap_result.parameters),
        )

    def validate(self) -> DataValidationReport:
        """Validate all workspace components against the same network."""
        report = self.network.validate()
        report = report.combine(self.lixels.validate(self.network))
        if self.events is not None:
            report = report.combine(self.events.validate(self.network))
        if self.distance_asset is not None:
            sources = None
            if self.events is not None:
                sources = NetworkLocations.from_events(self.events)
            targets = NetworkLocations.from_lixels(self.lixels)
            report = report.combine(
                self.distance_asset.validate(
                    self.network,
                    sources=sources,
                    targets=targets,
                )
            )
        if self.event_distance_asset is not None:
            locations = None
            if self.events is not None:
                locations = NetworkLocations.from_events(self.events)
            report = report.combine(
                self.event_distance_asset.validate(
                    self.network,
                    sources=locations,
                    targets=locations,
                )
            )
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
            "n_distance_pairs": (
                0 if self.distance_asset is None else self.distance_asset.n_pairs
            ),
            "distance_cutoff": (
                None if self.distance_asset is None else self.distance_asset.cutoff
            ),
            "n_event_distance_pairs": (
                0
                if self.event_distance_asset is None
                else self.event_distance_asset.n_pairs
            ),
            "event_distance_cutoff": (
                None
                if self.event_distance_asset is None
                else self.event_distance_asset.cutoff
            ),
            "valid": validation.valid,
            "n_warnings": len(validation.warnings),
            "fingerprint": self.fingerprint,
        }

    def with_event_lixel_distances(
        self,
        *,
        cutoff: float | None = None,
        weight: str = "length",
        directed: bool | None = None,
    ) -> "NetworkWorkspace":
        """Return a workspace with exact event-to-lixel distance assets."""
        if self.events is None:
            raise ValueError("Cannot build distances without accepted network events.")
        asset = build_event_lixel_distances(
            self.network,
            self.events,
            self.lixels,
            cutoff=cutoff,
            weight=weight,
            directed=directed,
        )
        return replace(self, distance_asset=asset)

    def with_event_event_distances(
        self,
        *,
        cutoff: float | None = None,
        weight: str = "length",
        directed: bool | None = None,
    ) -> "NetworkWorkspace":
        """Return a workspace with exact event-to-event distance assets."""
        if self.events is None:
            raise ValueError("Cannot build distances without accepted network events.")
        asset = build_event_event_distances(
            self.network,
            self.events,
            cutoff=cutoff,
            weight=weight,
            directed=directed,
        )
        return replace(self, event_distance_asset=asset)

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
