"""Numerical tests for normalized radial kernels."""

from math import gamma

import numpy as np
import pytest
from scipy.integrate import quad

from pykdex.kernels import (
    EpanechnikovKernel,
    ExponentialKernel,
    GaussianKernel,
    QuarticKernel,
    TriangularKernel,
    UniformKernel,
)


@pytest.mark.parametrize(
    "kernel",
    [
        GaussianKernel(),
        EpanechnikovKernel(),
        QuarticKernel(),
        TriangularKernel(),
        UniformKernel(),
        ExponentialKernel(),
    ],
)
@pytest.mark.parametrize("dimension", [1, 2, 3])
def test_radial_kernels_integrate_to_one(kernel, dimension):
    sphere_area = dimension * np.pi ** (dimension / 2.0) / gamma(dimension / 2.0 + 1.0)
    upper = 1.0 if kernel.finite_support else 40.0

    def integrand(radius):
        value = kernel(np.array([radius]), dimension)[0]
        return sphere_area * radius ** (dimension - 1) * value

    integral, _ = quad(integrand, 0.0, upper, epsabs=1e-10)
    np.testing.assert_allclose(integral, 1.0, rtol=2e-7, atol=2e-7)


def test_kernel_rejects_negative_distance():
    with pytest.raises(ValueError, match="non-negative"):
        GaussianKernel()(np.array([-1.0]), 2)
