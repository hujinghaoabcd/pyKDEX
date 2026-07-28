# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Immutable user-facing bootstrap requests."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pykdex.data._utils import stable_fingerprint
from pykdex.execution import ExecutionPlan


@dataclass(frozen=True)
class BootstrapPlan:
    """Requested ordinary bootstrap and pointwise interval contract.

    Args:
        n_resamples: Number of bootstrap replicates. At least two are required.
        confidence_level: Pointwise percentile interval level in ``(0, 1)``.
        random_state: Optional non-negative integer root seed.
        method: Resampling method. Version 0.0.16 initially supports only
            ``"ordinary"``.
        store_replicates: Whether complete replicate fields are retained. The
            first implementation requires this to be true.
        execution_plan: Optional replicate execution and memory contract.
    """

    n_resamples: int = 999
    confidence_level: float = 0.95
    random_state: int | None = None
    method: str = "ordinary"
    store_replicates: bool = True
    execution_plan: ExecutionPlan | None = None

    def __post_init__(self) -> None:
        if isinstance(self.n_resamples, (bool, np.bool_)) or not isinstance(
            self.n_resamples,
            (int, np.integer),
        ):
            raise TypeError("n_resamples must be an integer of at least two.")
        resamples = int(self.n_resamples)
        if resamples < 2:
            raise ValueError("n_resamples must be at least two.")
        if isinstance(self.confidence_level, (bool, np.bool_)):
            raise TypeError("confidence_level must be a number strictly between zero and one.")
        level = float(self.confidence_level)
        if not np.isfinite(level) or not 0.0 < level < 1.0:
            raise ValueError(
                "confidence_level must be finite and strictly between zero and one."
            )
        seed = self.random_state
        if seed is not None:
            if isinstance(seed, (bool, np.bool_)) or not isinstance(
                seed,
                (int, np.integer),
            ):
                raise TypeError("random_state must be a non-negative integer or None.")
            seed = int(seed)
            if seed < 0:
                raise ValueError("random_state must be non-negative or None.")
        method = str(self.method).strip().lower()
        if method != "ordinary":
            raise ValueError("method must be 'ordinary' in the initial implementation.")
        if not isinstance(self.store_replicates, (bool, np.bool_)):
            raise TypeError("store_replicates must be boolean.")
        if not bool(self.store_replicates):
            raise ValueError(
                "store_replicates=False is not supported; complete replicate storage "
                "is required for reproducible empirical quantiles."
            )
        if self.execution_plan is not None and not isinstance(
            self.execution_plan,
            ExecutionPlan,
        ):
            raise TypeError("execution_plan must be an ExecutionPlan or None.")
        object.__setattr__(self, "n_resamples", resamples)
        object.__setattr__(self, "confidence_level", level)
        object.__setattr__(self, "random_state", seed)
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "store_replicates", True)

    @property
    def fingerprint(self) -> str:
        """Deterministic bootstrap-request fingerprint."""
        return stable_fingerprint(
            "BootstrapPlan",
            self.n_resamples,
            self.confidence_level,
            self.random_state,
            self.method,
            self.store_replicates,
            (
                None
                if self.execution_plan is None
                else self.execution_plan.fingerprint
            ),
        )
