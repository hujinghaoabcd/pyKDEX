# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Input validation for spatial KDE estimators.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, TypeAlias

import numpy as np
import pandas as pd

from pykdex.data import GridSupport, PointSupport, SpatialEvents

ArrayLike: TypeAlias = np.ndarray | pd.DataFrame | pd.Series
PointInput: TypeAlias = ArrayLike | SpatialEvents | PointSupport | GridSupport
EventInput: TypeAlias = ArrayLike | SpatialEvents
SupportInput: TypeAlias = ArrayLike | PointSupport | GridSupport


@dataclass(frozen=True)
class ValidatedPointInput:
    """Validated coordinates and optional structured-data metadata."""

    coordinates: np.ndarray
    coordinate_names: Optional[np.ndarray]
    ids: Optional[np.ndarray] = None
    measure: Optional[np.ndarray] = None
    crs: Optional[str] = None
    spatial_unit: Optional[str] = None
    fingerprint: Optional[str] = None
    shape: Optional[tuple[int, ...]] = None


def validate_point_input(
    points: PointInput,
    *,
    name: str,
    expected_dimension: Optional[int] = None,
) -> ValidatedPointInput:
    """Validate coordinate input and retain structured support metadata."""
    ids: np.ndarray | None = None
    measure: np.ndarray | None = None
    crs: str | None = None
    spatial_unit: str | None = None
    fingerprint: str | None = None
    shape: tuple[int, ...] | None = None

    if isinstance(points, (SpatialEvents, PointSupport, GridSupport)):
        array_source = points.coordinates
        names = np.asarray(points.coordinate_names, dtype=object).copy()
        ids = np.asarray(points.ids).copy()
        crs = points.crs
        spatial_unit = points.spatial_unit
        fingerprint = points.fingerprint
        if isinstance(points, GridSupport):
            measure = np.asarray(points.measure, dtype=float).copy()
            shape = points.shape
    else:
        if isinstance(points, pd.Series):
            raise TypeError(f"{name} must be a two-dimensional coordinate matrix.")
        array_source = points
        names = (
            np.asarray(points.columns, dtype=object).copy()
            if isinstance(points, pd.DataFrame)
            else None
        )

    try:
        array = np.asarray(array_source, dtype=float)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain numeric coordinates.") from exc
    if array.ndim != 2:
        raise ValueError(f"{name} must be two-dimensional; got shape {array.shape}.")
    if array.shape[0] == 0:
        raise ValueError(f"{name} must contain at least one point.")
    if array.shape[1] == 0:
        raise ValueError(f"{name} must contain at least one coordinate column.")
    if expected_dimension is not None and array.shape[1] != expected_dimension:
        raise ValueError(
            f"{name} has dimension {array.shape[1]}, but dimension "
            f"{expected_dimension} is required."
        )
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite coordinates.")
    return ValidatedPointInput(
        coordinates=np.ascontiguousarray(array.copy()),
        coordinate_names=names,
        ids=None if ids is None else ids.copy(),
        measure=None if measure is None else measure.copy(),
        crs=crs,
        spatial_unit=spatial_unit,
        fingerprint=fingerprint,
        shape=shape,
    )


def validate_points(
    points: PointInput,
    *,
    name: str,
    expected_dimension: Optional[int] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Validate and copy a two-dimensional coordinate matrix.

    This compatibility wrapper returns only coordinates and names. New code that
    needs CRS, support identifiers, or integration measures should call
    :func:`validate_point_input`.
    """
    validated = validate_point_input(
        points,
        name=name,
        expected_dimension=expected_dimension,
    )
    return validated.coordinates, validated.coordinate_names


def validate_support_schema(
    support: SupportInput,
    expected_names: Optional[np.ndarray],
) -> None:
    """Require named support coordinates to match fitted event coordinates."""
    if expected_names is None:
        return
    if isinstance(support, pd.DataFrame):
        received = np.asarray(support.columns, dtype=object)
    elif isinstance(support, (PointSupport, GridSupport)):
        received = np.asarray(support.coordinate_names, dtype=object)
    else:
        return
    if received.shape != expected_names.shape or not np.array_equal(
        received, expected_names
    ):
        raise ValueError(
            "Support coordinate names must match fitted event coordinate names in "
            f"the same order. Expected {expected_names.tolist()}, got "
            f"{received.tolist()}."
        )


def validate_spatial_metadata(
    *,
    event_crs: str | None,
    support_crs: str | None,
    event_unit: str | None,
    support_unit: str | None,
) -> None:
    """Validate CRS and coordinate-unit compatibility when both are explicit."""
    if event_crs is not None and support_crs is not None and event_crs != support_crs:
        raise ValueError(
            f"Event CRS '{event_crs}' does not match support CRS '{support_crs}'."
        )
    if (
        event_unit is not None
        and support_unit is not None
        and event_unit != support_unit
    ):
        raise ValueError(
            "Event spatial_unit does not match support spatial_unit: "
            f"'{event_unit}' != '{support_unit}'."
        )


def validate_weights(weights: ArrayLike | None, n_events: int) -> np.ndarray:
    """Validate non-negative finite event weights and return an owned vector."""
    if weights is None:
        return np.ones(n_events, dtype=float)
    try:
        array = np.asarray(weights, dtype=float)
    except (TypeError, ValueError) as exc:
        raise TypeError("weights must contain numeric values.") from exc
    if array.ndim == 2 and 1 in array.shape:
        array = array.reshape(-1)
    if array.ndim != 1:
        raise ValueError("weights must be one-dimensional.")
    if array.shape[0] != n_events:
        raise ValueError(
            f"weights must contain {n_events} values; got {array.shape[0]}."
        )
    if not np.all(np.isfinite(array)):
        raise ValueError("weights must contain only finite values.")
    if np.any(array < 0.0):
        raise ValueError("weights must be non-negative.")
    if not np.any(array > 0.0):
        raise ValueError("weights must contain at least one positive value.")
    return np.ascontiguousarray(array.copy())


def validate_target(target: str) -> str:
    """Validate the estimation target."""
    if not isinstance(target, str) or not target.strip():
        raise ValueError("target must be a non-empty string.")
    normalized = target.strip().lower()
    if normalized not in {"density", "intensity"}:
        raise ValueError("target must be either 'density' or 'intensity'.")
    return normalized
