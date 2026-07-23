# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Reusable spatial and temporal distance assets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import numpy as np

from pykdex.core.validation import validate_spatial_metadata
from pykdex.data._utils import readonly_array, stable_fingerprint
from pykdex.data.spatiotemporal import (
    SpatiotemporalEvents,
    SpatiotemporalGridSupport,
    SpatiotemporalPointSupport,
)
from pykdex.metrics import BaseMetric, get_metric

SpatiotemporalSupport: TypeAlias = (
    SpatiotemporalEvents | SpatiotemporalPointSupport | SpatiotemporalGridSupport
)


@dataclass(frozen=True)
class SpatiotemporalDistanceAsset:
    """Target-by-source spatial distances and temporal offsets."""

    spatial_distances: np.ndarray
    temporal_offsets: np.ndarray
    temporal_distances: np.ndarray
    source_fingerprint: str
    target_fingerprint: str
    time_domain_fingerprint: str
    spatial_metric: str

    def __post_init__(self) -> None:
        spatial = readonly_array(
            self.spatial_distances,
            dtype=float,
            ndim=2,
            name="spatial_distances",
        )
        offsets = readonly_array(
            self.temporal_offsets,
            dtype=float,
            ndim=2,
            name="temporal_offsets",
        )
        temporal = readonly_array(
            self.temporal_distances,
            dtype=float,
            ndim=2,
            name="temporal_distances",
        )
        if spatial.shape != offsets.shape or spatial.shape != temporal.shape:
            raise ValueError("all distance arrays must have identical shapes.")
        if spatial.size == 0:
            raise ValueError("distance arrays must not be empty.")
        if (
            not np.all(np.isfinite(spatial))
            or np.any(spatial < 0.0)
            or not np.all(np.isfinite(offsets))
            or not np.all(np.isfinite(temporal))
            or np.any(temporal < 0.0)
        ):
            raise ValueError("distance assets must contain finite valid values.")
        for value, name in (
            (self.source_fingerprint, "source_fingerprint"),
            (self.target_fingerprint, "target_fingerprint"),
            (self.time_domain_fingerprint, "time_domain_fingerprint"),
            (self.spatial_metric, "spatial_metric"),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty string.")
        object.__setattr__(self, "spatial_distances", spatial)
        object.__setattr__(self, "temporal_offsets", offsets)
        object.__setattr__(self, "temporal_distances", temporal)

    @property
    def shape(self) -> tuple[int, int]:
        """Target-by-source matrix shape."""
        return (
            int(self.spatial_distances.shape[0]),
            int(self.spatial_distances.shape[1]),
        )

    @property
    def fingerprint(self) -> str:
        """Deterministic asset fingerprint."""
        return stable_fingerprint(
            self.spatial_distances,
            self.temporal_offsets,
            self.temporal_distances,
            self.source_fingerprint,
            self.target_fingerprint,
            self.time_domain_fingerprint,
            self.spatial_metric,
        )

    def validate_for(
        self,
        source: SpatiotemporalEvents,
        target: SpatiotemporalSupport,
        *,
        spatial_metric: str,
    ) -> None:
        """Raise when the asset does not match a requested evaluation."""
        target_size = (
            target.n_events
            if isinstance(target, SpatiotemporalEvents)
            else target.n_points
        )
        expected = (target_size, source.n_events)
        if self.shape != expected:
            raise ValueError("distance asset shape does not match source and target.")
        if self.source_fingerprint != source.fingerprint:
            raise ValueError("distance asset source fingerprint does not match events.")
        if self.target_fingerprint != target.fingerprint:
            raise ValueError(
                "distance asset target fingerprint does not match support."
            )
        if self.time_domain_fingerprint != source.temporal.domain.fingerprint:
            raise ValueError("distance asset time domain does not match events.")
        if self.spatial_metric != spatial_metric:
            raise ValueError("distance asset spatial metric does not match estimator.")


def _spatial_coordinates(
    value: SpatiotemporalSupport,
) -> tuple[np.ndarray, np.ndarray, str | None, str | None, str]:
    if isinstance(value, SpatiotemporalEvents):
        return (
            value.spatial_coordinates,
            value.times,
            value.spatial.crs,
            value.spatial.spatial_unit,
            value.fingerprint,
        )
    return (
        value.spatial_coordinates,
        value.times,
        value.spatial.crs,
        value.spatial.spatial_unit,
        value.fingerprint,
    )


def build_spatiotemporal_distance_asset(
    source: SpatiotemporalEvents,
    target: SpatiotemporalSupport,
    *,
    spatial_metric: str | BaseMetric = "euclidean",
) -> SpatiotemporalDistanceAsset:
    """Build a reusable target-by-source distance asset."""
    if not isinstance(source, SpatiotemporalEvents):
        raise TypeError("source must be SpatiotemporalEvents.")
    if not isinstance(
        target,
        (
            SpatiotemporalEvents,
            SpatiotemporalPointSupport,
            SpatiotemporalGridSupport,
        ),
    ):
        raise TypeError("target must be a supported space-time data object.")
    metric = get_metric(spatial_metric)
    coordinates, times, crs, unit, target_fingerprint = _spatial_coordinates(target)
    if coordinates.shape[1] != source.spatial.dimension:
        raise ValueError("source and target spatial dimensions must match.")
    validate_spatial_metadata(
        event_crs=source.spatial.crs,
        support_crs=crs,
        event_unit=source.spatial.spatial_unit,
        support_unit=unit,
    )
    if target.temporal.temporal_unit != source.temporal.temporal_unit:
        raise ValueError("source and target temporal units must match.")
    if target.temporal.domain.fingerprint != source.temporal.domain.fingerprint:
        raise ValueError("source and target time domains must match.")
    if target.temporal.temporal_origin != source.temporal.temporal_origin:
        raise ValueError("source and target temporal origins must match.")
    if target.temporal.timezone != source.temporal.timezone:
        raise ValueError("source and target timezones must match.")
    offsets = times[:, None] - source.times[None, :]
    return SpatiotemporalDistanceAsset(
        spatial_distances=metric.pairwise(coordinates, source.spatial_coordinates),
        temporal_offsets=offsets,
        temporal_distances=source.temporal.domain.distances_from_offsets(offsets),
        source_fingerprint=source.fingerprint,
        target_fingerprint=target_fingerprint,
        time_domain_fingerprint=source.temporal.domain.fingerprint,
        spatial_metric=metric.name,
    )
