# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Run a complete fixed-bandwidth spatial KDE example."""

from __future__ import annotations

import numpy as np

from pykdex import SpatialKDE


def main() -> None:
    rng = np.random.default_rng(42)
    events = np.vstack(
        [
            rng.normal(loc=(-1.0, 0.0), scale=0.35, size=(80, 2)),
            rng.normal(loc=(1.0, 0.5), scale=0.45, size=(120, 2)),
        ]
    )
    x = np.linspace(-3.0, 3.0, 30)
    y = np.linspace(-2.5, 2.5, 25)
    xx, yy = np.meshgrid(x, y)
    support = np.column_stack([xx.ravel(), yy.ravel()])

    model = SpatialKDE(kernel="gaussian", bandwidth=0.4, target="density")
    result = model.fit_predict(events, support)

    assert result.values.shape == (support.shape[0],)
    assert np.all(result.values >= 0.0)
    print(result.to_frame().head())


if __name__ == "__main__":
    main()
