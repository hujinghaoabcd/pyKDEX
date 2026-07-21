# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Public package interface for pyKDEX.

Author:
    Jinghao Hu
"""

from __future__ import annotations

__author__ = "Jinghao Hu"
__license__ = "MIT"
__version__ = "0.0.1"

from pykdex.bandwidths import FixedBandwidth
from pykdex.core import SpatialKDEResult
from pykdex.estimators import SpatialKDE
from pykdex.kernels import (
    EpanechnikovKernel,
    ExponentialKernel,
    GaussianKernel,
    QuarticKernel,
    TriangularKernel,
    UniformKernel,
    get_kernel,
)
from pykdex.metrics import EuclideanMetric

__all__ = [
    "SpatialKDE",
    "SpatialKDEResult",
    "FixedBandwidth",
    "EuclideanMetric",
    "GaussianKernel",
    "EpanechnikovKernel",
    "QuarticKernel",
    "TriangularKernel",
    "UniformKernel",
    "ExponentialKernel",
    "get_kernel",
    "__version__",
]
