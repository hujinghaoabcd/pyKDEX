"""Input validation tests."""

import numpy as np
import pytest

from pykdex import FixedBandwidth, SpatialKDE


def test_invalid_bandwidths_are_rejected():
    for value in [0.0, -1.0, np.inf, np.nan]:
        with pytest.raises(ValueError):
            FixedBandwidth(value)
    with pytest.raises(TypeError):
        FixedBandwidth(True)


def test_invalid_weights_are_rejected(events_2d):
    with pytest.raises(ValueError, match="non-negative"):
        SpatialKDE().fit(events_2d, weights=[1.0, 1.0, -1.0, 1.0])
    with pytest.raises(ValueError, match="positive"):
        SpatialKDE().fit(events_2d, weights=np.zeros(4))


def test_dimension_mismatch_is_rejected(events_2d):
    model = SpatialKDE().fit(events_2d)
    with pytest.raises(ValueError, match="dimension"):
        model.evaluate(np.ones((3, 3)))


def test_predict_before_fit_is_rejected():
    with pytest.raises(ValueError, match="not fitted"):
        SpatialKDE().evaluate(np.array([[0.0, 0.0]]))
