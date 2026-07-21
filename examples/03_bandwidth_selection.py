# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Select scalar spatial KDE bandwidths by two cross-validation criteria."""

from __future__ import annotations

import numpy as np

from pykdex import LeastSquaresCVBandwidth, LikelihoodCVBandwidth, SpatialKDE


def main() -> None:
    rng = np.random.default_rng(7)
    events = np.concatenate(
        [rng.normal(-1.0, 0.25, 40), rng.normal(1.0, 0.35, 60)]
    ).reshape(-1, 1)
    support = np.linspace(-3.0, 3.0, 200).reshape(-1, 1)

    likelihood = SpatialKDE(bandwidth=LikelihoodCVBandwidth(bounds=(0.05, 1.5))).fit(
        events
    )
    least_squares = SpatialKDE(
        bandwidth=LeastSquaresCVBandwidth(bounds=(0.05, 1.5))
    ).fit(events)

    likelihood_values = likelihood.evaluate(support)
    least_squares_values = least_squares.evaluate(support)
    assert likelihood.bandwidth_selection_ is not None
    assert least_squares.bandwidth_selection_ is not None
    print("Likelihood CV:", likelihood.bandwidth_selection_.bandwidth)
    print("Least-squares CV:", least_squares.bandwidth_selection_.bandwidth)
    print(likelihood_values[:3], least_squares_values[:3])


if __name__ == "__main__":
    main()
