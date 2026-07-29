# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from pykdex import GridSupport, SpatialEvents, SpatialKDE
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde


def test_spatial_bootstrap_preserves_events_keyword() -> None:
    events = SpatialEvents.from_array(
        [[0.25, 0.25], [0.75, 0.75]],
        spatial_unit="m",
    )
    support = GridSupport.from_bounds(
        (0.0, 0.0, 1.0, 1.0),
        resolution=0.5,
        spatial_unit="m",
    )

    result = bootstrap_kde(
        estimator=SpatialKDE(bandwidth=0.5),
        events=events,
        support=support,
        plan=BootstrapPlan(
            n_resamples=2,
            random_state=7,
            execution_plan=ExecutionPlan(memory_budget_bytes=None),
        ),
    )

    assert result.estimator_family == "spatial"
    assert result.ensemble.n_replicates == 2
