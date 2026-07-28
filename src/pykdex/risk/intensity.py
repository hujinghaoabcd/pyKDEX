# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Closed adapters for measured pyKDEX intensity results."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, TypeAlias

import numpy as np

from pykdex.core.network_results import NetworkField
from pykdex.core.network_time_results import NetworkTimeField
from pykdex.core.results import SpatialKDEResult
from pykdex.core.spatiotemporal_results import SpatiotemporalKDEResult
from pykdex.data._utils import normalize_unit, readonly_array, stable_fingerprint
from pykdex.data.support import GridSupport
from pykdex.risk.support import (
    MeasuredSupport,
    SupportDescriptor,
    describe_measured_support,
    require_same_measured_support,
)

IntensityResult: TypeAlias = (
    SpatialKDEResult | NetworkField | SpatiotemporalKDEResult | NetworkTimeField
)


@dataclass(frozen=True)
class IntensityFieldView:
    """Read-only common contract extracted from a measured intensity result."""

    values: np.ndarray
    support: MeasuredSupport
    descriptor: SupportDescriptor
    event_unit: str
    result_family: str
    source_fingerprint: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        values = readonly_array(self.values, dtype=float, ndim=1, name="values")
        if values.shape != (self.descriptor.n_elements,):
            raise ValueError("values must contain one intensity per support element.")
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("intensity values must be finite and non-negative.")
        unit = normalize_unit(self.event_unit, name="event_unit")
        if unit is None:
            raise ValueError("event_unit must be explicit.")
        family = str(self.result_family).strip()
        fingerprint = str(self.source_fingerprint).strip()
        if not family or not fingerprint:
            raise ValueError("result_family and source_fingerprint must be non-empty.")
        if describe_measured_support(self.support).fingerprint != self.descriptor.fingerprint:
            raise ValueError("support and descriptor fingerprints do not match.")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "event_unit", unit)
        object.__setattr__(self, "result_family", family)
        object.__setattr__(self, "source_fingerprint", fingerprint)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def event_mass(self) -> float:
        """Integrated event weight on the measured support."""
        return float(np.dot(self.values, self.descriptor.measure))


def adapt_intensity_result(
    result: IntensityResult,
    *,
    support: MeasuredSupport,
    event_unit: str,
) -> IntensityFieldView:
    """Validate and adapt an existing pyKDEX result as event intensity."""
    if isinstance(result, SpatialKDEResult):
        return _adapt_spatial(result, support=support, event_unit=event_unit)
    if isinstance(result, NetworkField):
        return _adapt_network(result, support=support, event_unit=event_unit)
    if isinstance(result, SpatiotemporalKDEResult):
        return _adapt_spatiotemporal(result, support=support, event_unit=event_unit)
    if isinstance(result, NetworkTimeField):
        return _adapt_network_time(result, support=support, event_unit=event_unit)
    raise TypeError(
        "result must be SpatialKDEResult, NetworkField, "
        "SpatiotemporalKDEResult, or NetworkTimeField."
    )


def _require_intensity(target: str) -> None:
    if str(target).strip().lower() != "intensity":
        raise ValueError(
            "Exposure-adjusted event rates require target='intensity'; "
            "probability density has discarded total event mass."
        )


def _adapt_spatial(
    result: SpatialKDEResult,
    *,
    support: MeasuredSupport,
    event_unit: str,
) -> IntensityFieldView:
    _require_intensity(result.target)
    if not isinstance(support, GridSupport):
        raise TypeError("SpatialKDEResult event rates require GridSupport exposure.")
    descriptor = describe_measured_support(support)
    if result.support_fingerprint is None:
        raise ValueError("SpatialKDEResult requires support_fingerprint for event rates.")
    if result.support_fingerprint != descriptor.fingerprint:
        raise ValueError("Spatial result and exposure use different support fingerprints.")
    if result.support_measure is None or result.support_ids is None:
        raise ValueError(
            "SpatialKDEResult requires support_measure and support_ids for event rates."
        )
    if not np.array_equal(result.support, support.coordinates):
        raise ValueError("Spatial result coordinates do not match exposure support.")
    if not np.array_equal(result.support_ids, descriptor.ids):
        raise ValueError("Spatial result identifiers do not match exposure support.")
    if not np.array_equal(result.support_measure, descriptor.measure):
        raise ValueError("Spatial result measures do not match exposure support.")
    if result.crs != descriptor.crs or result.spatial_unit != descriptor.spatial_unit:
        raise ValueError("Spatial result CRS or spatial unit does not match exposure.")
    metadata = dict(result.metadata)
    source_fingerprint = stable_fingerprint(
        "SpatialKDEResult",
        result.values,
        descriptor.fingerprint,
        result.bandwidth,
        result.kernel,
        result.metric,
        result.crs,
        result.spatial_unit,
        metadata,
    )
    return IntensityFieldView(
        values=result.values,
        support=support,
        descriptor=descriptor,
        event_unit=event_unit,
        result_family="spatial",
        source_fingerprint=source_fingerprint,
        metadata=metadata,
    )


def _adapt_network(
    result: NetworkField,
    *,
    support: MeasuredSupport,
    event_unit: str,
) -> IntensityFieldView:
    _require_intensity(result.target)
    descriptor = require_same_measured_support(result.support, support)
    metadata = dict(result.metadata)
    metadata.update(
        {
            "kernel": result.kernel,
            "junction_policy": result.junction_policy,
            "directed": result.directed,
            "network_fingerprint": result.network_fingerprint,
            "event_fingerprint": result.event_fingerprint,
        }
    )
    source_fingerprint = stable_fingerprint(
        "NetworkField",
        result.values,
        descriptor.fingerprint,
        result.bandwidth,
        result.kernel,
        result.junction_policy,
        result.directed,
        result.network_fingerprint,
        result.event_fingerprint,
        dict(result.metadata),
    )
    return IntensityFieldView(
        values=result.values,
        support=support,
        descriptor=descriptor,
        event_unit=event_unit,
        result_family="network",
        source_fingerprint=source_fingerprint,
        metadata=metadata,
    )


def _adapt_spatiotemporal(
    result: SpatiotemporalKDEResult,
    *,
    support: MeasuredSupport,
    event_unit: str,
) -> IntensityFieldView:
    _require_intensity(result.target)
    descriptor = require_same_measured_support(result.support, support)
    metadata = dict(result.metadata)
    metadata.update(
        {
            "spatial_kernel": result.spatial_kernel,
            "temporal_kernel": result.temporal_kernel,
            "spatial_metric": result.spatial_metric,
        }
    )
    source_fingerprint = stable_fingerprint(
        "SpatiotemporalKDEResult",
        result.values,
        descriptor.fingerprint,
        result.spatial_bandwidth,
        result.temporal_bandwidth,
        result.spatial_kernel,
        result.temporal_kernel,
        result.spatial_metric,
        dict(result.metadata),
    )
    return IntensityFieldView(
        values=result.values,
        support=support,
        descriptor=descriptor,
        event_unit=event_unit,
        result_family="spatiotemporal",
        source_fingerprint=source_fingerprint,
        metadata=metadata,
    )


def _adapt_network_time(
    result: NetworkTimeField,
    *,
    support: MeasuredSupport,
    event_unit: str,
) -> IntensityFieldView:
    _require_intensity(result.target)
    descriptor = require_same_measured_support(result.support, support)
    metadata = dict(result.metadata)
    metadata.update(
        {
            "spatial_kernel": result.spatial_kernel,
            "temporal_kernel": result.temporal_kernel,
            "junction_policy": result.junction_policy,
            "directed": result.directed,
            "network_fingerprint": result.network_fingerprint,
            "event_fingerprint": result.event_fingerprint,
        }
    )
    source_fingerprint = stable_fingerprint(
        "NetworkTimeField",
        result.values,
        descriptor.fingerprint,
        result.spatial_bandwidth,
        result.temporal_bandwidth,
        result.spatial_kernel,
        result.temporal_kernel,
        result.junction_policy,
        result.directed,
        result.network_fingerprint,
        result.event_fingerprint,
        dict(result.metadata),
    )
    return IntensityFieldView(
        values=result.values,
        support=support,
        descriptor=descriptor,
        event_unit=event_unit,
        result_family="network_time",
        source_fingerprint=source_fingerprint,
        metadata=metadata,
    )
