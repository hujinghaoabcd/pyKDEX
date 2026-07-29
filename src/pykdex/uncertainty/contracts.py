# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Internal normalized estimator contracts for derived uncertainty operations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any

import numpy as np

from pykdex.data._utils import stable_fingerprint


def _bandwidth_tuple(values: Sequence[float]) -> tuple[float, ...]:
    bandwidths = tuple(float(value) for value in values)
    if (
        not bandwidths
        or not np.all(np.isfinite(bandwidths))
        or any(value <= 0.0 for value in bandwidths)
    ):
        raise ValueError("relative-risk contract bandwidths must be finite and positive.")
    return bandwidths


def build_relative_risk_contract(
    *,
    result_family: str,
    support_fingerprint: str,
    target: str,
    bandwidths: Sequence[float],
    components: Mapping[str, Any],
) -> tuple[Mapping[str, Any], str]:
    """Build one immutable, execution-independent density compatibility contract."""
    family = str(result_family).strip()
    support = str(support_fingerprint).strip()
    resolved_target = str(target).strip().lower()
    if not family or not support:
        raise ValueError("result_family and support_fingerprint must be non-empty.")
    if resolved_target not in {"density", "intensity"}:
        raise ValueError("target must be 'density' or 'intensity'.")
    normalized: dict[str, Any] = {
        "schema_version": 1,
        "result_family": family,
        "support_fingerprint": support,
        "target": resolved_target,
        "bandwidths": _bandwidth_tuple(bandwidths),
    }
    for key, value in components.items():
        name = str(key).strip()
        if not name:
            raise ValueError("relative-risk contract component names must be non-empty.")
        if name in normalized:
            raise ValueError(f"relative-risk contract component duplicates {name!r}.")
        normalized[name] = value
    fingerprint = stable_fingerprint("RelativeRiskBootstrapContract", normalized)
    return MappingProxyType(normalized), fingerprint
