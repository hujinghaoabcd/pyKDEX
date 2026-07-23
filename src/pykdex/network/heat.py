# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Sparse finite-element assets for heat flow on metric graphs.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse

from pykdex.data._utils import readonly_array, stable_fingerprint
from pykdex.network.workspace import NetworkWorkspace


def _readonly_csr(matrix: sparse.spmatrix) -> sparse.csr_matrix:
    owned = sparse.csr_matrix(matrix, dtype=float, copy=True)
    owned.sort_indices()
    owned.data.setflags(write=False)
    owned.indices.setflags(write=False)
    owned.indptr.setflags(write=False)
    return owned


def _coalesce_offsets(values: np.ndarray, *, length: float) -> np.ndarray:
    ordered = np.sort(np.asarray(values, dtype=float))
    tolerance = max(1e-12, length * 1e-12)
    retained = [float(ordered[0])]
    for value in ordered[1:]:
        if float(value) - retained[-1] > tolerance:
            retained.append(float(value))
    result = np.asarray(retained, dtype=float)
    result[0] = 0.0
    result[-1] = length
    return result


@dataclass(frozen=True)
class NetworkHeatOperator:
    """Measured sparse heat operator for one prepared network workspace.

    The operator uses continuous piecewise-linear finite elements. Original
    network vertices are shared degrees of freedom, so vertex continuity and
    Kirchhoff flux balance are built into the weak formulation. Degree-one
    terminals receive the natural zero-flux (Neumann) condition.
    """

    mass: np.ndarray
    stiffness: sparse.csr_matrix
    edge_offsets: tuple[np.ndarray, ...]
    edge_dofs: tuple[np.ndarray, ...]
    event_dofs: np.ndarray
    dof_component_labels: np.ndarray
    mesh_size: float
    network_fingerprint: str
    event_fingerprint: str
    support_fingerprint: str

    def __post_init__(self) -> None:
        mass = readonly_array(self.mass, dtype=float, ndim=1, name="mass")
        if mass.size == 0 or not np.all(np.isfinite(mass)) or np.any(mass <= 0.0):
            raise ValueError("mass must contain finite positive nodal measures.")
        stiffness = _readonly_csr(self.stiffness)
        if stiffness.shape != (mass.size, mass.size):
            raise ValueError("stiffness shape must match the nodal mass vector.")
        if stiffness.nnz and not np.all(np.isfinite(stiffness.data)):
            raise ValueError("stiffness must contain only finite values.")
        offsets = tuple(
            readonly_array(values, dtype=float, ndim=1, name="edge_offsets")
            for values in self.edge_offsets
        )
        dofs = tuple(
            readonly_array(values, dtype=np.int64, ndim=1, name="edge_dofs")
            for values in self.edge_dofs
        )
        if len(offsets) == 0 or len(offsets) != len(dofs):
            raise ValueError("edge_offsets and edge_dofs must describe every edge.")
        for edge_offsets, edge_dofs in zip(offsets, dofs, strict=True):
            if edge_offsets.size < 2 or edge_offsets.shape != edge_dofs.shape:
                raise ValueError(
                    "each heat edge requires matching breakpoint and DOF arrays."
                )
            if not np.all(np.diff(edge_offsets) > 0.0):
                raise ValueError("heat edge offsets must be strictly increasing.")
            if np.any(edge_dofs < 0) or np.any(edge_dofs >= mass.size):
                raise ValueError("heat edge DOFs reference a missing node.")
        event_dofs = readonly_array(
            self.event_dofs, dtype=np.int64, ndim=1, name="event_dofs"
        )
        if (
            event_dofs.size == 0
            or np.any(event_dofs < 0)
            or np.any(event_dofs >= mass.size)
        ):
            raise ValueError("event_dofs must reference valid heat nodes.")
        labels = readonly_array(
            self.dof_component_labels,
            dtype=np.int64,
            ndim=1,
            name="dof_component_labels",
        )
        if labels.shape != mass.shape or np.any(labels < 0):
            raise ValueError("dof_component_labels must label every heat node.")
        mesh_size = float(self.mesh_size)
        if not np.isfinite(mesh_size) or mesh_size <= 0.0:
            raise ValueError("mesh_size must be finite and positive.")
        fingerprints = (
            str(self.network_fingerprint).strip(),
            str(self.event_fingerprint).strip(),
            str(self.support_fingerprint).strip(),
        )
        if any(not value for value in fingerprints):
            raise ValueError("heat operator fingerprints must be non-empty.")
        object.__setattr__(self, "mass", mass)
        object.__setattr__(self, "stiffness", stiffness)
        object.__setattr__(self, "edge_offsets", offsets)
        object.__setattr__(self, "edge_dofs", dofs)
        object.__setattr__(self, "event_dofs", event_dofs)
        object.__setattr__(self, "dof_component_labels", labels)
        object.__setattr__(self, "mesh_size", mesh_size)
        object.__setattr__(self, "network_fingerprint", fingerprints[0])
        object.__setattr__(self, "event_fingerprint", fingerprints[1])
        object.__setattr__(self, "support_fingerprint", fingerprints[2])

    @property
    def n_dofs(self) -> int:
        """Number of finite-element degrees of freedom."""
        return int(self.mass.size)

    @property
    def n_segments(self) -> int:
        """Number of one-dimensional finite elements."""
        return int(sum(offsets.size - 1 for offsets in self.edge_offsets))

    @property
    def fingerprint(self) -> str:
        """Deterministic operator fingerprint."""
        return stable_fingerprint(
            self.mass,
            self.stiffness.data,
            self.stiffness.indices,
            self.stiffness.indptr,
            self.edge_offsets,
            self.edge_dofs,
            self.event_dofs,
            self.dof_component_labels,
            self.mesh_size,
            self.network_fingerprint,
            self.event_fingerprint,
            self.support_fingerprint,
        )

    def symmetric_generator(self) -> sparse.csr_matrix:
        """Return ``M^-1/2 K M^-1/2`` for stable heat evolution."""
        inverse_root = sparse.diags(1.0 / np.sqrt(self.mass), format="csr")
        return sparse.csr_matrix(inverse_root @ self.stiffness @ inverse_root)

    def lixel_averages(
        self, nodal_values: np.ndarray, workspace: NetworkWorkspace
    ) -> np.ndarray:
        """Integrate a piecewise-linear field exactly over every lixel."""
        values = np.asarray(nodal_values, dtype=float)
        if values.shape != self.mass.shape:
            raise ValueError("nodal_values must contain one value per heat DOF.")
        if workspace.network.fingerprint != self.network_fingerprint:
            raise ValueError("workspace belongs to a different network.")
        if workspace.lixels.fingerprint != self.support_fingerprint:
            raise ValueError("workspace uses a different lixel support.")
        averages = np.empty(workspace.lixels.n_lixels, dtype=float)
        for index in range(workspace.lixels.n_lixels):
            edge = int(workspace.lixels.edge_indices[index])
            start = float(workspace.lixels.start_offsets[index])
            end = float(workspace.lixels.end_offsets[index])
            offsets = self.edge_offsets[edge]
            edge_values = values[self.edge_dofs[edge]]
            left = int(np.argmin(np.abs(offsets - start)))
            right = int(np.argmin(np.abs(offsets - end)))
            selected_offsets = offsets[left : right + 1]
            selected_values = edge_values[left : right + 1]
            if (
                selected_offsets.size < 2
                or not np.isclose(selected_offsets[0], start)
                or not np.isclose(selected_offsets[-1], end)
            ):
                raise RuntimeError("lixel boundaries are missing from the heat mesh.")
            widths = np.diff(selected_offsets)
            integral = float(
                np.sum(0.5 * widths * (selected_values[:-1] + selected_values[1:]))
            )
            averages[index] = integral / (end - start)
        return averages


def build_network_heat_operator(
    workspace: NetworkWorkspace,
    *,
    mesh_size: float | None = None,
) -> NetworkHeatOperator:
    """Build a reusable sparse metric-graph heat operator.

    Every event offset and lixel boundary is inserted exactly. ``mesh_size``
    adds uniform refinement where needed and defaults to the lixel target
    length.
    """
    if not isinstance(workspace, NetworkWorkspace):
        raise TypeError("workspace must be a NetworkWorkspace instance.")
    workspace.validate().raise_for_errors()
    network = workspace.network
    events = workspace.events
    if events is None:
        raise ValueError("workspace contains no accepted network events.")
    if network.directed:
        raise ValueError("NetworkHeatOperator requires an undirected metric graph.")
    if np.any(network.edge_u == network.edge_v):
        raise ValueError("NetworkHeatOperator does not yet support self-loop edges.")
    if isinstance(mesh_size, (bool, np.bool_)):
        raise TypeError("mesh_size must not be boolean.")
    resolved_size = (
        workspace.lixels.target_length if mesh_size is None else float(mesh_size)
    )
    if not np.isfinite(resolved_size) or resolved_size <= 0.0:
        raise ValueError("mesh_size must be finite and positive.")

    edge_offsets: list[np.ndarray] = []
    edge_dofs: list[np.ndarray] = []
    next_dof = network.n_nodes
    for edge in range(network.n_edges):
        length = float(network.edge_lengths[edge])
        subdivisions = max(1, int(np.ceil(length / resolved_size)))
        candidates = [
            np.linspace(0.0, length, subdivisions + 1, dtype=float),
            workspace.lixels.start_offsets[workspace.lixels.edge_indices == edge],
            workspace.lixels.end_offsets[workspace.lixels.edge_indices == edge],
            events.offsets[events.edge_indices == edge],
        ]
        breakpoints = _coalesce_offsets(np.concatenate(candidates), length=length)
        dofs = np.empty(breakpoints.size, dtype=np.int64)
        dofs[0] = int(network.edge_u[edge])
        dofs[-1] = int(network.edge_v[edge])
        if breakpoints.size > 2:
            dofs[1:-1] = np.arange(
                next_dof, next_dof + breakpoints.size - 2, dtype=np.int64
            )
            next_dof += breakpoints.size - 2
        edge_offsets.append(breakpoints)
        edge_dofs.append(dofs)

    rows: list[int] = []
    columns: list[int] = []
    data: list[float] = []
    mass = np.zeros(next_dof, dtype=float)
    labels = np.empty(next_dof, dtype=np.int64)
    labels[: network.n_nodes] = network.component_labels
    for edge, (offsets, dofs) in enumerate(zip(edge_offsets, edge_dofs, strict=True)):
        component = int(network.component_labels[int(network.edge_u[edge])])
        labels[dofs] = component
        for left in range(offsets.size - 1):
            right = left + 1
            length = float(offsets[right] - offsets[left])
            left_dof = int(dofs[left])
            right_dof = int(dofs[right])
            mass[left_dof] += 0.5 * length
            mass[right_dof] += 0.5 * length
            coefficient = 1.0 / length
            rows.extend((left_dof, left_dof, right_dof, right_dof))
            columns.extend((left_dof, right_dof, left_dof, right_dof))
            data.extend((coefficient, -coefficient, -coefficient, coefficient))
    stiffness = sparse.coo_matrix(
        (data, (rows, columns)), shape=(next_dof, next_dof), dtype=float
    ).tocsr()

    event_dofs = np.empty(events.n_events, dtype=np.int64)
    for index, (edge_value, offset_value) in enumerate(
        zip(events.edge_indices, events.offsets, strict=True)
    ):
        edge = int(edge_value)
        position = int(np.argmin(np.abs(edge_offsets[edge] - float(offset_value))))
        if not np.isclose(edge_offsets[edge][position], offset_value):
            raise RuntimeError("event offset is missing from the heat mesh.")
        event_dofs[index] = edge_dofs[edge][position]

    return NetworkHeatOperator(
        mass=mass,
        stiffness=stiffness,
        edge_offsets=tuple(edge_offsets),
        edge_dofs=tuple(edge_dofs),
        event_dofs=event_dofs,
        dof_component_labels=labels,
        mesh_size=resolved_size,
        network_fingerprint=network.fingerprint,
        event_fingerprint=events.fingerprint,
        support_fingerprint=workspace.lixels.fingerprint,
    )
