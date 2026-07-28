# pyKDEX current handoff

The latest merged release is **0.0.15**. Active development is pyKDEX **0.0.16** on Draft
PR #16. The deterministic execution foundation is complete; the exact next subunit is the
empirical bootstrap uncertainty foundation.

## Read these records in order

1. `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`;
2. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
3. `HANDOFF_0.0.16_DESIGN_UNCERTAINTY_SEPARABILITY_SCALABLE.md`;
4. `HANDOFF_0.0.16_DESIGN_VALIDATION.md`;
5. `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md`.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- stable base: pyKDEX `0.0.15` on `main`;
- base commit: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: `#16 Design pyKDEX 0.0.16 uncertainty, separability, and scalable execution`;
- package version: still `0.0.15`;
- merge: not merged;
- PR remains Draft;
- 0.0.16 top-level provisional exports: none;
- public execution import: `from pykdex.execution import ExecutionPlan`;
- exact next unit: empirical bootstrap uncertainty foundation.

Clean execution implementation head:

```text
cef94f9b26c3faab6aaeab85dadf0740bcc34078
```

CI #281, run `30369196085`, passed the complete repository matrix at that head.
Documentation and handoff commits after that implementation head require their own latest
CI check before being called validated.

## Completed subunit 01

The following are implemented:

```text
ExecutionPlan
private ResolvedExecutionPlan
conservative target memory resolution
sequential target execution
threaded target execution
logical output ordering
legacy chunk compatibility
execution metadata and fingerprints
```

Integrated estimators:

```text
SpatialKDE
SpatiotemporalKDE
NetworkKDE: simple, discontinuous, continuous
TemporalNetworkKDE
HeatNetworkKDE: non-chunkable budget audit only
```

Execution implementation files:

```text
src/pykdex/execution/__init__.py
src/pykdex/execution/plan.py
src/pykdex/execution/chunks.py
src/pykdex/estimators/spatial_kde.py
src/pykdex/estimators/spatiotemporal_kde.py
src/pykdex/estimators/network_kde.py
src/pykdex/estimators/temporal_network_kde.py
src/pykdex/estimators/heat_network_kde.py
src/pykdex/network/evaluation.py
```

Tests:

```text
tests/test_execution_plan.py
tests/test_execution_spatial_integration.py
tests/test_execution_network_integration.py
tests/test_execution_network_time_integration.py
tests/test_execution_heat_integration.py
```

Documentation and benchmark:

```text
docs/guides/execution.md
docs/api/execution.md
benchmarks/benchmark_execution_plan.py
docs/development/handoff-0.0.16-progress-01-execution-plan.md
```

## Execution rules that must not change

- Omitting a plan preserves legacy unbounded estimator defaults.
- Explicit `ExecutionPlan()` uses the default 256 MiB budget.
- Backends are only `sequential` and `thread`.
- `backend="sequential"` requires `n_jobs=1`.
- Only independent target chunks run concurrently in ordinary estimation.
- Source-event reduction order remains stable.
- Completed chunks write to fixed logical output slices.
- Chunk size and worker count are operational, not statistical parameters.
- Execution metadata is excluded from estimator and asset compatibility.
- Legacy chunks and explicit plan target chunks are mutually exclusive.
- `HeatNetworkKDE` is a global solve and must not expose fake target threading.
- No process pool, Dask, Joblib, Ray, GPU, approximate kernel, or distributed runtime is
  part of 0.0.16.

## Validation evidence

CI #281 passed:

- Black, isort, Ruff, and mypy;
- complete public API example mapping;
- strict MkDocs;
- full pytest regression suite;
- branch coverage;
- source and wheel distributions;
- Twine and archive verification;
- isolated wheel installation and smoke test;
- Linux, Windows, and macOS;
- Python 3.11, 3.12, 3.13, and 3.14.

A temporary focused workflow ran the 39 execution tests. It identified one overly narrow
error-message assertion, not a numerical defect. The assertion was corrected and the clean
implementation then passed CI #281. Temporary diagnostic and formatting workflows were
deleted and must remain absent from the PR diff.

## Exact next subunit: bootstrap uncertainty

Implement in this order:

1. inspect immutable event containers and workspace reconstruction paths;
2. implement immutable `BootstrapPlan`;
3. allow only `method="ordinary"` initially;
4. create a private NumPy `SeedSequence` ledger;
5. generate all child seeds in logical replicate order before scheduling work;
6. make replicate identity independent of worker completion order, `n_jobs`, target chunks,
   and replicate chunks;
7. implement immutable exact-support `FieldEnsemble` with full replicate storage;
8. validate support fingerprints, identifiers, measures, CRS, units, network, direction,
   and time domain;
9. implement pointwise percentile `PointwiseInterval`;
10. implement immutable fail-fast `BootstrapResult`;
11. implement `bootstrap_kde` first;
12. implement fixed-exposure `bootstrap_event_rate`;
13. implement independently resampled case/control `bootstrap_relative_risk`;
14. default relative-risk intervals to the log-risk scale;
15. use `ExecutionPlan.replicate_chunk_size` for deterministic logical replicate batches;
16. include complete ensemble storage in the memory budget before scheduling;
17. add cross-domain, seed-invariance, ordering, memory, denominator-policy, and failure
    tests;
18. add guide, API, executable example, benchmark, and
    `HANDOFF_0.0.16_PROGRESS_02_BOOTSTRAP.md`;
19. pass complete repository CI before starting separability.

## Bootstrap restrictions

The built-in bootstrap must require:

- immutable pyKDEX event objects or prepared workspaces;
- unit event weights;
- fixed event count within each resampled group;
- fixed support;
- fixed scalar bandwidths;
- fixed kernel, metric, boundary correction, junction policy, direction, network, and time
  domain;
- no bandwidth reselection inside replicates.

Interpretation:

- `bootstrap_kde` is conditional on observed event count;
- `bootstrap_event_rate` resamples only the event-intensity numerator and treats exposure as
  fixed;
- `bootstrap_relative_risk` independently resamples cases and controls within groups;
- pointwise percentile intervals are not simultaneous confidence bands.

## Do not add in subunit 02

- smoothed, parametric, Bayesian, block, wild, or weighted bootstrap;
- arbitrary non-unit weights;
- adaptive bandwidths or bandwidth matrices;
- replicate-wise bandwidth selection;
- unconditional Poisson count uncertainty;
- uncertain-exposure resampling;
- pooled case/control sampling;
- basic, bootstrap-t, BCa, or simultaneous intervals;
- approximate or streaming quantiles;
- Zarr or disk-backed ensembles;
- separability diagnostics;
- permutation p-values;
- local significance maps;
- global envelopes;
- package version bump or release merge.

## Recovery checklist

1. Inspect branch, PR #16, current head, changed files, and latest CI.
2. Confirm PR #16 remains open, Draft, and unmerged.
3. Confirm package version remains `0.0.15`.
4. Confirm temporary workflow and diagnostic files are absent.
5. Read the five required records at the top.
6. Preserve the execution contract exactly.
7. Begin only the bootstrap subunit.
8. Do not start separability until bootstrap has its own successful full-CI handoff.
