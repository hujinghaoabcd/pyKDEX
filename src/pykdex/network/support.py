# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Measured lixel support for network estimators.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from pykdex.data import DataProvenance
from pykdex.data._utils import (
    normalize_crs,
    normalize_unit,
    readonly_array,
    stable_fingerprint,
)
from pykdex.data.validation import DataIssue, DataValidationReport
from pykdex.network.linear_network import LinearNetwork


def _require_substring() -> Any:
    try:
        from shapely.ops import substring
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Lixel construction requires the 'network' optional dependencies."
        ) from exc
    return substring


@dataclass(frozen=True)
class LixelSupport:
    """A network partition into measured line segments and centre locations."""

    lixel_ids: np.ndarray
    edge_indices: np.ndarray
    edge_ids: np.ndarray
    start_offsets: np.ndarray
    end_offsets: np.ndarray
    center_offsets: np.ndarray
    lengths: np.ndarray
    center_coordinates: np.ndarray
    geometries: tuple[Any, ...]
    network_fingerprint: str
    target_length: float
    crs: str | None = None
    spatial_unit: str | None = None
    provenance: DataProvenance = field(default_factory=DataProvenance)

    def __post_init__(self) -> None:
        lixel_ids = readonly_array(self.lixel_ids, ndim=1, name="lixel_ids")
        n_lixels = lixel_ids.shape[0]
        if n_lixels == 0:
            raise ValueError("LixelSupport must contain at least one lixel.")
        if len({repr(value) for value in lixel_ids.tolist()}) != n_lixels:
            raise ValueError("lixel_ids must be unique.")
        edge_indices = readonly_array(
            self.edge_indices, dtype=np.int64, ndim=1, name="edge_indices"
        )
        edge_ids = readonly_array(self.edge_ids, ndim=1, name="edge_ids")
        start = readonly_array(
            self.start_offsets, dtype=float, ndim=1, name="start_offsets"
        )
        end = readonly_array(self.end_offsets, dtype=float, ndim=1, name="end_offsets")
        center = readonly_array(
            self.center_offsets, dtype=float, ndim=1, name="center_offsets"
        )
        lengths = readonly_array(self.lengths, dtype=float, ndim=1, name="lengths")
        coordinates = readonly_array(
            self.center_coordinates,
            dtype=float,
            ndim=2,
            name="center_coordinates",
        )
        for name, array in (
            ("edge_indices", edge_indices),
            ("edge_ids", edge_ids),
            ("start_offsets", start),
            ("end_offsets", end),
            ("center_offsets", center),
            ("lengths", lengths),
        ):
            if array.shape[0] != n_lixels:
                raise ValueError(f"{name} must contain one value per lixel.")
        if coordinates.shape != (n_lixels, 2):
            raise ValueError("center_coordinates must have shape (n_lixels, 2).")
        if np.any(edge_indices < 0):
            raise ValueError("edge_indices must be non-negative.")
        if not np.all(np.isfinite(start)) or np.any(start < 0.0):
            raise ValueError("start_offsets must be finite and non-negative.")
        if not np.all(np.isfinite(end)) or np.any(end <= start):
            raise ValueError("end_offsets must be finite and exceed start_offsets.")
        if not np.allclose(center, 0.5 * (start + end)):
            raise ValueError("center_offsets must be midpoint offsets.")
        if not np.allclose(lengths, end - start):
            raise ValueError("lengths must equal end_offsets minus start_offsets.")
        if not np.all(np.isfinite(coordinates)):
            raise ValueError("center_coordinates must contain only finite values.")
        geometries = tuple(self.geometries)
        if len(geometries) != n_lixels:
            raise ValueError("geometries must contain one line per lixel.")
        if any(
            geometry.is_empty or geometry.geom_type != "LineString"
            for geometry in geometries
        ):
            raise ValueError("lixel geometries must be non-empty LineString objects.")
        target = float(self.target_length)
        if not np.isfinite(target) or target <= 0.0:
            raise ValueError("target_length must be finite and positive.")
        fingerprint = str(self.network_fingerprint).strip()
        if not fingerprint:
            raise ValueError("network_fingerprint must be a non-empty string.")
        object.__setattr__(self, "lixel_ids", lixel_ids)
        object.__setattr__(self, "edge_indices", edge_indices)
        object.__setattr__(self, "edge_ids", edge_ids)
        object.__setattr__(self, "start_offsets", start)
        object.__setattr__(self, "end_offsets", end)
        object.__setattr__(self, "center_offsets", center)
        object.__setattr__(self, "lengths", lengths)
        object.__setattr__(self, "center_coordinates", coordinates)
        object.__setattr__(self, "geometries", geometries)
        object.__setattr__(self, "network_fingerprint", fingerprint)
        object.__setattr__(self, "target_length", target)
        object.__setattr__(self, "crs", normalize_crs(self.crs))
        object.__setattr__(
            self,
            "spatial_unit",
            normalize_unit(self.spatial_unit, name="spatial_unit"),
        )

    @property
    def n_lixels(self) -> int:
        """Number of lixels."""
        return int(self.lixel_ids.shape[0])

    @property
    def measure(self) -> np.ndarray:
        """Actual lixel lengths used for network integration."""
        return self.lengths

    @property
    def total_length(self) -> float:
        """Total support length."""
        return float(np.sum(self.lengths))

    @property
    def fingerprint(self) -> str:
        """Deterministic lixel partition fingerprint."""
        return stable_fingerprint(
            self.lixel_ids,
            self.edge_indices,
            self.edge_ids,
            self.start_offsets,
            self.end_offsets,
            self.center_offsets,
            self.lengths,
            self.center_coordinates,
            self.geometries,
            self.network_fingerprint,
            self.target_length,
            self.crs,
            self.spatial_unit,
            self.provenance.fingerprint,
        )

    def validate(self, network: LinearNetwork) -> DataValidationReport:
        """Validate lixel coverage and compatibility with a network."""
        issues: list[DataIssue] = []
        if self.network_fingerprint != network.fingerprint:
            issues.append(
                DataIssue(
                    "error",
                    "network_fingerprint_mismatch",
                    "LixelSupport was generated for a different network.",
                )
            )
        if np.any(self.edge_indices >= network.n_edges):
            issues.append(
                DataIssue(
                    "error",
                    "missing_edge_index",
                    "Some lixels reference an edge outside the network.",
                )
            )
        coverage_error = abs(self.total_length - network.total_length)
        tolerance = max(1e-9, network.total_length * 1e-12)
        if coverage_error > tolerance:
            issues.append(
                DataIssue(
                    "error",
                    "lixel_length_mismatch",
                    "Lixel measures do not cover the complete network length.",
                    {"absolute_error": coverage_error},
                )
            )
        remainder_count = int(
            np.count_nonzero(self.lengths < self.target_length - 1e-12)
        )
        return DataValidationReport(
            tuple(issues),
            {
                "n_lixels": self.n_lixels,
                "total_length": self.total_length,
                "target_length": self.target_length,
                "remainder_lixel_count": remainder_count,
            },
        )

    def to_frame(self) -> pd.DataFrame:
        """Return lixel attributes as a DataFrame."""
        return pd.DataFrame(
            {
                "lixel_id": self.lixel_ids,
                "edge_id": self.edge_ids,
                "edge_index": self.edge_indices,
                "start_offset": self.start_offsets,
                "end_offset": self.end_offsets,
                "center_offset": self.center_offsets,
                "length": self.lengths,
                "center_x": self.center_coordinates[:, 0],
                "center_y": self.center_coordinates[:, 1],
            }
        )

    def to_geodataframe(self) -> Any:
        """Return lixels as a line GeoDataFrame."""
        try:
            import geopandas as gpd
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "GeoDataFrame export requires the 'network' optional dependencies."
            ) from exc
        return gpd.GeoDataFrame(
            self.to_frame(), geometry=list(self.geometries), crs=self.crs
        )

    @classmethod
    def from_network(
        cls,
        network: LinearNetwork,
        *,
        length: float,
        provenance: DataProvenance | None = None,
    ) -> "LixelSupport":
        """Partition every network edge into lixels of at most ``length``."""
        if not isinstance(network, LinearNetwork):
            raise TypeError("network must be a LinearNetwork instance.")
        target = float(length)
        if not np.isfinite(target) or target <= 0.0:
            raise ValueError("length must be finite and positive.")
        substring = _require_substring()
        lixel_ids: list[int] = []
        edge_indices: list[int] = []
        edge_ids: list[Any] = []
        starts: list[float] = []
        ends: list[float] = []
        centers: list[float] = []
        lengths: list[float] = []
        coordinates: list[tuple[float, float]] = []
        geometries: list[Any] = []
        next_id = 0
        for edge_index in range(network.n_edges):
            edge_length = float(network.edge_lengths[edge_index])
            geometry = network.edge_geometries[edge_index]
            geometric_length = float(geometry.length)
            n_segments = max(1, int(np.ceil(edge_length / target)))
            for segment_index in range(n_segments):
                start = segment_index * target
                end = min((segment_index + 1) * target, edge_length)
                center = 0.5 * (start + end)
                start_geometry = (start / edge_length) * geometric_length
                end_geometry = (end / edge_length) * geometric_length
                line = substring(geometry, start_geometry, end_geometry)
                center_point = geometry.interpolate(
                    center / edge_length, normalized=True
                )
                lixel_ids.append(next_id)
                edge_indices.append(edge_index)
                edge_ids.append(network.edge_ids[edge_index])
                starts.append(start)
                ends.append(end)
                centers.append(center)
                lengths.append(end - start)
                coordinates.append((float(center_point.x), float(center_point.y)))
                geometries.append(line)
                next_id += 1
        edge_id_array = np.empty(len(edge_ids), dtype=object)
        edge_id_array[:] = edge_ids
        return cls(
            lixel_ids=np.asarray(lixel_ids, dtype=np.int64),
            edge_indices=np.asarray(edge_indices, dtype=np.int64),
            edge_ids=edge_id_array,
            start_offsets=np.asarray(starts, dtype=float),
            end_offsets=np.asarray(ends, dtype=float),
            center_offsets=np.asarray(centers, dtype=float),
            lengths=np.asarray(lengths, dtype=float),
            center_coordinates=np.asarray(coordinates, dtype=float),
            geometries=tuple(geometries),
            network_fingerprint=network.fingerprint,
            target_length=target,
            crs=network.crs,
            spatial_unit=network.spatial_unit,
            provenance=(provenance or network.provenance).with_transformation(
                "lixelized_network", target_length=target
            ),
        )
