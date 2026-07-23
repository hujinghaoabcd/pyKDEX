# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Fixed pairs and event-specific bandwidths for network-time KDE."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

import numpy as np

from pykdex.data._utils import readonly_array
from pykdex.network import (
    NetworkDistanceAsset,
    NetworkLocations,
    build_event_event_distances,
)
from pykdex.network_time import NetworkTimeWorkspace

BandwidthValue: TypeAlias = float | np.ndarray


def _bandwidth_value(value: object, *, name: str) -> BandwidthValue:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must not be boolean.")
    array = np.asarray(value, dtype=float)
    if array.ndim == 0:
        scalar = float(array)
        if not np.isfinite(scalar) or scalar <= 0.0:
            raise ValueError(f"{name} must be finite and positive.")
        return scalar
    array = readonly_array(array, dtype=float, ndim=1, name=name)
    if array.size == 0 or not np.all(np.isfinite(array)) or np.any(array <= 0.0):
        raise ValueError(f"{name} must contain finite positive values.")
    return array


def _validate_event_count(
    value: BandwidthValue,
    n_events: int,
    *,
    name: str,
) -> None:
    if isinstance(value, np.ndarray) and value.shape != (n_events,):
        raise ValueError(f"{name} must contain one value per event.")


@dataclass(frozen=True)
class NetworkTimeBandwidths:
    """Owned spatial and temporal bandwidths for network-time sources."""

    spatial: BandwidthValue
    temporal: BandwidthValue

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "spatial", _bandwidth_value(self.spatial, name="spatial_bandwidth")
        )
        object.__setattr__(
            self, "temporal", _bandwidth_value(self.temporal, name="temporal_bandwidth")
        )

    @property
    def adaptive_spatial(self) -> bool:
        """Whether spatial bandwidth varies by source event."""
        return isinstance(self.spatial, np.ndarray)

    @property
    def adaptive_temporal(self) -> bool:
        """Whether temporal bandwidth varies by source event."""
        return isinstance(self.temporal, np.ndarray)

    @property
    def adaptive(self) -> bool:
        """Whether either bandwidth component varies by source event."""
        return self.adaptive_spatial or self.adaptive_temporal

    def validate_for(self, n_events: int) -> None:
        """Raise when event-specific arrays do not match the source count."""
        _validate_event_count(self.spatial, n_events, name="spatial_bandwidth")
        _validate_event_count(self.temporal, n_events, name="temporal_bandwidth")


class NetworkTimeKNNBandwidth:
    """Resolve independent spatial and temporal kNN sample-point bandwidths."""

    def __init__(
        self,
        spatial_k: int,
        temporal_k: int,
        *,
        spatial_multiplier: float = 1.0,
        temporal_multiplier: float = 1.0,
        minimum_spatial_bandwidth: float | None = None,
        minimum_temporal_bandwidth: float | None = None,
    ) -> None:
        self.spatial_k = self._positive_integer(spatial_k, name="spatial_k")
        self.temporal_k = self._positive_integer(temporal_k, name="temporal_k")
        self.spatial_multiplier = self._positive(
            spatial_multiplier, name="spatial_multiplier"
        )
        self.temporal_multiplier = self._positive(
            temporal_multiplier, name="temporal_multiplier"
        )
        self.minimum_spatial_bandwidth = self._optional_positive(
            minimum_spatial_bandwidth, name="minimum_spatial_bandwidth"
        )
        self.minimum_temporal_bandwidth = self._optional_positive(
            minimum_temporal_bandwidth, name="minimum_temporal_bandwidth"
        )
        self.distance_asset_: NetworkDistanceAsset | None = None

    @staticmethod
    def _positive_integer(value: object, *, name: str) -> int:
        if isinstance(value, (bool, np.bool_)) or not isinstance(
            value, (int, np.integer)
        ):
            raise TypeError(f"{name} must be a positive integer.")
        result = int(value)
        if result <= 0:
            raise ValueError(f"{name} must be greater than zero.")
        return result

    @staticmethod
    def _positive(value: Any, *, name: str) -> float:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError(f"{name} must not be boolean.")
        result = float(value)
        if not np.isfinite(result) or result <= 0.0:
            raise ValueError(f"{name} must be finite and positive.")
        return result

    @classmethod
    def _optional_positive(cls, value: object | None, *, name: str) -> float | None:
        return None if value is None else cls._positive(value, name=name)

    def resolve(
        self,
        workspace: NetworkTimeWorkspace,
        *,
        directed: bool | None = None,
    ) -> NetworkTimeBandwidths:
        """Resolve one spatial and temporal bandwidth per accepted event."""
        if not isinstance(workspace, NetworkTimeWorkspace):
            raise TypeError("workspace must be NetworkTimeWorkspace.")
        if directed is not None and not isinstance(directed, (bool, np.bool_)):
            raise TypeError("directed must be boolean or None.")
        events = workspace.events
        maximum_k = events.n_events - 1
        if maximum_k < 1:
            raise ValueError("network-time kNN bandwidth requires at least two events.")
        if self.spatial_k > maximum_k or self.temporal_k > maximum_k:
            raise ValueError(f"k cannot exceed n_events - 1 = {maximum_k}.")
        effective_directed = bool(
            workspace.network.directed
            if directed is None
            else bool(directed) and workspace.network.directed
        )
        locations = NetworkLocations.from_events(events.network_events)
        asset = workspace.network_workspace.event_distance_asset
        if (
            asset is None
            or asset.source_fingerprint != locations.fingerprint
            or asset.target_fingerprint != locations.fingerprint
            or asset.weight != "length"
            or asset.directed != effective_directed
            or asset.cutoff is not None
        ):
            asset = build_event_event_distances(
                workspace.network,
                events.network_events,
                weight="length",
                directed=effective_directed,
            )
        self.distance_asset_ = asset
        spatial_distances = asset.to_dense()
        np.fill_diagonal(spatial_distances, np.inf)
        spatial = (
            np.partition(spatial_distances, self.spatial_k - 1, axis=1)[
                :, self.spatial_k - 1
            ]
            * self.spatial_multiplier
        )
        temporal_offsets = events.times[None, :] - events.times[:, None]
        temporal_distances = events.temporal.domain.distances_from_offsets(
            temporal_offsets
        )
        np.fill_diagonal(temporal_distances, np.inf)
        temporal = (
            np.partition(temporal_distances, self.temporal_k - 1, axis=1)[
                :, self.temporal_k - 1
            ]
            * self.temporal_multiplier
        )
        if self.minimum_spatial_bandwidth is not None:
            spatial = np.maximum(spatial, self.minimum_spatial_bandwidth)
        if self.minimum_temporal_bandwidth is not None:
            temporal = np.maximum(temporal, self.minimum_temporal_bandwidth)
        if not np.all(np.isfinite(spatial)):
            raise ValueError(
                "some events cannot reach the requested spatial neighbour rank."
            )
        if np.any(spatial <= 0.0):
            raise ValueError(
                "spatial kNN produced non-positive bandwidths; set "
                "minimum_spatial_bandwidth for duplicate network locations."
            )
        if np.any(temporal <= 0.0):
            raise ValueError(
                "temporal kNN produced non-positive bandwidths; set "
                "minimum_temporal_bandwidth for duplicate event times."
            )
        return NetworkTimeBandwidths(spatial=spatial, temporal=temporal)
