# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Use validated pyKDEX data objects and a measured grid support."""

from __future__ import annotations

import numpy as np

from pykdex import (
    DataProvenance,
    GridSupport,
    KDEDataset,
    PointSupport,
    SpatialBoundary,
    SpatialEvents,
    SpatialKDE,
    load_bimodal_points,
    load_bounded_square,
    make_bimodal_events,
)


def main() -> None:
    provenance = DataProvenance(source="synthetic example")
    events = SpatialEvents.from_array(
        [[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]],
        weights=[1.0, 2.0, 1.0],
        crs="EPSG:3857",
        spatial_unit="m",
        provenance=provenance,
    )
    boundary = SpatialBoundary.from_bounds(
        (-3.0, -3.0, 3.0, 3.0),
        crs="EPSG:3857",
        spatial_unit="m",
        provenance=provenance,
    )
    grid = GridSupport.from_bounds(
        boundary.bounds,
        resolution=0.1,
        crs="EPSG:3857",
        spatial_unit="m",
        provenance=provenance,
    )
    dataset = KDEDataset(
        name="triangle_events",
        events=events,
        support=grid,
        boundary=boundary,
    )
    report = dataset.validate()
    report.raise_for_errors()

    result = SpatialKDE(bandwidth=0.5).fit_predict(events, grid)
    print(dataset.summary())
    print(f"Approximate density integral: {result.integral():.6f}")
    assert result.to_grid().shape == grid.shape

    query = PointSupport.from_array([[0.5, 0.5]], ids=["centre"])
    assert SpatialKDE(bandwidth=0.5).fit(events).evaluate(query).shape == (1,)
    assert make_bimodal_events(10).n_events == 10
    assert load_bimodal_points(n_events=20).validate().valid
    assert load_bounded_square().validate().valid
    assert np.isfinite(result.values).all()


if __name__ == "__main__":
    main()
