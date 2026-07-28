"""Tests for kNN and Abramson sample-point adaptive bandwidths."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.integrate import trapezoid

from pykdex import (
    AbramsonBandwidth,
    KNNBandwidth,
    LikelihoodCVBandwidth,
    SpatialKDE,
)
from pykdex.kernels import GaussianKernel
from pykdex.metrics import EuclideanMetric


def test_knn_bandwidth_matches_hand_calculated_neighbour_distances():
    events = np.array([[0.0], [1.0], [3.0], [6.0]])
    metric = EuclideanMetric()
    first = KNNBandwidth(1).resolve(events, metric=metric)
    second = KNNBandwidth(2).resolve(events, metric=metric)
    np.testing.assert_allclose(first, [1.0, 1.0, 2.0, 3.0])
    np.testing.assert_allclose(second, [3.0, 2.0, 3.0, 5.0])


def test_knn_bandwidth_validates_k_and_duplicate_floor():
    with pytest.raises(ValueError, match="greater than zero"):
        KNNBandwidth(0)
    events = np.array([[0.0], [0.0], [1.0]])
    with pytest.raises(ValueError, match="duplicate"):
        KNNBandwidth(1).resolve(events)
    bandwidths = KNNBandwidth(1, minimum_bandwidth=0.1).resolve(events)
    np.testing.assert_allclose(bandwidths, [0.1, 0.1, 1.0])
    with pytest.raises(ValueError, match="cannot exceed"):
        KNNBandwidth(3).resolve(events)


def test_knn_spatial_density_preserves_mass():
    events = np.array([[-1.0], [-0.8], [-0.4], [0.0], [0.7], [1.3], [2.0]])
    model = SpatialKDE(bandwidth=KNNBandwidth(2)).fit(events)
    assert isinstance(model.bandwidth_, np.ndarray)
    x = np.linspace(-8.0, 9.0, 12001).reshape(-1, 1)
    values = model.evaluate(x)
    integral = trapezoid(values, x=x[:, 0])
    np.testing.assert_allclose(integral, 1.0, rtol=2e-4, atol=2e-4)


def test_abramson_assigns_smaller_bandwidths_to_dense_events():
    events = np.array([[-0.10], [-0.05], [0.0], [0.05], [0.10], [3.0]])
    strategy = AbramsonBandwidth(0.5, clip=None)
    bandwidths = strategy.resolve(
        events,
        weights=None,
        metric=EuclideanMetric(),
        kernel=GaussianKernel(),
    )
    assert strategy.pilot_bandwidth_ == 0.5
    assert strategy.pilot_density_.shape == (6,)
    assert np.isfinite(strategy.geometric_mean_)
    assert bandwidths[-1] > np.max(bandwidths[:-1])


def test_abramson_can_use_a_selected_scalar_pilot():
    rng = np.random.default_rng(9)
    events = rng.normal(size=(35, 1))
    pilot = LikelihoodCVBandwidth(bounds=(0.08, 1.2))
    strategy = AbramsonBandwidth(pilot, clip=(0.4, 2.5))
    model = SpatialKDE(bandwidth=strategy).fit(events)
    assert pilot.result_ is not None and pilot.result_.success
    assert np.isclose(strategy.pilot_bandwidth_, pilot.result_.bandwidth)
    assert isinstance(model.bandwidth_, np.ndarray)
    ratios = model.bandwidth_ / strategy.pilot_bandwidth_
    assert np.min(ratios) >= 0.4 - 1e-12
    assert np.max(ratios) <= 2.5 + 1e-12


def test_abramson_density_preserves_mass():
    rng = np.random.default_rng(12)
    events = np.concatenate(
        [rng.normal(-1.0, 0.2, 20), rng.normal(1.0, 0.45, 30)]
    ).reshape(-1, 1)
    model = SpatialKDE(bandwidth=AbramsonBandwidth(0.35)).fit(events)
    x = np.linspace(-8.0, 8.0, 16001).reshape(-1, 1)
    integral = trapezoid(model.evaluate(x), x=x[:, 0])
    np.testing.assert_allclose(integral, 1.0, rtol=2e-4, atol=2e-4)
