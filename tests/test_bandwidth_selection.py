"""Numerical and behavioural tests for scalar bandwidth selection."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import (
    BandwidthSelectionResult,
    LeastSquaresCV,
    LeastSquaresCVBandwidth,
    LikelihoodCV,
    LikelihoodCVBandwidth,
    QuarticKernel,
    SpatialKDE,
)
from pykdex.kernels import GaussianKernel
from pykdex.metrics import EuclideanMetric


def _clustered_events() -> np.ndarray:
    rng = np.random.default_rng(1234)
    return np.concatenate(
        [
            rng.normal(-1.0, 0.22, 35),
            rng.normal(0.9, 0.30, 45),
        ]
    ).reshape(-1, 1)


def test_likelihood_selector_is_deterministic_and_records_trace():
    events = _clustered_events()
    selector = LikelihoodCV(bounds=(0.05, 1.5), tolerance=1e-7)
    first = selector.select(
        events,
        weights=None,
        kernel=GaussianKernel(),
        metric=EuclideanMetric(),
    )
    second = selector.select(
        events,
        weights=None,
        kernel=GaussianKernel(),
        metric=EuclideanMetric(),
    )
    assert isinstance(first, BandwidthSelectionResult)
    assert first.success
    assert first.method == "likelihood_cv"
    assert first.n_evaluations == len(first.to_frame())
    np.testing.assert_allclose(first.bandwidth, second.bandwidth, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(first.score, second.score, rtol=0.0, atol=1e-12)
    assert 0.05 <= first.bandwidth <= 1.5


def test_likelihood_bandwidth_integrates_with_spatial_estimator():
    events = _clustered_events()
    strategy = LikelihoodCVBandwidth(bounds=(0.05, 1.5))
    model = SpatialKDE(bandwidth=strategy).fit(events)
    assert isinstance(model.bandwidth_, float)
    assert model.bandwidth_selection_ is strategy.result_
    assert model.bandwidth_selection_.success
    assert model.fit_metadata_["bandwidth_strategy"] == "LikelihoodCVBandwidth"


def test_weighted_likelihood_selection_changes_the_selected_scale():
    events = _clustered_events()
    weights = np.ones(events.shape[0])
    weights[events[:, 0] > 0.0] = 6.0
    selector = LikelihoodCV(bounds=(0.05, 1.5))
    unweighted = selector.select(
        events,
        weights=None,
        kernel=GaussianKernel(),
        metric=EuclideanMetric(),
    )
    weighted = selector.select(
        events,
        weights=weights,
        kernel=GaussianKernel(),
        metric=EuclideanMetric(),
    )
    assert not np.isclose(unweighted.bandwidth, weighted.bandwidth)


def test_least_squares_selector_matches_bandwidth_strategy():
    events = _clustered_events()
    selector = LeastSquaresCV(bounds=(0.05, 1.5), tolerance=1e-7)
    direct = selector.select(
        events,
        weights=None,
        kernel=GaussianKernel(),
        metric=EuclideanMetric(),
    )
    strategy = LeastSquaresCVBandwidth(bounds=(0.05, 1.5), tolerance=1e-7)
    model = SpatialKDE(bandwidth=strategy).fit(events)
    np.testing.assert_allclose(model.bandwidth_, direct.bandwidth, rtol=0.0, atol=1e-12)
    assert strategy.result_.method == "least_squares_cv"


def test_least_squares_selector_rejects_non_gaussian_kernel():
    events = _clustered_events()
    with pytest.raises(ValueError, match="Gaussian"):
        LeastSquaresCV(bounds=(0.05, 1.5)).select(
            events,
            weights=None,
            kernel=QuarticKernel(),
            metric=EuclideanMetric(),
        )


def test_selection_requires_distinct_locations_and_two_positive_weights():
    selector = LikelihoodCV()
    duplicates = np.zeros((4, 1))
    with pytest.raises(ValueError, match="distinct"):
        selector.select(
            duplicates,
            weights=None,
            kernel=GaussianKernel(),
            metric=EuclideanMetric(),
        )
    events = np.arange(4.0).reshape(-1, 1)
    with pytest.raises(ValueError, match="two positive"):
        selector.select(
            events,
            weights=np.array([1.0, 0.0, 0.0, 0.0]),
            kernel=GaussianKernel(),
            metric=EuclideanMetric(),
        )


def test_selection_result_rejects_inconsistent_history():
    with pytest.raises(ValueError, match="history length"):
        BandwidthSelectionResult(
            bandwidth=0.5,
            score=1.0,
            method="test",
            bounds=(0.1, 1.0),
            n_evaluations=2,
            success=True,
            message="ok",
            evaluated_bandwidths=np.array([0.5]),
            evaluated_scores=np.array([1.0]),
        )


def test_likelihood_objective_matches_manual_two_event_gaussian_value():
    from pykdex.selection.objectives import likelihood_cv_score

    events = np.array([[0.0], [2.0]])
    distances = EuclideanMetric().pairwise(events, events)
    weights = np.ones(2)
    bandwidth = 1.25
    score = likelihood_cv_score(
        bandwidth,
        distances,
        weights,
        GaussianKernel(),
        1,
        density_floor=1e-300,
    )
    density = np.exp(-0.5 * (2.0 / bandwidth) ** 2) / (np.sqrt(2.0 * np.pi) * bandwidth)
    np.testing.assert_allclose(score, -np.log(density), rtol=1e-13, atol=1e-13)


def test_gaussian_lscv_objective_matches_numerical_integral():
    from scipy.integrate import trapezoid

    from pykdex.selection.objectives import least_squares_cv_score

    events = np.array([[-1.0], [0.2], [1.4]])
    weights = np.array([1.0, 2.0, 1.0])
    bandwidth = 0.65
    distances = EuclideanMetric().pairwise(events, events)
    analytical = least_squares_cv_score(bandwidth, distances, weights, 1)

    grid = np.linspace(-8.0, 8.0, 100001)
    normalized = weights / weights.sum()
    density = np.zeros_like(grid)
    for location, coefficient in zip(events[:, 0], normalized):
        standardized = (grid - location) / bandwidth
        density += (
            coefficient
            * np.exp(-0.5 * standardized**2)
            / (np.sqrt(2.0 * np.pi) * bandwidth)
        )
    integrated_square = trapezoid(density**2, x=grid)

    loo = []
    for index, location in enumerate(events[:, 0]):
        remaining = weights.sum() - weights[index]
        value = 0.0
        for other, other_location in enumerate(events[:, 0]):
            if other == index:
                continue
            standardized = (location - other_location) / bandwidth
            value += (
                weights[other]
                * np.exp(-0.5 * standardized**2)
                / (np.sqrt(2.0 * np.pi) * bandwidth)
            )
        loo.append(value / remaining)
    numerical = integrated_square - 2.0 * np.dot(normalized, np.asarray(loo))
    np.testing.assert_allclose(analytical, numerical, rtol=2e-9, atol=2e-9)
