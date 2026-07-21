# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Estimate a weighted spatial event intensity."""

from __future__ import annotations

import numpy as np

from pykdex import QuarticKernel, SpatialKDE


def main() -> None:
    events = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    weights = np.array([1.0, 2.0, 3.0])
    support = np.array([[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]])

    model = SpatialKDE(
        kernel=QuarticKernel(),
        bandwidth=1.25,
        target="intensity",
    )
    result = model.fit_predict(events, support, weights=weights)
    print(result.to_frame())


if __name__ == "__main__":
    main()
