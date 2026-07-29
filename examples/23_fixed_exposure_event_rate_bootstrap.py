# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Transform an intensity Bootstrap into a fixed-exposure event-rate Bootstrap."""

import numpy as np

from pykdex import GridSupport, SpatialEvents, SpatialKDE
from pykdex.execution import ExecutionPlan
from pykdex.risk import ExposureField
from pykdex.uncertainty import BootstrapPlan, bootstrap_event_rate, bootstrap_kde

support = GridSupport.from_bounds(
    (0.0, 0.0, 2.0, 1.0),
    resolution=0.25,
    spatial_unit="km",
)
events = SpatialEvents.from_array(
    [[0.25, 0.25], [0.75, 0.75], [1.25, 0.25], [1.75, 0.75]],
    spatial_unit="km",
)

intensity_bootstrap = bootstrap_kde(
    SpatialKDE(
        bandwidth=0.5,
        kernel="epanechnikov",
        metric="euclidean",
        target="intensity",
    ),
    events,
    support,
    plan=BootstrapPlan(
        n_resamples=199,
        confidence_level=0.95,
        random_state=20260729,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=256 * 1024 * 1024,
            target_chunk_size=32,
            replicate_chunk_size=4,
            n_jobs=2,
            backend="thread",
        ),
    ),
)

exposure = ExposureField.from_density(
    np.linspace(100.0, 200.0, support.n_points),
    support,
    exposure_unit="person",
    metadata={"status": "fixed measured exposure"},
)
rate_bootstrap = bootstrap_event_rate(
    intensity_bootstrap,
    exposure,
    event_unit="event",
    zero_policy="raise",
    memory_budget_bytes=256 * 1024 * 1024,
)

print("rate unit:", rate_bootstrap.metadata["rate_unit"])
print("fixed exposure:", rate_bootstrap.metadata["fixed_exposure"])
print("exposure uncertainty:", rate_bootstrap.metadata["exposure_uncertainty"])
print("first estimate:", rate_bootstrap.interval.estimate[0])
print(
    "first pointwise interval:",
    rate_bootstrap.interval.lower[0],
    rate_bootstrap.interval.upper[0],
)
