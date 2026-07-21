# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Input validation for spatial KDE estimators."""

from __future__ import annotations

from typing import Optional, Tuple, TypeAlias

import numpy as np
import pandas as pd

ArrayLike: TypeAlias = np.ndarray | pd.DataFrame | pd.Series


def validate_points(
    points: ArrayLike,
    *,
    name: str,
    expected_dimension: Optional[int] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Validate and copy a two-dimensional coordinate matrix.

    Args:
        points: Coordinate matrix with rows as points and columns as dimensions.
        name: Human-readable parameter name used in errors.
        expected_dimension: Required number of coordinate columns.

    Returns:
        A C-contiguous float array and optional DataFrame column names.
    """
    if isinstance(points, pd.Series):
        raise TypeError(f"{name} must be a two-dimensional coordinate matrix.")
    try:
        array = np.asarray(points, dtype=float)
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
    names = (
        np.asarray(points.columns, dtype=object).copy()
        if isinstance(points, pd.DataFrame)
        else None
    )
    return np.ascontiguousarray(array.copy()), names


def validate_support_schema(
    support: ArrayLike,
    expected_names: Optional[np.ndarray],
) -> None:
    """Require DataFrame support columns to match fitted event columns."""
    if expected_names is None or not isinstance(support, pd.DataFrame):
        return
    received = np.asarray(support.columns, dtype=object)
    if received.shape != expected_names.shape or not np.array_equal(
        received, expected_names
    ):
        raise ValueError(
            "Support DataFrame columns must match fitted event columns in the same "
            f"order. Expected {expected_names.tolist()}, got {received.tolist()}."
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
