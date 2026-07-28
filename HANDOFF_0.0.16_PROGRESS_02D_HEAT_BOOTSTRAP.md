# pyKDEX 0.0.16 progress 02D: heat-network Bootstrap

## Purpose

This is the durable recovery record for the closed ordinary-Bootstrap adapter for
`HeatNetworkKDE`. It records the statistical boundary, fixed estimator contract, finite-element
reconstruction rules, deterministic execution, conservative memory model, tests, validation, and
exact continuation boundary.

This unit implements only:

```text
NetworkWorkspace + HeatNetworkKDE -> bootstrap_kde
```

It does not implement ordinary space-time, temporal-network, event-rate, relative-risk,
separability, or permutation inference.

## Repository state

- repository: `hujinghaoabcd/pyKDEX`;
- stable merged release: `0.0.15`;
- stable base commit: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: #16;
- package version remains `0.0.15`;
- PR remains open, Draft, and unmerged;
- uncertainty API remains in `pykdex.uncertainty`;
- no provisional 0.0.16 top-level exports.

Validated clean implementation head:

```text
c8f6760d7115c8f725c0e734e04f5c749cf74fbf
```

CI #360, run ID `30382166566`, passed the complete repository matrix at that head.

The guide, API, example, handoff, navigation, and status commits after this implementation head
require their own final CI inspection before being called validated.

## Required reading

Read in this order:

1. `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md`;
2. `HANDOFF_0.0.16_PROGRESS_02A_BOOTSTRAP_FOUNDATION.md`;
3. `HANDOFF_0.0.16_PROGRESS_02B_SPATIAL_BOOTSTRAP.md`;
4. `HANDOFF_0.0.16_PROGRESS_02C_NETWORK_BOOTSTRAP.md`;
5. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
6. this file.

## Public call

The existing dedicated-namespace function now dispatches heat-network inputs:

```python
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde

result = bootstrap_kde(
    estimator=heat_estimator,
    events=network_workspace,
    plan=bootstrap_plan,
)
```

The second parameter retains the public name `events=` for compatibility with the original
spatial adapter. For heat-network Bootstrap it contains a prepared `NetworkWorkspace`.

No explicit support argument is accepted. The exact measured support is
`workspace.lixels`.

## Statistical meaning

The implemented method is the ordinary nonparametric Bootstrap of accepted snapped-event
identities, conditional on:

- the observed accepted-event count;
- the observed snapping and rejection outcome;
- the fixed network and lixel support;
- the fixed heat estimator contract.

For logical replicate `b`:

1. draw `n` accepted-event indices independently with replacement from `0, ..., n - 1`;
2. preserve accepted-event count `n`;
3. reconstruct accepted `NetworkEvents` after snapping;
4. preserve the original rejected-event table and snapping parameters;
5. create a fresh finite-element heat operator from the replicate event offsets;
6. create a fresh heat compute plan with the fixed solver route;
7. run a fresh global heat evolution;
8. evaluate lixel cell averages on the exact original support;
9. write the result into logical ensemble row `b`.

Interpretation:

- density uncertainty is conditional on the observed accepted-event count;
- intensity uncertainty is also conditional on that count;
- unconditional Poisson count uncertainty is not represented;
- snapping uncertainty is not represented;
- heat-time selection uncertainty is not represented;
- intervals are pointwise empirical percentile intervals, not simultaneous bands.

Duplicate selections remain duplicate point masses at the same snapped location. They receive new
unique replicate-local IDs while their source indices remain in provenance.

## Fixed heat contract

The built-in adapter requires:

- `HeatNetworkKDE` exactly;
- a valid undirected `NetworkWorkspace` with accepted events;
- exact unit accepted-event weights;
- finite positive numeric scalar `diffusion_time`;
- fixed optional numeric `mesh_size`;
- fixed target (`density` or `intensity`);
- fixed finite positive `negative_tolerance`;
- exact network fingerprint;
- exact lixel-support fingerprint;
- no heat-time selection in observed or replicate fits.

Rejected configurations include:

- `HeatLikelihoodCVTime` and `HeatLeastSquaresCVTime`;
- arbitrary `BaseHeatTime` strategy objects;
- non-unit weights;
- directed networks;
- an explicit support argument;
- target chunks;
- zero, negative, non-finite, or Boolean numeric configuration;
- arbitrary resampling callbacks.

The supplied estimator may be fitted or unfitted. Bootstrap reads constructor configuration only.
It does not reuse or mutate fitted arrays, operators, plans, metadata, or estimator state.

## Post-snapping workspace reconstruction

Replicate workspaces preserve:

- the exact `LinearNetwork` object;
- exact `LixelSupport` object;
- network topology and edge direction state;
- CRS and spatial unit;
- snapped edge indices and offsets selected by the replicate index sequence;
- snapped and original coordinates;
- snap distances and statuses;
- optional event marks;
- original rejected-event DataFrame;
- original snapping parameters and validation report.

Replicate workspaces do not propagate radial event-to-lixel or event-to-event distance assets.
`HeatNetworkKDE` does not consume these assets. Omitting them avoids copying irrelevant sparse
assets while preserving every heat-estimation input.

Provenance records:

```text
ordinary_bootstrap_resample
replicate_index
sampled_source_indices
source_event_fingerprint
resampling_stage = after_accepted_event_snapping
```

## Fresh finite-element solve

Every replicate rebuilds:

- event-aware heat mesh breakpoints;
- shared metric-graph finite-element degrees of freedom;
- lumped nodal mass;
- sparse stiffness matrix;
- symmetric heat generator;
- stored eigendecomposition or sparse exponential route;
- source-mass vector;
- normalized nodal field;
- lixel cell-average field.

No fitted source heat operator or compute plan is reused as replicate numerical state.

Lixel boundaries and uniform mesh refinement are fixed. A replicate samples only observed event
offsets, so it can remove unique event breakpoints but cannot introduce a new one. Therefore:

```text
replicate n_dofs <= source n_dofs
```

The implementation checks this invariant.

## Fixed solver route

The observed source operator is built first to determine the solver route.

If source `n_dofs <= 1024`:

```text
dense_threshold = 1024
solver = dense_symmetric_eigendecomposition
```

All replicate meshes are no larger and remain on the same dense route.

If source `n_dofs > 1024`:

```text
dense_threshold = 1
solver = sparse_expm_multiply
```

The threshold of one forces all nontrivial replicate meshes to stay on the sparse route. This
prevents a replicate with fewer unique offsets from silently switching to a dense eigensolver and
changing the memory/execution contract.

Result metadata records:

- fixed solver;
- fixed dense threshold;
- source maximum DOF count;
- source compute-plan fingerprint;
- one compute-plan fingerprint per replicate.

## Deterministic random and scheduling contract

The adapter uses the shared `SeedLedger`:

- one NumPy `SeedSequence` root;
- one child stream per logical replicate;
- `PCG64` generators;
- child streams assigned before scheduling;
- generated root entropy retained when `random_state=None`.

Replicate `b` receives the same sampled accepted-event indices regardless of:

- sequential or thread outer backend;
- requested worker count;
- replicate chunk size;
- worker completion order.

Each inner heat estimator uses:

```text
backend = sequential
n_jobs = 1
target_chunk_size = None
```

Heat evolution is global. The adapter rejects `target_chunk_size` instead of pretending that a
global finite-element solve can be divided into independent target rows.

## Conservative memory model

A cheap lower-bound preflight runs before heat-operator construction and includes:

- complete `(B, M)` ensemble;
- observed field and validity mask;
- supplied network, accepted events, lixels, distance assets, and rejection audit;
- minimum reconstructed replicate event/workspace storage for every requested concurrent worker.

After building the source heat operator, the final preflight includes for every requested
concurrent worker:

- sampled-index vector;
- reconstructed accepted-event arrays;
- deep-copied rejection audit used by immutable `SnapResult`;
- finite-element mass, stiffness, edge breakpoint, edge DOF, event DOF, and component arrays;
- symmetric generator;
- stored eigenvalues/eigenvectors for dense plans;
- source mass, transformed source, evolved nodal, normalization, and output arrays;
- lixel result field;
- conservative dense or sparse solver temporary storage;
- a 1.25 safety factor.

The source solver state is also counted while the observed estimate is constructed. The source
plan is explicitly released before replicate scheduling.

Too-small budgets raise `MemoryError` before any replicate is scheduled. The memory model is
retained in ensemble metadata.

## Result contract

The returned `BootstrapResult` has:

```text
operation = bootstrap_kde
estimator_family = heat_network
field_family = density or intensity
support = exact source LixelSupport
resampling_method = ordinary
```

Metadata includes:

- estimator-contract fingerprint;
- source workspace and event fingerprints;
- network and support fingerprints;
- fixed diffusion time and mesh size;
- fixed solver and dense threshold;
- source maximum heat DOFs;
- source and replicate compute-plan fingerprints;
- replicate workspace fingerprints;
- fixed rejection count;
- `conditional_on_observed_event_count=True`;
- `resampling_stage=after_accepted_event_snapping`;
- `unit_event_weights=True`;
- `distance_assets_propagated=False`;
- resolved execution and memory model.

The default interval is produced by `pointwise_percentile_interval` at the confidence level in
`BootstrapPlan`.

## Files added or changed

```text
src/pykdex/uncertainty/heat.py
src/pykdex/uncertainty/api.py
tests/test_bootstrap_heat_network_kde.py
examples/20_heat_network_bootstrap.py
docs/guides/bootstrap.md
docs/api/uncertainty.md
HANDOFF_0.0.16_PROGRESS_02D_HEAT_BOOTSTRAP.md
docs/development/handoff-0.0.16-progress-02d-heat-bootstrap.md
HANDOFF_NEXT_CONVERSATION.md
mkdocs.yml
```

The public symbol set is unchanged; `bootstrap_kde` gained another closed overload.

## Test coverage

Tests cover:

- complete immutable heat-network Bootstrap result;
- exact lixel support and density integral;
- one-event degenerate ensemble and zero empirical uncertainty;
- first replicate agreement with a manually reconstructed post-snap sample;
- unique replicate IDs and source-index provenance;
- preserved network/lixel object identity;
- non-propagation of irrelevant radial distance assets;
- sequential/thread and replicate-chunk invariance;
- source estimator fitted-state immutability;
- source workspace fingerprint immutability;
- non-unit-weight rejection;
- heat-time selector rejection;
- target-chunk rejection;
- explicit support rejection;
- public `events=` keyword compatibility;
- memory failure before operator/replicate work;
- complete repository regression and branch coverage.

## Validation evidence

### First numerical run

Implementation head:

```text
5256926b3d508c68b8326484722fe27df9a3e185
```

CI #357 (`30381853307`) showed:

- full tests and branch coverage succeeded;
- distributions succeeded;
- completed platform jobs succeeded;
- the only failure was Black formatting.

### Clean implementation run

Clean head after exact Black/isort formatting and removal of the temporary workflow:

```text
c8f6760d7115c8f725c0e734e04f5c749cf74fbf
```

CI #360 (`30382166566`) passed:

- Black;
- isort;
- Ruff;
- mypy;
- top-level API example mapping;
- strict MkDocs;
- complete tests and branch coverage;
- source and wheel builds;
- Twine and archive verification;
- isolated installed-wheel smoke;
- Linux, Windows, and macOS;
- Python 3.11, 3.12, 3.13, and 3.14.

## Exact next implementation unit: 02E ordinary space-time Bootstrap

Implement only:

```text
SpatiotemporalEvents + SpatiotemporalKDE + exact product support
```

The next adapter must:

1. resample complete event identities with replacement, preserving each sampled event's spatial
   coordinates and time as one paired record;
2. preserve observed event count and use new unique replicate-local IDs;
3. retain sampled source indices and source fingerprint in provenance;
4. require unit weights;
5. require fixed numeric scalar spatial and temporal bandwidths;
6. preserve fixed spatial/temporal kernels, metrics, boundary correction, time domain, cyclic
   period/origin, target, and exact measured product support;
7. reject bandwidth selectors, adaptive arrays, matrices, balloon bandwidths, weighted built-in
   resampling, and arbitrary support;
8. keep outer replicate scheduling separate from inner sequential target-chunk execution;
9. preserve logical seed/result identity across workers, target chunks, and replicate chunks;
10. account for complete ensemble, event arrays, product support, spatial/temporal kernel blocks,
    reconstructed events, and concurrent outputs before scheduling;
11. test linear and cyclic time domains, paired space-time identity, manual reconstruction,
    scheduling, support identity, memory failure, and source immutability;
12. generate `HANDOFF_0.0.16_PROGRESS_02E_SPATIOTEMPORAL_BOOTSTRAP.md` and pass full CI.

Time permutation is not Bootstrap. It belongs only to the later explicitly Poisson first-order
separability test and must not be introduced in 02E.

## Excluded until later

- temporal-network Bootstrap;
- fixed-exposure event-rate Bootstrap;
- case-control relative-risk Bootstrap;
- separability diagnostics and permutation p-values;
- weighted, adaptive, smoothed, parametric, block, Bayesian, or wild Bootstrap;
- bandwidth/time reselection in replicates;
- BCa, bootstrap-t, basic, or simultaneous intervals;
- uncertain exposure;
- streaming or disk-backed ensembles;
- persistence changes;
- package version bump;
- ready-for-review transition or merge.
