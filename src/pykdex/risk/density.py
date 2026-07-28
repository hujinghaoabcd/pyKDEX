# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Closed adapters for measured pyKDEX probability-density results."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, TypeAlias

import numpy as np

from pykdex.core.network_results import NetworkField
from pykdex.core.network_time_results import NetworkTimeField
from pykdex.core.results import SpatialKDEResult
from pykdex.core.spatiotemporal_results import SpatiotemporalKDEResult
from pykdex.data._utils import readonly_array, stable_fingerprint
from pykdex.data.support import GridSupport
from pykdex.risk.support import (
    MeasuredSupport,
    SupportDescriptor,
    describe_measured_support,
    require_same_measured_support,
)

DensityResult: TypeAlias = (
    SpatialKDEResult | NetworkField | SpatiotemporalKDEResult | NetworkTimeField
)


@dataclass(frozen=True)
class DensityFieldView:
    """Read-only common contract extracted from a measured density result."""

    values: np.ndarray
    support: MeasuredSupport
    descriptor: SupportDescriptor
    result_family: str
    bandwidths: tuple[float, ...]
    estimator_contract: Mapping[str, Any]
    source_fingerprint: str
    normalization_tolerance: float
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        values = readonly_array(self.values, dtype=float, ndim=1, name="values")
        if values.shape != (self.descriptor.n_elements,):
            raise ValueError("values must contain one density per support element.")
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("density values must be finite and non-negative.")
        if (
            describe_measured_support(self.support).fingerprint
            != self.descriptor.fingerprint
        ):
            raise ValueError("support and descriptor fingerprints do not match.")
        family = str(self.result_family).strip()
        fingerprint = str(self.source_fingerprint).strip()
        if not family or not fingerprint:
            raise ValueError("result_family and source_fingerprint must be non-empty.")
        bandwidths = tuple(float(value) for value in self.bandwidths)
        if (
            not bandwidths
            or not np.all(np.isfinite(bandwidths))
            or any(value <= 0.0 for value in bandwidths)
        ):
            raise ValueError("bandwidths must contain finite positive scalars.")
        tolerance = _validate_normalization_tolerance(self.normalization_tolerance)
        integral = float(np.dot(values, self.descriptor.measure))
        if not np.isclose(integral, 1.0, rtol=0.0, atol=tolerance):
            raise ValueError(
                "Density must integrate to one on measured support within "
                f"normalization_tolerance={tolerance}; observed {integral}."
            )
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "result_family", family)
        object.__setattr__(self, "bandwidths", bandwidths)
        object.__setattr__(
            self,
            "estimator_contract",
            MappingProxyType(dict(self.estimator_contract)),
        )
        object.__setattr__(self, "source_fingerprint", fingerprint)
        object.__setattr__(self, "normalization_tolerance", tolerance)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def integral(self) -> float:
        """Measured probability-density integral."""
        return float(np.dot(self.values, self.descriptor.measure))

    @property
    def contract_fingerprint(self) -> str:
        """Fingerprint of the shared estimator configuration."""
        return stable_fingerprint(
            self.result_family,
            self.descriptor.fingerprint,
            self.bandwidths,
            dict(self.estimator_contract),
        )


def adapt_density_result(
    result: DensityResult,
    *,
    support: MeasuredSupport,
    normalization_tolerance: float = 1e-6,
) -> DensityFieldView:
    """Validate and adapt an existing pyKDEX result as probability density."""
    tolerance = _validate_normalization_tolerance(normalization_tolerance)
    if isinstance(result, SpatialKDEResult):
        return _adapt_spatial(result, support=support, tolerance=tolerance)
    if isinstance(result, NetworkField):
        return _adapt_network(result, support=support, tolerance=tolerance)
    if isinstance(result, SpatiotemporalKDEResult):
        return _adapt_spatiotemporal(result, support=support, tolerance=tolerance)
    if isinstance(result, NetworkTimeField):
        return _adapt_network_time(result, support=support, tolerance=tolerance)
    raise TypeError(
        "result must be SpatialKDEResult, NetworkField, "
        "SpatiotemporalKDEResult, or NetworkTimeField."
    )


def require_compatible_density_views(
    case: DensityFieldView,
    control: DensityFieldView,
) -> SupportDescriptor:
    """Require exact support and shared fixed estimator configuration."""
    descriptor = require_same_measured_support(case.support, control.support)
    if case.result_family != control.result_family:
        raise ValueError("Case and control must use the same result family.")
    if case.bandwidths != control.bandwidths:
        raise ValueError("Case and control must use the same fixed bandwidths.")
    if case.contract_fingerprint != control.contract_fingerprint:
        raise ValueError(
            "Case and control estimator contracts differ beyond event-specific data."
        )
    return descriptor


def _validate_normalization_tolerance(value: float) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError("normalization_tolerance must be a positive number.")
    tolerance = float(value)
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("normalization_tolerance must be finite and positive.")
    return tolerance


def _require_density(target: str) -> None:
    if str(target).strip().lower() != "density":
        raise ValueError(
            "Case-control relative risk requires target='density' for both inputs."
        )


def _scalar_bandwidth(value: Any, *, name: str) -> float:
    array = np.asarray(value, dtype=float)
    if array.ndim != 0:
        raise ValueError(
            f"{name} must be a fixed scalar; adaptive or matrix bandwidths are "
            "not supported for relative risk."
        )
    scalar = float(array)
    if not np.isfinite(scalar) or scalar <= 0.0:
        raise ValueError(f"{name} must be finite and positive.")
    return scalar


def _adapt_spatial(
    result: SpatialKDEResult,
    *,
    support: MeasuredSupport,
    tolerance: float,
) -> DensityFieldView:
    _require_density(result.target)
    if not isinstance(support, GridSupport):
        raise TypeError("SpatialKDEResult relative risk requires GridSupport.")
    descriptor = describe_measured_support(support)
    if result.support_fingerprint is None:
        raise ValueError(
            "SpatialKDEResult requires support_fingerprint for relative risk."
        )
    if result.support_fingerprint != descriptor.fingerprint:
        raise ValueError(
            "Spatial density result and requested support fingerprints differ."
        )
    if result.support_measure is None or result.support_ids is None:
        raise ValueError(
            "SpatialKDEResult requires support_measure and support_ids for "
            "relative risk."
        )
    if not np.array_equal(result.support, support.coordinates):
        raise ValueError("Spatial density coordinates do not match support.")
    if not np.array_equal(result.support_ids, descriptor.ids):
        raise ValueError("Spatial density identifiers do not match support.")
    if not np.array_equal(result.support_measure, descriptor.measure):
        raise ValueError("Spatial density measures do not match support.")
    if result.crs != descriptor.crs or result.spatial_unit != descriptor.spatial_unit:
        raise ValueError("Spatial density CRS or unit does not match support.")
    bandwidth = _scalar_bandwidth(result.bandwidth, name="bandwidth")
    metadata = dict(result.metadata)
    contract = {
        "kernel": result.kernel,
        "metric": result.metric,
        "bandwidth": bandwidth,
        "dimension": metadata.get("dimension", support.dimension),
        "boundary_correction": metadata.get("boundary_correction"),
        "boundary_fingerprint": metadata.get("boundary_fingerprint"),
    }
    source_fingerprint = stable_fingerprint(
        "SpatialKDEResult",
        result.values,
        descriptor.fingerprint,
        bandwidth,
        result.kernel,
        result.metric,
        result.crs,
        result.spatial_unit,
        metadata,
    )
    return DensityFieldView(
        values=result.values,
        support=support,
        descriptor=descriptor,
        result_family="spatial",
        bandwidths=(bandwidth,),
        estimator_contract=contract,
        source_fingerprint=source_fingerprint,
        normalization_tolerance=tolerance,
        metadata=metadata,
    )


def _adapt_network(
    result: NetworkField,
    *,
    support: MeasuredSupport,
    tolerance: float,
) -> DensityFieldView:
    _require_density(result.target)
    descriptor = require_same_measured_support(result.support, support)
    bandwidth = _scalar_bandwidth(result.bandwidth, name="bandwidth")
    metadata = dict(result.metadata)
    contract = {
        "kernel": result.kernel,
        "junction_policy": result.junction_policy,
        "directed": result.directed,
        "network_fingerprint": result.network_fingerprint,
        "bandwidth": bandwidth,
        "path_based": metadata.get("path_based"),
    }
    source_fingerprint = stable_fingerprint(
        "NetworkField",
        result.values,
        descriptor.fingerprint,
        bandwidth,
        result.kernel,
        result.junction_policy,
        result.directed,
        result.network_fingerprint,
        result.event_fingerprint,
        metadata,
    )
    return DensityFieldView(
        values=result.values,
        support=support,
        descriptor=descriptor,
        result_family="network",
        bandwidths=(bandwidth,),
        estimator_contract=contract,
        source_fingerprint=source_fingerprint,
        normalization_tolerance=tolerance,
        metadata=metadata,
    )


def _adapt_spatiotemporal(
    result: SpatiotemporalKDEResult,
    *,
    support: MeasuredSupport,
    tolerance: float,
) -> DensityFieldView:
    _require_density(result.target)
    descriptor = require_same_measured_support(result.support, support)
    spatial_bandwidth = _scalar_bandwidth(
        result.spatial_bandwidth,
        name="spatial_bandwidth",
    )
    temporal_bandwidth = _scalar_bandwidth(
        result.temporal_bandwidth,
        name="temporal_bandwidth",
    )
    metadata = dict(result.metadata)
    contract = {
        "spatial_kernel": result.spatial_kernel,
        "temporal_kernel": result.temporal_kernel,
        "spatial_metric": result.spatial_metric,
        "spatial_bandwidth": spatial_bandwidth,
        "temporal_bandwidth": temporal_bandwidth,
    }
    source_fingerprint = stable_fingerprint(
        "SpatiotemporalKDEResult",
        result.values,
        descriptor.fingerprint,
        spatial_bandwidth,
        temporal_bandwidth,
        result.spatial_kernel,
        result.temporal_kernel,
        result.spatial_metric,
        metadata,
    )
    return DensityFieldView(
        values=result.values,
        support=support,
        descriptor=descriptor,
        result_family="spatiotemporal",
        bandwidths=(spatial_bandwidth, temporal_bandwidth),
        estimator_contract=contract,
        source_fingerprint=source_fingerprint,
        normalization_tolerance=tolerance,
        metadata=metadata,
    )


def _adapt_network_time(
    result: NetworkTimeField,
    *,
    support: MeasuredSupport,
    tolerance: float,
) -> DensityFieldView:
    _require_density(result.target)
    descriptor = require_same_measured_support(result.support, support)
    spatial_bandwidth = _scalar_bandwidth(
        result.spatial_bandwidth,
        name="spatial_bandwidth",
    )
    temporal_bandwidth = _scalar_bandwidth(
        result.temporal_bandwidth,
        name="temporal_bandwidth",
    )
    metadata = dict(result.metadata)
    contract = {
        "spatial_kernel": result.spatial_kernel,
        "temporal_kernel": result.temporal_kernel,
        "junction_policy": result.junction_policy,
        "directed": result.directed,
        "network_fingerprint": result.network_fingerprint,
        "spatial_bandwidth": spatial_bandwidth,
        "temporal_bandwidth": temporal_bandwidth,
    }
    source_fingerprint = stable_fingerprint(
        "NetworkTimeField",
        result.values,
        descriptor.fingerprint,
        spatial_bandwidth,
        temporal_bandwidth,
        result.spatial_kernel,
        result.temporal_kernel,
        result.junction_policy,
        result.directed,
        result.network_fingerprint,
        result.event_fingerprint,
        metadata,
    )
    return DensityFieldView(
        values=result.values,
        support=support,
        descriptor=descriptor,
        result_family="network_time",
        bandwidths=(spatial_bandwidth, temporal_bandwidth),
        estimator_contract=contract,
        source_fingerprint=source_fingerprint,
        normalization_tolerance=tolerance,
        metadata=metadata,
    )
