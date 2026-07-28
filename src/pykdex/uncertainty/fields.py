# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Immutable empirical field ensembles and pointwise percentile intervals."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np

from pykdex.data._utils import readonly_array, stable_fingerprint
from pykdex.risk.support import (
    MeasuredSupport,
    SupportDescriptor,
    describe_measured_support,
)

_FIELD_FAMILIES = frozenset(
    {
        "density",
        "intensity",
        "event_rate",
        "relative_risk",
        "log_relative_risk",
    }
)


def _normalize_family(value: str) -> str:
    family = str(value).strip().lower()
    if family not in _FIELD_FAMILIES:
        raise ValueError(
            "field_family must be density, intensity, event_rate, relative_risk, "
            "or log_relative_risk."
        )
    return family


def _validate_fingerprint(value: str, *, name: str) -> str:
    fingerprint = str(value).strip()
    if not fingerprint:
        raise ValueError(f"{name} must be a non-empty string.")
    return fingerprint


def _validate_field_values(
    values: np.ndarray,
    *,
    family: str,
    valid_mask: np.ndarray,
    name: str,
) -> None:
    invalid = ~valid_mask
    if values.ndim == 1:
        invalid_values = values[invalid]
        valid_values = values[valid_mask]
    else:
        invalid_values = values[:, invalid]
        valid_values = values[:, valid_mask]
    if invalid_values.size and not np.all(np.isnan(invalid_values)):
        raise ValueError(f"{name} must contain NaN at every invalid support element.")
    if np.any(np.isnan(valid_values)):
        raise ValueError(f"{name} must not contain NaN at valid support elements.")
    if np.any(np.isposinf(valid_values)):
        raise ValueError(f"{name} must not contain positive infinity.")
    if family == "log_relative_risk":
        return
    if not np.all(np.isfinite(valid_values)):
        raise ValueError(
            f"{name} must contain finite values outside log_relative_risk fields."
        )
    if np.any(valid_values < 0.0):
        raise ValueError(f"{name} must be non-negative for field_family={family!r}.")


@dataclass(frozen=True)
class FieldEnsemble:
    """Complete empirical replicate fields on one exact measured support."""

    replicate_values: np.ndarray
    observed_values: np.ndarray
    support: MeasuredSupport
    field_family: str
    observed_field_fingerprint: str
    replicate_source_fingerprints: tuple[str, ...]
    resampling_method: str
    seed_ledger_fingerprint: str
    execution_metadata: Mapping[str, Any]
    valid_mask: np.ndarray | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    descriptor: SupportDescriptor = field(init=False, repr=False)

    def __post_init__(self) -> None:
        descriptor = describe_measured_support(self.support)
        replicates = readonly_array(
            self.replicate_values,
            dtype=float,
            ndim=2,
            name="replicate_values",
        )
        observed = readonly_array(
            self.observed_values,
            dtype=float,
            ndim=1,
            name="observed_values",
        )
        if replicates.shape[0] < 2:
            raise ValueError("replicate_values must contain at least two replicates.")
        if replicates.shape[1] != descriptor.n_elements:
            raise ValueError(
                "replicate_values must contain one column per support element."
            )
        if observed.shape != (descriptor.n_elements,):
            raise ValueError(
                "observed_values must contain one value per support element."
            )
        valid = (
            np.ones(descriptor.n_elements, dtype=bool)
            if self.valid_mask is None
            else np.asarray(self.valid_mask, dtype=bool)
        )
        valid = readonly_array(valid, dtype=bool, ndim=1, name="valid_mask")
        if valid.shape != (descriptor.n_elements,):
            raise ValueError("valid_mask must contain one value per support element.")
        family = _normalize_family(self.field_family)
        _validate_field_values(
            replicates,
            family=family,
            valid_mask=valid,
            name="replicate_values",
        )
        _validate_field_values(
            observed,
            family=family,
            valid_mask=valid,
            name="observed_values",
        )
        observed_fingerprint = _validate_fingerprint(
            self.observed_field_fingerprint,
            name="observed_field_fingerprint",
        )
        replicate_fingerprints = tuple(
            _validate_fingerprint(value, name="replicate_source_fingerprint")
            for value in self.replicate_source_fingerprints
        )
        if len(replicate_fingerprints) != replicates.shape[0]:
            raise ValueError(
                "replicate_source_fingerprints must contain one value per replicate."
            )
        method = str(self.resampling_method).strip().lower()
        if method != "ordinary":
            raise ValueError("resampling_method must be 'ordinary'.")
        seed_fingerprint = _validate_fingerprint(
            self.seed_ledger_fingerprint,
            name="seed_ledger_fingerprint",
        )
        object.__setattr__(self, "replicate_values", replicates)
        object.__setattr__(self, "observed_values", observed)
        object.__setattr__(self, "field_family", family)
        object.__setattr__(self, "observed_field_fingerprint", observed_fingerprint)
        object.__setattr__(
            self,
            "replicate_source_fingerprints",
            replicate_fingerprints,
        )
        object.__setattr__(self, "resampling_method", method)
        object.__setattr__(self, "seed_ledger_fingerprint", seed_fingerprint)
        object.__setattr__(
            self,
            "execution_metadata",
            MappingProxyType(dict(self.execution_metadata)),
        )
        object.__setattr__(self, "valid_mask", valid)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        object.__setattr__(self, "descriptor", descriptor)

    @property
    def n_replicates(self) -> int:
        """Number of stored empirical replicates."""
        return int(self.replicate_values.shape[0])

    @property
    def n_elements(self) -> int:
        """Number of measured support elements."""
        return self.descriptor.n_elements

    @property
    def memory_bytes(self) -> int:
        """Owned NumPy storage used by ensemble values and validity state."""
        assert self.valid_mask is not None
        return int(
            self.replicate_values.nbytes
            + self.observed_values.nbytes
            + self.valid_mask.nbytes
        )

    @property
    def fingerprint(self) -> str:
        """Deterministic exact-support ensemble fingerprint."""
        assert self.valid_mask is not None
        return stable_fingerprint(
            "FieldEnsemble",
            self.replicate_values,
            self.observed_values,
            self.descriptor.fingerprint,
            self.field_family,
            self.observed_field_fingerprint,
            self.replicate_source_fingerprints,
            self.resampling_method,
            self.seed_ledger_fingerprint,
            dict(self.execution_metadata),
            self.valid_mask,
            dict(self.metadata),
        )


@dataclass(frozen=True)
class PointwiseInterval:
    """Pointwise percentile bootstrap summary on one measured support."""

    lower: np.ndarray
    estimate: np.ndarray
    upper: np.ndarray
    standard_error: np.ndarray
    bias: np.ndarray
    support: MeasuredSupport
    field_family: str
    confidence_level: float
    source_ensemble_fingerprint: str
    valid_mask: np.ndarray | None = None
    method: str = "percentile"
    descriptor: SupportDescriptor = field(init=False, repr=False)

    def __post_init__(self) -> None:
        descriptor = describe_measured_support(self.support)
        arrays = {
            name: readonly_array(value, dtype=float, ndim=1, name=name)
            for name, value in (
                ("lower", self.lower),
                ("estimate", self.estimate),
                ("upper", self.upper),
                ("standard_error", self.standard_error),
                ("bias", self.bias),
            )
        }
        if any(value.shape != (descriptor.n_elements,) for value in arrays.values()):
            raise ValueError(
                "interval arrays must contain one value per support element."
            )
        valid = (
            np.ones(descriptor.n_elements, dtype=bool)
            if self.valid_mask is None
            else np.asarray(self.valid_mask, dtype=bool)
        )
        valid = readonly_array(valid, dtype=bool, ndim=1, name="valid_mask")
        if valid.shape != (descriptor.n_elements,):
            raise ValueError("valid_mask must contain one value per support element.")
        family = _normalize_family(self.field_family)
        for name in ("lower", "estimate", "upper"):
            _validate_field_values(
                arrays[name],
                family=family,
                valid_mask=valid,
                name=name,
            )
        invalid = ~valid
        for name in ("standard_error", "bias"):
            values = arrays[name]
            if values[invalid].size and not np.all(np.isnan(values[invalid])):
                raise ValueError(f"{name} must be NaN at invalid support elements.")
            if np.any(np.isinf(values[valid])):
                raise ValueError(f"{name} must not contain infinity.")
            if family != "log_relative_risk" and np.any(np.isnan(values[valid])):
                raise ValueError(f"{name} must be finite at valid support elements.")
        finite_bounds = (
            valid & np.isfinite(arrays["lower"]) & np.isfinite(arrays["upper"])
        )
        if np.any(arrays["lower"][finite_bounds] > arrays["upper"][finite_bounds]):
            raise ValueError("lower must not exceed upper.")
        if isinstance(self.confidence_level, (bool, np.bool_)):
            raise TypeError("confidence_level must be a number in (0, 1).")
        level = float(self.confidence_level)
        if not np.isfinite(level) or not 0.0 < level < 1.0:
            raise ValueError("confidence_level must be finite and lie in (0, 1).")
        method = str(self.method).strip().lower()
        if method != "percentile":
            raise ValueError("method must be 'percentile'.")
        source = _validate_fingerprint(
            self.source_ensemble_fingerprint,
            name="source_ensemble_fingerprint",
        )
        for name, value in arrays.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "field_family", family)
        object.__setattr__(self, "confidence_level", level)
        object.__setattr__(self, "source_ensemble_fingerprint", source)
        object.__setattr__(self, "valid_mask", valid)
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "descriptor", descriptor)

    @property
    def fingerprint(self) -> str:
        """Deterministic pointwise-summary fingerprint."""
        assert self.valid_mask is not None
        return stable_fingerprint(
            "PointwiseInterval",
            self.lower,
            self.estimate,
            self.upper,
            self.standard_error,
            self.bias,
            self.descriptor.fingerprint,
            self.field_family,
            self.confidence_level,
            self.source_ensemble_fingerprint,
            self.valid_mask,
            self.method,
        )


def pointwise_percentile_interval(
    ensemble: FieldEnsemble,
    *,
    confidence_level: float = 0.95,
) -> PointwiseInterval:
    """Summarize stored replicates as empirical pointwise percentiles."""
    if not isinstance(ensemble, FieldEnsemble):
        raise TypeError("ensemble must be a FieldEnsemble.")
    if isinstance(confidence_level, (bool, np.bool_)):
        raise TypeError("confidence_level must be a number in (0, 1).")
    level = float(confidence_level)
    if not np.isfinite(level) or not 0.0 < level < 1.0:
        raise ValueError("confidence_level must be finite and lie in (0, 1).")
    alpha = 1.0 - level
    valid = np.asarray(ensemble.valid_mask, dtype=bool)
    lower = np.full(ensemble.n_elements, np.nan, dtype=float)
    upper = np.full(ensemble.n_elements, np.nan, dtype=float)
    standard_error = np.full(ensemble.n_elements, np.nan, dtype=float)
    bias = np.full(ensemble.n_elements, np.nan, dtype=float)
    valid_indices = np.flatnonzero(valid)
    if valid_indices.size:
        values = ensemble.replicate_values[:, valid_indices]
        finite_columns = np.all(np.isfinite(values), axis=0)
        if np.any(finite_columns):
            selected = valid_indices[finite_columns]
            finite_values = values[:, finite_columns]
            lower[selected] = np.quantile(finite_values, alpha / 2.0, axis=0)
            upper[selected] = np.quantile(
                finite_values,
                1.0 - alpha / 2.0,
                axis=0,
            )
            standard_error[selected] = np.std(finite_values, axis=0, ddof=1)
            bias[selected] = (
                np.mean(finite_values, axis=0)
                - ensemble.observed_values[selected]
            )
        nonfinite_columns = ~finite_columns
        if np.any(nonfinite_columns):
            selected = valid_indices[nonfinite_columns]
            nonfinite_values = values[:, nonfinite_columns]
            lower[selected] = np.quantile(
                nonfinite_values,
                alpha / 2.0,
                axis=0,
                method="inverted_cdf",
            )
            upper[selected] = np.quantile(
                nonfinite_values,
                1.0 - alpha / 2.0,
                axis=0,
                method="inverted_cdf",
            )
    return PointwiseInterval(
        lower=lower,
        estimate=ensemble.observed_values,
        upper=upper,
        standard_error=standard_error,
        bias=bias,
        support=ensemble.support,
        field_family=ensemble.field_family,
        confidence_level=level,
        source_ensemble_fingerprint=ensemble.fingerprint,
        valid_mask=ensemble.valid_mask,
    )
