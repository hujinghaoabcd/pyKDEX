# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Fixed, selected, and event-specific bandwidths for NetworkKDE."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from pykdex.core.results import BandwidthSelectionResult
from pykdex.kernels import BaseKernel
from pykdex.network.distance import (
    NetworkDistanceAsset,
    NetworkLocations,
    build_event_event_distances,
)
from pykdex.network.propagation import JunctionPolicy
from pykdex.network.workspace import NetworkWorkspace
from pykdex.selection.network import NetworkLeastSquaresCV, NetworkLikelihoodCV


class BaseNetworkBandwidth(ABC):
    """Strategy resolving one scalar or one bandwidth per network event."""

    @abstractmethod
    def resolve(
        self,
        workspace: NetworkWorkspace,
        *,
        kernel: BaseKernel,
        junction_policy: str | JunctionPolicy,
        directed: bool | None,
        coefficient_tolerance: float,
        max_records_per_event: int,
    ) -> float | np.ndarray:
        """Resolve bandwidth values for a prepared network workspace."""


class FixedNetworkBandwidth(BaseNetworkBandwidth):
    """Use one positive bandwidth for every network event."""

    def __init__(self, value: float | int | np.floating) -> None:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError("bandwidth must not be boolean.")
        numeric = float(value)
        if not np.isfinite(numeric) or numeric <= 0.0:
            raise ValueError("bandwidth must be finite and positive.")
        self.value = numeric

    def resolve(
        self,
        workspace: NetworkWorkspace,
        *,
        kernel: BaseKernel,
        junction_policy: str | JunctionPolicy,
        directed: bool | None,
        coefficient_tolerance: float,
        max_records_per_event: int,
    ) -> float:
        if not isinstance(workspace, NetworkWorkspace):
            raise TypeError("workspace must be a NetworkWorkspace instance.")
        return self.value


class NetworkKNNBandwidth(BaseNetworkBandwidth):
    """Use each event's network distance to its k-th other event."""

    def __init__(
        self,
        k: int,
        *,
        multiplier: float = 1.0,
        minimum_bandwidth: float | None = None,
    ) -> None:
        if isinstance(k, (bool, np.bool_)) or not isinstance(k, (int, np.integer)):
            raise TypeError("k must be a positive integer.")
        if int(k) <= 0:
            raise ValueError("k must be greater than zero.")
        multiplier_value = float(multiplier)
        if not np.isfinite(multiplier_value) or multiplier_value <= 0.0:
            raise ValueError("multiplier must be finite and positive.")
        if minimum_bandwidth is not None:
            floor = float(minimum_bandwidth)
            if not np.isfinite(floor) or floor <= 0.0:
                raise ValueError("minimum_bandwidth must be finite and positive.")
        else:
            floor = None
        self.k = int(k)
        self.multiplier = multiplier_value
        self.minimum_bandwidth = floor
        self.distance_asset_: Optional[NetworkDistanceAsset] = None

    def resolve(
        self,
        workspace: NetworkWorkspace,
        *,
        kernel: BaseKernel,
        junction_policy: str | JunctionPolicy,
        directed: bool | None,
        coefficient_tolerance: float,
        max_records_per_event: int,
    ) -> np.ndarray:
        events = workspace.events
        if events is None:
            raise ValueError("workspace contains no accepted network events.")
        if events.n_events < 2:
            raise ValueError("network kNN bandwidth requires at least two events.")
        if self.k > events.n_events - 1:
            raise ValueError(f"k cannot exceed n_events - 1 = {events.n_events - 1}.")
        if directed is not None and not isinstance(directed, (bool, np.bool_)):
            raise TypeError("directed must be boolean or None.")
        effective_directed = bool(
            workspace.network.directed
            if directed is None
            else bool(directed) and workspace.network.directed
        )
        locations = NetworkLocations.from_events(events)
        asset = workspace.event_distance_asset
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
                events,
                weight="length",
                directed=effective_directed,
            )
        self.distance_asset_ = asset
        distances = asset.to_dense()
        np.fill_diagonal(distances, np.inf)
        kth = np.partition(distances, self.k - 1, axis=1)[:, self.k - 1]
        bandwidths = kth * self.multiplier
        if self.minimum_bandwidth is not None:
            bandwidths = np.maximum(bandwidths, self.minimum_bandwidth)
        if not np.all(np.isfinite(bandwidths)):
            raise ValueError(
                "some events cannot reach the requested k-th network neighbour; "
                "reduce k, use an undirected metric, or restrict events to compatible "
                "components."
            )
        if np.any(bandwidths <= 0.0):
            raise ValueError(
                "network kNN produced non-positive bandwidths, usually because of "
                "duplicate event locations. Set minimum_bandwidth to a meaningful "
                "network-distance floor."
            )
        owned = np.ascontiguousarray(bandwidths, dtype=float)
        owned.setflags(write=False)
        return owned


class NetworkLikelihoodCVBandwidth(BaseNetworkBandwidth):
    """Resolve one scalar bandwidth by network leave-one-out likelihood."""

    def __init__(
        self,
        *,
        bounds: tuple[float, float] | None = None,
        tolerance: float = 1e-5,
        maxiter: int = 200,
        density_floor: float = 1e-300,
    ) -> None:
        self.selector = NetworkLikelihoodCV(
            bounds=bounds,
            tolerance=tolerance,
            maxiter=maxiter,
            density_floor=density_floor,
        )
        self.result_: Optional[BandwidthSelectionResult] = None

    def resolve(
        self,
        workspace: NetworkWorkspace,
        *,
        kernel: BaseKernel,
        junction_policy: str | JunctionPolicy,
        directed: bool | None,
        coefficient_tolerance: float,
        max_records_per_event: int,
    ) -> float:
        self.result_ = self.selector.select(
            workspace,
            kernel=kernel,
            junction_policy=junction_policy,
            directed=directed,
            coefficient_tolerance=coefficient_tolerance,
            max_records_per_event=max_records_per_event,
        )
        return self.result_.bandwidth


class NetworkLeastSquaresCVBandwidth(BaseNetworkBandwidth):
    """Resolve one scalar bandwidth by lixel-integrated network LSCV."""

    def __init__(
        self,
        *,
        bounds: tuple[float, float] | None = None,
        tolerance: float = 1e-5,
        maxiter: int = 200,
    ) -> None:
        self.selector = NetworkLeastSquaresCV(
            bounds=bounds,
            tolerance=tolerance,
            maxiter=maxiter,
        )
        self.result_: Optional[BandwidthSelectionResult] = None

    def resolve(
        self,
        workspace: NetworkWorkspace,
        *,
        kernel: BaseKernel,
        junction_policy: str | JunctionPolicy,
        directed: bool | None,
        coefficient_tolerance: float,
        max_records_per_event: int,
    ) -> float:
        self.result_ = self.selector.select(
            workspace,
            kernel=kernel,
            junction_policy=junction_policy,
            directed=directed,
            coefficient_tolerance=coefficient_tolerance,
            max_records_per_event=max_records_per_event,
        )
        return self.result_.bandwidth


def get_network_bandwidth(
    bandwidth: float | int | np.floating | BaseNetworkBandwidth,
) -> BaseNetworkBandwidth:
    """Resolve a numeric or network-specific bandwidth strategy."""
    if isinstance(bandwidth, BaseNetworkBandwidth):
        return bandwidth
    return FixedNetworkBandwidth(bandwidth)
