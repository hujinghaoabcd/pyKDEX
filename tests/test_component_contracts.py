"""Contract and validation tests for composable pyKDEX components."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import SpatialKDE, SpatialKDEResult
from pykdex.bandwidths import BaseBandwidth, FixedBandwidth, get_bandwidth
from pykdex.kernels import BaseKernel, GaussianKernel, get_kernel
from pykdex.metrics import EuclideanMetric, get_metric


class EventBandwidth(BaseBandwidth):
    """Small deterministic event-specific bandwidth used only in tests."""

    def resolve(
        self,
        events: np.ndarray,
        *,
        weights: np.ndarray | None = None,
        metric: object | None = None,
        kernel: object | None = None,
    ) -> np.ndarray:
        return np.linspace(0.4, 0.7, events.shape[0])


class BadKernel(BaseKernel):
    """Kernel that intentionally violates the output-shape contract."""

    name = "bad"
    finite_support = False

    def evaluate(self, standardized_distance: np.ndarray, dimension: int) -> np.ndarray:
        return np.ones(1)


def test_component_resolvers_accept_instances_and_reject_unknown_names():
    fixed = FixedBandwidth(0.5)
    assert get_bandwidth(fixed) is fixed
    gaussian = GaussianKernel()
    assert get_kernel(gaussian) is gaussian
    euclidean = EuclideanMetric()
    assert get_metric(euclidean) is euclidean

    with pytest.raises(ValueError, match="Unknown kernel"):
        get_kernel("unknown")
    with pytest.raises(ValueError, match="Only the 'euclidean'"):
        get_metric("manhattan")
    with pytest.raises(TypeError):
        get_metric(3.0)  # type: ignore[arg-type]


def test_event_specific_bandwidth_evaluates_successfully(events_2d):
    model = SpatialKDE(bandwidth=EventBandwidth()).fit(events_2d)
    assert isinstance(model.bandwidth_, np.ndarray)
    values = model.evaluate(np.array([[0.0, 0.0], [1.0, 1.0]]))
    assert values.shape == (2,)
    assert np.all(values >= 0.0)


def test_constructor_and_fit_validation_branches(events_2d):
    with pytest.raises(TypeError, match="chunk_size"):
        SpatialKDE(chunk_size=True)
    with pytest.raises(ValueError, match="greater than zero"):
        SpatialKDE(chunk_size=0)
    with pytest.raises(ValueError, match="target"):
        SpatialKDE(target="rate")
    with pytest.raises(TypeError, match="numeric coordinates"):
        SpatialKDE().fit([["a", "b"]])
    with pytest.raises(ValueError, match="two-dimensional"):
        SpatialKDE().fit(np.array([1.0, 2.0]))
    with pytest.raises(ValueError, match="finite"):
        SpatialKDE().fit(np.array([[0.0, np.nan]]))


def test_metric_and_kernel_contract_validation():
    metric = EuclideanMetric()
    with pytest.raises(ValueError, match="two-dimensional"):
        metric.pairwise(np.array([0.0]), np.array([[0.0]]))
    with pytest.raises(ValueError, match="same coordinate dimension"):
        metric.pairwise(np.zeros((1, 2)), np.zeros((1, 3)))
    with pytest.raises(ValueError, match="unexpected shape"):
        BadKernel()(np.array([0.0, 1.0]), 2)
    with pytest.raises(ValueError, match="positive integer"):
        GaussianKernel()(np.array([0.0]), 0)


def test_result_validation_and_one_dimensional_geo_export():
    with pytest.raises(ValueError, match="one-dimensional"):
        SpatialKDEResult(
            values=np.ones((2, 1)),
            support=np.ones((2, 1)),
            bandwidth=1.0,
            target="density",
            kernel="gaussian",
            metric="euclidean",
        )
    with pytest.raises(ValueError, match="same number"):
        SpatialKDEResult(
            values=np.ones(2),
            support=np.ones((1, 1)),
            bandwidth=1.0,
            target="density",
            kernel="gaussian",
            metric="euclidean",
        )
    result = (
        SpatialKDE(bandwidth=0.5)
        .fit(np.array([[0.0], [1.0]]))
        .predict_result(np.array([[0.25], [0.75]]))
    )
    geoframe = result.to_geodataframe()
    assert geoframe.geometry.y.tolist() == [0.0, 0.0]
