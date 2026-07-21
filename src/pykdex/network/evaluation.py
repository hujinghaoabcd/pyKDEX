# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Internal numerical evaluation routes for network kernel estimators."""

from __future__ import annotations

import numpy as np

from pykdex.kernels import BaseKernel
from pykdex.network.distance import NetworkDistanceAsset, build_event_lixel_distances
from pykdex.network.events import NetworkEvents
from pykdex.network.propagation import (
    JunctionPolicy,
    PropagationTrace,
    trace_network_propagation,
)
from pykdex.network.support import LixelSupport
from pykdex.network.workspace import NetworkWorkspace


def _distance_asset_usable(
    asset: NetworkDistanceAsset | None,
    *,
    cutoff: float | None,
    directed: bool,
) -> bool:
    if asset is None or asset.weight != "length" or asset.directed != directed:
        return False
    if cutoff is None:
        return asset.cutoff is None
    return asset.cutoff is None or asset.cutoff >= cutoff - 1e-12


def evaluate_simple_kernel(
    workspace: NetworkWorkspace,
    events: NetworkEvents,
    kernel: BaseKernel,
    bandwidth: float,
    coefficients: np.ndarray,
    *,
    directed: bool,
) -> tuple[np.ndarray, NetworkDistanceAsset]:
    """Evaluate shortest-path radial kernels at all workspace lixel centres."""
    cutoff = bandwidth if kernel.finite_support else None
    asset = workspace.distance_asset
    if not _distance_asset_usable(asset, cutoff=cutoff, directed=directed):
        asset = build_event_lixel_distances(
            workspace.network,
            events,
            workspace.lixels,
            cutoff=cutoff,
            weight="length",
            directed=directed,
        )
    assert asset is not None
    values = np.zeros(workspace.lixels.n_lixels, dtype=float)
    kernel_values = kernel(asset.distances / bandwidth, 1) / bandwidth
    np.add.at(
        values,
        asset.column_indices,
        kernel_values * coefficients[asset.row_indices],
    )
    return values, asset


def _trace_values(
    trace: PropagationTrace,
    lixels: LixelSupport,
    edge_lixels: tuple[np.ndarray, ...],
    kernel: BaseKernel,
    bandwidth: float,
) -> np.ndarray:
    values = np.zeros(lixels.n_lixels, dtype=float)
    tolerance = max(1e-12, bandwidth * 1e-12)
    for record in trace.records:
        indices = edge_lixels[record.edge_index]
        if indices.size == 0:
            continue
        centers = lixels.center_offsets[indices]
        lower = min(record.start_offset, record.end_offset) - tolerance
        upper = max(record.start_offset, record.end_offset) + tolerance
        selected = (centers >= lower) & (centers <= upper)
        if not record.include_start:
            selected &= np.abs(centers - record.start_offset) > tolerance
        if not np.any(selected):
            continue
        selected_indices = indices[selected]
        distances = record.start_distance + np.abs(
            lixels.center_offsets[selected_indices] - record.start_offset
        )
        inside = distances <= bandwidth + tolerance
        if not np.any(inside):
            continue
        targets = selected_indices[inside]
        contribution = (
            record.coefficient * kernel(distances[inside] / bandwidth, 1) / bandwidth
        )
        np.add.at(values, targets, contribution)
    return values


def evaluate_path_kernel(
    workspace: NetworkWorkspace,
    events: NetworkEvents,
    kernel: BaseKernel,
    policy: JunctionPolicy,
    bandwidth: float,
    coefficients: np.ndarray,
    *,
    directed: bool,
    coefficient_tolerance: float,
    max_records_per_event: int,
) -> tuple[np.ndarray, tuple[PropagationTrace, ...], float, int]:
    """Evaluate equal-split path traces at all workspace lixel centres."""
    lixels = workspace.lixels
    edge_lixels = tuple(
        np.flatnonzero(lixels.edge_indices == edge_index)
        for edge_index in range(workspace.network.n_edges)
    )
    values = np.zeros(lixels.n_lixels, dtype=float)
    traces: list[PropagationTrace] = []
    n_records = 0
    for event_index in range(events.n_events):
        trace = trace_network_propagation(
            workspace.network,
            int(events.edge_indices[event_index]),
            float(events.offsets[event_index]),
            cutoff=bandwidth,
            junction_policy=policy,
            directed=directed,
            coefficient_tolerance=coefficient_tolerance,
            max_records=max_records_per_event,
            source_id=events.event_ids[event_index],
        )
        values += float(coefficients[event_index]) * _trace_values(
            trace,
            lixels,
            edge_lixels,
            kernel,
            bandwidth,
        )
        traces.append(trace)
        n_records += trace.n_records
    return values, tuple(traces), float(np.min(values)), n_records
