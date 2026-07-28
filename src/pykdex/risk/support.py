# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Closed adapters for measured supports used by risk fields."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import numpy as np

from pykdex.data._utils import readonly_array
from pykdex.data.spatiotemporal import (
    SpatiotemporalGridSupport,
    SpatiotemporalPointSupport,
)
from pykdex.data.support import GridSupport
from pykdex.network.support import LixelSupport
from pykdex.network_time.support import ArixelSupport

MeasuredSupport: TypeAlias = (
    GridSupport
    | LixelSupport
    | SpatiotemporalPointSupport
    | SpatiotemporalGridSupport
    | ArixelSupport
)


@dataclass(frozen=True)
class SupportDescriptor:
    """Immutable identity and measure contract for a pyKDEX support.

    The descriptor is deliberately strict. A matching array shape is not enough
    to establish compatibility: support kind, stable identifiers, measured
    integration weights, spatial and temporal metadata, and the source support
    fingerprint remain part of the contract.
    """

    kind: str
    n_elements: int
    measure: np.ndarray
    ids: np.ndarray
    fingerprint: str
    crs: str | None
    spatial_unit: str | None
    temporal_unit: str | None
    time_domain_fingerprint: str | None
    shape: tuple[int, ...]

    def __post_init__(self) -> None:
        kind = str(self.kind).strip()
        if kind not in {
            "spatial_grid",
            "network_lixel",
            "spatiotemporal_points",
            "spatiotemporal_grid",
            "network_time_arixel",
        }:
            raise ValueError("kind is not a supported measured-support kind.")
        count = int(self.n_elements)
        if count <= 0:
            raise ValueError("n_elements must be positive.")
        measure = readonly_array(self.measure, dtype=float, ndim=1, name="measure")
        ids = readonly_array(self.ids, ndim=1, name="ids")
        if measure.shape != (count,) or ids.shape != (count,):
            raise ValueError("measure and ids must contain one value per element.")
        if not np.all(np.isfinite(measure)) or np.any(measure <= 0.0):
            raise ValueError("measure must contain finite positive values.")
        fingerprint = str(self.fingerprint).strip()
        if not fingerprint:
            raise ValueError("fingerprint must be a non-empty string.")
        shape = tuple(int(value) for value in self.shape)
        if not shape or any(value <= 0 for value in shape):
            raise ValueError("shape must contain positive dimensions.")
        if int(np.prod(shape)) != count:
            raise ValueError("shape must contain exactly n_elements entries.")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "n_elements", count)
        object.__setattr__(self, "measure", measure)
        object.__setattr__(self, "ids", ids)
        object.__setattr__(self, "fingerprint", fingerprint)
        object.__setattr__(self, "shape", shape)

    @property
    def total_measure(self) -> float:
        """Total geometric or space-time integration measure."""
        return float(np.sum(self.measure))


def describe_measured_support(support: MeasuredSupport) -> SupportDescriptor:
    """Return the validated measured-support contract for ``support``.

    Unmeasured point supports are rejected because exposure density and event
    rate require an explicit integration measure.
    """
    if isinstance(support, GridSupport):
        assert support.ids is not None
        return SupportDescriptor(
            kind="spatial_grid",
            n_elements=support.n_points,
            measure=support.measure,
            ids=support.ids,
            fingerprint=support.fingerprint,
            crs=support.crs,
            spatial_unit=support.spatial_unit,
            temporal_unit=None,
            time_domain_fingerprint=None,
            shape=support.shape,
        )
    if isinstance(support, LixelSupport):
        return SupportDescriptor(
            kind="network_lixel",
            n_elements=support.n_lixels,
            measure=support.measure,
            ids=support.lixel_ids,
            fingerprint=support.fingerprint,
            crs=support.crs,
            spatial_unit=support.spatial_unit,
            temporal_unit=None,
            time_domain_fingerprint=None,
            shape=(support.n_lixels,),
        )
    if isinstance(support, SpatiotemporalPointSupport):
        if support.measure is None:
            raise ValueError(
                "SpatiotemporalPointSupport requires support_measure for risk fields."
            )
        assert support.spatial.ids is not None
        return SupportDescriptor(
            kind="spatiotemporal_points",
            n_elements=support.n_points,
            measure=support.measure,
            ids=support.spatial.ids,
            fingerprint=support.fingerprint,
            crs=support.spatial.crs,
            spatial_unit=support.spatial.spatial_unit,
            temporal_unit=support.temporal.temporal_unit,
            time_domain_fingerprint=support.temporal.domain.fingerprint,
            shape=(support.n_points,),
        )
    if isinstance(support, SpatiotemporalGridSupport):
        return SupportDescriptor(
            kind="spatiotemporal_grid",
            n_elements=support.n_points,
            measure=support.measure,
            ids=support.ids,
            fingerprint=support.fingerprint,
            crs=support.spatial.crs,
            spatial_unit=support.spatial.spatial_unit,
            temporal_unit=support.temporal_unit,
            time_domain_fingerprint=support.time_domain.fingerprint,
            shape=support.shape,
        )
    if isinstance(support, ArixelSupport):
        return SupportDescriptor(
            kind="network_time_arixel",
            n_elements=support.n_arixels,
            measure=support.measure,
            ids=support.arixel_ids,
            fingerprint=support.fingerprint,
            crs=support.lixels.crs,
            spatial_unit=support.lixels.spatial_unit,
            temporal_unit=support.temporal_unit,
            time_domain_fingerprint=support.time_domain.fingerprint,
            shape=support.shape,
        )
    raise TypeError(
        "support must be GridSupport, LixelSupport, measured "
        "SpatiotemporalPointSupport, SpatiotemporalGridSupport, or ArixelSupport."
    )


def require_same_measured_support(
    first: MeasuredSupport,
    second: MeasuredSupport,
) -> SupportDescriptor:
    """Validate exact measured-support identity and return its descriptor."""
    left = describe_measured_support(first)
    right = describe_measured_support(second)
    if left.kind != right.kind or left.fingerprint != right.fingerprint:
        raise ValueError("fields must use the same measured support fingerprint.")
    return left
