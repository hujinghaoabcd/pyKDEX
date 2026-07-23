# pyKDEX 0.0.9 handoff: heat-equation KDE on measured metric graphs

## 1. Purpose and recovery scope

This document is the recoverable engineering record for pyKDEX 0.0.9. It is
written so that a new conversation can understand the numerical model, public
contracts, implementation state, validation evidence, exclusions, and next
development order without access to earlier chat messages.

- Repository: `hujinghaoabcd/pyKDEX`
- Development branch: `agent/heat-network-kde`
- Version developed in this unit: `0.0.9`
- Stable version before this unit: `0.0.8`
- Development date: `2026-07-23`
- Pull request: `#9 Add heat-equation network KDE`
- Feature commit: `16bc4ba79d861b2651c227033be1b24bce7f5b9e`
- First complete PR CI: run `#113` (`29979483652`), conclusion `success`
- Merge commit: pending final squash merge

The source of truth is the repository. Final CI and merge fields at the end of
this document must be updated after the clean GitHub workflow.

## 2. Permanent project principles

pyKDEX remains a composition-oriented framework for spatial, network,
spatiotemporal, and network-time density estimation:

`data + domain + prepared assets + measure + metric/operator + smoothing parameter + correction + support + estimator + result`.

The following rules remain mandatory:

1. Numerical estimators are independently implemented inside pyKDEX. Research
   packages may guide validation but are not runtime dependencies or source
   donors.
2. OSMnx, NetworkX, GeoPandas, pandas, and NumPy are input ecosystems. Numerical
   estimators operate on pyKDEX-owned validated objects.
3. Along-edge offsets, actual edge/lixel measures, CRS, units, identifiers, and
   fingerprints are first-class data.
4. Exposed arrays are copied and read-only. Failed `fit()` calls atomically reset
   the estimator to an unfitted state.
5. One NumPy/SciPy route is public. Solver selection is an internal numerical
   decision, not a user-facing backend string.
6. Every public symbol must appear in an executable example.
7. Public mathematical meaning takes priority over implementation convenience.
8. Every development unit produces a versioned root handoff, a development-doc
   record, and an updated `HANDOFF_NEXT_CONVERSATION.md`.

## 3. Problem solved in 0.0.9

The existing `NetworkKDE` supports shortest-path radial evaluation and explicit
discontinuous/continuous walk propagation. An infinite-support Gaussian kernel
cannot be inserted into the path enumerator safely on cyclic networks: infinitely
many walks can contribute. Treating heat smoothing as a radial kernel name would
also hide its vertex conditions, terminal behavior, solver, and conserved
measure.

Version 0.0.9 therefore implements `HeatNetworkKDE` as a separate metric-graph
heat-equation estimator. It supplies:

- a measured graph discretization;
- exact event-offset insertion;
- shared vertex values;
- Kirchhoff junction balance;
- natural zero-flux terminal conditions;
- stable heat evolution;
- lixel cell-average output with exact piecewise-linear integration;
- per-connected-component mass diagnostics;
- a reusable and fingerprinted `NetworkHeatOperator`.

## 4. Public API added

### `HeatNetworkKDE`

```python
HeatNetworkKDE(
    diffusion_time=0.08,
    mesh_size=0.025,
    target="density",
)
```

Important parameters:

- `diffusion_time`: finite positive heat time \(t\);
- `mesh_size`: optional maximum element length; defaults to the workspace lixel
  target length;
- `target`: `density` or `intensity`;
- `negative_tolerance`: permitted negative numerical roundoff before explicit
  failure.

Fitted attributes include:

- `workspace_`;
- `network_events_`;
- `lixels_`;
- `heat_operator_`;
- `nodal_values_`;
- `values_`;
- `component_mass_error_`;
- `raw_minimum_`;
- `vertex_continuity_error_`;
- ordinary `BaseKDE` metadata and fingerprints.

### `NetworkHeatOperator`

This immutable public asset stores:

- positive lumped nodal measure vector `mass`;
- sparse symmetric `stiffness`;
- `edge_offsets` and `edge_dofs`;
- exact `event_dofs`;
- `dof_component_labels`;
- resolved `mesh_size`;
- network, event, and support fingerprints.

It exposes:

- `n_dofs`;
- `n_segments`;
- deterministic `fingerprint`;
- `symmetric_generator()`;
- `lixel_averages()`.

Sparse matrix storage arrays and NumPy arrays are copied and marked read-only.

### `build_network_heat_operator`

```python
operator = build_network_heat_operator(
    workspace,
    mesh_size=0.025,
)
```

The function validates the complete workspace and builds one reusable measured
operator. It rejects directed networks and self-loop edge records explicitly.
Ordinary rings composed of multiple edges are supported.

## 5. Numerical definition

### 5.1 Metric-graph finite elements

For every network edge of length \(L_e\), the mesh includes:

- offset \(0\);
- offset \(L_e\);
- every lixel start and end offset;
- every accepted event offset on that edge;
- uniform refinement points required by `mesh_size`.

Near-duplicate offsets created by independent floating-point constructions are
coalesced using a scale-dependent tolerance. This prevents nearly zero-length
elements and the resulting ill-conditioned generator.

Original network vertices occupy shared global degrees of freedom. Interior
points are edge-specific. Parallel edges therefore retain independent interiors
while sharing their topological endpoints.

For a segment of length \(\ell\), the local stiffness is

\[
K_e=\frac{1}{\ell}
\begin{bmatrix}
1 & -1\\
-1 & 1
\end{bmatrix},
\]

and the lumped local nodal measure is

\[
M_e=\frac{\ell}{2}
\begin{bmatrix}
1\\
1
\end{bmatrix}.
\]

Assembly produces a positive diagonal mass matrix \(M\) and sparse symmetric
positive-semidefinite stiffness matrix \(K\).

### 5.2 Heat equation and vertex conditions

The semi-discrete equation is

\[
M\frac{du}{dt}+Ku=0.
\]

Because all incident edges share the same vertex degree of freedom, function
continuity is exact by construction. The weak form supplies the Kirchhoff
condition

\[
\sum_{e\sim v}\partial_{\nu_e}u(v,t)=0
\]

at internal vertices. Degree-one terminals receive the natural homogeneous
Neumann condition. No synthetic reflection events or path coefficients are
used.

### 5.3 Symmetric evolution

The implementation transforms the system with

\[
A=M^{-1/2}KM^{-1/2},\qquad y=M^{1/2}u,
\]

so

\[
y(t)=\exp(-tA)y(0).
\]

Systems with at most 1,024 degrees of freedom use a dense symmetric
eigendecomposition. Larger systems use SciPy sparse exponential multiplication.
This solver choice is internal and recorded in result metadata.

Dense eigendecomposition was selected for small/medium systems because direct
`expm_multiply` can require excessive scaling steps when fine elements make the
largest eigenvalue very large. The sparse route remains available for systems
where dense factorization would be inappropriate.

### 5.4 Source mass and targets

An accepted event injects mass at its exact mesh node. Coincident events
accumulate at the same degree of freedom.

For density:

\[
b_i=\frac{w_i}{\sum_r w_r}.
\]

For intensity:

\[
b_i=w_i.
\]

The initial nodal density is \(u(0)=M^{-1}b\), represented in symmetric
coordinates as \(y(0)=b/\sqrt{M}\).

### 5.5 Positivity and connected-component mass

After evolution:

1. non-finite values cause explicit failure;
2. a negative value below `negative_tolerance` causes explicit failure;
3. smaller negative roundoff is clipped to zero;
4. each connected component is checked independently;
5. only roundoff-scale component drift is normalized back to the exact injected
   component mass;
6. empty components are set exactly to zero.

The pre-normalization error and raw minimum are retained in diagnostics. This
prevents silent leakage between disconnected components.

### 5.6 Lixel output

The finite-element solution is piecewise linear. `HeatNetworkKDE` integrates
that function by the exact segment trapezoid rule over each lixel and divides by
the actual lixel length. The returned `NetworkField.values` are therefore lixel
cell averages.

This differs from the midpoint samples produced by ordinary `NetworkKDE`.
`NetworkField` documentation was widened to allow point estimates or cell
averages, and heat metadata records:

```text
lixel_evaluation = "cell_average"
```

Consequently `NetworkField.integral()` exactly reproduces the discrete
finite-element mass rather than relying on a midpoint approximation.

### 5.7 Smoothing parameter interpretation

For one-dimensional free diffusion, Gaussian variance is \(2t\). The
`NetworkField.bandwidth` compatibility field therefore records

\[
h_{\mathrm{equiv}}=\sqrt{2t}.
\]

The authoritative input remains `diffusion_time`. Heat time is not silently
treated as an ordinary `NetworkKDE` bandwidth.

## 6. Rejected or deferred designs

### Heat as `kernel="gaussian"`

Rejected because radial shortest-path evaluation does not encode Kirchhoff
junction conditions, while explicit path enumeration is infinite on cycles.

### Event snapping to nearest heat-grid point

Rejected because it loses the exact along-edge event position and makes results
depend on arbitrary mesh phase. Event offsets are mandatory breakpoints.

### Only reporting lixel-centre values

Rejected for this estimator because fine heat elements can occur inside a lixel,
so midpoint integration would no longer reproduce the conserved finite-element
mass. Cell averages retain the measured-field contract.

### A user-facing `engine="..."` option

Rejected. Dense eigendecomposition and sparse exponential multiplication are
implementation routes selected from the operator size. Public statistical
meaning is invariant.

### Directed heat flow

Deferred. A directed diffusion generator needs explicit choices about
non-reversibility, stationary measure, conservation, and vertex conditions. The
undirected metric-graph estimator must not fabricate those semantics.

## 7. Validation fixtures and contracts

`tests/test_heat_network_kde.py` covers:

1. **Finite interval**: cell averages agree with the analytical Neumann series

   \[
   p_t(x,y)=1+2\sum_{n\ge1}
   \cos(n\pi x)\cos(n\pi y)e^{-n^2\pi^2t}.
   \]

2. **Square ring**: values agree with the periodic Fourier heat-kernel series on
   a circle of length four.
3. **Disconnected network**: no mass leaks into an empty component.
4. **Weighted density**: component integrals equal normalized component weights.
5. **Weighted intensity**: total integral equals the original weight sum and
   values scale exactly from density.
6. **T-junction**: all incident edge endpoint mappings reference the same shared
   degree of freedom.
7. **Exact offset insertion**: an event at a non-grid decimal offset appears at
   an exact heat node.
8. **Sparse/read-only operator**: stiffness storage and measure arrays satisfy
   ownership contracts.
9. **Deterministic fingerprint**: repeated operator construction is identical.
10. **State safety**: directed-network rejection resets fitted state.
11. **Constructor and workspace validation**: invalid time, mesh, tolerance,
    and input types fail explicitly.
12. **Result metadata/copying**: kernel, junction condition, equivalent
    bandwidth, cell-average semantics, and immutable fitted arrays are verified.

The full regression suite also confirms that 0.0.1-0.0.8 behavior is unchanged.

## 8. Important files

New source:

- `src/pykdex/network/heat.py`
- `src/pykdex/estimators/heat_network_kde.py`

Modified public interfaces:

- `src/pykdex/network/__init__.py`
- `src/pykdex/estimators/__init__.py`
- `src/pykdex/__init__.py`
- `src/pykdex/core/network_results.py`

Tests and examples:

- `tests/test_heat_network_kde.py`
- `examples/11_heat_network_kde.py`
- `examples/API_COVERAGE.csv`

Documentation:

- `docs/estimators/heat-network-kde.md`
- `docs/api/heat-network-kde.md`
- `docs/estimators/network-kde.md`
- `docs/development/roadmap.md`
- `README.md`
- `CHANGELOG.md`
- this handoff and its development-doc counterpart.

## 9. Local validation observed

Current observed development validation:

- heat-specific tests: `12 passed`;
- full suite: `161 passed`;
- branch coverage: `81.76%`, above the required `80%`;
- public API/example map: `80 public symbols`;
- heat example executes and reports density integral `1.0`;
- Ruff: passed;
- mypy: passed for `60 source files`.

Also observed locally:

- Black, isort, Ruff, and mypy passed;
- strict MkDocs passed;
- all 11 numbered examples passed;
- wheel and sdist built successfully;
- Twine and distribution-content checks passed;
- an isolated installed-wheel smoke test passed.

GitHub Actions run `#113` (`29979483652`) passed quality, coverage,
distributions, and Linux/Windows/macOS tests on Python 3.11-3.14. A final clean
run after recording these identifiers remains required before merge.

## 10. Known limitations

0.0.9 intentionally does not implement:

- directed or non-reversible graph diffusion;
- self-loop edge records;
- Robin, absorbing, or user-specified terminal boundary conditions;
- edge-varying diffusivity or drift;
- event-specific diffusion times;
- heat-time cross-validation;
- batched evaluation of several diffusion times;
- persistence of heat operators or decompositions in `NetworkWorkspace`;
- reuse of a prepared eigendecomposition across estimator instances;
- finite-element adaptivity or error estimators;
- network-time or spatiotemporal KDE;
- compiled or GPU acceleration.

Dense eigendecomposition is used only up to 1,024 degrees of freedom. The sparse
route is scientifically equivalent but should receive dedicated large-network
performance benchmarks in the next unit.

## 11. Next recommended unit: 0.0.10

Implement **batched heat-time evaluation, heat bandwidth selection, and reusable
solver plans** before moving into time as a data domain:

1. separate topology/mesh construction from source-event injection where safe;
2. introduce a workspace-compatible heat operator/decomposition cache with
   complete fingerprints;
3. evaluate several diffusion times in one spectral or Krylov plan;
4. define heat leave-one-out likelihood without self-contribution;
5. define lixel-integrated heat LSCV using exact lixel measures;
6. add deterministic diffusion-time experiments rather than requiring user
   loops;
7. benchmark sparse evolution on grid networks and document memory limits;
8. validate selected times on interval/ring reference problems;
9. preserve the separate `HeatNetworkKDE` estimator identity;
10. create `HANDOFF_0.0.10_HEAT_SELECTION_BATCH.md`.

After this unit, proceed to explicit temporal data objects, linear/cyclic time,
and separable STKDE.

## 12. Recovery procedure

1. Inspect the default branch and latest commit of `hujinghaoabcd/pyKDEX`.
2. Read this file, `HANDOFF_NEXT_CONVERSATION.md`,
   `BASELINE_VALIDATION.md`, and `CHANGELOG.md`.
3. Confirm `src/pykdex/__init__.py` reports `0.0.9`.
4. Inspect the 0.0.9 PR and final Actions run; do not rely only on chat text.
5. Run:

   ```bash
   python -m pytest --cov=pykdex --cov-branch
   python -m black --check src tests examples benchmarks tools
   python -m isort --check-only src tests examples benchmarks tools
   python -m ruff check src tests examples benchmarks tools
   python -m mypy src/pykdex
   python -m mkdocs build --strict
   python -m build
   python -m twine check dist/*
   ```

6. Run `examples/validate_coverage.py`, all numbered examples, the
   distribution-content checker, and the installed-wheel smoke checker.
7. Confirm no temporary login, export, transfer, patch, formatting, or
   diagnostic workflows were committed.
8. Begin 0.0.10 on a dedicated branch and create its handoff before merge.

## 13. Finalization fields

- Final version: `0.0.9`
- Final local test count: `161 passed`
- Final branch coverage: `81.76%`
- Public API/example count: `80 symbols; 11 examples`
- Final pull request: `#9 Add heat-equation network KDE`
- First complete CI run: `#113` (`29979483652`), `success`
- Final clean CI run after this metadata update: pending
- Squash merge commit: pending
- Temporary workflow removal: no temporary repository workflow added
