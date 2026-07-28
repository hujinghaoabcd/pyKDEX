# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Closed public dispatch for built-in Bootstrap KDE adapters."""

from __future__ import annotations

from typing import overload

from pykdex.data import GridSupport, SpatialEvents
from pykdex.estimators.network_kde import NetworkKDE
from pykdex.estimators.spatial_kde import SpatialKDE
from pykdex.network.workspace import NetworkWorkspace
from pykdex.uncertainty.network import bootstrap_network_kde
from pykdex.uncertainty.plan import BootstrapPlan
from pykdex.uncertainty.results import BootstrapResult
from pykdex.uncertainty.spatial import bootstrap_kde as bootstrap_spatial_kde


@overload
def bootstrap_kde(
    estimator: SpatialKDE,
    events: SpatialEvents,
    support: GridSupport,
    *,
    plan: BootstrapPlan | None = None,
) -> BootstrapResult: ...


@overload
def bootstrap_kde(
    estimator: NetworkKDE,
    events: NetworkWorkspace,
    support: None = None,
    *,
    plan: BootstrapPlan | None = None,
) -> BootstrapResult: ...


def bootstrap_kde(
    estimator: SpatialKDE | NetworkKDE,
    events: SpatialEvents | NetworkWorkspace,
    support: GridSupport | None = None,
    *,
    plan: BootstrapPlan | None = None,
) -> BootstrapResult:
    """Run a closed built-in ordinary Bootstrap adapter for the estimator domain.

    The second parameter retains the public name ``events`` for compatibility with
    the original spatial adapter. For ``NetworkKDE`` it receives a prepared
    ``NetworkWorkspace`` containing already-snapped accepted events.
    """
    if isinstance(estimator, SpatialKDE):
        if not isinstance(events, SpatialEvents):
            raise TypeError(
                "SpatialKDE bootstrap requires events to be a SpatialEvents object."
            )
        if not isinstance(support, GridSupport):
            raise TypeError(
                "SpatialKDE bootstrap requires an explicit GridSupport object."
            )
        return bootstrap_spatial_kde(estimator, events, support, plan=plan)
    if isinstance(estimator, NetworkKDE):
        if not isinstance(events, NetworkWorkspace):
            raise TypeError(
                "NetworkKDE bootstrap requires events to be a NetworkWorkspace object."
            )
        if support is not None:
            raise TypeError(
                "NetworkKDE bootstrap uses workspace.lixels and does not accept support."
            )
        return bootstrap_network_kde(estimator, events, plan=plan)
    raise TypeError("estimator must be a SpatialKDE or NetworkKDE.")
