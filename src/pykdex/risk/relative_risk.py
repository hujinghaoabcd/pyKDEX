# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Shared-fixed-bandwidth case-control relative-risk fields."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
import pandas as pd

from pykdex.core.network_results import NetworkField
from pykdex.core.network_time_results import NetworkTimeField
from pykdex.core.results import SpatialKDEResult
from pykdex.core.spatiotemporal_results import SpatiotemporalKDEResult
from pykdex.data._utils import readonly_array, stable_fingerprint
from pykdex.risk.density import (
    DensityResult,
    adapt_density_result,
    require_compatible_density_views,
)
from pykdex.risk.policies import (
    DenominatorPolicy,
    DenominatorPolicyInput,
    apply_denominator_policy,
    resolve_denominator_policy,
)
from pykdex.risk.support import (
    MeasuredSupport,
    SupportDescriptor,
    describe_measured_support,
    require_same_measured_support,
)


@dataclass(frozen=True)
class RelativeRiskField:
    """Case-control density ratio and log ratio on measured support."""

    values: np.ndarray
    log_values: np.ndarray
    support: MeasuredSupport
    case_density: np.ndarray
    control_density: np.ndarray
    effective_control_density: np.ndarray
    invalid_mask: np.ndarray
    adjusted_mask: np.ndarray
    policy: DenominatorPolicy
    result_family: str
    bandwidths: tuple[float, ...]
    estimator_contract: Mapping[str, Any]
    case_source_fingerprint: str
    control_source_fingerprint: str
    normalization_tolerance: float
    metadata: Mapping[str, Any] = field(default_factory=dict)
    descriptor: SupportDescriptor = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.policy, DenominatorPolicy):
            raise TypeError("policy must be a DenominatorPolicy instance.")
        descriptor = describe_measured_support(self.support)
        values = readonly_array(self.values, dtype=float, ndim=1, name="values")
        log_values = readonly_array(
            self.log_values,
            dtype=float,
            ndim=1,
            name="log_values",
        )
        case_density = readonly_array(
            self.case_density,
            dtype=float,
            ndim=1,
            name="case_density",
        )
        control_density = readonly_array(
            self.control_density,
            dtype=float,
            ndim=1,
            name="control_density",
        )
        effective_control = readonly_array(
            self.effective_control_density,
            dtype=float,
            ndim=1,
            name="effective_control_density",
        )
        invalid = readonly_array(
            self.invalid_mask,
            dtype=bool,
            ndim=1,
            name="invalid_mask",
        )
        adjusted = readonly_array(
            self.adjusted_mask,
            dtype=bool,
            ndim=1,
            name="adjusted_mask",
        )
        expected_shape = (descriptor.n_elements,)
        for name, array in (
            ("values", values),
            ("log_values", log_values),
            ("case_density", case_density),
            ("control_density", control_density),
            ("effective_control_density", effective_control),
            ("invalid_mask", invalid),
            ("adjusted_mask", adjusted),
        ):
            if array.shape != expected_shape:
                raise ValueError(f"{name} must contain one value per support element.")
        for name, density in (
            ("case_density", case_density),
            ("control_density", control_density),
        ):
            if not np.all(np.isfinite(density)) or np.any(density < 0.0):
                raise ValueError(f"{name} must be finite and non-negative.")
        tolerance = _validate_normalization_tolerance(self.normalization_tolerance)
        for name, density in (
            ("case_density", case_density),
            ("control_density", control_density),
        ):
            integral = float(np.dot(density, descriptor.measure))
            if not np.isclose(integral, 1.0, rtol=0.0, atol=tolerance):
                raise ValueError(
                    f"{name} must integrate to one within "
                    f"normalization_tolerance={tolerance}; observed {integral}."
                )

        resolution = apply_denominator_policy(control_density, self.policy)
        if not np.array_equal(invalid, resolution.invalid_mask):
            raise ValueError("invalid_mask is inconsistent with control density.")
        if not np.array_equal(adjusted, resolution.adjusted_mask):
            raise ValueError("adjusted_mask is inconsistent with control density.")
        if not np.array_equal(effective_control, resolution.effective, equal_nan=True):
            raise ValueError(
                "effective_control_density is inconsistent with the policy."
            )

        valid = np.isfinite(effective_control)
        expected_ratio = np.full_like(case_density, np.nan)
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            np.divide(
                case_density,
                effective_control,
                out=expected_ratio,
                where=valid,
            )
        if np.any(np.isinf(values)) or np.any(values[np.isfinite(values)] < 0.0):
            raise ValueError(
                "relative-risk values must be non-negative and never infinite."
            )
        if not np.allclose(
            values,
            expected_ratio,
            rtol=1e-12,
            atol=1e-15,
            equal_nan=True,
        ):
            raise ValueError("values are inconsistent with case/control division.")

        expected_log = np.full_like(case_density, np.nan)
        positive = valid & (case_density > 0.0)
        zero = valid & (case_density == 0.0)
        expected_log[positive] = np.log(case_density[positive]) - np.log(
            effective_control[positive]
        )
        expected_log[zero] = -np.inf
        if np.any(np.isposinf(log_values)):
            raise ValueError("log relative risk must never contain positive infinity.")
        if not np.allclose(
            log_values,
            expected_log,
            rtol=1e-12,
            atol=1e-15,
            equal_nan=True,
        ):
            raise ValueError("log_values are inconsistent with the density ratio.")

        if self.policy.mode == "nan":
            if not np.array_equal(np.isnan(values), invalid):
                raise ValueError(
                    "NaN relative risk must occur exactly at invalid cells."
                )
            if not np.array_equal(np.isnan(log_values), invalid):
                raise ValueError(
                    "NaN log relative risk must occur exactly at invalid cells."
                )
        elif np.any(np.isnan(values)) or np.any(np.isnan(log_values)):
            raise ValueError("NaN relative risk requires policy mode='nan'.")

        family = str(self.result_family).strip()
        case_fingerprint = str(self.case_source_fingerprint).strip()
        control_fingerprint = str(self.control_source_fingerprint).strip()
        if not family or not case_fingerprint or not control_fingerprint:
            raise ValueError("result_family and source fingerprints must be non-empty.")
        bandwidths = tuple(float(value) for value in self.bandwidths)
        if (
            not bandwidths
            or not np.all(np.isfinite(bandwidths))
            or any(value <= 0.0 for value in bandwidths)
        ):
            raise ValueError("bandwidths must contain finite positive scalars.")

        object.__setattr__(self, "values", values)
        object.__setattr__(self, "log_values", log_values)
        object.__setattr__(self, "case_density", case_density)
        object.__setattr__(self, "control_density", control_density)
        object.__setattr__(self, "effective_control_density", effective_control)
        object.__setattr__(self, "invalid_mask", invalid)
        object.__setattr__(self, "adjusted_mask", adjusted)
        object.__setattr__(self, "result_family", family)
        object.__setattr__(self, "bandwidths", bandwidths)
        object.__setattr__(
            self,
            "estimator_contract",
            MappingProxyType(dict(self.estimator_contract)),
        )
        object.__setattr__(self, "case_source_fingerprint", case_fingerprint)
        object.__setattr__(self, "control_source_fingerprint", control_fingerprint)
        object.__setattr__(self, "normalization_tolerance", tolerance)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        object.__setattr__(self, "descriptor", descriptor)

    @property
    def case_integral(self) -> float:
        """Measured integral of the case density."""
        return float(np.dot(self.case_density, self.descriptor.measure))

    @property
    def control_integral(self) -> float:
        """Measured integral of the original control density."""
        return float(np.dot(self.control_density, self.descriptor.measure))

    @property
    def effective_control_integral(self) -> float:
        """Measured integral of the effective control density."""
        valid = np.isfinite(self.effective_control_density)
        return float(
            np.dot(
                self.effective_control_density[valid],
                self.descriptor.measure[valid],
            )
        )

    @property
    def control_weighted_mean(self) -> float:
        """Mean relative risk weighted by original control density."""
        valid = np.isfinite(self.values)
        weights = self.control_density[valid] * self.descriptor.measure[valid]
        denominator = float(np.sum(weights))
        if denominator <= 0.0:
            return float("nan")
        return float(np.dot(self.values[valid], weights) / denominator)

    @property
    def effective_control_weighted_mean(self) -> float:
        """Mean relative risk weighted by the denominator used in division."""
        valid = np.isfinite(self.values) & np.isfinite(self.effective_control_density)
        weights = self.effective_control_density[valid] * self.descriptor.measure[valid]
        denominator = float(np.sum(weights))
        if denominator <= 0.0:
            return float("nan")
        return float(np.dot(self.values[valid], weights) / denominator)

    @property
    def fingerprint(self) -> str:
        """Deterministic relative-risk field fingerprint."""
        return stable_fingerprint(
            self.values,
            self.log_values,
            self.descriptor.fingerprint,
            self.case_density,
            self.control_density,
            self.effective_control_density,
            self.invalid_mask,
            self.adjusted_mask,
            self.policy.mode,
            self.policy.validity_threshold,
            self.policy.minimum_denominator,
            self.result_family,
            self.bandwidths,
            dict(self.estimator_contract),
            self.case_source_fingerprint,
            self.control_source_fingerprint,
            self.normalization_tolerance,
            dict(self.metadata),
        )

    def to_frame(self) -> pd.DataFrame:
        """Return support attributes and density-ratio diagnostics."""
        frame = self.support.to_frame()
        frame["case_density"] = self.case_density
        frame["control_density"] = self.control_density
        frame["effective_control_density"] = self.effective_control_density
        frame["relative_risk"] = self.values
        frame["log_relative_risk"] = self.log_values
        frame["invalid_control_density"] = self.invalid_mask
        frame["adjusted_control_density"] = self.adjusted_mask
        return frame

    def to_grid(self) -> np.ndarray:
        """Reshape raw relative risk on native grid support."""
        reshape = getattr(self.support, "reshape", None)
        if reshape is None or not callable(reshape):
            raise ValueError("This support has no native grid reshape operation.")
        return np.asarray(reshape(self.values))

    def log_to_grid(self) -> np.ndarray:
        """Reshape log relative risk on native grid support."""
        reshape = getattr(self.support, "reshape", None)
        if reshape is None or not callable(reshape):
            raise ValueError("This support has no native grid reshape operation.")
        return np.asarray(reshape(self.log_values))

    def to_geodataframe(self) -> Any:
        """Return geospatial support and density-ratio diagnostics."""
        exporter = getattr(self.support, "to_geodataframe", None)
        if exporter is None or not callable(exporter):
            raise ValueError("This support does not provide GeoDataFrame export.")
        frame = exporter()
        frame["case_density"] = self.case_density
        frame["control_density"] = self.control_density
        frame["effective_control_density"] = self.effective_control_density
        frame["relative_risk"] = self.values
        frame["log_relative_risk"] = self.log_values
        frame["invalid_control_density"] = self.invalid_mask
        frame["adjusted_control_density"] = self.adjusted_mask
        return frame


def estimate_relative_risk(
    case_density: DensityResult,
    control_density: DensityResult,
    *,
    support: MeasuredSupport | None = None,
    zero_policy: DenominatorPolicyInput = "raise",
    validity_threshold: float = 0.0,
    minimum_denominator: float | None = None,
    normalization_tolerance: float = 1e-6,
    metadata: Mapping[str, Any] | None = None,
) -> RelativeRiskField:
    """Estimate shared-fixed-bandwidth case-control density-ratio risk."""
    resolved_support = _resolve_support(case_density, control_density, support=support)
    policy = resolve_denominator_policy(
        zero_policy,
        validity_threshold=validity_threshold,
        minimum_denominator=minimum_denominator,
    )
    case = adapt_density_result(
        case_density,
        support=resolved_support,
        normalization_tolerance=normalization_tolerance,
    )
    control = adapt_density_result(
        control_density,
        support=resolved_support,
        normalization_tolerance=normalization_tolerance,
    )
    require_compatible_density_views(case, control)
    resolution = apply_denominator_policy(control.values, policy)
    valid = np.isfinite(resolution.effective)
    values = np.full_like(case.values, np.nan)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        np.divide(
            case.values,
            resolution.effective,
            out=values,
            where=valid,
        )
    if np.any(np.isinf(values)):
        raise ValueError(
            "Relative-risk division overflowed; use an explicit larger minimum "
            "denominator or inspect the density scale."
        )
    log_values = np.full_like(case.values, np.nan)
    positive = valid & (case.values > 0.0)
    zero = valid & (case.values == 0.0)
    log_values[positive] = np.log(case.values[positive]) - np.log(
        resolution.effective[positive]
    )
    log_values[zero] = -np.inf

    result_metadata = dict(metadata or {})
    result_metadata.update(
        {
            "result_family": case.result_family,
            "bandwidths": case.bandwidths,
            "estimator_contract": dict(case.estimator_contract),
            "case_integral": case.integral,
            "control_integral": control.integral,
            "normalization_tolerance": case.normalization_tolerance,
            "invalid_control_count": int(np.count_nonzero(resolution.invalid_mask)),
            "adjusted_control_count": int(np.count_nonzero(resolution.adjusted_mask)),
            "zero_policy": policy.mode,
            "validity_threshold": policy.validity_threshold,
            "minimum_denominator": policy.minimum_denominator,
            "case_source_metadata": dict(case.metadata),
            "control_source_metadata": dict(control.metadata),
        }
    )
    return RelativeRiskField(
        values=values,
        log_values=log_values,
        support=resolved_support,
        case_density=case.values,
        control_density=control.values,
        effective_control_density=resolution.effective,
        invalid_mask=resolution.invalid_mask,
        adjusted_mask=resolution.adjusted_mask,
        policy=policy,
        result_family=case.result_family,
        bandwidths=case.bandwidths,
        estimator_contract=case.estimator_contract,
        case_source_fingerprint=case.source_fingerprint,
        control_source_fingerprint=control.source_fingerprint,
        normalization_tolerance=case.normalization_tolerance,
        metadata=result_metadata,
    )


def _resolve_support(
    case_density: DensityResult,
    control_density: DensityResult,
    *,
    support: MeasuredSupport | None,
) -> MeasuredSupport:
    if support is not None:
        describe_measured_support(support)
        return support
    if isinstance(case_density, SpatialKDEResult) or isinstance(
        control_density,
        SpatialKDEResult,
    ):
        raise ValueError(
            "Spatial relative risk requires support=GridSupport because "
            "SpatialKDEResult does not retain complete grid geometry."
        )
    case_support = _embedded_support(case_density)
    control_support = _embedded_support(control_density)
    require_same_measured_support(case_support, control_support)
    return case_support


def _embedded_support(result: DensityResult) -> MeasuredSupport:
    if isinstance(result, NetworkField):
        return result.support
    if isinstance(result, SpatiotemporalKDEResult):
        return result.support
    if isinstance(result, NetworkTimeField):
        return result.support
    if isinstance(result, SpatialKDEResult):
        raise ValueError("SpatialKDEResult requires an explicit GridSupport.")
    raise TypeError(
        "result must be SpatialKDEResult, NetworkField, "
        "SpatiotemporalKDEResult, or NetworkTimeField."
    )


def _validate_normalization_tolerance(value: float) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError("normalization_tolerance must be a positive number.")
    tolerance = float(value)
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("normalization_tolerance must be finite and positive.")
    return tolerance
