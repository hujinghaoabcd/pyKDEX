# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Structured dataset bundles for examples and reproducible analysis.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from pykdex.data.boundary import SpatialBoundary
from pykdex.data.events import SpatialEvents
from pykdex.data.provenance import DataProvenance
from pykdex.data.support import GridSupport, PointSupport
from pykdex.data.validation import DataIssue, DataValidationReport

Support = PointSupport | GridSupport


@dataclass(frozen=True)
class KDEDataset:
    """A reproducible bundle of events, support, boundary, and reference values."""

    name: str
    events: SpatialEvents
    support: Support | None = None
    boundary: SpatialBoundary | None = None
    expected: Mapping[str, Any] = field(default_factory=dict)
    description: str = ""
    provenance: DataProvenance = field(default_factory=DataProvenance)

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if not name:
            raise ValueError("name must be a non-empty string.")
        if not isinstance(self.events, SpatialEvents):
            raise TypeError("events must be a SpatialEvents instance.")
        if self.support is not None and not isinstance(
            self.support, (PointSupport, GridSupport)
        ):
            raise TypeError("support must be PointSupport, GridSupport, or None.")
        if self.boundary is not None and not isinstance(self.boundary, SpatialBoundary):
            raise TypeError("boundary must be SpatialBoundary or None.")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", str(self.description).strip())
        object.__setattr__(self, "expected", MappingProxyType(dict(self.expected)))

    def validate(self) -> DataValidationReport:
        """Validate dimensional, CRS, unit, and boundary compatibility."""
        report = self.events.validate()
        issues = list(report.issues)
        statistics = dict(report.statistics)
        if self.support is not None:
            if self.support.dimension != self.events.dimension:
                issues.append(
                    DataIssue(
                        "error",
                        "dimension_mismatch",
                        "Event and support coordinate dimensions differ.",
                        {
                            "event_dimension": self.events.dimension,
                            "support_dimension": self.support.dimension,
                        },
                    )
                )
            _append_metadata_issues(
                issues,
                left_name="events",
                right_name="support",
                left_crs=self.events.crs,
                right_crs=self.support.crs,
                left_unit=self.events.spatial_unit,
                right_unit=self.support.spatial_unit,
            )
            statistics["n_support"] = self.support.n_points
        if self.boundary is not None:
            _append_metadata_issues(
                issues,
                left_name="events",
                right_name="boundary",
                left_crs=self.events.crs,
                right_crs=self.boundary.crs,
                left_unit=self.events.spatial_unit,
                right_unit=self.boundary.spatial_unit,
            )
            if self.events.dimension == 2:
                boundary_report = self.boundary.validate_points(self.events.coordinates)
                issues.extend(boundary_report.issues)
                statistics.update(
                    {
                        f"boundary_{key}": value
                        for key, value in boundary_report.statistics.items()
                    }
                )
        return DataValidationReport(tuple(issues), statistics)

    def summary(self) -> dict[str, Any]:
        """Return a compact serializable dataset summary."""
        validation = self.validate()
        return {
            "name": self.name,
            "description": self.description,
            "n_events": self.events.n_events,
            "dimension": self.events.dimension,
            "n_support": None if self.support is None else self.support.n_points,
            "has_boundary": self.boundary is not None,
            "valid": validation.valid,
            "n_warnings": len(validation.warnings),
            "fingerprint": self.fingerprint,
        }

    @property
    def fingerprint(self) -> str:
        """Deterministic fingerprint for the complete bundle."""
        from pykdex.data._utils import stable_fingerprint

        return stable_fingerprint(
            self.name,
            self.events.fingerprint,
            None if self.support is None else self.support.fingerprint,
            None if self.boundary is None else self.boundary.fingerprint,
            dict(self.expected),
            self.description,
            self.provenance.fingerprint,
        )


def _append_metadata_issues(
    issues: list[DataIssue],
    *,
    left_name: str,
    right_name: str,
    left_crs: str | None,
    right_crs: str | None,
    left_unit: str | None,
    right_unit: str | None,
) -> None:
    if left_crs is not None and right_crs is not None and left_crs != right_crs:
        issues.append(
            DataIssue(
                "error",
                "crs_mismatch",
                f"{left_name} and {right_name} use different CRS labels.",
                {left_name: left_crs, right_name: right_crs},
            )
        )
    if left_unit is not None and right_unit is not None and left_unit != right_unit:
        issues.append(
            DataIssue(
                "error",
                "spatial_unit_mismatch",
                f"{left_name} and {right_name} use different spatial units.",
                {left_name: left_unit, right_name: right_unit},
            )
        )
