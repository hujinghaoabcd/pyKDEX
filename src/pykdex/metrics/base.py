# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Base class for pairwise metrics."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class BaseMetric(ABC):
    """Pairwise metric strategy."""

    name: str

    @abstractmethod
    def pairwise(self, left: np.ndarray, right: np.ndarray) -> np.ndarray:
        """Return pairwise distances."""
