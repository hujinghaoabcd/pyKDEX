# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Immutable temporal and ordinary space-time data objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np
import pandas as pd

from pykdex.data._utils import normalize_unit, readonly_array, stable_fingerprint
from pykdex.data.events import SpatialEvents
from pykdex.data.provenance import DataProvenance
from pykdex.data.support import GridSupport, PointSupport
from pykdex.data.validation import DataIssue, DataValidationReport
from pykdex.temporal import BaseTimeDomain, CyclicTimeDomain, LinearTimeDomain


def _normalize_optional_text(value: str | None, *, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string or None.")
    return value.strip()


@dataclass(frozen=True)
class TemporalCoordinates:
    """Immutable numeric temporal coordinates with an explicit domain and unit."""

    values: np.ndarray
    domain: BaseTimeDomain = field(default_factory=LinearTimeDomain)
    temporal_unit: str = "unit"
    temporal_origin: str | None = None
    timezone: str | None = None
    provenance: DataProvenance = field(default_factory=DataProvenance)

    def __post_init__(self) -> None:
        if not isinstance(self.domain, BaseTimeDomain):
            raise TypeError("domain must be a BaseTimeDomain instance.")
        values = readonly_array(
            self.domain.canonicalize(np.asarray(self.values, dtype=float)),
            dtype=float,
            ndim=1,
            name="values",
        )
        if values.size == 0:
            raise ValueError("values must contain at least one temporal coordinate.")
        temporal_unit = normalize_unit(self.temporal_unit, name="temporal_unit")
        if temporal_unit is None:
            raise ValueError("temporal_unit must be explicit.")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "temporal_unit", temporal_unit)
        object.__setattr__(
            self,
            "temporal_origin",
            _normalize_optional_text(self.temporal_origin, name="temporal_origin"),
        )
        object.__setattr__(
            self,
            "timezone",
            _normalize_optional_text(self.timezone, name="timezone"),
        )

    @property
    def n_times(self) -> int:
        """Number of temporal coordinates."""
        return int(self.values.size)

    @property
    def fingerprint(self) -> str:
        """Deterministic content and metadata fingerprint."""
        return stable_fingerprint(
            self.values,
            self.domain.fingerprint,
            self.temporal_unit,
            self.temporal_origin,
            self.timezone,
            self.provenance.fingerprint,
        )

    def to_frame(self) -> pd.DataFrame:
        """Return temporal coordinates as a DataFrame."""
        return pd.DataFrame({"time": self.values})

    @classmethod
    def from_array(
        cls,
        values: Any,
        *,
        domain: BaseTimeDomain | None = None,
        temporal_unit: str,
        temporal_origin: str | None = None,
        timezone: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "TemporalCoordinates":
        """Construct numeric temporal coordinates."""
        return cls(
            values=np.asarray(values),
            domain=domain or LinearTimeDomain(),
            temporal_unit=temporal_unit,
            temporal_origin=temporal_origin,
            timezone=timezone,
            provenance=provenance or DataProvenance(),
        )

    @classmethod
    def from_datetime(
        cls,
        values: Any,
        *,
        temporal_unit: str = "hours",
        temporal_origin: Any = "1970-01-01T00:00:00+00:00",
        timezone: str | None = None,
        domain: BaseTimeDomain | None = None,
        provenance: DataProvenance | None = None,
    ) -> "TemporalCoordinates":
        """Convert datetimes to numeric offsets from an explicit origin."""
        index = pd.DatetimeIndex(pd.to_datetime(values))
        if index.size == 0:
            raise ValueError("values must contain at least one datetime.")
        if index.tz is None:
            if timezone is None:
                raise ValueError("naive datetimes require an explicit timezone.")
            index = index.tz_localize(timezone)
        elif timezone is not None:
            index = index.tz_convert(timezone)
        resolved_timezone = str(index.tz)
        origin = pd.Timestamp(temporal_origin)
        if origin.tzinfo is None:
            origin = origin.tz_localize(resolved_timezone)
        else:
            origin = origin.tz_convert(resolved_timezone)
        scales = {
            "seconds": 1.0,
            "minutes": 60.0,
            "hours": 3_600.0,
            "days": 86_400.0,
        }
        try:
            scale = scales[temporal_unit]
        except KeyError as exc:
            raise ValueError(
                "datetime temporal_unit must be seconds, minutes, hours, or days."
            ) from exc
        seconds = np.asarray((index - origin).total_seconds(), dtype=float)
        return cls(
            values=seconds / scale,
            domain=domain or LinearTimeDomain(),
            temporal_unit=temporal_unit,
            temporal_origin=origin.isoformat(),
            timezone=resolved_timezone,
            provenance=provenance or DataProvenance(),
        )


@dataclass(frozen=True)
class SpatiotemporalEvents:
    """Weighted spatial events paired one-to-one with temporal coordinates."""

    spatial: SpatialEvents
    temporal: TemporalCoordinates
    provenance: DataProvenance = field(default_factory=DataProvenance)

    def __post_init__(self) -> None:
        if not isinstance(self.spatial, SpatialEvents):
            raise TypeError("spatial must be a SpatialEvents instance.")
        if not isinstance(self.temporal, TemporalCoordinates):
            raise TypeError("temporal must be a TemporalCoordinates instance.")
        if self.spatial.n_events != self.temporal.n_times:
            raise ValueError(
                "spatial events and temporal coordinates must have equal length."
            )

    @property
    def n_events(self) -> int:
        return self.spatial.n_events

    @property
    def spatial_coordinates(self) -> np.ndarray:
        return self.spatial.coordinates

    @property
    def times(self) -> np.ndarray:
        return self.temporal.values

    @property
    def weights(self) -> np.ndarray:
        assert self.spatial.weights is not None
        return self.spatial.weights

    @property
    def weight_sum(self) -> float:
        return self.spatial.weight_sum

    @property
    def ids(self) -> np.ndarray:
        assert self.spatial.ids is not None
        return self.spatial.ids

    @property
    def fingerprint(self) -> str:
        return stable_fingerprint(
            self.spatial.fingerprint,
            self.temporal.fingerprint,
            self.provenance.fingerprint,
        )

    def validate(self) -> DataValidationReport:
        issues = list(self.spatial.validate().issues)
        if np.unique(self.times).size < self.n_events:
            issues.append(
                DataIssue(
                    "warning",
                    "duplicate_times",
                    "Multiple events share identical temporal coordinates.",
                )
            )
        return DataValidationReport(
            tuple(issues),
            {
                "n_events": self.n_events,
                "spatial_dimension": self.spatial.dimension,
                "weight_sum": self.weight_sum,
                "time_domain": self.temporal.domain.name,
                "temporal_unit": self.temporal.temporal_unit,
            },
        )

    def to_frame(self) -> pd.DataFrame:
        frame = self.spatial.to_frame()
        frame["time"] = self.times
        return frame

    @classmethod
    def from_arrays(
        cls,
        spatial_coordinates: Any,
        times: Any,
        *,
        weights: Any | None = None,
        ids: Any | None = None,
        coordinate_names: Iterable[str] | None = None,
        crs: Any | None = None,
        spatial_unit: str | None = None,
        temporal_unit: str,
        time_domain: BaseTimeDomain | None = None,
        temporal_origin: str | None = None,
        timezone: str | None = None,
        marks: Any | None = None,
        provenance: DataProvenance | None = None,
    ) -> "SpatiotemporalEvents":
        """Construct paired space-time events from array-like values."""
        record = provenance or DataProvenance()
        return cls(
            spatial=SpatialEvents.from_array(
                spatial_coordinates,
                weights=weights,
                ids=ids,
                coordinate_names=coordinate_names,
                crs=crs,
                spatial_unit=spatial_unit,
                marks=marks,
                provenance=record,
            ),
            temporal=TemporalCoordinates.from_array(
                times,
                domain=time_domain,
                temporal_unit=temporal_unit,
                temporal_origin=temporal_origin,
                timezone=timezone,
                provenance=record,
            ),
            provenance=record,
        )


@dataclass(frozen=True)
class SpatiotemporalPointSupport:
    """Paired space-time evaluation points with optional integration measure."""

    spatial: PointSupport
    temporal: TemporalCoordinates
    support_measure: np.ndarray | None = None
    provenance: DataProvenance = field(default_factory=DataProvenance)

    def __post_init__(self) -> None:
        if not isinstance(self.spatial, PointSupport):
            raise TypeError("spatial must be a PointSupport instance.")
        if not isinstance(self.temporal, TemporalCoordinates):
            raise TypeError("temporal must be a TemporalCoordinates instance.")
        if self.spatial.n_points != self.temporal.n_times:
            raise ValueError("spatial and temporal support must have equal length.")
        measure = None
        if self.support_measure is not None:
            measure = readonly_array(
                self.support_measure,
                dtype=float,
                ndim=1,
                name="support_measure",
            )
            if measure.shape != (self.spatial.n_points,):
                raise ValueError("support_measure must contain one value per point.")
            if not np.all(np.isfinite(measure)) or np.any(measure <= 0.0):
                raise ValueError("support_measure must be finite and positive.")
        object.__setattr__(self, "support_measure", measure)

    @property
    def n_points(self) -> int:
        return self.spatial.n_points

    @property
    def spatial_coordinates(self) -> np.ndarray:
        return self.spatial.coordinates

    @property
    def times(self) -> np.ndarray:
        return self.temporal.values

    @property
    def measure(self) -> np.ndarray | None:
        return self.support_measure

    @property
    def fingerprint(self) -> str:
        return stable_fingerprint(
            self.spatial.fingerprint,
            self.temporal.fingerprint,
            self.support_measure,
            self.provenance.fingerprint,
        )

    def to_frame(self) -> pd.DataFrame:
        frame = self.spatial.to_frame()
        frame["time"] = self.times
        if self.support_measure is not None:
            frame["support_measure"] = self.support_measure
        return frame

    @classmethod
    def from_arrays(
        cls,
        spatial_coordinates: Any,
        times: Any,
        *,
        support_measure: Any | None = None,
        ids: Any | None = None,
        coordinate_names: Iterable[str] | None = None,
        crs: Any | None = None,
        spatial_unit: str | None = None,
        temporal_unit: str,
        time_domain: BaseTimeDomain | None = None,
        temporal_origin: str | None = None,
        timezone: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "SpatiotemporalPointSupport":
        record = provenance or DataProvenance()
        return cls(
            spatial=PointSupport.from_array(
                spatial_coordinates,
                ids=ids,
                coordinate_names=coordinate_names,
                crs=crs,
                spatial_unit=spatial_unit,
                provenance=record,
            ),
            temporal=TemporalCoordinates.from_array(
                times,
                domain=time_domain,
                temporal_unit=temporal_unit,
                temporal_origin=temporal_origin,
                timezone=timezone,
                provenance=record,
            ),
            support_measure=(
                None if support_measure is None else np.asarray(support_measure)
            ),
            provenance=record,
        )


def _axis_edges(start: float, end: float, resolution: float) -> np.ndarray:
    count = int(np.floor((end - start) / resolution))
    edges = start + np.arange(count + 1, dtype=float) * resolution
    if edges[-1] < end - max(1e-12, abs(end) * 1e-12):
        edges = np.append(edges, end)
    else:
        edges[-1] = end
    return edges


@dataclass(frozen=True)
class SpatiotemporalGridSupport:
    """Cartesian product of a measured spatial grid and temporal cells."""

    spatial: GridSupport
    time_edges: np.ndarray
    time_domain: BaseTimeDomain
    temporal_unit: str
    temporal_origin: str | None = None
    timezone: str | None = None
    provenance: DataProvenance = field(default_factory=DataProvenance)
    time_centers: np.ndarray = field(init=False, repr=False)
    time_widths: np.ndarray = field(init=False, repr=False)
    spatial_coordinates: np.ndarray = field(init=False, repr=False)
    times: np.ndarray = field(init=False, repr=False)
    measure: np.ndarray = field(init=False, repr=False)
    ids: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.spatial, GridSupport):
            raise TypeError("spatial must be a GridSupport instance.")
        if not isinstance(self.time_domain, BaseTimeDomain):
            raise TypeError("time_domain must be a BaseTimeDomain instance.")
        edges = readonly_array(self.time_edges, dtype=float, ndim=1, name="time_edges")
        if edges.size < 2 or not np.all(np.isfinite(edges)):
            raise ValueError("time_edges must contain at least two finite values.")
        widths = np.diff(edges)
        if np.any(widths <= 0.0):
            raise ValueError("time_edges must be strictly increasing.")
        if isinstance(self.time_domain, CyclicTimeDomain) and not np.isclose(
            edges[-1] - edges[0],
            self.time_domain.period,
        ):
            raise ValueError(
                "cyclic grid time_edges must cover exactly one complete period."
            )
        temporal_unit = normalize_unit(self.temporal_unit, name="temporal_unit")
        if temporal_unit is None:
            raise ValueError("temporal_unit must be explicit.")
        centers = self.time_domain.canonicalize(0.5 * (edges[:-1] + edges[1:]))
        n_space = self.spatial.n_points
        n_time = widths.size
        expanded_space = np.tile(self.spatial.coordinates, (n_time, 1))
        expanded_times = np.repeat(centers, n_space)
        expanded_measure = np.repeat(widths, n_space) * np.tile(
            self.spatial.measure, n_time
        )
        ids = np.arange(n_space * n_time, dtype=np.int64)
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
            "spatial_coordinates",
            readonly_array(
                expanded_space,
                dtype=float,
                ndim=2,
                name="spatial_coordinates",
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
            readonly_array(expanded_measure, dtype=float, ndim=1, name="measure"),
        )
        object.__setattr__(
            self,
            "ids",
            readonly_array(ids, dtype=np.int64, ndim=1, name="ids"),
        )
        object.__setattr__(self, "temporal_unit", temporal_unit)
        object.__setattr__(
            self,
            "temporal_origin",
            _normalize_optional_text(self.temporal_origin, name="temporal_origin"),
        )
        object.__setattr__(
            self,
            "timezone",
            _normalize_optional_text(self.timezone, name="timezone"),
        )

    @property
    def n_points(self) -> int:
        return int(self.times.size)

    @property
    def n_times(self) -> int:
        return int(self.time_centers.size)

    @property
    def shape(self) -> tuple[int, int, int]:
        return (self.n_times, *self.spatial.shape)

    @property
    def temporal(self) -> TemporalCoordinates:
        return TemporalCoordinates(
            values=self.times,
            domain=self.time_domain,
            temporal_unit=self.temporal_unit,
            temporal_origin=self.temporal_origin,
            timezone=self.timezone,
            provenance=self.provenance,
        )

    @property
    def fingerprint(self) -> str:
        return stable_fingerprint(
            self.spatial.fingerprint,
            self.time_edges,
            self.time_domain.fingerprint,
            self.temporal_unit,
            self.temporal_origin,
            self.timezone,
            self.provenance.fingerprint,
        )

    def reshape(self, values: Any) -> np.ndarray:
        array = np.asarray(values)
        if array.ndim != 1 or array.shape[0] != self.n_points:
            raise ValueError("values must contain one value per space-time cell.")
        return array.reshape(self.shape)

    def to_frame(self) -> pd.DataFrame:
        frame = pd.DataFrame(
            self.spatial_coordinates,
            columns=list(self.spatial.coordinate_names),
        )
        frame.insert(0, "support_id", self.ids)
        frame["time"] = self.times
        frame["cell_measure"] = self.measure
        return frame

    @classmethod
    def from_spatial_grid(
        cls,
        spatial: GridSupport,
        *,
        temporal_resolution: float,
        temporal_unit: str,
        time_domain: BaseTimeDomain | None = None,
        temporal_bounds: tuple[float, float] | None = None,
        temporal_origin: str | None = None,
        timezone: str | None = None,
        provenance: DataProvenance | None = None,
    ) -> "SpatiotemporalGridSupport":
        """Build a Cartesian measured grid with boundary remainder cells."""
        domain = time_domain or LinearTimeDomain()
        if isinstance(temporal_resolution, (bool, np.bool_)):
            raise TypeError("temporal_resolution must not be boolean.")
        resolution = float(temporal_resolution)
        if not np.isfinite(resolution) or resolution <= 0.0:
            raise ValueError("temporal_resolution must be finite and positive.")
        if temporal_bounds is None:
            if not isinstance(domain, CyclicTimeDomain):
                raise ValueError("linear time grids require temporal_bounds.")
            start, end = domain.origin, domain.origin + domain.period
        else:
            if not isinstance(temporal_bounds, tuple) or len(temporal_bounds) != 2:
                raise TypeError("temporal_bounds must be a (start, end) tuple.")
            start, end = (float(value) for value in temporal_bounds)
        if not np.isfinite(start) or not np.isfinite(end) or not start < end:
            raise ValueError("temporal_bounds must be finite and increasing.")
        return cls(
            spatial=spatial,
            time_edges=_axis_edges(start, end, resolution),
            time_domain=domain,
            temporal_unit=temporal_unit,
            temporal_origin=temporal_origin,
            timezone=timezone,
            provenance=provenance or DataProvenance(),
        )
