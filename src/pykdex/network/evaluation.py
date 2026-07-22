# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Internal numerical evaluation routes for network kernel estimators."""

from __future__ import annotations

import numpy as np

from pykdex.kernels import BaseKernel
from pykdex.network.distance import (
    NetworkDistanceAsset,
    NetworkLocations,
    build_event_lixel_distances,
)
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


def _as_source_bandwidths(
    bandwidth: float | np.ndarray,
    n_sources: int,
) -> np.ndarray:
    values = np.asarray(bandwidth, dtype=float)
    if values.ndim == 0:
        values = np.full(n_sources, float(values), dtype=float)
    elif values.ndim == 1 and values.shape[0] == n_sources:
        values = values.copy()
    else:
        raise ValueError("bandwidth must be scalar or contain one value per source.")
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ValueError("bandwidth values must be finite and positive.")
    return np.ascontiguousarray(values)


def evaluate_distance_kernel_matrix(
    asset: NetworkDistanceAsset,
    kernel: BaseKernel,
    bandwidth: float | np.ndarray,
) -> np.ndarray:
    """Evaluate a source-by-target kernel matrix from a distance asset."""
    bandwidths = _as_source_bandwidths(bandwidth, asset.shape[0])
    matrix = np.zeros(asset.shape, dtype=float)
    if asset.n_pairs == 0:
        return matrix
    local_bandwidths = bandwidths[asset.row_indices]
    standardized = asset.distances / local_bandwidths
    values = kernel(standardized, 1) / local_bandwidths
    matrix[asset.row_indices, asset.column_indices] = values
    return matrix


def evaluate_propagation_kernel_matrix(
    traces: tuple[PropagationTrace, ...],
    targets: NetworkLocations,
    kernel: BaseKernel,
    bandwidth: float | np.ndarray,
) -> np.ndarray:
    """Evaluate cached signed propagation traces at arbitrary network locations."""
    bandwidths = _as_source_bandwidths(bandwidth, len(traces))
    matrix = np.zeros((len(traces), targets.n_locations), dtype=float)
    edge_targets: dict[int, np.ndarray] = {}
    for edge_index in np.unique(targets.edge_indices):
        edge_targets[int(edge_index)] = np.flatnonzero(
            targets.edge_indices == edge_index
        )
    for source_index, trace in enumerate(traces):
        h = float(bandwidths[source_index])
        tolerance = max(1e-12, h * 1e-12)
        for record in trace.records:
            indices = edge_targets.get(record.edge_index)
            if indices is None or indices.size == 0:
                continue
            offsets = targets.offsets[indices]
            lower = min(record.start_offset, record.end_offset) - tolerance
            upper = max(record.start_offset, record.end_offset) + tolerance
            selected = (offsets >= lower) & (offsets <= upper)
            if not record.include_start:
                selected &= np.abs(offsets - record.start_offset) > tolerance
            if not np.any(selected):
                continue
            selected_indices = indices[selected]
            distances = record.start_distance + np.abs(
                targets.offsets[selected_indices] - record.start_offset
            )
            inside = distances <= h + tolerance
            if not np.any(inside):
                continue
            target_indices = selected_indices[inside]
            contribution = (
                record.coefficient * kernel(distances[inside] / h, 1) / h
            )
            np.add.at(matrix[source_index], target_indices, contribution)
    return matrix


def evaluate_simple_kernel(
    workspace: NetworkWorkspace,
    events: NetworkEvents,
    kernel: BaseKernel,
    bandwidth: float | np.ndarray,
    coefficients: np.ndarray,
    *,
    directed: bool,
) -> tuple[np.ndarray, NetworkDistanceAsset]:
    """Evaluate shortest-path radial kernels at all workspace lixel centres."""
    bandwidths = _as_source_bandwidths(bandwidth, events.n_events)
    maximum_bandwidth = float(np.max(bandwidths))
    cutoff = maximum_bandwidth if kernel.finite_support else None
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
    local_bandwidths = bandwidths[asset.row_indices]
    kernel_values = kernel(asset.distances / local_bandwidths, 1) / local_bandwidths
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
    bandwidth: float | np.ndarray,
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
    bandwidths = _as_source_bandwidths(bandwidth, events.n_events)
    values = np.zeros(lixels.n_lixels, dtype=float)
    traces: list[PropagationTrace] = []
    n_records = 0
    for event_index in range(events.n_events):
        event_bandwidth = float(bandwidths[event_index])
        trace = trace_network_propagation(
            workspace.network,
            int(events.edge_indices[event_index]),
            float(events.offsets[event_index]),
            cutoff=event_bandwidth,
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
            event_bandwidth,
        )
        traces.append(trace)
        n_records += trace.n_records
    return values, tuple(traces), float(np.min(values)), n_records
