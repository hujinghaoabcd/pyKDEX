# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Exposure fields defined on measured pyKDEX supports."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
import pandas as pd

from pykdex.data._utils import normalize_unit, readonly_array, stable_fingerprint
from pykdex.data.provenance import DataProvenance
from pykdex.risk.support import (
    MeasuredSupport,
    SupportDescriptor,
    describe_measured_support,
)


@dataclass(frozen=True)
class ExposureField:
    """Non-negative exposure density on a measured support.

    ``values`` always stores exposure density with respect to the support
    measure, even when the object was created from per-element exposure amounts.
    The ``representation`` field records which public constructor supplied the
    original values.
    """

    values: np.ndarray
    support: MeasuredSupport
    exposure_unit: str
    representation: str = "density"
    provenance: DataProvenance = field(default_factory=DataProvenance)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    descriptor: SupportDescriptor = field(init=False, repr=False)

    def __post_init__(self) -> None:
        descriptor = describe_measured_support(self.support)
        values = readonly_array(self.values, dtype=float, ndim=1, name="values")
        if values.shape != (descriptor.n_elements,):
            raise ValueError(
                "values must contain one exposure value per support element."
            )
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("exposure values must be finite and non-negative.")
        unit = normalize_unit(self.exposure_unit, name="exposure_unit")
        if unit is None:
            raise ValueError("exposure_unit must be explicit.")
        representation = str(self.representation).strip().lower()
        if representation not in {"density", "amount"}:
            raise ValueError("representation must be 'density' or 'amount'.")
        if not isinstance(self.provenance, DataProvenance):
            raise TypeError("provenance must be a DataProvenance instance.")
        metadata = MappingProxyType(dict(self.metadata))
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "exposure_unit", unit)
        object.__setattr__(self, "representation", representation)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "descriptor", descriptor)

    @classmethod
    def from_density(
        cls,
        values: Any,
        support: MeasuredSupport,
        *,
        exposure_unit: str,
        provenance: DataProvenance | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "ExposureField":
        """Construct from exposure density per unit support measure."""
        return cls(
            values=np.asarray(values),
            support=support,
            exposure_unit=exposure_unit,
            representation="density",
            provenance=provenance or DataProvenance(),
            metadata={} if metadata is None else metadata,
        )

    @classmethod
    def from_amounts(
        cls,
        amounts: Any,
        support: MeasuredSupport,
        *,
        exposure_unit: str,
        provenance: DataProvenance | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "ExposureField":
        """Construct from exposure amount represented by each support element."""
        descriptor = describe_measured_support(support)
        amount_values = readonly_array(
            amounts,
            dtype=float,
            ndim=1,
            name="amounts",
        )
        if amount_values.shape != (descriptor.n_elements,):
            raise ValueError("amounts must contain one value per support element.")
        if not np.all(np.isfinite(amount_values)) or np.any(amount_values < 0.0):
            raise ValueError("exposure amounts must be finite and non-negative.")
        density = amount_values / descriptor.measure
        return cls(
            values=density,
            support=support,
            exposure_unit=exposure_unit,
            representation="amount",
            provenance=provenance or DataProvenance(),
            metadata={} if metadata is None else metadata,
        )

    @property
    def density(self) -> np.ndarray:
        """Canonical exposure density values."""
        return self.values

    @property
    def amounts(self) -> np.ndarray:
        """Exposure amount represented by each measured support element."""
        amounts = np.ascontiguousarray(self.values * self.descriptor.measure)
        amounts.setflags(write=False)
        return amounts

    @property
    def total_exposure(self) -> float:
        """Total exposure integrated over the measured support."""
        return float(np.dot(self.values, self.descriptor.measure))

    @property
    def is_zero(self) -> bool:
        """Whether the complete field contains zero exposure."""
        return bool(np.all(self.values == 0.0))

    @property
    def fingerprint(self) -> str:
        """Deterministic content and support identity fingerprint."""
        return stable_fingerprint(
            self.values,
            self.descriptor.fingerprint,
            self.exposure_unit,
            self.representation,
            self.provenance.fingerprint,
            dict(self.metadata),
        )

    def to_frame(self) -> pd.DataFrame:
        """Return support attributes, exposure density, and exposure amount."""
        frame = self.support.to_frame()
        frame["exposure_density"] = self.values
        frame["exposure_amount"] = self.amounts
        return frame

    def to_grid(self) -> np.ndarray:
        """Reshape values when the support has a native grid representation."""
        reshape = getattr(self.support, "reshape", None)
        if reshape is None or not callable(reshape):
            raise ValueError("This support has no native grid reshape operation.")
        return np.asarray(reshape(self.values))

    def to_geodataframe(self) -> Any:
        """Return a GeoDataFrame when the support provides geospatial export."""
        exporter = getattr(self.support, "to_geodataframe", None)
        if exporter is None or not callable(exporter):
            raise ValueError("This support does not provide GeoDataFrame export.")
        frame = exporter()
        frame["exposure_density"] = self.values
        frame["exposure_amount"] = self.amounts
        return frame
