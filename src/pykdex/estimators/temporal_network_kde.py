# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Separable product-kernel estimation on a linear network and time."""

from __future__ import annotations

from typing import Optional

import numpy as np

from pykdex.bandwidths.network_time import (
    NetworkTimeBandwidths,
    NetworkTimeKNNBandwidth,
)
from pykdex.core.base import BaseKDE
from pykdex.core.network_time_results import NetworkTimeField
from pykdex.kernels import BaseKernel, get_kernel
from pykdex.network import NetworkLocations
from pykdex.network.evaluation import (
    evaluate_distance_kernel_matrix,
    evaluate_propagation_kernel_matrix,
)
from pykdex.network.propagation import (
    JunctionPolicy,
    PropagationTrace,
    get_junction_policy,
    trace_network_propagation,
)
from pykdex.network_time import (
    NetworkTimeDistanceAsset,
    NetworkTimeWorkspace,
    build_network_time_distance_asset,
)
from pykdex.spatiotemporal import evaluate_temporal_kernel


class TemporalNetworkKDE(BaseKDE):
    r"""Fixed or sample-point adaptive KDE on a linear network and time.

    The spatial factor follows the selected network junction policy. The
    temporal factor follows the event time domain, including normalized
    periodic image sums for cyclic time.
    """

    def __init__(
        self,
        spatial_bandwidth: float | np.ndarray = 1.0,
        temporal_bandwidth: float | np.ndarray = 1.0,
        *,
        bandwidths: NetworkTimeBandwidths | NetworkTimeKNNBandwidth | None = None,
        spatial_kernel: str | BaseKernel = "epanechnikov",
        temporal_kernel: str | BaseKernel = "gaussian",
        junction_policy: str | JunctionPolicy = "continuous",
        target: str = "density",
        directed: bool | None = None,
        time_chunk_size: Optional[int] = None,
        cyclic_tail_tolerance: float = 1e-12,
        coefficient_tolerance: float = 1e-12,
        max_records_per_event: int = 100_000,
        store_propagation: bool = False,
        random_state: Optional[int] = None,
        verbose: bool = False,
    ) -> None:
        super().__init__(target=target, random_state=random_state, verbose=verbose)
        fixed_bandwidths = NetworkTimeBandwidths(
            spatial=spatial_bandwidth,
            temporal=temporal_bandwidth,
        )
        if bandwidths is not None and not isinstance(
            bandwidths, (NetworkTimeBandwidths, NetworkTimeKNNBandwidth)
        ):
            raise TypeError(
                "bandwidths must be NetworkTimeBandwidths, "
                "NetworkTimeKNNBandwidth, or None."
            )
        self.spatial_bandwidth = fixed_bandwidths.spatial
        self.temporal_bandwidth = fixed_bandwidths.temporal
        self.bandwidths = bandwidths
        if directed is not None and not isinstance(directed, (bool, np.bool_)):
            raise TypeError("directed must be boolean or None.")
        if time_chunk_size is not None:
            if isinstance(time_chunk_size, (bool, np.bool_)) or not isinstance(
                time_chunk_size, (int, np.integer)
            ):
                raise TypeError("time_chunk_size must be a positive integer or None.")
            if int(time_chunk_size) <= 0:
                raise ValueError("time_chunk_size must be greater than zero.")
        tolerance = float(cyclic_tail_tolerance)
        coefficient = float(coefficient_tolerance)
        if not np.isfinite(tolerance) or not 0.0 < tolerance < 1.0:
            raise ValueError(
                "cyclic_tail_tolerance must lie strictly between zero and one."
            )
        if not np.isfinite(coefficient) or coefficient <= 0.0:
            raise ValueError("coefficient_tolerance must be finite and positive.")
        if isinstance(max_records_per_event, bool) or not isinstance(
            max_records_per_event, (int, np.integer)
        ):
            raise TypeError("max_records_per_event must be a positive integer.")
        if int(max_records_per_event) <= 0:
            raise ValueError("max_records_per_event must be greater than zero.")
        if not isinstance(store_propagation, (bool, np.bool_)):
            raise TypeError("store_propagation must be boolean.")
        self.spatial_kernel = spatial_kernel
        self.temporal_kernel = temporal_kernel
        self.junction_policy = junction_policy
        self.directed = None if directed is None else bool(directed)
        self.time_chunk_size = None if time_chunk_size is None else int(time_chunk_size)
        self.cyclic_tail_tolerance = tolerance
        self.coefficient_tolerance = coefficient
        self.max_records_per_event = int(max_records_per_event)
        self.store_propagation = bool(store_propagation)
        self._reset_fit_state()

    def _reset_fit_state(self) -> None:
        self._mark_unfitted()
        self._reset_common_state()
        self.workspace_: NetworkTimeWorkspace | None = None
        self.spatial_kernel_: BaseKernel | None = None
        self.temporal_kernel_: BaseKernel | None = None
        self.junction_policy_: JunctionPolicy | None = None
        self.directed_: bool | None = None
        self.distance_asset_: NetworkTimeDistanceAsset | None = None
        self.propagation_traces_: tuple[PropagationTrace, ...] | None = None
        self.network_time_bandwidths_: NetworkTimeBandwidths | None = None
        self.values_: np.ndarray | None = None

    @staticmethod
    def _asset_usable(
        asset: NetworkTimeDistanceAsset | None,
        workspace: NetworkTimeWorkspace,
        *,
        cutoff: float | None,
        directed: bool,
    ) -> bool:
        if asset is None:
            return False
        try:
            asset.validate_for(
                workspace.network_workspace,
                workspace.events,
                workspace.arixels,
                directed=directed,
            )
        except ValueError:
            return False
        network_asset = asset.network_distances
        if cutoff is None:
            return network_asset.cutoff is None
        return network_asset.cutoff is None or network_asset.cutoff >= cutoff - 1e-12

    def fit(self, workspace: NetworkTimeWorkspace) -> "TemporalNetworkKDE":
        """Fit and evaluate a prepared network-time workspace."""
        self._reset_fit_state()
        try:
            if not isinstance(workspace, NetworkTimeWorkspace):
                raise TypeError("workspace must be NetworkTimeWorkspace.")
            workspace.validate().raise_for_errors()
            spatial_kernel = get_kernel(self.spatial_kernel)
            temporal_kernel = get_kernel(self.temporal_kernel)
            policy = get_junction_policy(self.junction_policy)
            effective_directed = bool(
                workspace.network.directed
                if self.directed is None
                else self.directed and workspace.network.directed
            )
            if effective_directed and not policy.supports_directed:
                raise ValueError(
                    f"The '{policy.name}' junction policy requires an undirected "
                    "network."
                )
            if policy.path_based and not spatial_kernel.finite_support:
                raise ValueError(
                    "Path-based TemporalNetworkKDE requires a finite-support "
                    "spatial kernel."
                )
            events = workspace.events
            if isinstance(self.bandwidths, NetworkTimeKNNBandwidth):
                fitted_bandwidths = self.bandwidths.resolve(
                    workspace, directed=effective_directed
                )
            elif isinstance(self.bandwidths, NetworkTimeBandwidths):
                fitted_bandwidths = self.bandwidths
            else:
                fitted_bandwidths = NetworkTimeBandwidths(
                    spatial=self.spatial_bandwidth,
                    temporal=self.temporal_bandwidth,
                )
            fitted_bandwidths.validate_for(events.n_events)
            spatial_bandwidth = fitted_bandwidths.spatial
            temporal_bandwidth = fitted_bandwidths.temporal
            maximum_spatial_bandwidth = float(np.max(spatial_bandwidth))
            traces: tuple[PropagationTrace, ...] | None = None
            distance_asset: NetworkTimeDistanceAsset | None = None
            if policy.path_based:
                traces = tuple(
                    trace_network_propagation(
                        workspace.network,
                        int(events.edge_indices[index]),
                        float(events.offsets[index]),
                        cutoff=maximum_spatial_bandwidth,
                        junction_policy=policy,
                        directed=effective_directed,
                        coefficient_tolerance=self.coefficient_tolerance,
                        max_records=self.max_records_per_event,
                        source_id=events.event_ids[index],
                    )
                    for index in range(events.n_events)
                )
                spatial_matrix = evaluate_propagation_kernel_matrix(
                    traces,
                    NetworkLocations.from_lixels(workspace.arixels.lixels),
                    spatial_kernel,
                    spatial_bandwidth,
                )
                temporal_offsets = (
                    workspace.arixels.time_centers[:, None] - events.times[None, :]
                )
            else:
                cutoff = (
                    maximum_spatial_bandwidth if spatial_kernel.finite_support else None
                )
                distance_asset = workspace.distance_asset
                if not self._asset_usable(
                    distance_asset,
                    workspace,
                    cutoff=cutoff,
                    directed=effective_directed,
                ):
                    distance_asset = build_network_time_distance_asset(
                        workspace.network_workspace,
                        events,
                        workspace.arixels,
                        cutoff=cutoff,
                        directed=effective_directed,
                    )
                assert distance_asset is not None
                spatial_matrix = evaluate_distance_kernel_matrix(
                    distance_asset.network_distances,
                    spatial_kernel,
                    spatial_bandwidth,
                )
                temporal_offsets = distance_asset.temporal_offsets
            temporal_matrix = evaluate_temporal_kernel(
                temporal_offsets,
                domain=events.temporal.domain,
                kernel=temporal_kernel,
                bandwidth=temporal_bandwidth,
                tail_tolerance=self.cyclic_tail_tolerance,
            )
            coefficients = (
                events.weights / events.weight_sum
                if self.target == "density"
                else events.weights
            )
            values_2d = np.empty(workspace.arixels.shape, dtype=float)
            chunk = self.time_chunk_size or workspace.arixels.n_times
            for start in range(0, workspace.arixels.n_times, chunk):
                stop = min(start + chunk, workspace.arixels.n_times)
                values_2d[start:stop] = (
                    temporal_matrix[start:stop] * coefficients[None, :]
                ) @ spatial_matrix
            raw_minimum = float(np.min(values_2d))
            values_2d[values_2d < 0.0] = 0.0
            if not np.all(np.isfinite(values_2d)):
                raise FloatingPointError(
                    "TemporalNetworkKDE produced non-finite values."
                )
            values = np.ascontiguousarray(values_2d.ravel())
            values.setflags(write=False)
            self.workspace_ = workspace
            self.events_ = np.ascontiguousarray(
                events.network_events.coordinates.copy()
            )
            self.weights_ = np.ascontiguousarray(events.weights.copy())
            self.n_events_ = events.n_events
            self.dimension_ = 2
            self.coordinate_names_in_ = np.asarray(
                ["network_distance", "time"], dtype=object
            )
            self.weight_sum_ = events.weight_sum
            if not fitted_bandwidths.adaptive:
                self.bandwidth_ = np.asarray(
                    [spatial_bandwidth, temporal_bandwidth], dtype=float
                )
            else:
                spatial_values = np.broadcast_to(
                    np.asarray(spatial_bandwidth, dtype=float), (events.n_events,)
                )
                temporal_values = np.broadcast_to(
                    np.asarray(temporal_bandwidth, dtype=float), (events.n_events,)
                )
                bandwidth_matrix = np.ascontiguousarray(
                    np.vstack((spatial_values, temporal_values))
                )
                bandwidth_matrix.setflags(write=False)
                self.bandwidth_ = bandwidth_matrix
            self.event_crs_ = events.network_events.crs
            self.spatial_unit_ = events.network_events.spatial_unit
            self.event_fingerprint_ = events.fingerprint
            self.spatial_kernel_ = spatial_kernel
            self.temporal_kernel_ = temporal_kernel
            self.junction_policy_ = policy
            self.directed_ = effective_directed
            self.distance_asset_ = distance_asset
            self.propagation_traces_ = traces if self.store_propagation else None
            self.network_time_bandwidths_ = fitted_bandwidths
            self.values_ = values
            self.fit_metadata_ = {
                "spatial_kernel": spatial_kernel.name,
                "temporal_kernel": temporal_kernel.name,
                "spatial_bandwidth_min": float(np.min(spatial_bandwidth)),
                "spatial_bandwidth_max": float(np.max(spatial_bandwidth)),
                "temporal_bandwidth_min": float(np.min(temporal_bandwidth)),
                "temporal_bandwidth_max": float(np.max(temporal_bandwidth)),
                "spatial_bandwidth": (
                    float(spatial_bandwidth)
                    if not fitted_bandwidths.adaptive_spatial
                    else None
                ),
                "temporal_bandwidth": (
                    float(temporal_bandwidth)
                    if not fitted_bandwidths.adaptive_temporal
                    else None
                ),
                "adaptive_spatial_bandwidth": fitted_bandwidths.adaptive_spatial,
                "adaptive_temporal_bandwidth": fitted_bandwidths.adaptive_temporal,
                "bandwidth_strategy": (
                    "NetworkTimeBandwidths"
                    if self.bandwidths is None
                    else self.bandwidths.__class__.__name__
                ),
                "junction_policy": policy.name,
                "target": self.target,
                "directed": effective_directed,
                "n_events": events.n_events,
                "n_lixels": workspace.arixels.lixels.n_lixels,
                "n_times": workspace.arixels.n_times,
                "n_arixels": workspace.arixels.n_arixels,
                "time_domain": events.temporal.domain.name,
                "temporal_unit": events.temporal.temporal_unit,
                "network_fingerprint": workspace.network.fingerprint,
                "event_fingerprint": events.fingerprint,
                "support_fingerprint": workspace.arixels.fingerprint,
                "distance_asset_fingerprint": (
                    None if distance_asset is None else distance_asset.fingerprint
                ),
                "path_based": policy.path_based,
                "n_propagation_records": (
                    0 if traces is None else sum(trace.n_records for trace in traces)
                ),
                "raw_minimum_before_clipping": raw_minimum,
            }
            self._mark_fitted()
            return self
        except Exception:
            self._reset_fit_state()
            raise

    def evaluate(self) -> np.ndarray:
        """Return fitted values in time-major arixel order."""
        self._check_is_fitted()
        if self.values_ is None:
            raise RuntimeError("Fitted network-time values are unavailable.")
        return self.values_.copy()

    predict = evaluate

    def predict_result(self) -> NetworkTimeField:
        """Return an immutable measured network-time field."""
        self._check_is_fitted()
        if (
            self.workspace_ is None
            or self.values_ is None
            or self.spatial_kernel_ is None
            or self.temporal_kernel_ is None
            or self.junction_policy_ is None
            or self.directed_ is None
            or self.event_fingerprint_ is None
            or self.network_time_bandwidths_ is None
        ):
            raise RuntimeError("Fitted estimator components are unavailable.")
        return NetworkTimeField(
            values=self.values_,
            support=self.workspace_.arixels,
            spatial_bandwidth=self.network_time_bandwidths_.spatial,
            temporal_bandwidth=self.network_time_bandwidths_.temporal,
            target=self.target,
            spatial_kernel=self.spatial_kernel_.name,
            temporal_kernel=self.temporal_kernel_.name,
            junction_policy=self.junction_policy_.name,
            directed=self.directed_,
            network_fingerprint=self.workspace_.network.fingerprint,
            event_fingerprint=self.event_fingerprint_,
            metadata=dict(self.fit_metadata_ or {}),
        )

    def fit_predict(self, workspace: NetworkTimeWorkspace) -> NetworkTimeField:
        """Fit a workspace and return its measured field."""
        return self.fit(workspace).predict_result()
