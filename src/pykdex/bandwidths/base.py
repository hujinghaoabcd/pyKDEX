# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Base class for bandwidth strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class BaseBandwidth(ABC):
    """Strategy that resolves a scalar or event-specific bandwidth."""

    @abstractmethod
    def resolve(self, events: np.ndarray) -> float | np.ndarray:
        """Resolve bandwidth values for fitted events."""
