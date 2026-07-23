# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Factorized network-distance and temporal-offset assets."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pykdex.data._utils import readonly_array, stable_fingerprint
from pykdex.network.distance import (
    NetworkDistanceAsset,
    NetworkLocations,
    build_event_lixel_distances,
)
from pykdex.network.workspace import NetworkWorkspace
from pykdex.network_time.events import NetworkTimeEvents
from pykdex.network_time.support import ArixelSupport


@dataclass(frozen=True)
class NetworkTimeDistanceAsset:
    """Factorized event-lixel network distances and time-event offsets."""

    network_distances: NetworkDistanceAsset
    temporal_offsets: np.ndarray
    temporal_distances: np.ndarray
    event_fingerprint: str
    support_fingerprint: str
    time_domain_fingerprint: str
    workspace_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.network_distances, NetworkDistanceAsset):
            raise TypeError("network_distances must be NetworkDistanceAsset.")
        offsets = readonly_array(
            self.temporal_offsets,
            dtype=float,
            ndim=2,
            name="temporal_offsets",
        )
        distances = readonly_array(
            self.temporal_distances,
            dtype=float,
            ndim=2,
            name="temporal_distances",
        )
        if offsets.shape != distances.shape:
            raise ValueError("temporal offsets and distances must have one shape.")
        if (
            offsets.size == 0
            or not np.all(np.isfinite(offsets))
            or not np.all(np.isfinite(distances))
            or np.any(distances < 0.0)
        ):
            raise ValueError("temporal arrays must contain finite valid values.")
        if offsets.shape[1] != self.network_distances.shape[0]:
            raise ValueError(
                "temporal source count must match network-distance sources."
            )
        for value, name in (
            (self.event_fingerprint, "event_fingerprint"),
            (self.support_fingerprint, "support_fingerprint"),
            (self.time_domain_fingerprint, "time_domain_fingerprint"),
            (self.workspace_fingerprint, "workspace_fingerprint"),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty string.")
        object.__setattr__(self, "temporal_offsets", offsets)
        object.__setattr__(self, "temporal_distances", distances)

    @property
    def n_times(self) -> int:
        """Number of distinct target time cells."""
        return int(self.temporal_offsets.shape[0])

    @property
    def n_events(self) -> int:
        """Number of source events."""
        return int(self.temporal_offsets.shape[1])

    @property
    def n_lixels(self) -> int:
        """Number of spatial target lixels."""
        return self.network_distances.shape[1]

    @property
    def arixel_shape(self) -> tuple[int, int]:
        """Time-by-lixel output shape."""
        return (self.n_times, self.n_lixels)

    @property
    def fingerprint(self) -> str:
        """Deterministic factorized asset fingerprint."""
        return stable_fingerprint(
            self.network_distances.fingerprint,
            self.temporal_offsets,
            self.temporal_distances,
            self.event_fingerprint,
            self.support_fingerprint,
            self.time_domain_fingerprint,
            self.workspace_fingerprint,
        )

    def validate_for(
        self,
        network_workspace: NetworkWorkspace,
        events: NetworkTimeEvents,
        support: ArixelSupport,
        *,
        directed: bool,
    ) -> None:
        """Raise when this asset does not match a network-time workspace."""
        sources = NetworkLocations.from_events(events.network_events)
        targets = NetworkLocations.from_lixels(support.lixels)
        self.network_distances.validate(
            network_workspace.network,
            sources=sources,
            targets=targets,
        ).raise_for_errors()
        if self.network_distances.weight != "length":
            raise ValueError("network-time assets require length-weighted distance.")
        if self.network_distances.directed != directed:
            raise ValueError("network-time asset directed mode does not match.")
        if self.event_fingerprint != events.fingerprint:
            raise ValueError("network-time asset event fingerprint does not match.")
        if self.support_fingerprint != support.fingerprint:
            raise ValueError("network-time asset support fingerprint does not match.")
        if self.time_domain_fingerprint != events.temporal.domain.fingerprint:
            raise ValueError("network-time asset time domain does not match.")
        if self.workspace_fingerprint != network_workspace.fingerprint:
            raise ValueError("network-time asset base workspace does not match.")
        if self.arixel_shape != support.shape:
            raise ValueError("network-time asset shape does not match support.")


def build_network_time_distance_asset(
    network_workspace: NetworkWorkspace,
    events: NetworkTimeEvents,
    support: ArixelSupport,
    *,
    cutoff: float | None = None,
    directed: bool | None = None,
) -> NetworkTimeDistanceAsset:
    """Build factorized reusable network and temporal distances."""
    if not isinstance(network_workspace, NetworkWorkspace):
        raise TypeError("network_workspace must be NetworkWorkspace.")
    if not isinstance(events, NetworkTimeEvents):
        raise TypeError("events must be NetworkTimeEvents.")
    if not isinstance(support, ArixelSupport):
        raise TypeError("support must be ArixelSupport.")
    if directed is not None and not isinstance(directed, (bool, np.bool_)):
        raise TypeError("directed must be boolean or None.")
    network_workspace.validate().raise_for_errors()
    if network_workspace.events is None:
        raise ValueError("network workspace contains no accepted events.")
    if events.network_events.fingerprint != network_workspace.events.fingerprint:
        raise ValueError("network-time events do not match base workspace events.")
    if support.lixels.fingerprint != network_workspace.lixels.fingerprint:
        raise ValueError("arixel lixels do not match base workspace lixels.")
    if support.temporal.temporal_unit != events.temporal.temporal_unit:
        raise ValueError("event and support temporal units must match.")
    if support.temporal.domain.fingerprint != events.temporal.domain.fingerprint:
        raise ValueError("event and support time domains must match.")
    if support.temporal.temporal_origin != events.temporal.temporal_origin:
        raise ValueError("event and support temporal origins must match.")
    if support.temporal.timezone != events.temporal.timezone:
        raise ValueError("event and support timezones must match.")
    effective_directed = bool(
        network_workspace.network.directed
        if directed is None
        else bool(directed) and network_workspace.network.directed
    )
    network_asset = build_event_lixel_distances(
        network_workspace.network,
        events.network_events,
        support.lixels,
        cutoff=cutoff,
        weight="length",
        directed=effective_directed,
    )
    offsets = support.time_centers[:, None] - events.times[None, :]
    return NetworkTimeDistanceAsset(
        network_distances=network_asset,
        temporal_offsets=offsets,
        temporal_distances=events.temporal.domain.distances_from_offsets(offsets),
        event_fingerprint=events.fingerprint,
        support_fingerprint=support.fingerprint,
        time_domain_fingerprint=events.temporal.domain.fingerprint,
        workspace_fingerprint=network_workspace.fingerprint,
    )
