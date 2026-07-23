# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Boundary correction, anisotropic matrices, and balloon bandwidths."""

from __future__ import annotations

import numpy as np

from pykdex import (
    BalloonKNNBandwidth,
    BandwidthMatrix,
    BaseBalloonBandwidth,
    BaseBoundaryCorrection,
    GridSupport,
    NoBoundaryCorrection,
    ReflectionCorrection,
    RenormalizationCorrection,
    SpatialBoundary,
    SpatialKDE,
)


def main() -> None:
    boundary = SpatialBoundary.from_bounds((0.0, 0.0, 1.0, 1.0))
    events = np.array([[0.05, 0.50], [0.70, 0.65]])
    grid = GridSupport.from_bounds(boundary.bounds, resolution=0.05)

    corrections: tuple[BaseBoundaryCorrection, ...] = (
        NoBoundaryCorrection(),
        RenormalizationCorrection(cells_per_axis=32),
        ReflectionCorrection(),
    )
    for correction in corrections:
        result = SpatialKDE(
            bandwidth=0.12,
            boundary=boundary,
            boundary_correction=correction,
        ).fit_predict(events, grid)
        print(correction.name, result.integral())

    anisotropic = SpatialKDE(
        bandwidth=BandwidthMatrix(np.array([[0.08, 0.02], [0.02, 0.03]]))
    ).fit_predict(events, grid)
    print("matrix", anisotropic.values.max())

    balloon_strategy: BaseBalloonBandwidth = BalloonKNNBandwidth(
        1,
        minimum_bandwidth=0.05,
    )
    balloon = SpatialKDE(bandwidth=balloon_strategy).fit_predict(events, grid)
    print("balloon range", np.min(balloon.bandwidth), np.max(balloon.bandwidth))


if __name__ == "__main__":
    main()
