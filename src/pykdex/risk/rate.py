# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Exposure-adjusted event-rate fields on measured supports."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
import pandas as pd

from pykdex.data._utils import normalize_unit, readonly_array, stable_fingerprint
from pykdex.risk.exposure import ExposureField
from pykdex.risk.intensity import IntensityResult, adapt_intensity_result
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
class EventRateField:
    """Event intensity divided by exposure density on measured support."""

    values: np.ndarray
    support: MeasuredSupport
    event_intensity: np.ndarray
    exposure: ExposureField
    effective_exposure: np.ndarray
    invalid_mask: np.ndarray
    adjusted_mask: np.ndarray
    policy: DenominatorPolicy
    event_unit: str
    intensity_fingerprint: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    descriptor: SupportDescriptor = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.exposure, ExposureField):
            raise TypeError("exposure must be an ExposureField instance.")
        if not isinstance(self.policy, DenominatorPolicy):
            raise TypeError("policy must be a DenominatorPolicy instance.")
        descriptor = require_same_measured_support(
            self.support,
            self.exposure.support,
        )
        values = readonly_array(self.values, dtype=float, ndim=1, name="values")
        intensity = readonly_array(
            self.event_intensity,
            dtype=float,
            ndim=1,
            name="event_intensity",
        )
        effective = readonly_array(
            self.effective_exposure,
            dtype=float,
            ndim=1,
            name="effective_exposure",
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
            ("event_intensity", intensity),
            ("effective_exposure", effective),
            ("invalid_mask", invalid),
            ("adjusted_mask", adjusted),
        ):
            if array.shape != expected_shape:
                raise ValueError(f"{name} must contain one value per support element.")
        if not np.all(np.isfinite(intensity)) or np.any(intensity < 0.0):
            raise ValueError("event_intensity must be finite and non-negative.")
        if np.any(np.isinf(values)) or np.any(values[np.isfinite(values)] < 0.0):
            raise ValueError("event-rate values must be non-negative and never infinite.")

        resolution = apply_denominator_policy(self.exposure.values, self.policy)
        if not np.array_equal(invalid, resolution.invalid_mask):
            raise ValueError("invalid_mask is inconsistent with exposure and policy.")
        if not np.array_equal(adjusted, resolution.adjusted_mask):
            raise ValueError("adjusted_mask is inconsistent with exposure and policy.")
        if not np.array_equal(effective, resolution.effective, equal_nan=True):
            raise ValueError("effective_exposure is inconsistent with the policy.")

        valid = np.isfinite(effective)
        expected_rate = np.full_like(intensity, np.nan)
        np.divide(intensity, effective, out=expected_rate, where=valid)
        if not np.allclose(values, expected_rate, rtol=1e-12, atol=1e-15, equal_nan=True):
            raise ValueError("values are inconsistent with intensity/exposure division.")
        if self.policy.mode == "nan":
            if not np.array_equal(np.isnan(values), invalid):
                raise ValueError("NaN event rates must occur exactly at invalid cells.")
        elif np.any(np.isnan(values)):
            raise ValueError("NaN event rates require policy mode='nan'.")

        event_unit = normalize_unit(self.event_unit, name="event_unit")
        if event_unit is None:
            raise ValueError("event_unit must be explicit.")
        fingerprint = str(self.intensity_fingerprint).strip()
        if not fingerprint:
            raise ValueError("intensity_fingerprint must be non-empty.")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "event_intensity", intensity)
        object.__setattr__(self, "effective_exposure", effective)
        object.__setattr__(self, "invalid_mask", invalid)
        object.__setattr__(self, "adjusted_mask", adjusted)
        object.__setattr__(self, "event_unit", event_unit)
        object.__setattr__(self, "intensity_fingerprint", fingerprint)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        object.__setattr__(self, "descriptor", descriptor)

    @property
    def rate_unit(self) -> str:
        """Event-weight unit per exposure unit."""
        return f"{self.event_unit}/{self.exposure.exposure_unit}"

    @property
    def event_mass(self) -> float:
        """Integrated event intensity on the measured support."""
        return float(np.dot(self.event_intensity, self.descriptor.measure))

    @property
    def total_exposure(self) -> float:
        """Original total exposure before denominator handling."""
        return self.exposure.total_exposure

    @property
    def effective_exposure_total(self) -> float:
        """Total effective exposure over cells with a defined denominator."""
        valid = np.isfinite(self.effective_exposure)
        return float(
            np.dot(
                self.effective_exposure[valid],
                self.descriptor.measure[valid],
            )
        )

    @property
    def exposure_weighted_mean_rate(self) -> float:
        """Mean rate weighted by original exposure over finite-rate cells."""
        valid = np.isfinite(self.values)
        weights = self.exposure.values[valid] * self.descriptor.measure[valid]
        denominator = float(np.sum(weights))
        if denominator <= 0.0:
            return float("nan")
        return float(np.dot(self.values[valid], weights) / denominator)

    @property
    def effective_exposure_weighted_mean_rate(self) -> float:
        """Mean rate weighted by the effective exposure used in division."""
        valid = np.isfinite(self.values) & np.isfinite(self.effective_exposure)
        weights = self.effective_exposure[valid] * self.descriptor.measure[valid]
        denominator = float(np.sum(weights))
        if denominator <= 0.0:
            return float("nan")
        return float(np.dot(self.values[valid], weights) / denominator)

    @property
    def fingerprint(self) -> str:
        """Deterministic event-rate field fingerprint."""
        return stable_fingerprint(
            self.values,
            self.descriptor.fingerprint,
            self.event_intensity,
            self.exposure.fingerprint,
            self.effective_exposure,
            self.invalid_mask,
            self.adjusted_mask,
            self.policy.mode,
            self.policy.validity_threshold,
            self.policy.minimum_denominator,
            self.event_unit,
            self.intensity_fingerprint,
            dict(self.metadata),
        )

    def to_frame(self) -> pd.DataFrame:
        """Return support attributes and all numerator/denominator diagnostics."""
        frame = self.support.to_frame()
        frame["event_intensity"] = self.event_intensity
        frame["exposure_density"] = self.exposure.values
        frame["effective_exposure_density"] = self.effective_exposure
        frame["event_rate"] = self.values
        frame["invalid_denominator"] = self.invalid_mask
        frame["adjusted_denominator"] = self.adjusted_mask
        return frame

    def to_grid(self) -> np.ndarray:
        """Reshape rates when the support has a native grid representation."""
        reshape = getattr(self.support, "reshape", None)
        if reshape is None or not callable(reshape):
            raise ValueError("This support has no native grid reshape operation.")
        return np.asarray(reshape(self.values))

    def to_geodataframe(self) -> Any:
        """Return a GeoDataFrame when the support provides geospatial export."""
        exporter = getattr(self.support, "to_geodataframe", None)
        if exporter is None or not callable(exporter):
            raise ValueError("This support does not provide GeoDataFrame export.")
        frame = exporter()
        frame["event_intensity"] = self.event_intensity
        frame["exposure_density"] = self.exposure.values
        frame["effective_exposure_density"] = self.effective_exposure
        frame["event_rate"] = self.values
        frame["invalid_denominator"] = self.invalid_mask
        frame["adjusted_denominator"] = self.adjusted_mask
        return frame


def estimate_event_rate(
    event_intensity: IntensityResult,
    exposure: ExposureField,
    *,
    event_unit: str,
    zero_policy: DenominatorPolicyInput = "raise",
    validity_threshold: float = 0.0,
    minimum_denominator: float | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EventRateField:
    """Divide measured event intensity by an explicit exposure-density field."""
    if not isinstance(exposure, ExposureField):
        raise TypeError("exposure must be an ExposureField instance.")
    describe_measured_support(exposure.support)
    policy = resolve_denominator_policy(
        zero_policy,
        validity_threshold=validity_threshold,
        minimum_denominator=minimum_denominator,
    )
    intensity = adapt_intensity_result(
        event_intensity,
        support=exposure.support,
        event_unit=event_unit,
    )
    resolution = apply_denominator_policy(exposure.values, policy)
    valid = np.isfinite(resolution.effective)
    rates = np.full_like(intensity.values, np.nan)
    np.divide(
        intensity.values,
        resolution.effective,
        out=rates,
        where=valid,
    )
    result_metadata = dict(metadata or {})
    result_metadata.update(
        {
            "result_family": intensity.result_family,
            "invalid_denominator_count": int(
                np.count_nonzero(resolution.invalid_mask)
            ),
            "adjusted_denominator_count": int(
                np.count_nonzero(resolution.adjusted_mask)
            ),
            "zero_policy": policy.mode,
            "validity_threshold": policy.validity_threshold,
            "minimum_denominator": policy.minimum_denominator,
            "source_metadata": dict(intensity.metadata),
        }
    )
    return EventRateField(
        values=rates,
        support=exposure.support,
        event_intensity=intensity.values,
        exposure=exposure,
        effective_exposure=resolution.effective,
        invalid_mask=resolution.invalid_mask,
        adjusted_mask=resolution.adjusted_mask,
        policy=policy,
        event_unit=intensity.event_unit,
        intensity_fingerprint=intensity.source_fingerprint,
        metadata=result_metadata,
    )
