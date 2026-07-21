# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Public package interface for pyKDEX.

Author:
    Jinghao Hu
"""

from __future__ import annotations

__author__ = "Jinghao Hu"
__license__ = "MIT"
__version__ = "0.0.4"

from pykdex.adapters import from_networkx_graph, from_osmnx_graph, network_from_place
from pykdex.bandwidths import (
    AbramsonBandwidth,
    FixedBandwidth,
    KNNBandwidth,
    LeastSquaresCVBandwidth,
    LikelihoodCVBandwidth,
)
from pykdex.core import BandwidthSelectionResult, SpatialKDEResult
from pykdex.data import (
    DataProvenance,
    DataValidationReport,
    GridSupport,
    KDEDataset,
    PointSupport,
    SpatialBoundary,
    SpatialEvents,
)
from pykdex.datasets import (
    load_bimodal_points,
    load_bounded_square,
    load_cross_network,
    load_disconnected_network,
    load_osmnx_fixture,
    load_ring_network,
    load_t_junction,
    make_bimodal_events,
    make_grid_network,
)
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
from pykdex.network import (
    LinearNetwork,
    LixelSupport,
    NetworkDataset,
    NetworkEvents,
    NetworkWorkspace,
    SnapResult,
    snap_events,
)
from pykdex.selection import LeastSquaresCV, LikelihoodCV

__all__ = [
    "SpatialKDE",
    "SpatialKDEResult",
    "BandwidthSelectionResult",
    "SpatialEvents",
    "PointSupport",
    "GridSupport",
    "SpatialBoundary",
    "KDEDataset",
    "DataProvenance",
    "DataValidationReport",
    "make_bimodal_events",
    "load_bimodal_points",
    "load_bounded_square",
    "load_t_junction",
    "load_cross_network",
    "load_ring_network",
    "load_disconnected_network",
    "load_osmnx_fixture",
    "make_grid_network",
    "LinearNetwork",
    "NetworkEvents",
    "SnapResult",
    "snap_events",
    "LixelSupport",
    "NetworkWorkspace",
    "NetworkDataset",
    "from_networkx_graph",
    "from_osmnx_graph",
    "network_from_place",
    "FixedBandwidth",
    "KNNBandwidth",
    "AbramsonBandwidth",
    "LikelihoodCVBandwidth",
    "LeastSquaresCVBandwidth",
    "LikelihoodCV",
    "LeastSquaresCV",
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
