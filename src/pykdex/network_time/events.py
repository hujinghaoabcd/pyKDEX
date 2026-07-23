# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Accepted network events paired with authoritative temporal coordinates."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from pykdex.data import DataProvenance, TemporalCoordinates
from pykdex.data._utils import stable_fingerprint
from pykdex.data.validation import DataIssue, DataValidationReport
from pykdex.network import LinearNetwork, NetworkEvents


@dataclass(frozen=True)
class NetworkTimeEvents:
    """Immutable accepted network locations paired one-to-one with time."""

    network_events: NetworkEvents
    temporal: TemporalCoordinates
    provenance: DataProvenance = field(default_factory=DataProvenance)

    def __post_init__(self) -> None:
        if not isinstance(self.network_events, NetworkEvents):
            raise TypeError("network_events must be a NetworkEvents instance.")
        if not isinstance(self.temporal, TemporalCoordinates):
            raise TypeError("temporal must be a TemporalCoordinates instance.")
        if self.network_events.n_events != self.temporal.n_times:
            raise ValueError(
                "network events and temporal coordinates must have equal length."
            )

    @property
    def n_events(self) -> int:
        """Number of accepted network-time events."""
        return self.network_events.n_events

    @property
    def event_ids(self) -> np.ndarray:
        """Stable event identifiers."""
        return self.network_events.event_ids

    @property
    def edge_indices(self) -> np.ndarray:
        """Network edge index per event."""
        return self.network_events.edge_indices

    @property
    def offsets(self) -> np.ndarray:
        """Along-edge offset per event."""
        return self.network_events.offsets

    @property
    def times(self) -> np.ndarray:
        """Canonical temporal coordinate per event."""
        return self.temporal.values

    @property
    def weights(self) -> np.ndarray:
        """Non-negative event weights."""
        return self.network_events.weights

    @property
    def weight_sum(self) -> float:
        """Total event weight."""
        return self.network_events.weight_sum

    @property
    def network_fingerprint(self) -> str:
        """Fingerprint of the network owning event locations."""
        return self.network_events.network_fingerprint

    @property
    def fingerprint(self) -> str:
        """Deterministic network-location and time fingerprint."""
        return stable_fingerprint(
            self.network_events.fingerprint,
            self.temporal.fingerprint,
            self.provenance.fingerprint,
        )

    def validate(self, network: LinearNetwork) -> DataValidationReport:
        """Validate network compatibility and temporal duplication."""
        report = self.network_events.validate(network)
        issues = list(report.issues)
        if np.unique(self.times).size < self.n_events:
            issues.append(
                DataIssue(
                    "warning",
                    "duplicate_times",
                    "Multiple accepted events share a temporal coordinate.",
                )
            )
        statistics = dict(report.statistics)
        statistics.update(
            {
                "time_domain": self.temporal.domain.name,
                "temporal_unit": self.temporal.temporal_unit,
            }
        )
        return DataValidationReport(tuple(issues), statistics)

    def to_frame(self) -> pd.DataFrame:
        """Return accepted network locations, weights, and times."""
        frame = self.network_events.to_frame()
        frame["time"] = self.times
        return frame
