# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Fixed- or strategy-bandwidth spatial kernel density estimation.

This module is the reference estimator used to establish pyKDEX API, state,
validation, and numerical conventions before network and temporal estimators
are added.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from pykdex.bandwidths import BaseBandwidth, get_bandwidth
from pykdex.core.base import BaseKDE
from pykdex.core.results import SpatialKDEResult
from pykdex.core.validation import (
    ArrayLike,
    validate_points,
    validate_support_schema,
    validate_weights,
)
from pykdex.kernels import BaseKernel, get_kernel
from pykdex.metrics import BaseMetric, get_metric


class SpatialKDE(BaseKDE):
    r"""Kernel density or intensity estimation in Euclidean space.

    For event coordinates :math:`x_i`, event weights :math:`w_i`, and bandwidth
    :math:`h_i`, the estimator evaluated at :math:`x` is

    .. math::

        \hat f(x) = \sum_i a_i h_i^{-d}
        K\left(\lVert x-x_i\rVert / h_i\right),

    where ``a_i = w_i / sum(w)`` for ``target="density"`` and ``a_i = w_i``
    for ``target="intensity"``.

    Args:
        kernel: Normalized radial kernel name or instance.
        bandwidth: Positive numeric bandwidth or bandwidth strategy.
        metric: Pairwise metric name or instance.
        target: ``"density"`` or ``"intensity"``.
        chunk_size: Optional positive number of support rows evaluated per chunk.
        random_state: Reserved deterministic random seed for future selectors.
        verbose: Print estimator progress.
    """

    def __init__(
        self,
        kernel: str | BaseKernel = "gaussian",
        bandwidth: float | BaseBandwidth = 1.0,
        metric: str | BaseMetric = "euclidean",
        target: str = "density",
        chunk_size: Optional[int] = None,
        random_state: Optional[int] = None,
        verbose: bool = False,
    ) -> None:
        super().__init__(target=target, random_state=random_state, verbose=verbose)
        if chunk_size is not None:
            if isinstance(chunk_size, (bool, np.bool_)) or not isinstance(
                chunk_size, (int, np.integer)
            ):
                raise TypeError("chunk_size must be a positive integer or None.")
            if int(chunk_size) <= 0:
                raise ValueError("chunk_size must be greater than zero.")
        self.kernel = kernel
        self.bandwidth = bandwidth
        self.metric = metric
        self.chunk_size = int(chunk_size) if chunk_size is not None else None
        self._reset_fit_state()

    def _reset_fit_state(self) -> None:
        self._mark_unfitted()
        self._reset_common_state()
        self.kernel_: Optional[BaseKernel] = None
        self.metric_: Optional[BaseMetric] = None

    def fit(
        self,
        events: ArrayLike,
        weights: ArrayLike | None = None,
    ) -> "SpatialKDE":
        """Fit the estimator to event coordinates and optional event weights."""
        self._reset_fit_state()
        try:
            events_array, coordinate_names = validate_points(events, name="events")
            weights_array = validate_weights(weights, events_array.shape[0])
            kernel = get_kernel(self.kernel)
            metric = get_metric(self.metric)
            bandwidth_strategy = get_bandwidth(self.bandwidth)
            resolved = bandwidth_strategy.resolve(events_array)
            bandwidth = self._validate_resolved_bandwidth(
                resolved, n_events=events_array.shape[0]
            )

            self.events_ = events_array
            self.weights_ = weights_array
            self.n_events_ = int(events_array.shape[0])
            self.dimension_ = int(events_array.shape[1])
            self.coordinate_names_in_ = coordinate_names
            self.weight_sum_ = float(np.sum(weights_array))
            self.kernel_ = kernel
            self.metric_ = metric
            self.bandwidth_ = bandwidth
            self.fit_metadata_ = {
                "kernel": kernel.name,
                "metric": metric.name,
                "target": self.target,
                "n_events": self.n_events_,
                "dimension": self.dimension_,
            }
            self._mark_fitted()
            return self
        except Exception:
            self._reset_fit_state()
            raise

    @staticmethod
    def _validate_resolved_bandwidth(
        bandwidth: float | np.ndarray,
        *,
        n_events: int,
    ) -> float | np.ndarray:
        array = np.asarray(bandwidth, dtype=float)
        if array.ndim == 0:
            value = float(array)
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError("resolved bandwidth must be finite and positive.")
            return value
        if array.ndim != 1 or array.shape[0] != n_events:
            raise ValueError(
                "event-specific bandwidth must be a vector with one value per event."
            )
        if not np.all(np.isfinite(array)) or np.any(array <= 0.0):
            raise ValueError("resolved bandwidth values must be finite and positive.")
        return np.ascontiguousarray(array.copy())

    def evaluate(self, support: ArrayLike) -> np.ndarray:
        """Evaluate the fitted estimator at support coordinates."""
        self._check_is_fitted()
        validate_support_schema(support, self.coordinate_names_in_)
        support_array, _ = validate_points(
            support,
            name="support",
            expected_dimension=self.dimension_,
        )
        chunk_size = self.chunk_size or support_array.shape[0]
        values = np.empty(support_array.shape[0], dtype=float)
        for start in range(0, support_array.shape[0], chunk_size):
            stop = min(start + chunk_size, support_array.shape[0])
            values[start:stop] = self._evaluate_chunk(support_array[start:stop])
        return values

    predict = evaluate

    def _evaluate_chunk(self, support: np.ndarray) -> np.ndarray:
        if (
            self.events_ is None
            or self.weights_ is None
            or self.weight_sum_ is None
            or self.bandwidth_ is None
            or self.kernel_ is None
            or self.metric_ is None
            or self.dimension_ is None
        ):
            raise RuntimeError("Fitted estimator components are unavailable.")
        distances = self.metric_.pairwise(support, self.events_)
        bandwidth = self.bandwidth_
        if isinstance(bandwidth, np.ndarray):
            h_vector = np.asarray(bandwidth, dtype=float)
            standardized = distances / h_vector[None, :]
            kernel_values = self.kernel_(standardized, self.dimension_) / (
                h_vector[None, :] ** self.dimension_
            )
        else:
            h = float(bandwidth)
            standardized = distances / h
            kernel_values = (
                self.kernel_(standardized, self.dimension_) / h**self.dimension_
            )
        coefficients = (
            self.weights_ / self.weight_sum_
            if self.target == "density"
            else self.weights_
        )
        estimates = kernel_values @ coefficients
        estimates = np.asarray(estimates, dtype=float)
        estimates[estimates < 0.0] = 0.0
        if not np.all(np.isfinite(estimates)):
            raise FloatingPointError("KDE evaluation produced non-finite values.")
        return estimates

    def predict_result(self, support: ArrayLike) -> SpatialKDEResult:
        """Evaluate and return a structured result object."""
        self._check_is_fitted()
        validate_support_schema(support, self.coordinate_names_in_)
        support_array, support_names = validate_points(
            support,
            name="support",
            expected_dimension=self.dimension_,
        )
        values = self.evaluate(support)
        if self.kernel_ is None or self.metric_ is None or self.bandwidth_ is None:
            raise RuntimeError("Fitted estimator components are unavailable.")
        names = (
            tuple(str(name) for name in support_names)
            if support_names is not None
            else None
        )
        return SpatialKDEResult(
            values=values,
            support=support_array,
            bandwidth=self.bandwidth_,
            target=self.target,
            kernel=self.kernel_.name,
            metric=self.metric_.name,
            coordinate_names=names,
            metadata=dict(self.fit_metadata_ or {}),
        )

    def fit_predict(
        self,
        events: ArrayLike,
        support: ArrayLike,
        weights: ArrayLike | None = None,
    ) -> SpatialKDEResult:
        """Fit to events and immediately evaluate a support."""
        return self.fit(events, weights=weights).predict_result(support)
