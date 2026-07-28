# pyKDEX current handoff

The latest merged release is **0.0.15**. Active development is pyKDEX **0.0.16** on Draft
PR #16. Deterministic execution and the empirical Bootstrap foundation are complete. The
exact next unit is `BootstrapResult` plus spatial `bootstrap_kde`.

## Read these records in order

1. `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`;
2. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
3. `HANDOFF_0.0.16_DESIGN_UNCERTAINTY_SEPARABILITY_SCALABLE.md`;
4. `HANDOFF_0.0.16_DESIGN_VALIDATION.md`;
5. `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md`;
6. `HANDOFF_0.0.16_PROGRESS_02A_BOOTSTRAP_FOUNDATION.md`.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- stable base: pyKDEX `0.0.15` on `main`;
- base commit: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: `#16 Develop pyKDEX 0.0.16 uncertainty, separability, and scalable execution`;
- package version remains `0.0.15`;
- PR remains open, Draft, unmerged;
- no 0.0.16 top-level provisional exports;
- public execution import: `from pykdex.execution import ExecutionPlan`;
- public uncertainty foundation import: `from pykdex.uncertainty import ...`;
- exact next unit: immutable `BootstrapResult` and spatial `bootstrap_kde`.

Validated Bootstrap foundation head:

```text
b9d5110f7ea1879311b4edcdbd588a18c5662ca3
```

CI #314, run `30374221919`, passed the complete repository matrix at that head.
Documentation and handoff commits after that head require their own latest CI check before
being called validated.

## Completed subunit 01: execution

Implemented:

```text
ExecutionPlan
private ResolvedExecutionPlan
conservative target memory resolution
sequential and thread target execution
logical output ordering
legacy chunk compatibility
execution metadata and fingerprints
```

Integrated:

```text
SpatialKDE
SpatiotemporalKDE
NetworkKDE: simple, discontinuous, continuous
TemporalNetworkKDE
HeatNetworkKDE: non-chunkable budget audit only
```

Execution rules that must not change:

- omitting a plan preserves legacy unbounded estimator defaults;
- explicit `ExecutionPlan()` uses the default 256 MiB budget;
- backends are only `sequential` and `thread`;
- only independent target chunks run concurrently;
- source-event reduction order remains stable;
- logical output slices are fixed before scheduling;
- chunking and worker count are operational, not statistical;
- execution metadata is excluded from estimator and asset compatibility;
- legacy and explicit target chunks are mutually exclusive;
- `HeatNetworkKDE` must not expose fake target threading.

## Completed subunit 02A: Bootstrap foundation

Public dedicated-namespace objects:

```text
BootstrapPlan
FieldEnsemble
PointwiseInterval
pointwise_percentile_interval
```

Private foundations:

```text
SeedLedger
build_seed_ledger
ResolvedReplicateExecution
resolve_replicate_execution
replicate_chunk_ranges
execute_replicate_chunks
```

Files:

```text
src/pykdex/execution/replicates.py
src/pykdex/uncertainty/__init__.py
src/pykdex/uncertainty/plan.py
src/pykdex/uncertainty/seeds.py
src/pykdex/uncertainty/fields.py
tests/test_bootstrap_plan_seed_execution.py
tests/test_uncertainty_fields.py
```

### `BootstrapPlan` rules

- `n_resamples >= 2`;
- confidence level lies strictly in `(0, 1)`;
- optional non-negative integer root seed;
- only `method="ordinary"`;
- complete replicate storage is required;
- `store_replicates=False` is rejected;
- optional `ExecutionPlan` controls replicate chunks, workers, backend, and memory;
- stable immutable fingerprint.

### Seed rules

- use NumPy `SeedSequence` and `PCG64`;
- derive all child streams in logical replicate order before scheduling;
- store root entropy and child spawn keys;
- generated entropy from `random_state=None` is recorded and replayable;
- replicate identity is independent of worker completion, `n_jobs`, target chunks, and
  replicate chunks.

### Replicate execution rules

- `execution_plan=None` for Bootstrap uses the explicit default 256 MiB execution budget;
- complete ensemble storage must be included in fixed overhead by callers;
- fixed overhead and at least one replicate must fit before work starts;
- requested replicate chunks must fit the memory budget;
- thread workers execute independent logical replicate ranges;
- results are yielded in logical range order;
- the first replicate error aborts the operation;
- no process pool, distributed scheduler, streaming quantiles, or disk-backed ensemble.

### `FieldEnsemble` rules

- complete `(B, M)` replicate array;
- one observed field on the same exact measured support;
- existing closed measured-support descriptor is reused;
- one source fingerprint per replicate;
- one support validity mask applies to observed and all replicate fields;
- invalid support elements are `NaN` everywhere;
- closed field families:
  `density`, `intensity`, `event_rate`, `relative_risk`, `log_relative_risk`;
- arrays are read-only and mappings immutable.

### Pointwise interval rules

- percentile lower and upper bounds;
- observed estimate;
- replicate standard error with `ddof=1`;
- empirical bias;
- finite columns use ordinary linear NumPy quantiles;
- log-risk columns containing `-inf` use empirical order quantiles with
  `method="inverted_cdf"`;
- `+inf` is rejected;
- undefined moments for non-finite log-risk columns remain `NaN`;
- intervals are pointwise, not simultaneous.

## Validation evidence

CI #314 passed:

- Black, isort, Ruff, and mypy;
- public API example mapping;
- strict MkDocs;
- complete pytest and branch coverage;
- source and wheel distributions;
- Twine and archive verification;
- isolated-wheel smoke test;
- Linux, Windows, and macOS;
- Python 3.11, 3.12, 3.13, and 3.14.

Temporary Black and mypy workflows were deleted and must remain absent from the PR diff.

## Exact next unit: spatial `bootstrap_kde`

Implement only:

1. immutable fail-fast `BootstrapResult`;
2. closed adapter for `SpatialEvents + GridSupport + SpatialKDE`;
3. ordinary event-index resampling with replacement;
4. new unique replicate event IDs;
5. sampled source indices retained in replicate provenance;
6. fixed finite positive scalar numeric bandwidth only;
7. unit weights only;
8. fixed kernel, metric, target, boundary, and boundary correction;
9. observed result estimated exactly once from the fixed contract;
10. independent replicate estimators constructed from configuration, not fitted state;
11. complete `(B, M)` ensemble storage counted before scheduling;
12. seed, worker, and replicate-chunk invariance tests;
13. analytical duplicate-event tests;
14. support, estimator, weight, bandwidth, memory, and failure tests;
15. a durable spatial-bootstrap handoff before adding other domains.

## Spatial adapter boundary

Accept only:

```text
SpatialEvents
GridSupport
SpatialKDE
```

Reject:

- raw arrays, DataFrames, and arbitrary external objects;
- non-unit weights;
- bandwidth strategies, adaptive vectors, matrices, and balloon bandwidths;
- replicate-wise bandwidth selection;
- changing support or estimator contract;
- ambiguous callbacks or external resamplers.

The source `SpatialKDE` may be fitted or unfitted, but Bootstrap must read only its immutable
configuration and construct independent estimators. It must not mutate or reuse fitted
state. The bandwidth constructor input itself must be a finite positive numeric scalar.

## Do not begin until spatial Bootstrap passes full CI

- network, heat, space-time, or network-time Bootstrap adapters;
- event-rate Bootstrap;
- relative-risk Bootstrap;
- separability diagnostics;
- permutation p-values;
- adaptive bandwidth uncertainty;
- bandwidth reselection;
- uncertain exposure;
- simultaneous bands, BCa, bootstrap-t, or basic intervals;
- streaming or approximate quantiles;
- persistence changes;
- package version bump, ready-for-review status, or merge.

## Recovery checklist

1. Inspect PR #16, current branch head, changed files, and latest CI.
2. Confirm PR remains Draft, open, and unmerged.
3. Confirm package version remains `0.0.15`.
4. Confirm temporary workflow and diagnostic files are absent.
5. Read all six required records.
6. Preserve execution and seed-ordering contracts exactly.
7. Implement only `BootstrapResult` and spatial `bootstrap_kde`.
8. Do not expand to other domains before a successful full-CI spatial handoff.
