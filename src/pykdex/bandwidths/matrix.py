# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Global positive-definite bandwidth matrices."""

from __future__ import annotations

import numpy as np

from pykdex.bandwidths.base import BaseBandwidth


class BandwidthMatrix(BaseBandwidth):
    r"""Use one global positive-definite bandwidth matrix.

    The matrix is interpreted as the kernel covariance/shape matrix :math:`H`:

    .. math::

        |H|^{-1/2} K(\|H^{-1/2}(x-x_i)\|).

    A scalar bandwidth ``h`` is therefore equivalent to ``H = h**2 * I``.

    Args:
        matrix: Symmetric positive-definite square matrix.
    """

    def __init__(self, matrix: np.ndarray) -> None:
        array = np.asarray(matrix, dtype=float)
        if array.ndim != 2 or array.shape[0] != array.shape[1] or array.size == 0:
            raise ValueError("matrix must be a non-empty square array.")
        if not np.all(np.isfinite(array)):
            raise ValueError("matrix must contain finite values.")
        if not np.allclose(array, array.T, rtol=1e-10, atol=1e-12):
            raise ValueError("matrix must be symmetric.")
        try:
            np.linalg.cholesky(array)
        except np.linalg.LinAlgError as exc:
            raise ValueError("matrix must be positive definite.") from exc
        self.matrix = np.ascontiguousarray(array.copy())
        self.matrix.setflags(write=False)

    def resolve(
        self,
        events: np.ndarray,
        *,
        weights: np.ndarray | None = None,
        metric: object | None = None,
        kernel: object | None = None,
    ) -> np.ndarray:
        if events.ndim != 2 or events.shape[0] == 0:
            raise ValueError("events must be a non-empty two-dimensional array.")
        if events.shape[1] != self.matrix.shape[0]:
            raise ValueError(
                "bandwidth matrix dimension must match the event coordinate dimension."
            )
        return self.matrix.copy()
