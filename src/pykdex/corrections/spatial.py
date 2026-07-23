# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Boundary-correction strategies for planar KDE.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np
from scipy.special import ndtr
from scipy.stats import multivariate_normal

from pykdex.data import SpatialBoundary
from pykdex.kernels import BaseKernel
from pykdex.metrics import BaseMetric
from pykdex.spatial.evaluation import evaluate_sample_point_kernel


@dataclass(frozen=True)
class BoundaryCorrectionState:
    """Prepared immutable state used during support evaluation."""

    masses: np.ndarray | None = None
    expanded_events: np.ndarray | None = None
    source_indices: np.ndarray | None = None
    expanded_bandwidth: float | np.ndarray | None = None

    def __post_init__(self) -> None:
        for name in ("masses", "expanded_events", "source_indices", "expanded_bandwidth"):
            value = getattr(self, name)
            if isinstance(value, np.ndarray):
                owned = np.ascontiguousarray(value.copy())
                owned.setflags(write=False)
                object.__setattr__(self, name, owned)


class BaseBoundaryCorrection(ABC):
    """Base class for spatial boundary corrections."""

    name: str

    @abstractmethod
    def prepare(
        self,
        events: np.ndarray,
        *,
        boundary: SpatialBoundary | None,
        kernel: BaseKernel,
        metric: BaseMetric,
        bandwidth: float | np.ndarray,
    ) -> BoundaryCorrectionState:
        """Prepare correction state from fitted events."""

    @abstractmethod
    def evaluate_kernel(
        self,
        support: np.ndarray,
        events: np.ndarray,
        *,
        kernel: BaseKernel,
        metric: BaseMetric,
        bandwidth: float | np.ndarray,
        state: BoundaryCorrectionState,
    ) -> np.ndarray:
        """Return corrected source-event kernel values."""


class NoBoundaryCorrection(BaseBoundaryCorrection):
    """Leave spatial kernels unmodified."""

    name = "none"

    def prepare(
        self,
        events: np.ndarray,
        *,
        boundary: SpatialBoundary | None,
        kernel: BaseKernel,
        metric: BaseMetric,
        bandwidth: float | np.ndarray,
    ) -> BoundaryCorrectionState:
        return BoundaryCorrectionState()

    def evaluate_kernel(
        self,
        support: np.ndarray,
        events: np.ndarray,
        *,
        kernel: BaseKernel,
        metric: BaseMetric,
        bandwidth: float | np.ndarray,
        state: BoundaryCorrectionState,
    ) -> np.ndarray:
        return evaluate_sample_point_kernel(
            support,
            events,
            kernel=kernel,
            metric=metric,
            bandwidth=bandwidth,
        )


class RenormalizationCorrection(BaseBoundaryCorrection):
    """Renormalize every source kernel by its mass inside a polygon.

    Rectangular Gaussian domains use analytical probabilities. Other supported
    combinations use a deterministic polygon-cell quadrature whose cells carry
    their exact intersection area with the study polygon.

    Args:
        cells_per_axis: Number of quadrature cells along each boundary-box axis.
        mass_floor: Positive minimum accepted in-domain kernel mass.
    """

    name = "renormalization"

    def __init__(self, *, cells_per_axis: int = 64, mass_floor: float = 1e-10) -> None:
        if isinstance(cells_per_axis, (bool, np.bool_)) or not isinstance(
            cells_per_axis, (int, np.integer)
        ):
            raise TypeError("cells_per_axis must be a positive integer.")
        if int(cells_per_axis) < 8:
            raise ValueError("cells_per_axis must be at least 8.")
        if not np.isfinite(mass_floor) or float(mass_floor) <= 0.0:
            raise ValueError("mass_floor must be finite and positive.")
        self.cells_per_axis = int(cells_per_axis)
        self.mass_floor = float(mass_floor)

    def prepare(
        self,
        events: np.ndarray,
        *,
        boundary: SpatialBoundary | None,
        kernel: BaseKernel,
        metric: BaseMetric,
        bandwidth: float | np.ndarray,
    ) -> BoundaryCorrectionState:
        if boundary is None:
            raise ValueError("renormalization correction requires a boundary.")
        if events.shape[1] != 2:
            raise ValueError("boundary correction currently supports planar events only.")
        masses = self._analytical_rectangle_gaussian_mass(
            events,
            boundary=boundary,
            kernel=kernel,
            bandwidth=bandwidth,
        )
        if masses is None:
            points, measures = self._polygon_quadrature(boundary)
            kernel_values = evaluate_sample_point_kernel(
                points,
                events,
                kernel=kernel,
                metric=metric,
                bandwidth=bandwidth,
            )
            masses = np.asarray(kernel_values.T @ measures, dtype=float)
        if not np.all(np.isfinite(masses)) or np.any(masses <= self.mass_floor):
            raise ValueError(
                "Some event kernels have too little mass inside the boundary. "
                "Increase bandwidth support, quadrature resolution, or mass_floor "
                "only with a documented numerical reason."
            )
        return BoundaryCorrectionState(masses=masses)

    def evaluate_kernel(
        self,
        support: np.ndarray,
        events: np.ndarray,
        *,
        kernel: BaseKernel,
        metric: BaseMetric,
        bandwidth: float | np.ndarray,
        state: BoundaryCorrectionState,
    ) -> np.ndarray:
        if state.masses is None:
            raise RuntimeError("renormalization state has no kernel masses.")
        values = evaluate_sample_point_kernel(
            support,
            events,
            kernel=kernel,
            metric=metric,
            bandwidth=bandwidth,
        )
        return values / state.masses[None, :]

    @staticmethod
    def _is_axis_aligned_rectangle(boundary: SpatialBoundary) -> bool:
        try:
            from shapely.geometry import box
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "Boundary correction requires the 'geo' optional dependencies."
            ) from exc
        reference = box(*boundary.bounds)
        tolerance = max(1.0, boundary.area) * 1e-12
        return float(reference.symmetric_difference(boundary.geometry).area) <= tolerance

    def _analytical_rectangle_gaussian_mass(
        self,
        events: np.ndarray,
        *,
        boundary: SpatialBoundary,
        kernel: BaseKernel,
        bandwidth: float | np.ndarray,
    ) -> np.ndarray | None:
        if kernel.name != "gaussian" or not self._is_axis_aligned_rectangle(boundary):
            return None
        lower = np.asarray(boundary.bounds[:2], dtype=float)
        upper = np.asarray(boundary.bounds[2:], dtype=float)
        array = np.asarray(bandwidth, dtype=float)
        if array.ndim == 0:
            h = float(array)
            probabilities = ndtr((upper[None, :] - events) / h) - ndtr(
                (lower[None, :] - events) / h
            )
            return np.prod(probabilities, axis=1)
        if array.ndim == 1:
            probabilities = ndtr((upper[None, :] - events) / array[:, None]) - ndtr(
                (lower[None, :] - events) / array[:, None]
            )
            return np.prod(probabilities, axis=1)
        diagonal = np.diag(np.diag(array))
        if np.allclose(array, diagonal, rtol=1e-12, atol=1e-14):
            scales = np.sqrt(np.diag(array))
            probabilities = ndtr((upper[None, :] - events) / scales[None, :]) - ndtr(
                (lower[None, :] - events) / scales[None, :]
            )
            return np.prod(probabilities, axis=1)
        masses = np.empty(events.shape[0], dtype=float)
        corners = (
            (upper[0], upper[1], 1.0),
            (lower[0], upper[1], -1.0),
            (upper[0], lower[1], -1.0),
            (lower[0], lower[1], 1.0),
        )
        for index, event in enumerate(events):
            mass = 0.0
            for x_value, y_value, sign in corners:
                mass += sign * float(
                    multivariate_normal.cdf(
                        [x_value, y_value],
                        mean=event,
                        cov=array,
                    )
                )
            masses[index] = mass
        return masses

    def _polygon_quadrature(
        self,
        boundary: SpatialBoundary,
    ) -> tuple[np.ndarray, np.ndarray]:
        try:
            from shapely.geometry import box
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "Boundary correction requires the 'geo' optional dependencies."
            ) from exc
        xmin, ymin, xmax, ymax = boundary.bounds
        x_edges = np.linspace(xmin, xmax, self.cells_per_axis + 1)
        y_edges = np.linspace(ymin, ymax, self.cells_per_axis + 1)
        points: list[tuple[float, float]] = []
        measures: list[float] = []
        for x0, x1 in zip(x_edges[:-1], x_edges[1:]):
            for y0, y1 in zip(y_edges[:-1], y_edges[1:]):
                clipped = boundary.geometry.intersection(box(x0, y0, x1, y1))
                area = float(clipped.area)
                if area <= 0.0:
                    continue
                representative = clipped.representative_point()
                points.append((float(representative.x), float(representative.y)))
                measures.append(area)
        if not points:
            raise ValueError("boundary quadrature produced no positive-area cells.")
        return np.asarray(points, dtype=float), np.asarray(measures, dtype=float)


class ReflectionCorrection(BaseBoundaryCorrection):
    """Reflect events across all sides and corners of a rectangular boundary.

    This is the standard one-generation reflection estimator: in two dimensions
    every event contributes the original location, four side mirrors, and four
    corner mirrors. Full non-diagonal bandwidth matrices are rejected because
    their cross-axis covariance must also be transformed under reflection.
    """

    name = "reflection"

    def prepare(
        self,
        events: np.ndarray,
        *,
        boundary: SpatialBoundary | None,
        kernel: BaseKernel,
        metric: BaseMetric,
        bandwidth: float | np.ndarray,
    ) -> BoundaryCorrectionState:
        if boundary is None:
            raise ValueError("reflection correction requires a boundary.")
        if events.shape[1] != 2:
            raise ValueError("reflection correction currently supports 2D events only.")
        if not RenormalizationCorrection._is_axis_aligned_rectangle(boundary):
            raise ValueError(
                "reflection correction requires an axis-aligned rectangular boundary."
            )
        array = np.asarray(bandwidth, dtype=float)
        if array.ndim == 2 and not np.allclose(
            array,
            np.diag(np.diag(array)),
            rtol=1e-12,
            atol=1e-14,
        ):
            raise ValueError(
                "reflection correction supports scalar, event-specific scalar, or "
                "diagonal matrix bandwidths; full matrices require covariance reflection."
            )
        xmin, ymin, xmax, ymax = boundary.bounds
        expanded: list[np.ndarray] = []
        indices: list[int] = []
        for source_index, (x_value, y_value) in enumerate(events):
            x_images = (x_value, 2.0 * xmin - x_value, 2.0 * xmax - x_value)
            y_images = (y_value, 2.0 * ymin - y_value, 2.0 * ymax - y_value)
            for reflected_x, reflected_y in product(x_images, y_images):
                expanded.append(np.asarray([reflected_x, reflected_y], dtype=float))
                indices.append(source_index)
        source_indices = np.asarray(indices, dtype=int)
        expanded_bandwidth: float | np.ndarray
        if array.ndim == 1:
            expanded_bandwidth = array[source_indices]
        else:
            expanded_bandwidth = bandwidth
        return BoundaryCorrectionState(
            expanded_events=np.asarray(expanded, dtype=float),
            source_indices=source_indices,
            expanded_bandwidth=expanded_bandwidth,
        )

    def evaluate_kernel(
        self,
        support: np.ndarray,
        events: np.ndarray,
        *,
        kernel: BaseKernel,
        metric: BaseMetric,
        bandwidth: float | np.ndarray,
        state: BoundaryCorrectionState,
    ) -> np.ndarray:
        if (
            state.expanded_events is None
            or state.source_indices is None
            or state.expanded_bandwidth is None
        ):
            raise RuntimeError("reflection state is incomplete.")
        expanded_values = evaluate_sample_point_kernel(
            support,
            state.expanded_events,
            kernel=kernel,
            metric=metric,
            bandwidth=state.expanded_bandwidth,
        )
        values = np.zeros((support.shape[0], events.shape[0]), dtype=float)
        for image_index, source_index in enumerate(state.source_indices):
            values[:, source_index] += expanded_values[:, image_index]
        return values


def get_boundary_correction(
    correction: str | BaseBoundaryCorrection,
) -> BaseBoundaryCorrection:
    """Resolve a boundary-correction name or strategy object."""
    if isinstance(correction, BaseBoundaryCorrection):
        return correction
    if not isinstance(correction, str) or not correction.strip():
        raise TypeError(
            "boundary_correction must be a non-empty string or strategy object."
        )
    name = correction.strip().lower().replace("-", "_")
    if name in {"none", "off"}:
        return NoBoundaryCorrection()
    if name in {"renormalization", "renormalize", "renorm"}:
        return RenormalizationCorrection()
    if name in {"reflection", "reflect"}:
        return ReflectionCorrection()
    raise ValueError(
        "Unknown boundary correction. Supported values are 'none', "
        "'renormalization', and 'reflection'."
    )
