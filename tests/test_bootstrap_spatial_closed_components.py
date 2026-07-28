# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest

from pykdex import GridSupport, SpatialEvents, SpatialKDE
from pykdex.corrections import get_boundary_correction
from pykdex.kernels import get_kernel
from pykdex.metrics import get_metric
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde


def _events() -> SpatialEvents:
    return SpatialEvents.from_array(
        [[0.25, 0.25], [0.75, 0.75]],
        spatial_unit="m",
    )


def _support() -> GridSupport:
    return GridSupport.from_bounds(
        (0.0, 0.0, 1.0, 1.0),
        resolution=0.5,
        spatial_unit="m",
    )


@pytest.mark.parametrize(
    "estimator",
    [
        SpatialKDE(bandwidth=0.5, kernel=get_kernel("gaussian")),
        SpatialKDE(bandwidth=0.5, metric=get_metric("euclidean")),
        SpatialKDE(
            bandwidth=0.5,
            boundary_correction=get_boundary_correction("none"),
        ),
    ],
)
def test_spatial_bootstrap_rejects_component_objects(estimator: SpatialKDE) -> None:
    with pytest.raises(ValueError, match="built-in string names"):
        bootstrap_kde(
            estimator,
            _events(),
            _support(),
            plan=BootstrapPlan(n_resamples=2, random_state=1),
        )
