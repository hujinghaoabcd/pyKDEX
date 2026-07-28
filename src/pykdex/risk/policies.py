# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Explicit denominator policies for rate and risk calculations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import numpy as np

from pykdex.data._utils import readonly_array


@dataclass(frozen=True)
class DenominatorPolicy:
    """Immutable and explicit handling of small or zero denominators.

    ``raise`` and ``nan`` classify values less than or equal to
    ``validity_threshold`` as invalid. ``minimum`` replaces values below
    ``minimum_denominator`` by that positive lower bound. No hidden epsilon is
    introduced.
    """

    mode: str = "raise"
    validity_threshold: float = 0.0
    minimum_denominator: float | None = None

    def __post_init__(self) -> None:
        mode = str(self.mode).strip().lower()
        if mode not in {"raise", "nan", "minimum"}:
            raise ValueError("mode must be 'raise', 'nan', or 'minimum'.")
        threshold = float(self.validity_threshold)
        if not np.isfinite(threshold) or threshold < 0.0:
            raise ValueError("validity_threshold must be finite and non-negative.")
        minimum = self.minimum_denominator
        if mode == "minimum":
            if minimum is None:
                raise ValueError("minimum mode requires minimum_denominator.")
            minimum = float(minimum)
            if not np.isfinite(minimum) or minimum <= 0.0:
                raise ValueError("minimum_denominator must be finite and positive.")
            if threshold != 0.0:
                raise ValueError(
                    "minimum mode uses minimum_denominator and requires "
                    "validity_threshold=0."
                )
        elif minimum is not None:
            raise ValueError("minimum_denominator is only valid when mode='minimum'.")
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "validity_threshold", threshold)
        object.__setattr__(self, "minimum_denominator", minimum)

    @classmethod
    def raise_invalid(cls, *, validity_threshold: float = 0.0) -> "DenominatorPolicy":
        """Reject calculations containing an invalid denominator."""
        return cls(mode="raise", validity_threshold=validity_threshold)

    @classmethod
    def nan_invalid(cls, *, validity_threshold: float = 0.0) -> "DenominatorPolicy":
        """Return NaN where a denominator is invalid."""
        return cls(mode="nan", validity_threshold=validity_threshold)

    @classmethod
    def minimum(cls, minimum_denominator: float) -> "DenominatorPolicy":
        """Floor denominators at an explicit positive lower bound."""
        return cls(mode="minimum", minimum_denominator=minimum_denominator)


DenominatorPolicyInput: TypeAlias = DenominatorPolicy | str


@dataclass(frozen=True)
class DenominatorResolution:
    """Read-only result of applying a denominator policy."""

    effective: np.ndarray
    invalid_mask: np.ndarray
    adjusted_mask: np.ndarray

    def __post_init__(self) -> None:
        effective = readonly_array(
            self.effective,
            dtype=float,
            ndim=1,
            name="effective",
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
        if invalid.shape != effective.shape or adjusted.shape != effective.shape:
            raise ValueError("denominator masks must match effective values.")
        object.__setattr__(self, "effective", effective)
        object.__setattr__(self, "invalid_mask", invalid)
        object.__setattr__(self, "adjusted_mask", adjusted)


def resolve_denominator_policy(
    policy: DenominatorPolicyInput = "raise",
    *,
    validity_threshold: float = 0.0,
    minimum_denominator: float | None = None,
) -> DenominatorPolicy:
    """Resolve a policy object or canonical policy name."""
    if isinstance(policy, DenominatorPolicy):
        if validity_threshold != 0.0 or minimum_denominator is not None:
            raise ValueError(
                "Do not combine a DenominatorPolicy object with policy parameters."
            )
        return policy
    mode = str(policy).strip().lower()
    return DenominatorPolicy(
        mode=mode,
        validity_threshold=validity_threshold,
        minimum_denominator=minimum_denominator,
    )


def apply_denominator_policy(
    values: np.ndarray,
    policy: DenominatorPolicy,
) -> DenominatorResolution:
    """Apply ``policy`` to finite non-negative denominator values."""
    denominator = readonly_array(values, dtype=float, ndim=1, name="denominator")
    if not np.all(np.isfinite(denominator)) or np.any(denominator < 0.0):
        raise ValueError("denominator values must be finite and non-negative.")

    if policy.mode == "minimum":
        assert policy.minimum_denominator is not None
        invalid = denominator <= 0.0
        adjusted = denominator < policy.minimum_denominator
        effective = np.maximum(denominator, policy.minimum_denominator)
        return DenominatorResolution(effective, invalid, adjusted)

    invalid = denominator <= policy.validity_threshold
    adjusted = np.zeros_like(invalid)
    if policy.mode == "raise" and np.any(invalid):
        count = int(np.count_nonzero(invalid))
        raise ValueError(
            f"Denominator policy rejected {count} value(s) at or below "
            f"{policy.validity_threshold}."
        )
    effective = denominator.copy()
    if policy.mode == "nan":
        effective[invalid] = np.nan
    return DenominatorResolution(effective, invalid, adjusted)
