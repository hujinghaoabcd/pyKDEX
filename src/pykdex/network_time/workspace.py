# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Reusable prepared assets for temporal network estimation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from os import PathLike
from pathlib import Path
from typing import Any

import numpy as np

from pykdex.data import DataProvenance, SpatialEvents, TemporalCoordinates
from pykdex.data._utils import stable_fingerprint
from pykdex.data.validation import DataIssue, DataValidationReport
from pykdex.network import LinearNetwork, LixelSupport, NetworkWorkspace
from pykdex.network_time.distance import (
    NetworkTimeDistanceAsset,
    build_network_time_distance_asset,
)
from pykdex.network_time.events import NetworkTimeEvents
from pykdex.network_time.support import ArixelSupport
from pykdex.temporal import BaseTimeDomain


@dataclass(frozen=True)
class NetworkTimeWorkspace:
    """Prepared network, accepted event times, arixels, and distances."""

    network_workspace: NetworkWorkspace
    events: NetworkTimeEvents
    arixels: ArixelSupport
    distance_asset: NetworkTimeDistanceAsset | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.network_workspace, NetworkWorkspace):
            raise TypeError("network_workspace must be NetworkWorkspace.")
        if not isinstance(self.events, NetworkTimeEvents):
            raise TypeError("events must be NetworkTimeEvents.")
        if not isinstance(self.arixels, ArixelSupport):
            raise TypeError("arixels must be ArixelSupport.")
        if self.distance_asset is not None and not isinstance(
            self.distance_asset, NetworkTimeDistanceAsset
        ):
            raise TypeError("distance_asset must be NetworkTimeDistanceAsset or None.")
        self.validate().raise_for_errors()

    @property
    def network(self) -> LinearNetwork:
        """Canonical network."""
        return self.network_workspace.network

    @property
    def lixels(self) -> LixelSupport:
        """Measured lixel support."""
        return self.network_workspace.lixels

    @property
    def fingerprint(self) -> str:
        """Deterministic fingerprint of all prepared network-time assets."""
        return stable_fingerprint(
            self.network_workspace.fingerprint,
            self.events.fingerprint,
            self.arixels.fingerprint,
            (None if self.distance_asset is None else self.distance_asset.fingerprint),
        )

    def validate(self) -> DataValidationReport:
        """Validate network, event, lixel, time, and optional distance identity."""
        report = self.network_workspace.validate()
        report = report.combine(self.events.validate(self.network))
        issues = list(report.issues)
        base_events = self.network_workspace.events
        if base_events is None:
            issues.append(
                DataIssue(
                    "error",
                    "missing_network_events",
                    "Base network workspace contains no accepted events.",
                )
            )
        elif base_events.fingerprint != self.events.network_events.fingerprint:
            issues.append(
                DataIssue(
                    "error",
                    "event_fingerprint_mismatch",
                    "Network-time events differ from base accepted events.",
                )
            )
        if self.arixels.lixels.fingerprint != self.network_workspace.lixels.fingerprint:
            issues.append(
                DataIssue(
                    "error",
                    "lixel_fingerprint_mismatch",
                    "Arixels use a different lixel partition.",
                )
            )
        support_time = self.arixels.temporal
        if support_time.temporal_unit != self.events.temporal.temporal_unit:
            issues.append(
                DataIssue(
                    "error",
                    "temporal_unit_mismatch",
                    "Event and arixel temporal units differ.",
                )
            )
        if support_time.domain.fingerprint != self.events.temporal.domain.fingerprint:
            issues.append(
                DataIssue(
                    "error",
                    "time_domain_mismatch",
                    "Event and arixel time domains differ.",
                )
            )
        if support_time.temporal_origin != self.events.temporal.temporal_origin:
            issues.append(
                DataIssue(
                    "error",
                    "temporal_origin_mismatch",
                    "Event and arixel temporal origins differ.",
                )
            )
        if support_time.timezone != self.events.temporal.timezone:
            issues.append(
                DataIssue(
                    "error",
                    "timezone_mismatch",
                    "Event and arixel timezones differ.",
                )
            )
        combined = DataValidationReport(
            tuple(issues),
            {
                **dict(report.statistics),
                "n_arixels": self.arixels.n_arixels,
                "n_times": self.arixels.n_times,
                "arixel_total_measure": self.arixels.total_measure,
            },
        )
        if self.distance_asset is not None and not combined.errors:
            try:
                self.distance_asset.validate_for(
                    self.network_workspace,
                    self.events,
                    self.arixels,
                    directed=self.distance_asset.network_distances.directed,
                )
            except ValueError as exc:
                combined = combined.combine(
                    DataValidationReport(
                        (
                            DataIssue(
                                "error",
                                "distance_asset_mismatch",
                                str(exc),
                            ),
                        )
                    )
                )
        return combined

    def summary(self) -> dict[str, Any]:
        """Return a compact serializable workspace summary."""
        report = self.validate()
        return {
            "n_nodes": self.network.n_nodes,
            "n_edges": self.network.n_edges,
            "n_events": self.events.n_events,
            "n_lixels": self.arixels.lixels.n_lixels,
            "n_times": self.arixels.n_times,
            "n_arixels": self.arixels.n_arixels,
            "total_measure": self.arixels.total_measure,
            "has_distance_asset": self.distance_asset is not None,
            "valid": report.valid,
            "n_warnings": len(report.warnings),
            "fingerprint": self.fingerprint,
        }

    def save(
        self,
        path: str | PathLike[str],
        *,
        format: str = "archive",
        overwrite: bool = False,
    ) -> Path:
        """Persist this workspace as a checksummed directory or ZIP archive."""
        from pykdex.persistence import save_network_time_workspace

        return save_network_time_workspace(
            self,
            path,
            format=format,
            overwrite=overwrite,
        )

    @classmethod
    def load(
        cls,
        path: str | PathLike[str],
        *,
        max_payload_bytes: int = 1_073_741_824,
    ) -> "NetworkTimeWorkspace":
        """Load and validate a persisted temporal-network workspace."""
        from pykdex.persistence import load_network_time_workspace

        return load_network_time_workspace(
            path,
            max_payload_bytes=max_payload_bytes,
        )

    def with_distances(
        self,
        *,
        cutoff: float | None = None,
        directed: bool | None = None,
    ) -> "NetworkTimeWorkspace":
        """Return a workspace with factorized event-lixel/time distances."""
        asset = build_network_time_distance_asset(
            self.network_workspace,
            self.events,
            self.arixels,
            cutoff=cutoff,
            directed=directed,
        )
        return replace(self, distance_asset=asset)

    @classmethod
    def from_network_workspace(
        cls,
        workspace: NetworkWorkspace,
        temporal: TemporalCoordinates,
        arixels: ArixelSupport,
    ) -> "NetworkTimeWorkspace":
        """Pair an existing prepared network workspace with accepted times."""
        if not isinstance(workspace, NetworkWorkspace):
            raise TypeError("workspace must be NetworkWorkspace.")
        if workspace.events is None:
            raise ValueError("workspace contains no accepted events.")
        return cls(
            network_workspace=workspace,
            events=NetworkTimeEvents(workspace.events, temporal),
            arixels=arixels,
        )

    @classmethod
    def prepare(
        cls,
        network: LinearNetwork,
        spatial_events: SpatialEvents,
        times: Any,
        *,
        temporal_unit: str,
        lixel_length: float,
        temporal_resolution: float,
        temporal_bounds: tuple[float, float] | None = None,
        time_domain: BaseTimeDomain | None = None,
        temporal_origin: str | None = None,
        timezone: str | None = None,
        max_snap_distance: float | None = None,
        tie_tolerance: float = 1e-9,
        endpoint_tolerance: float = 1e-9,
        provenance: DataProvenance | None = None,
    ) -> "NetworkTimeWorkspace":
        """Snap raw events, retain accepted times, and construct arixels."""
        if not isinstance(spatial_events, SpatialEvents):
            raise TypeError("spatial_events must be SpatialEvents.")
        record = provenance or DataProvenance()
        temporal = TemporalCoordinates.from_array(
            times,
            domain=time_domain,
            temporal_unit=temporal_unit,
            temporal_origin=temporal_origin,
            timezone=timezone,
            provenance=record,
        )
        if temporal.n_times != spatial_events.n_events:
            raise ValueError("times must contain one value per raw spatial event.")
        workspace = NetworkWorkspace.prepare(
            network,
            spatial_events,
            lixel_length=lixel_length,
            max_snap_distance=max_snap_distance,
            tie_tolerance=tie_tolerance,
            endpoint_tolerance=endpoint_tolerance,
        )
        if workspace.events is None:
            raise ValueError("no raw events were accepted by network snapping.")
        assert spatial_events.ids is not None
        raw_indices = {
            repr(event_id): index
            for index, event_id in enumerate(spatial_events.ids.tolist())
        }
        accepted_indices = np.asarray(
            [
                raw_indices[repr(event_id)]
                for event_id in workspace.events.event_ids.tolist()
            ],
            dtype=np.int64,
        )
        accepted_temporal = TemporalCoordinates(
            values=temporal.values[accepted_indices],
            domain=temporal.domain,
            temporal_unit=temporal.temporal_unit,
            temporal_origin=temporal.temporal_origin,
            timezone=temporal.timezone,
            provenance=temporal.provenance,
        )
        arixels = ArixelSupport.from_lixels(
            workspace.lixels,
            temporal_resolution=temporal_resolution,
            temporal_unit=temporal.temporal_unit,
            time_domain=temporal.domain,
            temporal_bounds=temporal_bounds,
            temporal_origin=temporal.temporal_origin,
            timezone=temporal.timezone,
            provenance=record,
        )
        return cls(
            network_workspace=workspace,
            events=NetworkTimeEvents(
                workspace.events, accepted_temporal, provenance=record
            ),
            arixels=arixels,
        )
