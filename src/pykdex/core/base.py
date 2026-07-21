# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Base classes for pyKDEX estimators.

The hierarchy standardizes atomic fitted-state replacement, input ownership,
and common result metadata. The package exposes one NumPy/SciPy numerical route;
future acceleration belongs behind numerical routines rather than in estimator
constructors.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

import numpy as np

from pykdex.core.exceptions import NotFittedError
from pykdex.core.validation import validate_target


class BaseEstimator(ABC):
    """Root class for all pyKDEX estimators."""

    def __init__(self, *, random_state: Optional[int] = None, verbose: bool = False):
        if random_state is not None:
            if isinstance(random_state, (bool, np.bool_)) or not isinstance(
                random_state, (int, np.integer)
            ):
                raise TypeError("random_state must be an integer or None.")
        if not isinstance(verbose, (bool, np.bool_)):
            raise TypeError("verbose must be boolean.")
        self.random_state = random_state
        self.verbose = bool(verbose)
        self._is_fitted = False

    @property
    def is_fitted_(self) -> bool:
        """Whether the estimator completed a successful fit."""
        return bool(self._is_fitted)

    def _mark_fitted(self) -> None:
        self._is_fitted = True

    def _mark_unfitted(self) -> None:
        self._is_fitted = False

    def _check_is_fitted(self) -> None:
        if not self._is_fitted:
            raise NotFittedError(
                f"{self.__class__.__name__} is not fitted yet. Call 'fit' first."
            )


class BaseKDE(BaseEstimator):
    """Base class for kernel density and intensity estimators."""

    def __init__(
        self,
        *,
        target: str = "density",
        random_state: Optional[int] = None,
        verbose: bool = False,
    ) -> None:
        super().__init__(random_state=random_state, verbose=verbose)
        self.target = validate_target(target)
        self._reset_common_state()

    def _reset_common_state(self) -> None:
        self.n_events_: Optional[int] = None
        self.dimension_: Optional[int] = None
        self.coordinate_names_in_: Optional[np.ndarray] = None
        self.events_: Optional[np.ndarray] = None
        self.weights_: Optional[np.ndarray] = None
        self.weight_sum_: Optional[float] = None
        self.bandwidth_: Optional[float | np.ndarray] = None
        self.event_crs_: Optional[str] = None
        self.spatial_unit_: Optional[str] = None
        self.event_fingerprint_: Optional[str] = None
        self.fit_metadata_: Optional[dict[str, Any]] = None

    @abstractmethod
    def _reset_fit_state(self) -> None:
        """Clear all fitted state before each fit attempt."""
