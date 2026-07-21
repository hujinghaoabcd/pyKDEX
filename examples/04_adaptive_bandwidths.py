# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Compare kNN and Abramson event-specific spatial KDE bandwidths."""

from __future__ import annotations

import numpy as np

from pykdex import AbramsonBandwidth, KNNBandwidth, SpatialKDE


def main() -> None:
    rng = np.random.default_rng(11)
    events = np.concatenate(
        [rng.normal(-1.0, 0.15, 45), rng.normal(1.0, 0.55, 45)]
    ).reshape(-1, 1)
    support = np.linspace(-4.0, 4.0, 300).reshape(-1, 1)

    knn = SpatialKDE(bandwidth=KNNBandwidth(k=8)).fit(events)
    abramson = SpatialKDE(bandwidth=AbramsonBandwidth(0.35)).fit(events)

    assert isinstance(knn.bandwidth_, np.ndarray)
    assert isinstance(abramson.bandwidth_, np.ndarray)
    print("kNN bandwidth range:", knn.bandwidth_.min(), knn.bandwidth_.max())
    print(
        "Abramson bandwidth range:",
        abramson.bandwidth_.min(),
        abramson.bandwidth_.max(),
    )
    print(knn.evaluate(support)[:3], abramson.evaluate(support)[:3])


if __name__ == "__main__":
    main()
