# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Separable product-kernel estimation in ordinary space-time."""

from __future__ import annotations

from typing import Optional, TypeAlias

import numpy as np

from pykdex.core.base import BaseKDE
from pykdex.core.spatiotemporal_results import SpatiotemporalKDEResult
from pykdex.data import SpatiotemporalEvents
from pykdex.data.spatiotemporal import (
    SpatiotemporalGridSupport,
    SpatiotemporalPointSupport,
)
from pykdex.kernels import BaseKernel, get_kernel
from pykdex.metrics import BaseMetric, get_metric
from pykdex.spatiotemporal import (
    SpatiotemporalDistanceAsset,
    build_spatiotemporal_distance_asset,
    evaluate_product_kernel,
)
from pykdex.temporal import BaseTimeDomain

SpaceTimeSupport: TypeAlias = SpatiotemporalPointSupport | SpatiotemporalGridSupport


def _validate_bandwidth(value: float, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must not be boolean.")
    resolved = float(value)
    if not np.isfinite(resolved) or resolved <= 0.0:
        raise ValueError(f"{name} must be finite and positive.")
    return resolved


class SpatiotemporalKDE(BaseKDE):
    r"""Separable KDE with independent spatial and temporal bandwidths.

    The estimator uses

    .. math::

        \hat f(x,t)=\sum_i a_i h_s^{-d}K_s(d(x,x_i)/h_s)
        h_t^{-1}K_t((t-t_i)/h_t).

    Cyclic time is evaluated by summing periodic kernel images, preserving
    normalization even for Gaussian and other infinite-support kernels.
    """

    def __init__(
        self,
        spatial_bandwidth: float = 1.0,
        temporal_bandwidth: float = 1.0,
        *,
        spatial_kernel: str | BaseKernel = "gaussian",
        temporal_kernel: str | BaseKernel = "gaussian",
        spatial_metric: str | BaseMetric = "euclidean",
        target: str = "density",
        chunk_size: Optional[int] = None,
        cyclic_tail_tolerance: float = 1e-12,
        random_state: Optional[int] = None,
        verbose: bool = False,
    ) -> None:
        super().__init__(target=target, random_state=random_state, verbose=verbose)
        self.spatial_bandwidth = _validate_bandwidth(
            spatial_bandwidth, name="spatial_bandwidth"
        )
        self.temporal_bandwidth = _validate_bandwidth(
            temporal_bandwidth, name="temporal_bandwidth"
        )
        if chunk_size is not None:
            if isinstance(chunk_size, (bool, np.bool_)) or not isinstance(
                chunk_size, (int, np.integer)
            ):
                raise TypeError("chunk_size must be a positive integer or None.")
            if int(chunk_size) <= 0:
                raise ValueError("chunk_size must be greater than zero.")
        tolerance = float(cyclic_tail_tolerance)
        if not np.isfinite(tolerance) or not 0.0 < tolerance < 1.0:
            raise ValueError(
                "cyclic_tail_tolerance must lie strictly between zero and one."
            )
        self.spatial_kernel = spatial_kernel
        self.temporal_kernel = temporal_kernel
        self.spatial_metric = spatial_metric
        self.chunk_size = int(chunk_size) if chunk_size is not None else None
        self.cyclic_tail_tolerance = tolerance
        self._reset_fit_state()

    def _reset_fit_state(self) -> None:
        self._mark_unfitted()
        self._reset_common_state()
        self.events_object_: SpatiotemporalEvents | None = None
        self.times_: np.ndarray | None = None
        self.temporal_unit_: str | None = None
        self.time_domain_: BaseTimeDomain | None = None
        self.spatial_kernel_: BaseKernel | None = None
        self.temporal_kernel_: BaseKernel | None = None
        self.spatial_metric_: BaseMetric | None = None

    def fit(self, events: SpatiotemporalEvents) -> "SpatiotemporalKDE":
        """Fit immutable weighted space-time events."""
        self._reset_fit_state()
        try:
            if not isinstance(events, SpatiotemporalEvents):
                raise TypeError("events must be SpatiotemporalEvents.")
            spatial_kernel = get_kernel(self.spatial_kernel)
            temporal_kernel = get_kernel(self.temporal_kernel)
            metric = get_metric(self.spatial_metric)
            self.events_object_ = events
            self.events_ = events.spatial_coordinates
            self.times_ = events.times
            self.weights_ = events.weights
            self.weight_sum_ = events.weight_sum
            self.n_events_ = events.n_events
            self.dimension_ = events.spatial.dimension
            self.coordinate_names_in_ = np.asarray(events.spatial.coordinate_names)
            self.event_crs_ = events.spatial.crs
            self.spatial_unit_ = events.spatial.spatial_unit
            self.temporal_unit_ = events.temporal.temporal_unit
            self.time_domain_ = events.temporal.domain
            self.event_fingerprint_ = events.fingerprint
            self.spatial_kernel_ = spatial_kernel
            self.temporal_kernel_ = temporal_kernel
            self.spatial_metric_ = metric
            self.bandwidth_ = np.asarray(
                [self.spatial_bandwidth, self.temporal_bandwidth], dtype=float
            )
            self.fit_metadata_ = {
                "spatial_kernel": spatial_kernel.name,
                "temporal_kernel": temporal_kernel.name,
                "spatial_metric": metric.name,
                "spatial_bandwidth": self.spatial_bandwidth,
                "temporal_bandwidth": self.temporal_bandwidth,
                "target": self.target,
                "n_events": events.n_events,
                "dimension": events.spatial.dimension,
                "time_domain": events.temporal.domain.name,
                "spatial_unit": events.spatial.spatial_unit,
                "temporal_unit": events.temporal.temporal_unit,
                "event_fingerprint": events.fingerprint,
            }
            self._mark_fitted()
            return self
        except Exception:
            self._reset_fit_state()
            raise

    def _components(
        self,
    ) -> tuple[
        SpatiotemporalEvents,
        BaseKernel,
        BaseKernel,
        BaseMetric,
        np.ndarray,
        float,
    ]:
        self._check_is_fitted()
        if (
            self.events_object_ is None
            or self.spatial_kernel_ is None
            or self.temporal_kernel_ is None
            or self.spatial_metric_ is None
            or self.weights_ is None
            or self.weight_sum_ is None
        ):
            raise RuntimeError("Fitted estimator components are unavailable.")
        return (
            self.events_object_,
            self.spatial_kernel_,
            self.temporal_kernel_,
            self.spatial_metric_,
            self.weights_,
            self.weight_sum_,
        )

    @staticmethod
    def _validate_support(support: SpaceTimeSupport) -> None:
        if not isinstance(
            support, (SpatiotemporalPointSupport, SpatiotemporalGridSupport)
        ):
            raise TypeError("support must be a space-time support object.")

    def _evaluate_asset(self, asset: SpatiotemporalDistanceAsset) -> np.ndarray:
        (
            events,
            spatial_kernel,
            temporal_kernel,
            _metric,
            weights,
            weight_sum,
        ) = self._components()
        if self.dimension_ is None or self.time_domain_ is None:
            raise RuntimeError("Fitted dimensions and time domain are unavailable.")
        kernel_values = evaluate_product_kernel(
            asset.spatial_distances,
            asset.temporal_offsets,
            dimension=self.dimension_,
            spatial_kernel=spatial_kernel,
            temporal_kernel=temporal_kernel,
            spatial_bandwidth=self.spatial_bandwidth,
            temporal_bandwidth=self.temporal_bandwidth,
            time_domain=self.time_domain_,
            tail_tolerance=self.cyclic_tail_tolerance,
        )
        coefficients = weights / weight_sum if self.target == "density" else weights
        estimates = np.asarray(kernel_values @ coefficients, dtype=float)
        estimates[estimates < 0.0] = 0.0
        if not np.all(np.isfinite(estimates)):
            raise FloatingPointError("Space-time KDE produced non-finite values.")
        return estimates

    def evaluate(
        self,
        support: SpaceTimeSupport,
        *,
        distance_asset: SpatiotemporalDistanceAsset | None = None,
    ) -> np.ndarray:
        """Evaluate support, optionally reusing a matching distance asset."""
        self._validate_support(support)
        events, _, _, metric, _, _ = self._components()
        if distance_asset is not None:
            distance_asset.validate_for(events, support, spatial_metric=metric.name)
            return self._evaluate_asset(distance_asset)
        chunk_size = self.chunk_size or support.n_points
        values = np.empty(support.n_points, dtype=float)
        for start in range(0, support.n_points, chunk_size):
            stop = min(start + chunk_size, support.n_points)
            chunk = SpatiotemporalPointSupport.from_arrays(
                support.spatial_coordinates[start:stop],
                support.times[start:stop],
                support_measure=None,
                ids=np.arange(stop - start),
                coordinate_names=support.spatial.coordinate_names,
                crs=support.spatial.crs,
                spatial_unit=support.spatial.spatial_unit,
                temporal_unit=support.temporal.temporal_unit,
                time_domain=support.temporal.domain,
                temporal_origin=support.temporal.temporal_origin,
                timezone=support.temporal.timezone,
            )
            asset = build_spatiotemporal_distance_asset(
                events, chunk, spatial_metric=metric
            )
            values[start:stop] = self._evaluate_asset(asset)
        values.setflags(write=False)
        return values

    predict = evaluate

    def predict_result(
        self,
        support: SpaceTimeSupport,
        *,
        distance_asset: SpatiotemporalDistanceAsset | None = None,
    ) -> SpatiotemporalKDEResult:
        """Evaluate and return a structured measured result."""
        values = self.evaluate(support, distance_asset=distance_asset)
        _, spatial_kernel, temporal_kernel, metric, _, _ = self._components()
        return SpatiotemporalKDEResult(
            values=values,
            support=support,
            spatial_bandwidth=self.spatial_bandwidth,
            temporal_bandwidth=self.temporal_bandwidth,
            target=self.target,
            spatial_kernel=spatial_kernel.name,
            temporal_kernel=temporal_kernel.name,
            spatial_metric=metric.name,
            metadata=dict(self.fit_metadata_ or {}),
        )

    def fit_predict(
        self,
        events: SpatiotemporalEvents,
        support: SpaceTimeSupport,
        *,
        distance_asset: SpatiotemporalDistanceAsset | None = None,
    ) -> SpatiotemporalKDEResult:
        """Fit events and immediately evaluate support."""
        return self.fit(events).predict_result(support, distance_asset=distance_asset)
