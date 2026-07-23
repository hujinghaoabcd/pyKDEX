# pyKDEX 0.0.10 handoff: reusable heat plans, batch times, and selection

## 1. Purpose and recovery scope

This is the recoverable engineering record for pyKDEX 0.0.10. A new
conversation should be able to reconstruct the public design, numerical
definitions, implementation locations, validation evidence, deliberate
limitations, and next development order from this file and the repository
alone.

- Repository: `hujinghaoabcd/pyKDEX`
- Development branch: `agent/heat-selection-batch`
- Version developed: `0.0.10`
- Stable version before this unit: `0.0.9`
- Development date: `2026-07-23`
- Pull request: `#10 Add reusable heat plans and time selection`
- Feature commit: `9342a414f99947137a6cf45051687f15c065c8f2`
- First complete PR CI: run `#118` (`29996503549`), conclusion `success`
- Final clean CI: run `#119` (`29996740029`), conclusion `success`
- Squash merge commit: `49bb6ba36f9ac1dc82a655ee23a06397dba0a529`

The source tree and tests are authoritative. The GitHub fields above record the
observed final CI and squash merge.

## 2. Permanent project principles

pyKDEX remains a composition-oriented research framework:

`data + domain + prepared assets + measure + metric/operator + smoothing parameter + correction + support + compute plan + estimator + result`.

The following rules remain mandatory:

1. Numerical algorithms are implemented independently in pyKDEX. External
   research packages may inform comparisons but are not copied or used as
   runtime computational dependencies.
2. OSMnx, NetworkX, GeoPandas, pandas, and NumPy are data ecosystems. Core
   numerical algorithms consume validated pyKDEX objects.
3. CRS, units, along-edge offsets, actual support measures, identifiers,
   provenance, and fingerprints are first-class data.
4. Public arrays and reusable assets are owned and read-only.
5. Failed fits reset estimator state atomically.
6. Solver selection is an internal numerical decision, not an arbitrary public
   backend string.
7. Every public symbol is mapped to an executable example.
8. Mathematical meaning takes priority over a superficially convenient API.
9. Heat smoothing remains a separate estimator family; it is not represented as
   a radial kernel name inside traversal-based `NetworkKDE`.
10. Every completed development unit creates a detailed versioned root handoff,
    a documentation handoff page, and an updated current-handoff entry.

## 3. Problem solved in 0.0.10

Version 0.0.9 assembled a correct measured finite-element heat operator and
evolved one event mixture at one diffusion time. Repeated calls nevertheless
rebuilt the same operator and repeated the same dense eigendecomposition.
Bandwidth exploration required user-written loops, and there was no
heat-specific leave-one-out selection contract.

Version 0.0.10 separates three responsibilities:

1. `NetworkHeatOperator` owns the measured finite-element topology and mesh.
2. `HeatComputePlan` owns the symmetric generator and reusable numerical
   decomposition.
3. `HeatNetworkKDE` and `HeatNetworkExperiment` inject sources and produce
   measured results.

This separation enables deterministic evaluation of several diffusion times
from one plan and heat-specific likelihood/least-squares selection without
reassembling topology or rediagonalizing the generator.

## 4. Public API added

### 4.1 `HeatComputePlan`

```python
plan = HeatComputePlan.from_workspace(
    workspace,
    mesh_size=25.0,
    dense_threshold=1024,
)
```

or:

```python
plan = build_heat_compute_plan(
    workspace,
    mesh_size=25.0,
)
```

A plan stores:

- the immutable `NetworkHeatOperator`;
- read-only sparse symmetric generator \(M^{-1/2}KM^{-1/2}\);
- solver identity;
- dense threshold;
- read-only eigenvalues and eigenvectors for the dense route;
- operator, network, event, and support fingerprints through the operator.

It exposes:

- `fingerprint`;
- `memory_bytes`;
- `validate_workspace()`;
- `evolve()`;
- `event_nodal_kernels()`;
- `event_kernel_matrix()`.

`evolve()` accepts one source vector or several source columns and one or
several positive diffusion times. It returns an array shaped
`(n_times, n_dofs, n_sources)`. Input order and duplicate times are retained.

For at most `dense_threshold` degrees of freedom, the plan computes one
symmetric eigendecomposition:

\[
A=Q\Lambda Q^\mathsf{T}.
\]

Every later time/source evaluation reuses \(Q\) and \(\Lambda\). Larger plans
retain the sparse generator and call deterministic Krylov exponential
multiplication. Sparse plans never store a dense transition matrix.

### 4.2 `HeatNetworkExperiment`

```python
experiment = HeatNetworkExperiment(
    diffusion_times=[500.0, 2000.0, 8000.0],
    mesh_size=100.0,
    target="density",
)
batch = experiment.run(workspace, compute_plan=plan)
```

The experiment:

- validates positive ordered diffusion times;
- accepts an optional compatible prebuilt plan;
- injects the weighted source only once;
- performs one batched plan evolution call;
- normalizes numerical roundoff independently for each result;
- returns exact lixel cell averages;
- preserves requested order and duplicate times;
- records solver, mesh, memory, mass, and fingerprint diagnostics.

### 4.3 `HeatNetworkBatchResult`

The immutable batch result stores:

- read-only `diffusion_times`;
- one `NetworkField` per requested time;
- the compute-plan fingerprint;
- immutable batch metadata.

It provides:

- `n_times`;
- `at_index()`;
- `to_frame()` for long-form output with `batch_index` and
  `diffusion_time`.

All fields in a batch must share network, accepted events, lixel support, and
target.

### 4.4 Heat diffusion-time selectors

The public selectors are:

- `HeatLikelihoodCV`;
- `HeatLeastSquaresCV`;
- `HeatSelectionCache`.

Both accept a compatible `HeatComputePlan`. The returned generic
`BandwidthSelectionResult.bandwidth` contains the selected **diffusion time**,
not the equivalent Gaussian distance. Method names are
`heat_likelihood_cv` and `heat_least_squares_cv`.

### 4.5 Heat-time strategies

The estimator-compatible strategies are:

- `BaseHeatTime`;
- `FixedHeatTime`;
- `HeatLikelihoodCVTime`;
- `HeatLeastSquaresCVTime`.

`HeatNetworkKDE(diffusion_time=...)` now accepts either a positive numeric time
or one of these strategies. Fitted state includes:

- `heat_compute_plan_`;
- `diffusion_time_`;
- `diffusion_time_selection_`.

`fit()` and `fit_predict()` accept the keyword-only `compute_plan`.

## 5. Numerical definitions

### 5.1 Authoritative smoothing parameter

The heat equation is parameterized by diffusion time \(t>0\):

\[
M\frac{du}{dt}+Ku=0.
\]

The effective Gaussian distance scale

\[
h_{\mathrm{eq}}=\sqrt{2t}
\]

is metadata for interpretation. Optimizers search \(t\), not
\(h_{\mathrm{eq}}\), and explicit bounds are time bounds.

Automatic time bounds are derived from finite positive event-to-event network
distances. Robust lower and upper distance scales are computed first and then
mapped through \(t=h^2/2\).

### 5.2 Source and target heat kernels

For each source event \(r\), the plan injects one unit of mass at its exact
finite-element degree of freedom and evolves it to time \(t\). The resulting
nodal column is the discrete transition density from source \(r\). Evaluating
those columns at event degrees of freedom produces the source-by-target matrix

\[
H_t[r,i].
\]

The matrix is symmetric for the undirected measured graph. Distinct events at
the same finite-element node remain distinct source columns.

### 5.3 Weighted heat leave-one-out likelihood

For positive event weights \(w_r\), total weight \(W\), and target event \(i\),

\[
\hat f_{-i,t}(x_i)
=
\frac{\sum_{r\ne i}w_r H_t[r,i]}{W-w_i}.
\]

Only the diagonal corresponding to event \(i\) is removed. Other events at the
same location remain valid zero-distance observations. The optimized score is

\[
-\sum_i\frac{w_i}{W}
\log\left(\max(\hat f_{-i,t}(x_i),\varepsilon)\right).
\]

`density_floor` controls \(\varepsilon\).

### 5.4 Exact finite-element least-squares CV

Heat LSCV uses

\[
\operatorname{LSCV}(t)
=
\int_G \hat f_t(x)^2\,d\ell(x)
-2\sum_i\frac{w_i}{W}\hat f_{-i,t}(x_i).
\]

The first term is not approximated by lixel-centre sampling. For a
piecewise-linear field with endpoint values \(a,b\) on a segment of length
\(\ell\),

\[
\int_0^\ell u(x)^2\,dx
=
\frac{\ell}{3}(a^2+ab+b^2).
\]

`NetworkHeatOperator.integrate_squared()` sums this exact expression over all
finite elements. Since every lixel boundary is a heat-mesh breakpoint, the
integration is consistent with the measured lixel partition while retaining
the full linear field.

### 5.5 Roundoff and component mass

Dense spectral and sparse Krylov outputs may contain very small negative
roundoff. `normalize_heat_solution()`:

1. rejects values below the configured negative tolerance;
2. clips smaller negative roundoff to zero;
3. checks desired and actual mass per connected component;
4. zeros unoccupied components;
5. rescales occupied components to their exact requested mass.

This helper is shared by single-time and batch estimators.

## 6. Cache and compatibility contracts

A compute plan is data-specific. `validate_workspace()` compares:

- network fingerprint;
- accepted network-event fingerprint;
- lixel-support fingerprint.

The operator fingerprint also includes mesh, mass, stiffness, degree-of-freedom
maps, exact event nodes, and component labels. Passing a plan to a workspace
with different topology, events, support, or lixel construction fails
explicitly.

If an estimator or experiment declares `mesh_size`, it must agree with the
supplied plan's resolved mesh size. No silent remeshing occurs.

`HeatSelectionCache` retains the exact plan object, resolved bounds, and
workspace fingerprint. Repeated objective calls reuse source kernels from the
same decomposition rather than rebuilding network assets.

## 7. Main implementation files

Core numerical assets:

- `src/pykdex/network/heat.py`
  - `NetworkHeatOperator.integrate_squared`;
  - `normalize_heat_solution`;
  - `HeatComputePlan`;
  - `build_heat_compute_plan`.

Estimators and results:

- `src/pykdex/estimators/heat_network_kde.py`;
- `src/pykdex/estimators/heat_experiment.py`;
- `src/pykdex/core/heat_results.py`.

Selection and strategies:

- `src/pykdex/selection/heat.py`;
- `src/pykdex/bandwidths/heat.py`.

Public exports:

- `src/pykdex/__init__.py`;
- `src/pykdex/network/__init__.py`;
- `src/pykdex/estimators/__init__.py`;
- `src/pykdex/core/__init__.py`;
- `src/pykdex/selection/__init__.py`;
- `src/pykdex/bandwidths/__init__.py`.

Tests, examples, benchmark, and docs:

- `tests/test_heat_selection_batch.py`;
- `examples/12_heat_selection_batch.py`;
- `benchmarks/benchmark_heat_selection_batch.py`;
- `docs/estimators/heat-network-kde.md`;
- `docs/api/heat-network-kde.md`;
- `docs/development/handoff-0.0.10-heat-selection-batch.md`.

## 8. Validation evidence

The 0.0.10 tests cover:

- deterministic plan fingerprints;
- read-only spectral assets;
- workspace/support fingerprint mismatch;
- ordered batched times and duplicates;
- dense batch versus independent single-time evolution;
- sparse Krylov versus dense spectral evolution;
- symmetric event heat-kernel matrices;
- exact piecewise-linear squared-field integration;
- batch results versus independent `HeatNetworkKDE` fits;
- density mass conservation for every batch field;
- long-form batch output;
- deterministic heat likelihood CV;
- exact finite-element heat LSCV;
- plan reuse inside both selectors;
- both selector strategy wrappers inside `HeatNetworkKDE`;
- automatic time bounds;
- invalid times, thresholds, bounds, and workspace compatibility.

Observed local development results before final publication:

- pytest: `178 passed`;
- branch coverage: `81.67%` with required minimum `80%`;
- public API map: `91 public symbols`;
- executable examples: `12`;
- new heat benchmark: batch fields exactly equal independent fits in the
  deterministic grid run;
- benchmark sample: 81 heat DOFs, 116 segments, 57,220 plan bytes, and about
  3.14x batch speedup excluding initial plan construction on this machine.

Benchmark timings are diagnostic rather than contractual. Numerical equality,
fingerprints, shapes, and memory accounting are contractual.

## 9. Deliberate exclusions and limitations

The following remain intentionally unsupported:

- directed heat generators and non-reversible stationary measures;
- self-loop edge records in the heat finite-element builder;
- variable diffusivity, drift, absorption, and alternative vertex conditions;
- alternative terminal conditions beyond natural Neumann;
- partial eigensystems or rational approximations for very large repeated-time
  workloads;
- persistent serialization of heat plans;
- incremental source updates after the accepted-event fingerprint changes;
- bootstrap uncertainty and relative-risk heat fields;
- spatiotemporal and temporal-network heat processes.

The sparse plan shares an assembled generator but currently executes arbitrary
requested times as deterministic individual Krylov exponential products.
Equally spaced multi-time Krylov acceleration may be added later if profiling
shows it materially improves large sparse workloads.

## 10. Recovery commands

From a clean clone:

```bash
git fetch origin
git switch main
git pull --ff-only
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev,docs]"
.venv/bin/pytest --cov=pykdex --cov-branch --cov-report=term-missing
.venv/bin/python examples/run_all.py
.venv/bin/python examples/validate_coverage.py
.venv/bin/black --check src tests examples benchmarks
.venv/bin/isort --check-only src tests examples benchmarks
.venv/bin/ruff check src tests examples benchmarks
.venv/bin/mypy src/pykdex
.venv/bin/mkdocs build --strict
```

Then inspect:

1. `HANDOFF_NEXT_CONVERSATION.md`;
2. this file;
3. `src/pykdex/network/heat.py`;
4. `src/pykdex/estimators/heat_experiment.py`;
5. `src/pykdex/selection/heat.py`;
6. `tests/test_heat_selection_batch.py`.

## 11. Next development unit: 0.0.11 temporal data and separable STKDE

Do not proceed directly to temporal-network KDE. First establish a validated
ordinary space-time foundation.

Recommended order:

1. Add immutable temporal coordinates with explicit units and time-zone/source
   provenance.
2. Distinguish linear time from cyclic time; cyclic distance requires an
   explicit period.
3. Add `SpatiotemporalEvents` or an equivalent structured composition that
   preserves spatial CRS and temporal unit independently.
4. Add measured point/grid space-time supports and a result object suitable for
   `xarray` export without requiring xarray in the minimal core.
5. Implement separable product STKDE:

   \[
   \hat f(x,t)
   =
   \sum_i p_i
   K_s\!\left(\frac{d_s(x,x_i)}{h_s}\right)
   K_t\!\left(\frac{d_t(t,t_i)}{h_t}\right)
   /(h_s^d h_t).
   \]

6. Keep spatial and temporal kernels, metrics, and bandwidths explicit; do not
   concatenate coordinates and hide units in one Euclidean norm.
7. Add joint and separate bandwidth-selection experiments with shared spatial
   and temporal distance assets.
8. Validate mass on measured space-time cells, moving-hotspot references,
   cyclic boundary behavior, weighted events, and chunk invariance.
9. Add a versioned `HANDOFF_0.0.11_SPATIOTEMPORAL_FOUNDATION.md`.

Temporal-network arixels, network-time workspaces, PostGIS/Zarr persistence, and
TNKDE remain later units.

## 12. Final publication status

Update this section only with observed GitHub results:

- feature commit: `9342a414f99947137a6cf45051687f15c065c8f2`;
- pull request: `#10 Add reusable heat plans and time selection`;
- first complete CI: run `#118` (`29996503549`), conclusion `success`;
- final clean CI: run `#119` (`29996740029`), conclusion `success`;
- squash merge commit: `49bb6ba36f9ac1dc82a655ee23a06397dba0a529`;
- post-merge handoff commit:
  `7459ce3666955caded92b2b7eecb82afb321f439`;
- merged and closed: yes.
