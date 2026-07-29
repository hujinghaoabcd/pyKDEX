# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Fixed-exposure transformation of completed intensity Bootstrap ensembles."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from pykdex.data._utils import normalize_unit, stable_fingerprint
from pykdex.risk.exposure import ExposureField
from pykdex.risk.policies import (
    DenominatorPolicy,
    DenominatorPolicyInput,
    apply_denominator_policy,
    resolve_denominator_policy,
)
from pykdex.risk.support import require_same_measured_support
from pykdex.uncertainty.fields import FieldEnsemble, pointwise_percentile_interval
from pykdex.uncertainty.results import BootstrapResult


@dataclass(frozen=True)
class _EventRateMemoryModel:
    source_ensemble_bytes: int
    exposure_and_support_bytes: int
    denominator_state_bytes: int
    output_ensemble_bytes: int
    working_bytes: int
    total_peak_bytes: int
    memory_budget_bytes: int | None

    def to_metadata(self) -> dict[str, int | None]:
        return {
            "source_ensemble_bytes": self.source_ensemble_bytes,
            "exposure_and_support_bytes": self.exposure_and_support_bytes,
            "denominator_state_bytes": self.denominator_state_bytes,
            "output_ensemble_bytes": self.output_ensemble_bytes,
            "working_bytes": self.working_bytes,
            "total_peak_bytes": self.total_peak_bytes,
            "memory_budget_bytes": self.memory_budget_bytes,
        }


def _resolve_memory_budget(value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (int, np.integer),
    ):
        raise TypeError("memory_budget_bytes must be a positive integer or None.")
    budget = int(value)
    if budget <= 0:
        raise ValueError("memory_budget_bytes must be greater than zero.")
    return budget


def _require_intensity_bootstrap(result: BootstrapResult) -> None:
    if not isinstance(result, BootstrapResult):
        raise TypeError("intensity_bootstrap must be a BootstrapResult.")
    if result.operation != "bootstrap_kde":
        raise ValueError(
            "fixed-exposure event-rate Bootstrap requires a bootstrap_kde source result."
        )
    if result.ensemble.field_family != "intensity":
        raise ValueError(
            "fixed-exposure event-rate Bootstrap requires field_family='intensity'."
        )


def _event_unit(value: str) -> str:
    unit = normalize_unit(value, name="event_unit")
    if unit is None:
        raise ValueError("event_unit must be explicit.")
    return unit


def _policy_fingerprint(policy: DenominatorPolicy) -> str:
    return stable_fingerprint(
        "EventRateDenominatorPolicy",
        policy.mode,
        policy.validity_threshold,
        policy.minimum_denominator,
    )


def _memory_model(
    intensity_bootstrap: BootstrapResult,
    exposure: ExposureField,
    *,
    memory_budget_bytes: int | None,
) -> _EventRateMemoryModel:
    ensemble = intensity_bootstrap.ensemble
    n_replicates = ensemble.n_replicates
    n_elements = ensemble.n_elements
    source_bytes = ensemble.memory_bytes
    exposure_bytes = int(exposure.values.nbytes + exposure.descriptor.measure.nbytes)
    denominator_bytes = int(n_elements * (8 + 1 + 1 + 1))
    output_bytes = int(n_replicates * n_elements * 8 + n_elements * 8 + n_elements)
    working_bytes = int(n_elements * 8)
    total = int(
        source_bytes + exposure_bytes + denominator_bytes + output_bytes + working_bytes
    )
    model = _EventRateMemoryModel(
        source_ensemble_bytes=source_bytes,
        exposure_and_support_bytes=exposure_bytes,
        denominator_state_bytes=denominator_bytes,
        output_ensemble_bytes=output_bytes,
        working_bytes=working_bytes,
        total_peak_bytes=total,
        memory_budget_bytes=memory_budget_bytes,
    )
    if memory_budget_bytes is not None and total > memory_budget_bytes:
        raise MemoryError(
            "bootstrap_event_rate requires an estimated peak of "
            f"{total} bytes, exceeding memory_budget_bytes={memory_budget_bytes}."
        )
    return model


def _derived_field_fingerprint(
    source_fingerprint: str,
    exposure: ExposureField,
    policy: DenominatorPolicy,
    event_unit: str,
) -> str:
    return stable_fingerprint(
        "FixedExposureEventRateField",
        source_fingerprint,
        exposure.fingerprint,
        _policy_fingerprint(policy),
        event_unit,
        exposure.descriptor.fingerprint,
    )


def bootstrap_event_rate(
    intensity_bootstrap: BootstrapResult,
    exposure: ExposureField,
    *,
    event_unit: str,
    zero_policy: DenominatorPolicyInput = "raise",
    validity_threshold: float = 0.0,
    minimum_denominator: float | None = None,
    memory_budget_bytes: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BootstrapResult:
    """Transform an intensity Bootstrap using one fixed measured exposure field.

    Only event-resampling uncertainty is propagated. Exposure is conditioned upon
    and is never resampled by this operation.
    """
    _require_intensity_bootstrap(intensity_bootstrap)
    if not isinstance(exposure, ExposureField):
        raise TypeError("exposure must be an ExposureField instance.")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping or None.")

    ensemble = intensity_bootstrap.ensemble
    descriptor = require_same_measured_support(ensemble.support, exposure.support)
    unit = _event_unit(event_unit)
    policy = resolve_denominator_policy(
        zero_policy,
        validity_threshold=validity_threshold,
        minimum_denominator=minimum_denominator,
    )
    resolution = apply_denominator_policy(exposure.values, policy)
    budget = _resolve_memory_budget(memory_budget_bytes)
    memory_model = _memory_model(
        intensity_bootstrap,
        exposure,
        memory_budget_bytes=budget,
    )

    source_valid = np.asarray(ensemble.valid_mask, dtype=bool)
    valid = source_valid & np.isfinite(resolution.effective)
    replicate_rates = np.full_like(ensemble.replicate_values, np.nan, dtype=float)
    observed_rates = np.full_like(ensemble.observed_values, np.nan, dtype=float)
    with np.errstate(divide="raise", invalid="raise", over="raise"):
        np.divide(
            ensemble.replicate_values,
            resolution.effective[None, :],
            out=replicate_rates,
            where=valid[None, :],
        )
        np.divide(
            ensemble.observed_values,
            resolution.effective,
            out=observed_rates,
            where=valid,
        )
    if np.any(~np.isfinite(replicate_rates[:, valid])) or np.any(
        ~np.isfinite(observed_rates[valid])
    ):
        raise FloatingPointError(
            "fixed-exposure event-rate Bootstrap produced non-finite valid rates."
        )

    observed_fingerprint = _derived_field_fingerprint(
        ensemble.observed_field_fingerprint,
        exposure,
        policy,
        unit,
    )
    replicate_fingerprints = tuple(
        _derived_field_fingerprint(
            source_fingerprint,
            exposure,
            policy,
            unit,
        )
        for source_fingerprint in ensemble.replicate_source_fingerprints
    )
    source_result_fingerprint = intensity_bootstrap.fingerprint
    common_metadata: dict[str, Any] = {
        "source_operation": intensity_bootstrap.operation,
        "source_estimator_family": intensity_bootstrap.estimator_family,
        "source_bootstrap_fingerprint": source_result_fingerprint,
        "source_intensity_ensemble_fingerprint": ensemble.fingerprint,
        "source_observed_intensity_fingerprint": ensemble.observed_field_fingerprint,
        "exposure_fingerprint": exposure.fingerprint,
        "exposure_unit": exposure.exposure_unit,
        "exposure_representation": exposure.representation,
        "support_fingerprint": descriptor.fingerprint,
        "support_kind": descriptor.kind,
        "event_unit": unit,
        "rate_unit": f"{unit}/{exposure.exposure_unit}",
        "fixed_exposure": True,
        "conditional_on_fixed_exposure": True,
        "event_uncertainty": True,
        "exposure_uncertainty": False,
        "zero_policy": policy.mode,
        "validity_threshold": policy.validity_threshold,
        "minimum_denominator": policy.minimum_denominator,
        "invalid_denominator_count": int(np.count_nonzero(resolution.invalid_mask)),
        "adjusted_denominator_count": int(np.count_nonzero(resolution.adjusted_mask)),
        "source_invalid_count": int(np.count_nonzero(~source_valid)),
        "output_invalid_count": int(np.count_nonzero(~valid)),
        "memory_model": memory_model.to_metadata(),
    }
    source_condition = ensemble.metadata.get("conditional_on_observed_event_count")
    if source_condition is not None:
        common_metadata["conditional_on_observed_event_count"] = bool(source_condition)
    result_metadata = dict(metadata or {})
    result_metadata.update(common_metadata)

    rate_ensemble = FieldEnsemble(
        replicate_values=replicate_rates,
        observed_values=observed_rates,
        support=exposure.support,
        field_family="event_rate",
        observed_field_fingerprint=observed_fingerprint,
        replicate_source_fingerprints=replicate_fingerprints,
        resampling_method=ensemble.resampling_method,
        seed_ledger_fingerprint=ensemble.seed_ledger_fingerprint,
        execution_metadata=dict(ensemble.execution_metadata),
        valid_mask=valid,
        metadata={
            **result_metadata,
            "source_execution_metadata": dict(ensemble.execution_metadata),
        },
    )
    interval = pointwise_percentile_interval(
        rate_ensemble,
        confidence_level=intensity_bootstrap.plan.confidence_level,
    )
    return BootstrapResult(
        ensemble=rate_ensemble,
        interval=interval,
        plan=intensity_bootstrap.plan,
        operation="bootstrap_event_rate",
        estimator_family=intensity_bootstrap.estimator_family,
        seed_metadata=dict(intensity_bootstrap.seed_metadata),
        metadata=result_metadata,
    )
