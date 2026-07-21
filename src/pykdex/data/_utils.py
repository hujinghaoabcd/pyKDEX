# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Internal utilities for immutable data objects.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from hashlib import blake2b
from typing import Any

import numpy as np


def readonly_array(
    values: Any,
    *,
    dtype: Any | None = None,
    ndim: int | None = None,
    name: str = "array",
) -> np.ndarray:
    """Return an owned, C-contiguous, read-only NumPy array."""
    try:
        array = np.asarray(values, dtype=dtype)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} could not be converted to a NumPy array.") from exc
    if ndim is not None and array.ndim != ndim:
        raise ValueError(f"{name} must be {ndim}-dimensional; got shape {array.shape}.")
    owned = np.ascontiguousarray(array.copy())
    owned.setflags(write=False)
    return owned


def normalize_names(
    names: Iterable[Any] | None,
    *,
    dimension: int,
    prefix: str = "coord",
) -> tuple[str, ...]:
    """Normalize coordinate names and enforce uniqueness."""
    if names is None:
        standard = {1: ("x",), 2: ("x", "y"), 3: ("x", "y", "z")}
        resolved = standard.get(
            dimension, tuple(f"{prefix}_{index}" for index in range(dimension))
        )
    else:
        resolved = tuple(str(value) for value in names)
    if len(resolved) != dimension:
        raise ValueError(
            f"coordinate_names must contain {dimension} values; got {len(resolved)}."
        )
    if len(set(resolved)) != len(resolved):
        raise ValueError("coordinate_names must be unique.")
    if any(not value for value in resolved):
        raise ValueError("coordinate_names must not contain empty names.")
    return resolved


def normalize_crs(crs: Any | None) -> str | None:
    """Normalize a CRS-like object to a stable string representation."""
    if crs is None:
        return None
    text = str(crs).strip()
    if not text:
        raise ValueError("crs must not be empty.")
    return text


def normalize_unit(unit: str | None, *, name: str) -> str | None:
    """Normalize an optional unit label."""
    if unit is None:
        return None
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError(f"{name} must be a non-empty string or None.")
    return unit.strip()


def stable_fingerprint(*parts: Any) -> str:
    """Create a deterministic content fingerprint for arrays and metadata."""
    digest = blake2b(digest_size=20)
    for part in parts:
        _update_digest(digest, part)
    return digest.hexdigest()


def _update_digest(digest: Any, value: Any) -> None:
    if value is None:
        digest.update(b"N")
        return
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        digest.update(b"A")
        digest.update(str(array.dtype).encode("utf-8"))
        digest.update(repr(array.shape).encode("utf-8"))
        if array.dtype.hasobject:
            for item in array.ravel(order="C"):
                _update_digest(digest, item)
        else:
            digest.update(array.tobytes(order="C"))
        return
    if isinstance(value, Mapping):
        digest.update(b"M")
        for key in sorted(value, key=lambda item: repr(item)):
            _update_digest(digest, key)
            _update_digest(digest, value[key])
        return
    if isinstance(value, (tuple, list)):
        digest.update(b"L")
        for item in value:
            _update_digest(digest, item)
        return
    if isinstance(value, (str, bytes, int, float, bool, np.generic)):
        digest.update(type(value).__name__.encode("utf-8"))
        digest.update(repr(value).encode("utf-8"))
        return
    if hasattr(value, "wkb"):
        digest.update(b"G")
        digest.update(bytes(value.wkb))
        return
    digest.update(type(value).__qualname__.encode("utf-8"))
    digest.update(repr(value).encode("utf-8"))
