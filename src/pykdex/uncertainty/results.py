# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Immutable completed-bootstrap results."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np

from pykdex.data._utils import stable_fingerprint
from pykdex.uncertainty.fields import FieldEnsemble, PointwiseInterval
from pykdex.uncertainty.plan import BootstrapPlan


@dataclass(frozen=True)
class BootstrapResult:
    """Completed fail-fast ordinary Bootstrap result for one field family."""

    ensemble: FieldEnsemble
    interval: PointwiseInterval
    plan: BootstrapPlan
    operation: str
    estimator_family: str
    seed_metadata: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.ensemble, FieldEnsemble):
            raise TypeError("ensemble must be a FieldEnsemble.")
        if not isinstance(self.interval, PointwiseInterval):
            raise TypeError("interval must be a PointwiseInterval.")
        if not isinstance(self.plan, BootstrapPlan):
            raise TypeError("plan must be a BootstrapPlan.")
        if self.plan.n_resamples != self.ensemble.n_replicates:
            raise ValueError("plan and ensemble replicate counts differ.")
        if not np.isclose(
            self.plan.confidence_level,
            self.interval.confidence_level,
            rtol=0.0,
            atol=0.0,
        ):
            raise ValueError("plan and interval confidence levels differ.")
        if self.interval.source_ensemble_fingerprint != self.ensemble.fingerprint:
            raise ValueError("interval does not belong to the supplied ensemble.")
        if self.interval.descriptor.fingerprint != self.ensemble.descriptor.fingerprint:
            raise ValueError("interval and ensemble supports differ.")
        if self.interval.field_family != self.ensemble.field_family:
            raise ValueError("interval and ensemble field families differ.")
        operation = str(self.operation).strip().lower()
        if operation not in {
            "bootstrap_kde",
            "bootstrap_event_rate",
            "bootstrap_relative_risk",
        }:
            raise ValueError("operation is not a supported Bootstrap operation.")
        family = str(self.estimator_family).strip().lower()
        if not family:
            raise ValueError("estimator_family must be non-empty.")
        seed_metadata = dict(self.seed_metadata)
        seed_fingerprint = str(
            seed_metadata.get("seed_ledger_fingerprint", "")
        ).strip()
        if not seed_fingerprint:
            raise ValueError(
                "seed_metadata must contain seed_ledger_fingerprint."
            )
        if seed_fingerprint != self.ensemble.seed_ledger_fingerprint:
            raise ValueError("seed metadata and ensemble seed fingerprints differ.")
        if int(seed_metadata.get("n_logical_tasks", -1)) != self.ensemble.n_replicates:
            raise ValueError("seed metadata logical-task count differs from ensemble.")
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "estimator_family", family)
        object.__setattr__(
            self,
            "seed_metadata",
            MappingProxyType(seed_metadata),
        )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def fingerprint(self) -> str:
        """Deterministic completed-bootstrap fingerprint."""
        return stable_fingerprint(
            "BootstrapResult",
            self.ensemble.fingerprint,
            self.interval.fingerprint,
            self.plan.fingerprint,
            self.operation,
            self.estimator_family,
            dict(self.seed_metadata),
            dict(self.metadata),
        )
