"""Shared deterministic test fixtures."""

import numpy as np
import pytest


@pytest.fixture
def events_2d():
    return np.array(
        [
            [-0.5, 0.0],
            [0.0, 0.0],
            [0.5, 0.0],
            [0.0, 0.5],
        ],
        dtype=float,
    )
