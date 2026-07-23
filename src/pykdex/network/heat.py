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
from scipy.linalg import eigh
from scipy.sparse.linalg import expm_multiply

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

    def integrate_squared(self, nodal_values: np.ndarray) -> float:
        r"""Integrate the square of a piecewise-linear nodal field exactly.

        On a segment of length :math:`\ell` with endpoint values ``a`` and
        ``b``, the exact contribution is

        .. math::

            \frac{\ell}{3}(a^2 + ab + b^2).
        """
        values = np.asarray(nodal_values, dtype=float)
        if values.shape != self.mass.shape:
            raise ValueError("nodal_values must contain one value per heat DOF.")
        if not np.all(np.isfinite(values)):
            raise ValueError("nodal_values must contain only finite values.")
        result = 0.0
        for offsets, dofs in zip(self.edge_offsets, self.edge_dofs, strict=True):
            widths = np.diff(offsets)
            edge_values = values[dofs]
            left = edge_values[:-1]
            right = edge_values[1:]
            result += float(
                np.sum(widths * (left * left + left * right + right * right) / 3.0)
            )
        return result


def _validate_diffusion_times(diffusion_times: np.ndarray) -> np.ndarray:
    values = np.asarray(diffusion_times, dtype=float)
    if values.ndim == 0:
        values = values.reshape(1)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("diffusion_times must be a non-empty one-dimensional array.")
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ValueError("diffusion_times must contain finite positive values.")
    return values


def normalize_heat_solution(
    operator: NetworkHeatOperator,
    raw_values: np.ndarray,
    event_coefficients: np.ndarray,
    *,
    negative_tolerance: float = 1e-10,
) -> tuple[np.ndarray, float, float]:
    """Clip solver roundoff and restore exact occupied-component mass."""
    values = np.asarray(raw_values, dtype=float)
    coefficients = np.asarray(event_coefficients, dtype=float)
    if values.shape != operator.mass.shape:
        raise ValueError("raw_values must contain one value per heat DOF.")
    if coefficients.shape != operator.event_dofs.shape:
        raise ValueError("event_coefficients must contain one value per event.")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(coefficients)):
        raise ValueError("heat values and event coefficients must be finite.")
    tolerance = float(negative_tolerance)
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("negative_tolerance must be finite and positive.")
    raw_minimum = float(np.min(values))
    if raw_minimum < -tolerance:
        raise FloatingPointError(
            "heat evolution exceeded the configured negative roundoff tolerance."
        )
    normalized_values = np.maximum(values, 0.0)
    event_components = operator.dof_component_labels[operator.event_dofs]
    component_errors: list[float] = []
    for component in np.unique(operator.dof_component_labels):
        dof_mask = operator.dof_component_labels == component
        desired = float(np.sum(coefficients[event_components == component]))
        actual = float(np.dot(operator.mass[dof_mask], normalized_values[dof_mask]))
        component_errors.append(abs(actual - desired))
        if desired == 0.0:
            normalized_values[dof_mask] = 0.0
        elif actual <= 0.0:
            raise FloatingPointError(
                "heat evolution lost all mass in an occupied component."
            )
        else:
            normalized_values[dof_mask] *= desired / actual
    return (
        np.asarray(normalized_values, dtype=float),
        max(component_errors, default=0.0),
        raw_minimum,
    )


@dataclass(frozen=True)
class HeatComputePlan:
    """Reusable heat generator and optional dense eigendecomposition.

    A plan belongs to exactly one network, event pattern, lixel support, and
    heat mesh. Dense plans diagonalize the symmetric generator once and reuse
    that decomposition for every source vector and diffusion time. Larger
    sparse plans retain the assembled generator and use Krylov exponential
    products without materializing a dense transition matrix.
    """

    operator: NetworkHeatOperator
    generator: sparse.csr_matrix
    solver: str
    dense_threshold: int
    eigenvalues: np.ndarray | None = None
    eigenvectors: np.ndarray | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.operator, NetworkHeatOperator):
            raise TypeError("operator must be a NetworkHeatOperator instance.")
        generator = _readonly_csr(self.generator)
        expected = (self.operator.n_dofs, self.operator.n_dofs)
        if generator.shape != expected:
            raise ValueError("generator shape must match the heat operator.")
        if isinstance(self.dense_threshold, (bool, np.bool_)) or not isinstance(
            self.dense_threshold, (int, np.integer)
        ):
            raise TypeError("dense_threshold must be a positive integer.")
        threshold = int(self.dense_threshold)
        if threshold <= 0:
            raise ValueError("dense_threshold must be greater than zero.")
        solver = str(self.solver).strip()
        valid_solvers = {
            "dense_symmetric_eigendecomposition",
            "sparse_expm_multiply",
        }
        if solver not in valid_solvers:
            raise ValueError("solver is not a supported heat-plan solver.")

        eigenvalues: np.ndarray | None = None
        eigenvectors: np.ndarray | None = None
        if solver == "dense_symmetric_eigendecomposition":
            if self.eigenvalues is None or self.eigenvectors is None:
                raise ValueError(
                    "dense heat plans require eigenvalues and eigenvectors."
                )
            eigenvalues = readonly_array(
                self.eigenvalues, dtype=float, ndim=1, name="eigenvalues"
            )
            eigenvectors = readonly_array(
                self.eigenvectors, dtype=float, ndim=2, name="eigenvectors"
            )
            if eigenvalues.shape != (self.operator.n_dofs,) or eigenvectors.shape != (
                self.operator.n_dofs,
                self.operator.n_dofs,
            ):
                raise ValueError("dense spectral assets have incompatible shapes.")
            if not np.all(np.isfinite(eigenvalues)) or not np.all(
                np.isfinite(eigenvectors)
            ):
                raise ValueError("dense spectral assets must contain finite values.")
        elif self.eigenvalues is not None or self.eigenvectors is not None:
            raise ValueError("sparse heat plans must not store dense spectral assets.")

        object.__setattr__(self, "generator", generator)
        object.__setattr__(self, "solver", solver)
        object.__setattr__(self, "dense_threshold", threshold)
        object.__setattr__(self, "eigenvalues", eigenvalues)
        object.__setattr__(self, "eigenvectors", eigenvectors)

    @classmethod
    def from_workspace(
        cls,
        workspace: NetworkWorkspace,
        *,
        mesh_size: float | None = None,
        dense_threshold: int = 1_024,
    ) -> "HeatComputePlan":
        """Build a reusable plan from one prepared network workspace."""
        operator = build_network_heat_operator(workspace, mesh_size=mesh_size)
        return cls.from_operator(operator, dense_threshold=dense_threshold)

    @classmethod
    def from_operator(
        cls,
        operator: NetworkHeatOperator,
        *,
        dense_threshold: int = 1_024,
    ) -> "HeatComputePlan":
        """Build a reusable plan from an already assembled heat operator."""
        if not isinstance(operator, NetworkHeatOperator):
            raise TypeError("operator must be a NetworkHeatOperator instance.")
        if isinstance(dense_threshold, (bool, np.bool_)) or not isinstance(
            dense_threshold, (int, np.integer)
        ):
            raise TypeError("dense_threshold must be a positive integer.")
        threshold = int(dense_threshold)
        if threshold <= 0:
            raise ValueError("dense_threshold must be greater than zero.")
        generator = operator.symmetric_generator()
        if operator.n_dofs <= threshold:
            eigenvalues, eigenvectors = eigh(
                generator.toarray(),
                check_finite=False,
                driver="evr",
            )
            return cls(
                operator=operator,
                generator=generator,
                solver="dense_symmetric_eigendecomposition",
                dense_threshold=threshold,
                eigenvalues=np.maximum(eigenvalues, 0.0),
                eigenvectors=eigenvectors,
            )
        return cls(
            operator=operator,
            generator=generator,
            solver="sparse_expm_multiply",
            dense_threshold=threshold,
        )

    @property
    def fingerprint(self) -> str:
        """Deterministic identity of the operator and compute route."""
        return stable_fingerprint(
            self.operator.fingerprint,
            self.solver,
            self.dense_threshold,
            self.eigenvalues,
            self.eigenvectors,
        )

    @property
    def memory_bytes(self) -> int:
        """Bytes owned by the reusable generator and spectral arrays."""
        size = (
            self.generator.data.nbytes
            + self.generator.indices.nbytes
            + self.generator.indptr.nbytes
        )
        if self.eigenvalues is not None:
            size += self.eigenvalues.nbytes
        if self.eigenvectors is not None:
            size += self.eigenvectors.nbytes
        return int(size)

    def validate_workspace(self, workspace: NetworkWorkspace) -> None:
        """Raise when a workspace is incompatible with this plan."""
        if not isinstance(workspace, NetworkWorkspace):
            raise TypeError("workspace must be a NetworkWorkspace instance.")
        events = workspace.events
        if events is None:
            raise ValueError("workspace contains no accepted network events.")
        if workspace.network.fingerprint != self.operator.network_fingerprint:
            raise ValueError("heat compute plan belongs to a different network.")
        if events.fingerprint != self.operator.event_fingerprint:
            raise ValueError("heat compute plan belongs to different network events.")
        if workspace.lixels.fingerprint != self.operator.support_fingerprint:
            raise ValueError("heat compute plan belongs to a different lixel support.")

    def evolve(
        self,
        source_mass: np.ndarray,
        diffusion_times: np.ndarray | list[float] | tuple[float, ...] | float,
    ) -> np.ndarray:
        """Evolve one or many source columns at one or many diffusion times.

        Returns an array shaped ``(n_times, n_dofs, n_sources)``. A one-
        dimensional source vector is represented by a final axis of length one.
        Requested times retain their original order and duplicates.
        """
        sources = np.asarray(source_mass, dtype=float)
        if sources.ndim == 1:
            sources = sources[:, None]
        if sources.ndim != 2 or sources.shape[0] != self.operator.n_dofs:
            raise ValueError(
                "source_mass must have one row per heat DOF and optional source columns."
            )
        if not np.all(np.isfinite(sources)):
            raise ValueError("source_mass must contain only finite values.")
        times = _validate_diffusion_times(np.asarray(diffusion_times, dtype=float))
        inverse_root = 1.0 / np.sqrt(self.operator.mass)
        transformed_sources = inverse_root[:, None] * sources
        results: list[np.ndarray] = []
        if self.solver == "dense_symmetric_eigendecomposition":
            if self.eigenvalues is None or self.eigenvectors is None:
                raise RuntimeError("dense heat plan lost its spectral assets.")
            coefficients = self.eigenvectors.T @ transformed_sources
            for time in times:
                evolved = self.eigenvectors @ (
                    np.exp(-float(time) * self.eigenvalues)[:, None] * coefficients
                )
                results.append(inverse_root[:, None] * evolved)
        else:
            for time in times:
                evolved = expm_multiply(
                    -float(time) * self.generator, transformed_sources
                )
                results.append(inverse_root[:, None] * np.asarray(evolved, dtype=float))
        return np.asarray(results, dtype=float)

    def event_nodal_kernels(self, diffusion_time: float) -> np.ndarray:
        """Return nodal heat fields with one unit point source per event."""
        sources = np.zeros(
            (self.operator.n_dofs, self.operator.event_dofs.size), dtype=float
        )
        sources[self.operator.event_dofs, np.arange(self.operator.event_dofs.size)] = (
            1.0
        )
        return self.evolve(sources, diffusion_time)[0]

    def event_kernel_matrix(self, diffusion_time: float) -> np.ndarray:
        """Return source-event by target-event heat-kernel values."""
        nodal = self.event_nodal_kernels(diffusion_time)
        return np.asarray(nodal[self.operator.event_dofs, :].T, dtype=float)


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


def build_heat_compute_plan(
    workspace: NetworkWorkspace,
    *,
    mesh_size: float | None = None,
    dense_threshold: int = 1_024,
) -> HeatComputePlan:
    """Build a workspace-compatible reusable heat computation plan."""
    return HeatComputePlan.from_workspace(
        workspace,
        mesh_size=mesh_size,
        dense_threshold=dense_threshold,
    )
