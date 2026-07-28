# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Run a small reproducible spatial ordinary Bootstrap."""

from __future__ import annotations

import numpy as np

from pykdex import GridSupport, SpatialEvents, SpatialKDE
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde


def main() -> None:
    """Estimate a density field and pointwise percentile uncertainty."""
    events = SpatialEvents.from_array(
        [[0.2, 0.2], [0.8, 0.7], [1.5, 0.4]],
        spatial_unit="km",
    )
    support = GridSupport.from_bounds(
        (0.0, 0.0, 2.0, 1.0),
        resolution=0.25,
        spatial_unit="km",
    )
    result = bootstrap_kde(
        SpatialKDE(
            bandwidth=0.5,
            kernel="epanechnikov",
            metric="euclidean",
            target="density",
        ),
        events,
        support,
        plan=BootstrapPlan(
            n_resamples=9,
            confidence_level=0.8,
            random_state=20260728,
            execution_plan=ExecutionPlan(
                memory_budget_bytes=None,
                target_chunk_size=4,
                replicate_chunk_size=3,
                n_jobs=2,
                backend="thread",
            ),
        ),
    )

    assert result.ensemble.replicate_values.shape == (9, support.n_points)
    assert np.all(result.interval.lower <= result.interval.upper)
    print(
        {
            "n_replicates": result.ensemble.n_replicates,
            "n_grid_cells": result.ensemble.n_elements,
            "confidence_level": result.interval.confidence_level,
            "parallel_axis": result.ensemble.execution_metadata["parallel_axis"],
            "root_entropy": result.seed_metadata["root_entropy"],
        }
    )


if __name__ == "__main__":
    main()
