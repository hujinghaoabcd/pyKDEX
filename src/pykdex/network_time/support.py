# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Measured lixel-by-time support for temporal network estimation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from pykdex.data import DataProvenance, TemporalCoordinates
from pykdex.data._utils import normalize_unit, readonly_array, stable_fingerprint
from pykdex.network import LixelSupport
from pykdex.temporal import BaseTimeDomain, CyclicTimeDomain, LinearTimeDomain


def _axis_edges(start: float, end: float, resolution: float) -> np.ndarray:
    count = int(np.floor((end - start) / resolution))
    edges = start + np.arange(count + 1, dtype=float) * resolution
    if edges[-1] < end - max(1e-12, abs(end) * 1e-12):
        edges = np.append(edges, end)
    else:
        edges[-1] = end
    return edges


def _optional_text(value: str | None, *, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string or None.")
    return value.strip()


@dataclass(frozen=True)
class ArixelSupport:
    """Cartesian lixel-by-time cells with length-times-time measure."""

    lixels: LixelSupport
    time_edges: np.ndarray
    time_domain: BaseTimeDomain
    temporal_unit: str
    temporal_origin: str | None = None
    timezone: str | None = None
    provenance: DataProvenance = field(default_factory=DataProvenance)
    time_centers: np.ndarray = field(init=False, repr=False)
    time_widths: np.ndarray = field(init=False, repr=False)
    lixel_indices: np.ndarray = field(init=False, repr=False)
    times: np.ndarray = field(init=False, repr=False)
    measure: np.ndarray = field(init=False, repr=False)
    arixel_ids: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.lixels, LixelSupport):
            raise TypeError("lixels must be a LixelSupport instance.")
        if not isinstance(self.time_domain, BaseTimeDomain):
            raise TypeError("time_domain must be a BaseTimeDomain instance.")
        edges = readonly_array(self.time_edges, dtype=float, ndim=1, name="time_edges")
        if edges.size < 2 or not np.all(np.isfinite(edges)):
            raise ValueError("time_edges must contain at least two finite values.")
        widths = np.diff(edges)
        if np.any(widths <= 0.0):
            raise ValueError("time_edges must be strictly increasing.")
        if isinstance(self.time_domain, CyclicTimeDomain):
            if not np.isclose(edges[0], self.time_domain.origin):
                raise ValueError(
                    "cyclic arixel time_edges must begin at domain origin."
                )
            if not np.isclose(edges[-1] - edges[0], self.time_domain.period):
                raise ValueError(
                    "cyclic arixel time_edges must cover one complete period."
                )
        unit = normalize_unit(self.temporal_unit, name="temporal_unit")
        if unit is None:
            raise ValueError("temporal_unit must be explicit.")
        centers = self.time_domain.canonicalize(0.5 * (edges[:-1] + edges[1:]))
        n_lixels = self.lixels.n_lixels
        n_times = widths.size
        lixel_indices = np.tile(np.arange(n_lixels, dtype=np.int64), n_times)
        expanded_times = np.repeat(centers, n_lixels)
        measure = np.repeat(widths, n_lixels) * np.tile(self.lixels.lengths, n_times)
        ids = np.arange(n_lixels * n_times, dtype=np.int64)
        object.__setattr__(self, "time_edges", edges)
        object.__setattr__(
            self,
            "time_centers",
            readonly_array(centers, dtype=float, ndim=1, name="time_centers"),
        )
        object.__setattr__(
            self,
            "time_widths",
            readonly_array(widths, dtype=float, ndim=1, name="time_widths"),
        )
        object.__setattr__(
            self,
            "lixel_indices",
            readonly_array(
                lixel_indices,
                dtype=np.int64,
                ndim=1,
                name="lixel_indices",
            ),
        )
        object.__setattr__(
            self,
            "times",
            readonly_array(expanded_times, dtype=float, ndim=1, name="times"),
        )
        object.__setattr__(
            self,
            "measure",
            readonly_array(measure, dtype=float, ndim=1, name="measure"),
        )
        object.__setattr__(
            self,
            "arixel_ids",
            readonly_array(ids, dtype=np.int64, ndim=1, name="arixel_ids"),
        )
        object.__setattr__(self, "temporal_unit", unit)
        object.__setattr__(
            self,
            "temporal_origin",
            _optional_text(self.temporal_origin, name="temporal_origin"),
        )
        object.__setattr__(
            self,
            "timezone",
            _optional_text(self.timezone, name="timezone"),
        )

    @property
    def n_times(self) -> int:
        """Number of temporal cells."""
        return int(self.time_centers.size)

    @property
    def n_arixels(self) -> int:
        """Number of lixel-by-time cells."""
        return int(self.arixel_ids.size)

    @property
    def shape(self) -> tuple[int, int]:
        """Time-by-lixel result shape."""
        return (self.n_times, self.lixels.n_lixels)

    @property
    def total_measure(self) -> float:
        """Total length-times-time support measure."""
        return float(np.sum(self.measure))

    @property
    def temporal(self) -> TemporalCoordinates:
        """Temporal coordinates for distinct time-cell centres."""
        return TemporalCoordinates(
            values=self.time_centers,
            domain=self.time_domain,
            temporal_unit=self.temporal_unit,
            temporal_origin=self.temporal_origin,
            timezone=self.timezone,
            provenance=self.provenance,
        )

    @property
    def fingerprint(self) -> str:
        """Deterministic lixel-time support fingerprint."""
        return stable_fingerprint(
            self.lixels.fingerprint,
            self.time_edges,
            self.time_domain.fingerprint,
            self.temporal_unit,
            self.temporal_origin,
            self.timezone,
            self.provenance.fingerprint,
        )

    def reshape(self, values: Any) -> np.ndarray:
        """Reshape one value per arixel to time-by-lixel."""
        array = np.asarray(values)
        if array.ndim != 1 or array.shape[0] != self.n_arixels:
            raise ValueError("values must contain one value per arixel.")
        return array.reshape(self.shape)

    def to_frame(self) -> pd.DataFrame:
        """Return repeated lixel attributes, time, widths, and measure."""
        base = self.lixels.to_frame().iloc[self.lixel_indices].reset_index(drop=True)
        base.insert(0, "arixel_id", self.arixel_ids)
        base["time"] = self.times
        base["time_width"] = np.repeat(self.time_widths, self.lixels.n_lixels)
        base["arixel_measure"] = self.measure
        return base

    def to_geodataframe(self) -> Any:
        """Return repeated lixel geometries for every temporal cell."""
        try:
            import geopandas as gpd
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "GeoDataFrame export requires the 'network' dependencies."
            ) from exc
        geometries = [self.lixels.geometries[index] for index in self.lixel_indices]
        return gpd.GeoDataFrame(
            self.to_frame(), geometry=geometries, crs=self.lixels.crs
        )

    @classmethod
    def from_lixels(
        cls,
        lixels: LixelSupport,
        *,
        temporal_resolution: float,
        temporal_unit: str,
        time_domain: BaseTimeDomain | None = None,
        temporal_bounds: tuple[float, float] | None = None,
        temporal_origin: str | None = None,
        timezone: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "ArixelSupport":
        """Build measured arixels, retaining a final remainder time cell."""
        domain = time_domain or LinearTimeDomain()
        if isinstance(temporal_resolution, (bool, np.bool_)):
            raise TypeError("temporal_resolution must not be boolean.")
        resolution = float(temporal_resolution)
        if not np.isfinite(resolution) or resolution <= 0.0:
            raise ValueError("temporal_resolution must be finite and positive.")
        if temporal_bounds is None:
            if not isinstance(domain, CyclicTimeDomain):
                raise ValueError("linear arixel support requires temporal_bounds.")
            start, end = domain.origin, domain.origin + domain.period
        else:
            if not isinstance(temporal_bounds, tuple) or len(temporal_bounds) != 2:
                raise TypeError("temporal_bounds must be a (start, end) tuple.")
            start, end = (float(value) for value in temporal_bounds)
        if not np.isfinite(start) or not np.isfinite(end) or not start < end:
            raise ValueError("temporal_bounds must be finite and increasing.")
        return cls(
            lixels=lixels,
            time_edges=_axis_edges(start, end, resolution),
            time_domain=domain,
            temporal_unit=temporal_unit,
            temporal_origin=temporal_origin,
            timezone=timezone,
            provenance=provenance or DataProvenance(),
        )
