# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Structured bundles for network examples and analytical fixtures.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from pykdex.data import DataProvenance, SpatialEvents
from pykdex.data._utils import stable_fingerprint
from pykdex.data.validation import DataValidationReport
from pykdex.network.events import NetworkEvents
from pykdex.network.linear_network import LinearNetwork
from pykdex.network.support import LixelSupport


@dataclass(frozen=True)
class NetworkDataset:
    """A reproducible network, event, support, and expected-value bundle."""

    name: str
    network: LinearNetwork
    raw_events: SpatialEvents
    network_events: NetworkEvents | None = None
    lixels: LixelSupport | None = None
    expected: Mapping[str, Any] = field(default_factory=dict)
    description: str = ""
    provenance: DataProvenance = field(default_factory=DataProvenance)

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if not name:
            raise ValueError("name must be a non-empty string.")
        if not isinstance(self.network, LinearNetwork):
            raise TypeError("network must be a LinearNetwork instance.")
        if not isinstance(self.raw_events, SpatialEvents):
            raise TypeError("raw_events must be a SpatialEvents instance.")
        if self.network_events is not None and not isinstance(
            self.network_events, NetworkEvents
        ):
            raise TypeError("network_events must be NetworkEvents or None.")
        if self.lixels is not None and not isinstance(self.lixels, LixelSupport):
            raise TypeError("lixels must be LixelSupport or None.")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", str(self.description).strip())
        object.__setattr__(self, "expected", MappingProxyType(dict(self.expected)))

    @property
    def fingerprint(self) -> str:
        """Deterministic fingerprint for the complete network bundle."""
        return stable_fingerprint(
            self.name,
            self.network.fingerprint,
            self.raw_events.fingerprint,
            None if self.network_events is None else self.network_events.fingerprint,
            None if self.lixels is None else self.lixels.fingerprint,
            dict(self.expected),
            self.description,
            self.provenance.fingerprint,
        )

    def validate(self) -> DataValidationReport:
        """Validate network, event, and lixel compatibility."""
        report = self.network.validate()
        if self.network_events is not None:
            report = report.combine(self.network_events.validate(self.network))
        if self.lixels is not None:
            report = report.combine(self.lixels.validate(self.network))
        return report

    def summary(self) -> dict[str, Any]:
        """Return a compact serializable dataset summary."""
        report = self.validate()
        return {
            "name": self.name,
            "description": self.description,
            "n_nodes": self.network.n_nodes,
            "n_edges": self.network.n_edges,
            "n_raw_events": self.raw_events.n_events,
            "n_network_events": (
                None if self.network_events is None else self.network_events.n_events
            ),
            "n_lixels": None if self.lixels is None else self.lixels.n_lixels,
            "valid": report.valid,
            "n_warnings": len(report.warnings),
            "fingerprint": self.fingerprint,
        }
