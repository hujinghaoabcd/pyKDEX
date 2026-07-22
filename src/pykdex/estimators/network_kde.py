# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Kernel density and intensity estimation on linear networks."""

from __future__ import annotations

from typing import Optional

import numpy as np

from pykdex.bandwidths.network import (
    BaseNetworkBandwidth,
    get_network_bandwidth,
)
from pykdex.core.base import BaseKDE
from pykdex.core.network_results import NetworkField
from pykdex.core.results import BandwidthSelectionResult
from pykdex.kernels import BaseKernel, get_kernel
from pykdex.network.distance import NetworkDistanceAsset
from pykdex.network.evaluation import evaluate_path_kernel, evaluate_simple_kernel
from pykdex.network.events import NetworkEvents
from pykdex.network.propagation import (
    JunctionPolicy,
    PropagationTrace,
    get_junction_policy,
)
from pykdex.network.support import LixelSupport
from pykdex.network.workspace import NetworkWorkspace


class NetworkKDE(BaseKDE):
    r"""Density or intensity estimation on a prepared linear network.

    ``simple`` uses shortest-path distance without splitting mass at vertices.
    ``discontinuous`` uses equal-split non-backtracking propagation.
    ``continuous`` adds signed reflected paths to enforce a common limiting
    value on all incident edges of each undirected vertex.

    The bandwidth may be numeric, selected by network cross-validation, or
    event-specific through :class:`~pykdex.NetworkKNNBandwidth`.

    Args:
        kernel: Normalized one-dimensional radial kernel name or instance.
        bandwidth: Positive numeric bandwidth or network bandwidth strategy.
        junction_policy: Junction policy name or compatible policy object.
        target: ``"density"`` or ``"intensity"``.
        directed: Respect stored edge direction when true.
        coefficient_tolerance: Recursive path-coefficient cutoff.
        max_records_per_event: Safety limit for path records per event.
        store_propagation: Retain complete traces on the fitted estimator.
        random_state: Reserved deterministic random seed.
        verbose: Print estimator progress.
    """

    def __init__(
        self,
        kernel: str | BaseKernel = "epanechnikov",
        bandwidth: float | int | np.floating | BaseNetworkBandwidth = 1.0,
        junction_policy: str | JunctionPolicy = "discontinuous",
        target: str = "density",
        directed: bool | None = None,
        coefficient_tolerance: float = 1e-12,
        max_records_per_event: int = 100_000,
        store_propagation: bool = False,
        random_state: Optional[int] = None,
        verbose: bool = False,
    ) -> None:
        super().__init__(target=target, random_state=random_state, verbose=verbose)
        if not isinstance(bandwidth, BaseNetworkBandwidth):
            if isinstance(bandwidth, (bool, np.bool_)):
                raise TypeError("bandwidth must not be boolean.")
            bandwidth_value = float(bandwidth)
            if not np.isfinite(bandwidth_value) or bandwidth_value <= 0.0:
                raise ValueError("bandwidth must be finite and positive.")
        if directed is not None and not isinstance(directed, (bool, np.bool_)):
            raise TypeError("directed must be boolean or None.")
        coefficient_value = float(coefficient_tolerance)
        if not np.isfinite(coefficient_value) or coefficient_value <= 0.0:
            raise ValueError("coefficient_tolerance must be finite and positive.")
        if isinstance(max_records_per_event, bool) or not isinstance(
            max_records_per_event, (int, np.integer)
        ):
            raise TypeError("max_records_per_event must be a positive integer.")
        record_limit = int(max_records_per_event)
        if record_limit <= 0:
            raise ValueError("max_records_per_event must be greater than zero.")
        if not isinstance(store_propagation, (bool, np.bool_)):
            raise TypeError("store_propagation must be boolean.")
        self.kernel = kernel
        self.bandwidth = bandwidth
        self.junction_policy = junction_policy
        self.directed = None if directed is None else bool(directed)
        self.coefficient_tolerance = coefficient_value
        self.max_records_per_event = record_limit
        self.store_propagation = bool(store_propagation)
        self._reset_fit_state()

    def _reset_fit_state(self) -> None:
        self._mark_unfitted()
        self._reset_common_state()
        self.workspace_: NetworkWorkspace | None = None
        self.network_events_: NetworkEvents | None = None
        self.lixels_: LixelSupport | None = None
        self.kernel_: BaseKernel | None = None
        self.junction_policy_: JunctionPolicy | None = None
        self.directed_: bool | None = None
        self.distance_asset_: NetworkDistanceAsset | None = None
        self.propagation_traces_: tuple[PropagationTrace, ...] | None = None
        self.values_: np.ndarray | None = None
        self.network_bandwidth_strategy_: BaseNetworkBandwidth | None = None
        self.bandwidth_selection_: BandwidthSelectionResult | None = None

    def fit(self, workspace: NetworkWorkspace) -> "NetworkKDE":
        """Fit and evaluate the estimator on a prepared network workspace."""
        self._reset_fit_state()
        try:
            if not isinstance(workspace, NetworkWorkspace):
                raise TypeError("workspace must be a NetworkWorkspace instance.")
            workspace.validate().raise_for_errors()
            events = workspace.events
            if events is None:
                raise ValueError("workspace contains no accepted network events.")
            kernel = get_kernel(self.kernel)
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
            if policy.path_based and not kernel.finite_support:
                raise ValueError(
                    "Path-based NetworkKDE requires a finite-support kernel. "
                    "Use a compact kernel or junction_policy='simple'."
                )

            bandwidth_strategy = get_network_bandwidth(self.bandwidth)
            resolved_bandwidth = bandwidth_strategy.resolve(
                workspace,
                kernel=kernel,
                junction_policy=policy,
                directed=effective_directed,
                coefficient_tolerance=self.coefficient_tolerance,
                max_records_per_event=self.max_records_per_event,
            )
            bandwidth_array = np.asarray(resolved_bandwidth, dtype=float)
            if bandwidth_array.ndim == 0:
                fitted_bandwidth: float | np.ndarray = float(bandwidth_array)
            elif (
                bandwidth_array.ndim == 1
                and bandwidth_array.shape[0] == events.n_events
            ):
                fitted_array = np.ascontiguousarray(bandwidth_array.copy())
                fitted_array.setflags(write=False)
                fitted_bandwidth = fitted_array
            else:
                raise ValueError(
                    "network bandwidth strategy must resolve to one scalar or one "
                    "value per accepted event."
                )
            if not np.all(np.isfinite(np.asarray(fitted_bandwidth))) or np.any(
                np.asarray(fitted_bandwidth) <= 0.0
            ):
                raise ValueError(
                    "resolved network bandwidths must be finite and positive."
                )

            coefficients = (
                events.weights / events.weight_sum
                if self.target == "density"
                else events.weights
            )
            distance_asset: NetworkDistanceAsset | None = None
            traces: tuple[PropagationTrace, ...] | None = None
            if policy.path_based:
                values, traces, raw_minimum, n_records = evaluate_path_kernel(
                    workspace,
                    events,
                    kernel,
                    policy,
                    fitted_bandwidth,
                    coefficients,
                    directed=effective_directed,
                    coefficient_tolerance=self.coefficient_tolerance,
                    max_records_per_event=self.max_records_per_event,
                )
            else:
                values, distance_asset = evaluate_simple_kernel(
                    workspace,
                    events,
                    kernel,
                    fitted_bandwidth,
                    coefficients,
                    directed=effective_directed,
                )
                raw_minimum = float(np.min(values))
                n_records = 0

            values = np.asarray(values, dtype=float)
            if not np.all(np.isfinite(values)):
                raise FloatingPointError(
                    "NetworkKDE evaluation produced non-finite values."
                )
            values[values < 0.0] = 0.0
            owned_values = np.ascontiguousarray(values.copy())
            owned_values.setflags(write=False)

            selection_result = getattr(bandwidth_strategy, "result_", None)
            bandwidth_values = np.atleast_1d(np.asarray(fitted_bandwidth, dtype=float))
            self.workspace_ = workspace
            self.network_events_ = events
            self.lixels_ = workspace.lixels
            self.events_ = np.ascontiguousarray(events.coordinates.copy())
            self.weights_ = np.ascontiguousarray(events.weights.copy())
            self.n_events_ = events.n_events
            self.dimension_ = 1
            self.coordinate_names_in_ = np.asarray(["network_distance"], dtype=object)
            self.weight_sum_ = events.weight_sum
            self.bandwidth_ = fitted_bandwidth
            self.event_crs_ = events.crs
            self.spatial_unit_ = events.spatial_unit
            self.event_fingerprint_ = events.fingerprint
            self.kernel_ = kernel
            self.junction_policy_ = policy
            self.directed_ = effective_directed
            self.distance_asset_ = distance_asset
            self.propagation_traces_ = traces if self.store_propagation else None
            self.values_ = owned_values
            self.network_bandwidth_strategy_ = bandwidth_strategy
            self.bandwidth_selection_ = (
                selection_result
                if isinstance(selection_result, BandwidthSelectionResult)
                else None
            )
            self.fit_metadata_ = {
                "kernel": kernel.name,
                "target": self.target,
                "junction_policy": policy.name,
                "bandwidth": (
                    float(fitted_bandwidth)
                    if np.asarray(fitted_bandwidth).ndim == 0
                    else None
                ),
                "bandwidth_strategy": bandwidth_strategy.__class__.__name__,
                "adaptive_bandwidth": bool(np.asarray(fitted_bandwidth).ndim == 1),
                "bandwidth_min": float(np.min(bandwidth_values)),
                "bandwidth_max": float(np.max(bandwidth_values)),
                "n_events": events.n_events,
                "n_lixels": workspace.lixels.n_lixels,
                "directed": effective_directed,
                "network_fingerprint": workspace.network.fingerprint,
                "event_fingerprint": events.fingerprint,
                "support_fingerprint": workspace.lixels.fingerprint,
                "path_based": policy.path_based,
                "n_propagation_records": n_records,
                "raw_minimum_before_clipping": raw_minimum,
                "bandwidth_selection_method": (
                    None
                    if self.bandwidth_selection_ is None
                    else self.bandwidth_selection_.method
                ),
            }
            self._mark_fitted()
            return self
        except Exception:
            self._reset_fit_state()
            raise

    def evaluate(self) -> np.ndarray:
        """Return fitted values at the workspace lixel centres."""
        self._check_is_fitted()
        if self.values_ is None:
            raise RuntimeError("Fitted network values are unavailable.")
        return self.values_.copy()

    predict = evaluate

    def predict_result(self) -> NetworkField:
        """Return fitted values as an immutable measured network field."""
        self._check_is_fitted()
        if (
            self.values_ is None
            or self.lixels_ is None
            or self.kernel_ is None
            or self.junction_policy_ is None
            or self.directed_ is None
            or self.workspace_ is None
            or self.event_fingerprint_ is None
            or self.bandwidth_ is None
        ):
            raise RuntimeError("Fitted estimator components are unavailable.")
        return NetworkField(
            values=self.values_,
            support=self.lixels_,
            bandwidth=self.bandwidth_,
            target=self.target,
            kernel=self.kernel_.name,
            junction_policy=self.junction_policy_.name,
            directed=self.directed_,
            network_fingerprint=self.workspace_.network.fingerprint,
            event_fingerprint=self.event_fingerprint_,
            metadata=dict(self.fit_metadata_ or {}),
        )

    def fit_predict(self, workspace: NetworkWorkspace) -> NetworkField:
        """Fit a workspace and immediately return its network field."""
        return self.fit(workspace).predict_result()
