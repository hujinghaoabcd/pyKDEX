# pyKDEX current handoff

The latest merged release is **0.0.15**. Active development is pyKDEX **0.0.16** on Draft
PR #16. Deterministic execution, the empirical Bootstrap foundation, and the closed spatial
`bootstrap_kde` adapter are complete. The exact next unit is ordinary radial Bootstrap for
accepted, already snapped events in a prepared network workspace.

## Read these records in order

1. `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`;
2. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
3. `HANDOFF_0.0.16_DESIGN_UNCERTAINTY_SEPARABILITY_SCALABLE.md`;
4. `HANDOFF_0.0.16_DESIGN_VALIDATION.md`;
5. `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md`;
6. `HANDOFF_0.0.16_PROGRESS_02A_BOOTSTRAP_FOUNDATION.md`;
7. `HANDOFF_0.0.16_PROGRESS_02B_SPATIAL_BOOTSTRAP.md`.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- stable base: pyKDEX `0.0.15` on `main`;
- base commit: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: `#16 Develop pyKDEX 0.0.16 uncertainty, separability, and scalable execution`;
- package version remains `0.0.15`;
- PR remains open, Draft, and unmerged;
- no 0.0.16 top-level provisional exports;
- public execution import: `from pykdex.execution import ExecutionPlan`;
- public uncertainty import: `from pykdex.uncertainty import ...`;
- exact next unit: prepared radial-network `bootstrap_kde` adapter;
- heat-equation network Bootstrap remains a separate later unit.

Validated spatial Bootstrap implementation head:

```text
957c8551744f52a642103e83c91f1fdb2159f305
```

CI #332, run `30376591895`, passed the complete repository matrix at that head.

Validated guide/API/example head:

```text
b18dea683cd4de29ad80bf705fcb6261f06d2fef
```

CI #335, run `30377065654`, passed the complete repository matrix at that head.

The 02B handoff and navigation/status commits after `b18dea6...` require inspection of their
own latest CI before being called validated.

## Completed subunit 01: deterministic execution

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

Integrated estimators:

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

### Plan rules

- `n_resamples >= 2`;
- confidence level lies strictly in `(0, 1)`;
- root seed is optional and non-negative;
- only `method="ordinary"`;
- complete replicate storage is mandatory;
- `store_replicates=False` is rejected;
- optional `ExecutionPlan` controls memory and replicate scheduling;
- immutable stable fingerprint.

### Seed rules

- use NumPy `SeedSequence` and `PCG64`;
- create child streams in logical replicate order before scheduling;
- store root entropy and spawn keys;
- generated entropy from `random_state=None` is replayable;
- replicate identity is independent of workers, completion order, target chunks, and replicate
  chunks.

### Replicate execution rules

- Bootstrap default execution uses the explicit 256 MiB budget;
- callers include the complete ensemble in fixed overhead;
- fixed overhead and at least one replicate must fit before work starts;
- requested replicate chunks must fit;
- thread workers execute independent logical ranges;
- results are yielded in logical range order;
- the first replicate error aborts;
- no process pool, distributed scheduler, streaming quantile, or disk-backed ensemble.

### Ensemble and interval rules

- full `(B, M)` replicate array;
- observed field on the exact same measured support;
- shared support validity mask;
- invalid cells are `NaN` in observed and every replicate;
- closed families: `density`, `intensity`, `event_rate`, `relative_risk`,
  `log_relative_risk`;
- arrays read-only, mappings immutable;
- percentile endpoints, observed estimate, `ddof=1` standard error, and empirical bias;
- finite columns use ordinary linear quantiles;
- log-risk columns containing `-inf` use empirical order quantiles;
- `+inf` rejected;
- pointwise intervals are not simultaneous bands.

## Completed subunit 02B: spatial Bootstrap

Public additions:

```text
BootstrapResult
bootstrap_kde
```

Closed signature:

```python
bootstrap_kde(
    estimator: SpatialKDE,
    events: SpatialEvents,
    support: GridSupport,
    *,
    plan: BootstrapPlan | None = None,
) -> BootstrapResult
```

### Spatial statistical semantics

- ordinary event-index sampling with replacement;
- fixed observed event count;
- duplicate selected events remain duplicate contributions;
- density and intensity uncertainty are conditional on event count;
- no unconditional Poisson count uncertainty;
- no bandwidth-selection uncertainty;
- observed and replicate fields use the same fixed estimator contract;
- default summaries are pointwise percentile intervals.

### Spatial input boundary

Accept only:

```text
SpatialKDE
SpatialEvents
GridSupport
```

Require:

- exact unit event weights;
- finite positive scalar numeric bandwidth;
- built-in string kernel;
- built-in string metric;
- built-in string boundary correction;
- fixed target;
- fixed optional `SpatialBoundary`;
- exact fixed `GridSupport`.

Reject:

- raw arrays and DataFrames;
- arbitrary estimators and callbacks;
- weighted events;
- selector, adaptive, matrix, and balloon bandwidths;
- Boolean and invalid scalar bandwidths;
- custom kernel, metric, and correction objects;
- changing support or configuration.

### Replicate event rule

Each replicate:

- receives new unique local event IDs;
- preserves sampled source indices in provenance;
- records the logical replicate index and source fingerprint;
- preserves coordinates, CRS, unit, coordinate names, and optional marks;
- is constructed as a new immutable event object.

### Estimator isolation

- source estimator may be fitted or unfitted;
- only constructor configuration is used;
- fitted state is not reused or mutated;
- observed and every replicate use separate new estimator instances;
- inner KDE execution is sequential with one worker;
- outer execution owns replicate concurrency;
- target chunk size still controls inner working memory.

### Spatial memory rule

Pre-execution fixed overhead includes:

- complete ensemble;
- observed field and validity mask;
- event and support inputs;
- per-worker sampled indices and resampled event arrays;
- per-worker output field;
- target-by-event kernel working estimate;
- safety factor and requested workers.

Insufficient memory raises before replicate work begins.

### Spatial implementation files

```text
src/pykdex/uncertainty/results.py
src/pykdex/uncertainty/spatial.py
src/pykdex/uncertainty/__init__.py
tests/test_bootstrap_spatial_kde.py
tests/test_bootstrap_spatial_closed_components.py
docs/guides/bootstrap.md
docs/api/uncertainty.md
examples/18_spatial_bootstrap.py
```

### Spatial test coverage

- immutable cross-object result validation;
- one-event degenerate fields;
- manual seed/reconstruction agreement;
- provenance and unique IDs;
- sequential/thread invariance;
- target/replicate chunk invariance;
- logical ordering;
- source estimator immutability;
- density/intensity labels;
- support identity;
- read-only arrays and mappings;
- invalid input, weight, bandwidth, component, boundary, and memory cases.

## Validation evidence

CI #332 passed the clean spatial implementation across:

- Black, isort, Ruff, mypy;
- public API example mapping;
- strict MkDocs;
- full pytest and branch coverage;
- source/wheel distributions, Twine, archive verification, isolated-wheel smoke;
- Linux, Windows, macOS;
- Python 3.11, 3.12, 3.13, 3.14.

CI #335 repeated the complete successful matrix after adding the guide, API page, and numbered
example.

Temporary formatting, patching, mypy, and quality workflows were deleted and must remain
absent from the PR diff.

## Exact next unit: prepared radial-network Bootstrap

Implement only an ordinary Bootstrap adapter for already accepted and snapped network events
with radial `NetworkKDE`.

Required steps:

1. inspect current `NetworkWorkspace`, accepted `NetworkEvents`, `LixelSupport`, distance
   assets, and estimator constructors;
2. identify which workspace arrays have an event axis and can be exactly column-reindexed;
3. sample accepted event identities after snapping;
4. never re-snap selected duplicate events;
5. keep network geometry, lixels, support, rejected-event audit, CRS, unit, directed setting,
   and topology fixed;
6. create new unique replicate event IDs;
7. retain sampled accepted-event indices and source fingerprints;
8. require unit event weights;
9. require finite positive fixed scalar bandwidth;
10. require built-in kernel name and fixed junction policy;
11. keep target, network fingerprint, support fingerprint, direction, and estimator semantics
    fixed;
12. build independent replicate workspace/estimator state without mutating source objects;
13. include complete ensemble and per-worker network working memory before scheduling;
14. preserve seed, result, and logical replicate identity across workers/chunks;
15. test duplicate-event contributions, exact asset reindexing, immutability, memory failures,
    and scheduling invariance;
16. generate `HANDOFF_0.0.16_PROGRESS_02C_NETWORK_BOOTSTRAP.md` and docs counterpart;
17. pass complete repository CI before beginning heat or later domains.

## Network design cautions

- sampling occurs after accepted-event snapping;
- rejected source events are not in the sampling population;
- rejected-event audit remains fixed and unchanged;
- duplicate selected accepted events are duplicate contributions;
- network geometry is never rebuilt per replicate;
- event-axis assets may need exact sampled-index reindexing;
- do not assume every prepared asset can be shared unchanged;
- do not allow configuration changes across replicates;
- do not expose user callbacks;
- do not mix heat-equation support into the radial adapter.

## Do not begin in 02C

- heat-equation network Bootstrap;
- spatiotemporal or network-time Bootstrap;
- fixed-exposure event-rate Bootstrap;
- case-control relative-risk Bootstrap;
- separability or permutation testing;
- weighted, adaptive, selected-bandwidth, BCa, bootstrap-t, basic, or simultaneous methods;
- uncertain exposure;
- persistence changes;
- top-level exports;
- package version bump;
- ready-for-review status or merge.

## Recovery checklist

1. Inspect PR #16, branch head, changed files, and latest CI.
2. Confirm PR remains open, Draft, and unmerged.
3. Confirm package version remains `0.0.15`.
4. Confirm temporary workflows and diagnostic files are absent.
5. Read all seven required records.
6. Preserve execution, seed, support, fail-fast, and full-ensemble contracts.
7. Start only the prepared radial-network adapter.
8. Do not start heat or later uncertainty/separability work before a successful 02C full-CI
   handoff.
