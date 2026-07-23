# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Spatial kernel density and intensity estimation.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from pykdex.bandwidths import BaseBalloonBandwidth, BaseBandwidth, get_bandwidth
from pykdex.core.base import BaseKDE
from pykdex.core.results import BandwidthSelectionResult, SpatialKDEResult
from pykdex.core.validation import (
    ArrayLike,
    EventInput,
    SupportInput,
    ValidatedPointInput,
    validate_point_input,
    validate_spatial_metadata,
    validate_support_schema,
    validate_weights,
)
from pykdex.corrections import (
    BaseBoundaryCorrection,
    BoundaryCorrectionState,
    get_boundary_correction,
)
from pykdex.data import SpatialBoundary, SpatialEvents
from pykdex.kernels import BaseKernel, get_kernel
from pykdex.metrics import BaseMetric, get_metric
from pykdex.spatial.evaluation import (
    bandwidth_kind,
    evaluate_balloon_kernel,
    validate_spatial_bandwidth,
)


class SpatialKDE(BaseKDE):
    r"""Kernel density or intensity estimation in Euclidean space.

    Scalar and event-specific sample-point bandwidths use

    .. math::

        \hat f(x) = \sum_i a_i h_i^{-d}
        K\left(\lVert x-x_i\rVert / h_i\right).

    A global matrix bandwidth :math:`H` uses

    .. math::

        \hat f(x) = \sum_i a_i |H|^{-1/2}
        K\left(\lVert H^{-1/2}(x-x_i)\rVert\right).

    Query-centred balloon bandwidths instead use one scalar :math:`h(x)` per
    support location. ``a_i = w_i / sum(w)`` for ``target="density"`` and
    ``a_i = w_i`` for ``target="intensity"``.

    Args:
        kernel: Normalized radial kernel name or instance.
        bandwidth: Positive scalar, sample-point strategy, bandwidth matrix, or
            support-dependent balloon strategy.
        metric: Pairwise metric name or instance. Matrix bandwidths require the
            Euclidean metric.
        target: ``"density"`` or ``"intensity"``.
        boundary: Optional planar study boundary. When present, fitted events
            and evaluated support must lie inside or on the polygon.
        boundary_correction: ``"none"``, ``"renormalization"``,
            ``"reflection"``, or a correction strategy instance.
        chunk_size: Optional positive number of support rows evaluated per chunk.
        random_state: Reserved deterministic random seed for future selectors.
        verbose: Print estimator progress.
    """

    def __init__(
        self,
        kernel: str | BaseKernel = "gaussian",
        bandwidth: (
            float | int | np.floating | BaseBandwidth | BaseBalloonBandwidth
        ) = 1.0,
        metric: str | BaseMetric = "euclidean",
        target: str = "density",
        boundary: SpatialBoundary | None = None,
        boundary_correction: str | BaseBoundaryCorrection = "none",
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
        if boundary is not None and not isinstance(boundary, SpatialBoundary):
            raise TypeError("boundary must be a SpatialBoundary or None.")
        self.kernel = kernel
        self.bandwidth = bandwidth
        self.metric = metric
        self.boundary = boundary
        self.boundary_correction = boundary_correction
        self.chunk_size = int(chunk_size) if chunk_size is not None else None
        self._reset_fit_state()

    def _reset_fit_state(self) -> None:
        self._mark_unfitted()
        self._reset_common_state()
        self.kernel_: Optional[BaseKernel] = None
        self.metric_: Optional[BaseMetric] = None
        self.bandwidth_strategy_: Optional[BaseBandwidth] = None
        self.balloon_bandwidth_strategy_: Optional[BaseBalloonBandwidth] = None
        self.bandwidth_selection_: Optional[BandwidthSelectionResult] = None
        self.boundary_: Optional[SpatialBoundary] = None
        self.boundary_correction_: Optional[BaseBoundaryCorrection] = None
        self.boundary_correction_state_: Optional[BoundaryCorrectionState] = None

    def fit(
        self,
        events: EventInput,
        weights: ArrayLike | None = None,
    ) -> "SpatialKDE":
        """Fit the estimator to coordinates or a :class:`SpatialEvents` object."""
        self._reset_fit_state()
        try:
            event_input = validate_point_input(events, name="events")
            if isinstance(events, SpatialEvents):
                if weights is not None:
                    raise ValueError(
                        "weights must be omitted when events is SpatialEvents; "
                        "the object already owns validated event weights."
                    )
                weights_array = validate_weights(
                    events.weights,
                    event_input.coordinates.shape[0],
                )
            else:
                weights_array = validate_weights(
                    weights,
                    event_input.coordinates.shape[0],
                )
            events_array = event_input.coordinates
            kernel = get_kernel(self.kernel)
            metric = get_metric(self.metric)
            correction = get_boundary_correction(self.boundary_correction)
            boundary = self.boundary
            self._validate_boundary_fit_context(
                events_array,
                event_crs=event_input.crs,
                event_unit=event_input.spatial_unit,
                boundary=boundary,
                correction=correction,
            )

            bandwidth_strategy: BaseBandwidth | None = None
            balloon_strategy: BaseBalloonBandwidth | None = None
            bandwidth: float | np.ndarray | None
            correction_state: BoundaryCorrectionState
            if isinstance(self.bandwidth, BaseBalloonBandwidth):
                balloon_strategy = self.bandwidth
                balloon_strategy.validate_events(events_array)
                if correction.name != "none":
                    raise ValueError(
                        "balloon bandwidths cannot yet be combined with boundary "
                        "renormalization or reflection because their correction mass "
                        "depends on each support-specific bandwidth."
                    )
                bandwidth = None
                correction_state = correction.prepare(
                    events_array,
                    boundary=boundary,
                    kernel=kernel,
                    metric=metric,
                    bandwidth=1.0,
                )
            else:
                bandwidth_strategy = get_bandwidth(self.bandwidth)
                resolved = bandwidth_strategy.resolve(
                    events_array,
                    weights=weights_array,
                    metric=metric,
                    kernel=kernel,
                )
                bandwidth = validate_spatial_bandwidth(
                    resolved,
                    n_events=events_array.shape[0],
                    dimension=events_array.shape[1],
                )
                if np.asarray(bandwidth).ndim == 2 and metric.name != "euclidean":
                    raise ValueError("bandwidth matrices require the Euclidean metric.")
                correction_state = correction.prepare(
                    events_array,
                    boundary=boundary,
                    kernel=kernel,
                    metric=metric,
                    bandwidth=bandwidth,
                )

            self.events_ = events_array
            self.weights_ = weights_array
            self.n_events_ = int(events_array.shape[0])
            self.dimension_ = int(events_array.shape[1])
            self.coordinate_names_in_ = event_input.coordinate_names
            self.weight_sum_ = float(np.sum(weights_array))
            self.event_crs_ = event_input.crs
            self.spatial_unit_ = event_input.spatial_unit
            self.event_fingerprint_ = event_input.fingerprint
            self.kernel_ = kernel
            self.metric_ = metric
            self.bandwidth_ = bandwidth
            self.bandwidth_strategy_ = bandwidth_strategy
            self.balloon_bandwidth_strategy_ = balloon_strategy
            self.bandwidth_selection_ = (
                None
                if bandwidth_strategy is None
                else getattr(bandwidth_strategy, "result_", None)
            )
            self.boundary_ = boundary
            self.boundary_correction_ = correction
            self.boundary_correction_state_ = correction_state
            resolved_kind = (
                "support"
                if balloon_strategy is not None
                else bandwidth_kind(np.asarray(bandwidth, dtype=float))
            )
            self.fit_metadata_ = {
                "kernel": kernel.name,
                "metric": metric.name,
                "target": self.target,
                "n_events": self.n_events_,
                "dimension": self.dimension_,
                "bandwidth_strategy": (
                    balloon_strategy.__class__.__name__
                    if balloon_strategy is not None
                    else bandwidth_strategy.__class__.__name__
                ),
                "bandwidth_kind": resolved_kind,
                "boundary_correction": correction.name,
                "boundary_fingerprint": (
                    None if boundary is None else boundary.fingerprint
                ),
                "event_crs": self.event_crs_,
                "spatial_unit": self.spatial_unit_,
                "event_fingerprint": self.event_fingerprint_,
            }
            self._mark_fitted()
            return self
        except Exception:
            self._reset_fit_state()
            raise

    @staticmethod
    def _validate_boundary_fit_context(
        events: np.ndarray,
        *,
        event_crs: str | None,
        event_unit: str | None,
        boundary: SpatialBoundary | None,
        correction: BaseBoundaryCorrection,
    ) -> None:
        if boundary is None:
            if correction.name != "none":
                raise ValueError("boundary correction requires a SpatialBoundary.")
            return
        if events.shape[1] != 2:
            raise ValueError("SpatialBoundary requires two-dimensional event coordinates.")
        validate_spatial_metadata(
            event_crs=event_crs,
            support_crs=boundary.crs,
            event_unit=event_unit,
            support_unit=boundary.spatial_unit,
        )
        covered = boundary.covers(events)
        if not np.all(covered):
            outside = int(np.count_nonzero(~covered))
            raise ValueError(
                f"All fitted events must lie inside the study boundary; {outside} "
                "event(s) are outside."
            )

    def _prepare_support(self, support: SupportInput) -> ValidatedPointInput:
        self._check_is_fitted()
        validate_support_schema(support, self.coordinate_names_in_)
        validated = validate_point_input(
            support,
            name="support",
            expected_dimension=self.dimension_,
        )
        validate_spatial_metadata(
            event_crs=self.event_crs_,
            support_crs=validated.crs,
            event_unit=self.spatial_unit_,
            support_unit=validated.spatial_unit,
        )
        if self.boundary_ is not None:
            covered = self.boundary_.covers(validated.coordinates)
            if not np.all(covered):
                outside = int(np.count_nonzero(~covered))
                raise ValueError(
                    f"All support coordinates must lie inside the study boundary; "
                    f"{outside} support point(s) are outside."
                )
        return validated

    def evaluate(self, support: SupportInput) -> np.ndarray:
        """Evaluate the fitted estimator at support coordinates."""
        validated = self._prepare_support(support)
        values, _ = self._evaluate_array(validated.coordinates)
        return values

    predict = evaluate

    def _evaluate_array(
        self,
        support: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray | None]:
        chunk_size = self.chunk_size or support.shape[0]
        values = np.empty(support.shape[0], dtype=float)
        support_bandwidths = (
            np.empty(support.shape[0], dtype=float)
            if self.balloon_bandwidth_strategy_ is not None
            else None
        )
        for start in range(0, support.shape[0], chunk_size):
            stop = min(start + chunk_size, support.shape[0])
            chunk_values, chunk_bandwidths = self._evaluate_chunk(
                support[start:stop]
            )
            values[start:stop] = chunk_values
            if support_bandwidths is not None:
                if chunk_bandwidths is None:
                    raise RuntimeError("balloon bandwidth evaluation returned no values.")
                support_bandwidths[start:stop] = chunk_bandwidths
        if support_bandwidths is not None:
            support_bandwidths.setflags(write=False)
        return values, support_bandwidths

    def _evaluate_chunk(
        self,
        support: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray | None]:
        if (
            self.events_ is None
            or self.weights_ is None
            or self.weight_sum_ is None
            or self.kernel_ is None
            or self.metric_ is None
            or self.dimension_ is None
            or self.boundary_correction_ is None
            or self.boundary_correction_state_ is None
        ):
            raise RuntimeError("Fitted estimator components are unavailable.")
        support_bandwidths: np.ndarray | None = None
        if self.balloon_bandwidth_strategy_ is not None:
            support_bandwidths = self.balloon_bandwidth_strategy_.resolve_support(
                support,
                self.events_,
                metric=self.metric_,
            )
            kernel_values = evaluate_balloon_kernel(
                support,
                self.events_,
                kernel=self.kernel_,
                metric=self.metric_,
                support_bandwidths=support_bandwidths,
            )
        else:
            if self.bandwidth_ is None:
                raise RuntimeError("Fitted sample-point bandwidth is unavailable.")
            kernel_values = self.boundary_correction_.evaluate_kernel(
                support,
                self.events_,
                kernel=self.kernel_,
                metric=self.metric_,
                bandwidth=self.bandwidth_,
                state=self.boundary_correction_state_,
            )
        coefficients = (
            self.weights_ / self.weight_sum_
            if self.target == "density"
            else self.weights_
        )
        estimates = np.asarray(kernel_values @ coefficients, dtype=float)
        estimates[estimates < 0.0] = 0.0
        if not np.all(np.isfinite(estimates)):
            raise FloatingPointError("KDE evaluation produced non-finite values.")
        return estimates, support_bandwidths

    def predict_result(self, support: SupportInput) -> SpatialKDEResult:
        """Evaluate and return a structured result object."""
        validated = self._prepare_support(support)
        values, support_bandwidths = self._evaluate_array(validated.coordinates)
        if self.kernel_ is None or self.metric_ is None:
            raise RuntimeError("Fitted estimator components are unavailable.")
        result_bandwidth: float | np.ndarray
        if support_bandwidths is not None:
            result_bandwidth = support_bandwidths
        elif self.bandwidth_ is not None:
            result_bandwidth = self.bandwidth_
        else:
            raise RuntimeError("Fitted bandwidth is unavailable.")
        names = (
            tuple(str(name) for name in validated.coordinate_names)
            if validated.coordinate_names is not None
            else None
        )
        metadata = dict(self.fit_metadata_ or {})
        if validated.shape is not None:
            metadata["support_shape"] = validated.shape
        return SpatialKDEResult(
            values=values,
            support=validated.coordinates,
            bandwidth=result_bandwidth,
            target=self.target,
            kernel=self.kernel_.name,
            metric=self.metric_.name,
            coordinate_names=names,
            support_ids=validated.ids,
            support_measure=validated.measure,
            crs=validated.crs or self.event_crs_,
            spatial_unit=validated.spatial_unit or self.spatial_unit_,
            support_fingerprint=validated.fingerprint,
            metadata=metadata,
        )

    def fit_predict(
        self,
        events: EventInput,
        support: SupportInput,
        weights: ArrayLike | None = None,
    ) -> SpatialKDEResult:
        """Fit to events and immediately evaluate a support."""
        return self.fit(events, weights=weights).predict_result(support)
