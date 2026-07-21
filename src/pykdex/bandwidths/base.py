# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Base class for bandwidth strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from pykdex.kernels import BaseKernel
    from pykdex.metrics import BaseMetric


class BaseBandwidth(ABC):
    """Strategy that resolves a scalar or event-specific bandwidth."""

    @abstractmethod
    def resolve(
        self,
        events: np.ndarray,
        *,
        weights: np.ndarray | None = None,
        metric: BaseMetric | None = None,
        kernel: BaseKernel | None = None,
    ) -> float | np.ndarray:
        """Resolve bandwidth values for fitted events and estimator context."""
