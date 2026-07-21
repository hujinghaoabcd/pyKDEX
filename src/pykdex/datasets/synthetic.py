# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Deterministic synthetic datasets for tutorials and numerical tests.

Author:
    Jinghao Hu
"""

from __future__ import annotations

import numpy as np

from pykdex.data import (
    DataProvenance,
    GridSupport,
    KDEDataset,
    SpatialBoundary,
    SpatialEvents,
)


def make_bimodal_events(
    n_events: int = 200,
    *,
    random_state: int | None = 42,
) -> SpatialEvents:
    """Generate a reproducible two-cluster planar event pattern."""
    if isinstance(n_events, bool) or not isinstance(n_events, int):
        raise TypeError("n_events must be an integer.")
    if n_events < 2:
        raise ValueError("n_events must be at least two.")
    rng = np.random.default_rng(random_state)
    first_count = n_events // 2
    second_count = n_events - first_count
    first = rng.normal(loc=(-1.0, 0.0), scale=(0.35, 0.25), size=(first_count, 2))
    second = rng.normal(loc=(1.0, 0.6), scale=(0.45, 0.35), size=(second_count, 2))
    return SpatialEvents.from_array(
        np.vstack([first, second]),
        coordinate_names=("x", "y"),
        spatial_unit="unit",
        provenance=DataProvenance(
            source="pyKDEX synthetic generator",
            transformations=("generated_bimodal_events",),
            metadata={"random_state": random_state, "n_events": n_events},
        ),
    )


def load_bimodal_points(
    *,
    n_events: int = 200,
    resolution: float = 0.1,
    random_state: int | None = 42,
) -> KDEDataset:
    """Load a complete bimodal spatial KDE tutorial bundle."""
    events = make_bimodal_events(n_events, random_state=random_state)
    boundary = SpatialBoundary.from_bounds(
        (-3.0, -2.5, 3.0, 2.5),
        spatial_unit="unit",
        provenance=DataProvenance(source="pyKDEX synthetic generator"),
    )
    support = GridSupport.from_bounds(
        boundary.bounds,
        resolution=resolution,
        spatial_unit="unit",
        provenance=DataProvenance(source="pyKDEX synthetic generator"),
    )
    return KDEDataset(
        name="bimodal_points",
        events=events,
        support=support,
        boundary=boundary,
        description="Two Gaussian event clusters on a regular planar grid.",
        provenance=DataProvenance(
            source="pyKDEX synthetic generator",
            transformations=("assembled_bimodal_dataset",),
        ),
    )


def load_bounded_square() -> KDEDataset:
    """Load a small boundary-focused dataset with events near square edges."""
    coordinates = np.array(
        [
            [0.05, 0.05],
            [0.95, 0.05],
            [0.05, 0.95],
            [0.95, 0.95],
            [0.50, 0.50],
        ]
    )
    provenance = DataProvenance(source="pyKDEX analytical fixture")
    events = SpatialEvents.from_array(
        coordinates,
        coordinate_names=("x", "y"),
        spatial_unit="unit",
        provenance=provenance,
    )
    boundary = SpatialBoundary.from_bounds(
        (0.0, 0.0, 1.0, 1.0),
        spatial_unit="unit",
        provenance=provenance,
    )
    support = GridSupport.from_bounds(
        boundary.bounds,
        resolution=0.02,
        spatial_unit="unit",
        provenance=provenance,
    )
    return KDEDataset(
        name="bounded_square",
        events=events,
        support=support,
        boundary=boundary,
        description="Five events used to inspect boundary bias and correction.",
        provenance=provenance,
    )
