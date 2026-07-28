# pyKDEX 0.0.16 progress 02B: spatial Bootstrap

## Purpose

This is the durable recovery record for the first complete estimator adapter in the pyKDEX
0.0.16 empirical uncertainty subunit. It records the immutable Bootstrap result contract,
the closed spatial ordinary-Bootstrap adapter, its statistical interpretation, execution and
memory rules, tests, documentation, and exact continuation boundary.

This unit implements only:

```text
SpatialEvents + GridSupport + SpatialKDE -> bootstrap_kde
```

It does not implement network, heat-equation, spatiotemporal, or network-time Bootstrap,
fixed-exposure event-rate Bootstrap, case-control relative-risk Bootstrap, separability, or
permutation testing.

## Repository state

- repository: `hujinghaoabcd/pyKDEX`;
- stable merged release: `0.0.15`;
- stable base commit: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: #16;
- package version remains `0.0.15`;
- PR remains open, Draft, and unmerged;
- no release/version bump;
- no 0.0.16 top-level provisional exports;
- uncertainty API remains in the dedicated `pykdex.uncertainty` namespace.

Validated clean spatial implementation head:

```text
957c8551744f52a642103e83c91f1fdb2159f305
```

CI #332, run ID `30376591895`, passed the complete repository matrix at that head.

Validated guide/API/example head:

```text
b18dea683cd4de29ad80bf705fcb6261f06d2fef
```

CI #335, run ID `30377065654`, passed the complete repository matrix at that head.

This handoff and subsequent navigation/status commits require their own latest CI inspection
before they are called validated.

## Required reading

Read in this order:

1. `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md`;
2. `HANDOFF_0.0.16_PROGRESS_02A_BOOTSTRAP_FOUNDATION.md`;
3. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
4. this file.

## Public uncertainty imports now available

```python
from pykdex.uncertainty import (
    BootstrapPlan,
    BootstrapResult,
    FieldEnsemble,
    PointwiseInterval,
    bootstrap_kde,
    pointwise_percentile_interval,
)
```

These are dedicated-namespace exports only. They are not re-exported from top-level
`pykdex` during the incomplete 0.0.16 development cycle.

## Completed immutable `BootstrapResult`

File:

```text
src/pykdex/uncertainty/results.py
```

`BootstrapResult` is the fail-fast result container for a completed built-in Bootstrap
operation. It stores:

- the complete immutable `FieldEnsemble`;
- the default immutable `PointwiseInterval`;
- the exact `BootstrapPlan`;
- operation name;
- estimator-family label;
- seed-ledger metadata;
- immutable operation metadata.

Validation rules include:

- interval and ensemble support fingerprints must match exactly;
- interval and ensemble field families must match;
- interval source fingerprint must equal the ensemble fingerprint;
- plan replicate count must equal ensemble replicate count;
- plan confidence level must equal interval confidence level;
- seed metadata must contain the exact ensemble seed-ledger fingerprint;
- seed metadata logical-task count must equal the number of replicates;
- operation and estimator-family labels must be non-empty;
- mappings are immutable;
- no failed replicates are silently dropped.

The initial built-in policy is fail-fast. Partial ensembles and failure-tolerant policies
remain outside 0.0.16.

## Completed spatial `bootstrap_kde`

Files:

```text
src/pykdex/uncertainty/spatial.py
src/pykdex/uncertainty/__init__.py
```

Public signature:

```python
bootstrap_kde(
    estimator: SpatialKDE,
    events: SpatialEvents,
    support: GridSupport,
    *,
    plan: BootstrapPlan | None = None,
) -> BootstrapResult
```

The adapter is intentionally closed. It accepts only:

```text
SpatialKDE
SpatialEvents
GridSupport
```

Raw NumPy arrays, DataFrames, arbitrary estimators, arbitrary support objects, callbacks,
and external resamplers are rejected.

## Statistical semantics

The implemented method is the ordinary nonparametric event Bootstrap conditional on the
observed event count.

For each logical replicate `b`:

1. draw `n` source-event indices independently with replacement from `0, ..., n - 1`;
2. preserve the observed sample size `n`;
3. construct a new immutable `SpatialEvents` object from those sampled rows;
4. fit a new `SpatialKDE` with the same fixed estimator contract;
5. evaluate it on the same exact `GridSupport`;
6. store the field in logical replicate row `b`.

Duplicate selected events remain duplicate events at the same coordinates. This is the
intended ordinary-Bootstrap multiplicity, not a deduplication error.

Interpretation:

- density uncertainty is conditional on the observed event count;
- intensity uncertainty is also conditional on the observed event count;
- unconditional Poisson count uncertainty is not represented;
- no bandwidth-selection uncertainty is represented;
- intervals are pointwise empirical percentile intervals, not simultaneous bands.

## Event resampling and provenance

Every replicate event container:

- preserves coordinates selected by the sampled source indices;
- uses unit weights;
- receives new unique replicate-local event IDs `0, ..., n - 1`;
- preserves coordinate names, CRS, spatial unit, and optional marks;
- appends an `ordinary_bootstrap_resample` provenance transformation;
- records the logical replicate index;
- records the complete sampled source-index sequence;
- records the original source-event fingerprint.

New unique IDs are mandatory because one source event can be selected more than once. The
sampled source-index ledger retains the identity and multiplicity needed for audit and replay.

No geometric transformation, snapping, bandwidth selection, or support reconstruction occurs
in the spatial adapter.

## Fixed estimator contract

The adapter reads only constructor configuration from the supplied `SpatialKDE`. It never
reuses or mutates fitted estimator state.

Every observed or replicate fit is performed by a newly constructed `SpatialKDE` with fixed:

- kernel;
- finite positive scalar numeric bandwidth;
- metric;
- target (`density` or `intensity`);
- optional immutable `SpatialBoundary`;
- boundary-correction mode;
- exact `GridSupport` fingerprint.

The initial adapter accepts built-in string names only for:

```text
kernel
metric
boundary_correction
```

Custom kernel, metric, and boundary-correction objects are rejected even when they expose a
`.name`, because reconstructing arbitrary object semantics from a name would be unsafe.

Rejected bandwidth configurations include:

- bandwidth selector objects;
- adaptive sample-point bandwidth arrays;
- balloon bandwidths;
- bandwidth matrices;
- Boolean values;
- non-finite values;
- zero or negative values.

No bandwidth is reselected inside a replicate.

## Weight rule

Built-in Bootstrap currently requires exact unit event weights:

```text
weights == [1, 1, ..., 1]
```

Non-unit weights are rejected because pyKDEX does not yet distinguish frequency, probability,
exposure, and analytic weighting semantics for resampling. Users with an externally justified
weighted resampling design may construct validated `FieldEnsemble` objects outside the built-in
adapter.

## Observed field rule

The observed field is estimated once from the original events using a newly constructed
estimator with the same fixed contract used by every replicate.

The supplied source estimator may be fitted or unfitted. Its fitted arrays, metadata, and
execution state are neither read as replicate state nor modified. Tests verify that calling
`bootstrap_kde` leaves the source estimator unchanged.

## Seed and scheduling determinism

The adapter uses the completed private `SeedLedger` foundation:

- NumPy `SeedSequence`;
- one child sequence per logical replicate;
- `PCG64` generators;
- all child streams assigned before scheduling;
- generated root entropy retained when `random_state=None`.

Replicate `b` therefore receives the same random sample regardless of:

- sequential versus thread backend;
- worker completion order;
- `n_jobs`;
- target chunk size;
- replicate chunk size.

Replicate results are written to fixed logical output rows, not completion-order rows.

## Execution model

Bootstrap replicate scheduling uses:

```text
src/pykdex/execution/replicates.py
```

The outer level may execute independent logical replicate ranges sequentially or with threads.
Each inner `SpatialKDE` is deliberately configured with:

```text
backend="sequential"
n_jobs=1
```

This prevents nested replicate-thread and target-thread pools. The caller's target chunk size
is retained for per-replicate KDE memory control, while replicate concurrency is controlled by
the outer resolved Bootstrap execution.

The first replicate-chunk exception aborts the operation. No failed replicate is omitted or
replaced.

## Memory model

Before any replicate is scheduled, the spatial adapter conservatively accounts for:

- complete `(B, M)` ensemble storage;
- observed field storage;
- support validity mask;
- input event coordinates, weights, IDs, and marks;
- support coordinates, measures, and IDs;
- sampled-index array per concurrent worker;
- resampled event coordinates, weights, and IDs per concurrent worker;
- optional resampled marks;
- one replicate output field per worker;
- the target-chunk by source-event kernel working estimate;
- a safety factor;
- requested concurrent workers.

The complete ensemble is part of fixed overhead and must fit before scheduling. The resolver
then determines a replicate chunk that also fits. Too-small budgets raise `MemoryError` before
replicate work begins.

Resolved execution and memory-model metadata are retained in the ensemble.

## Result contents

The returned `BootstrapResult` contains an ensemble with:

- replicate values shaped `(n_resamples, support.n_points)`;
- observed values shaped `(support.n_points,)`;
- exact `GridSupport` identity;
- field family equal to the estimator target;
- observed result fingerprint;
- one resampled-event fingerprint per logical replicate;
- resampling method `ordinary`;
- seed-ledger fingerprint;
- resolved execution metadata;
- estimator-contract fingerprint;
- original source-event fingerprint;
- exact support fingerprint;
- `conditional_on_observed_event_count=True`;
- `unit_event_weights=True`;
- event count and memory-model audit metadata.

The default interval is calculated by `pointwise_percentile_interval` at the confidence level
stored in `BootstrapPlan`.

## Files added in 02B

```text
src/pykdex/uncertainty/results.py
src/pykdex/uncertainty/spatial.py
tests/test_bootstrap_spatial_kde.py
tests/test_bootstrap_spatial_closed_components.py
docs/guides/bootstrap.md
docs/api/uncertainty.md
examples/18_spatial_bootstrap.py
HANDOFF_0.0.16_PROGRESS_02B_SPATIAL_BOOTSTRAP.md
docs/development/handoff-0.0.16-progress-02b-spatial-bootstrap.md
```

The namespace export file was extended:

```text
src/pykdex/uncertainty/__init__.py
```

## Test coverage

The spatial Bootstrap tests cover:

- immutable `BootstrapResult` construction and cross-object consistency;
- one-event degenerate Bootstrap fields;
- exact agreement with a manually reconstructed first replicate;
- source-index provenance and unique replicate IDs;
- deterministic seed replay;
- equality across sequential and threaded outer execution;
- equality across target and replicate chunk configurations;
- logical replicate ordering;
- source estimator fitted-state preservation;
- density and intensity field-family propagation;
- fixed exact GridSupport identity;
- read-only ensemble arrays and immutable metadata;
- non-unit-weight rejection;
- raw-input and incorrect-support rejection;
- adaptive, matrix, balloon, selector, invalid, and Boolean bandwidth rejection;
- custom kernel-object rejection;
- custom metric-object rejection;
- custom boundary-correction-object rejection;
- boundary-correction-without-boundary rejection;
- memory-budget failure before work begins.

## Documentation and example

User-facing files:

```text
docs/guides/bootstrap.md
docs/api/uncertainty.md
examples/18_spatial_bootstrap.py
```

The guide explains:

- conditional-on-count ordinary Bootstrap interpretation;
- fixed-contract restrictions;
- deterministic seed and scheduling behaviour;
- complete ensemble storage;
- pointwise percentile interval semantics;
- exclusions and non-goals.

The executable example builds immutable spatial events and a measured grid, runs a small
reproducible Bootstrap, and prints observed estimates and pointwise bounds.

## Validation evidence

### Clean spatial implementation

Head:

```text
957c8551744f52a642103e83c91f1fdb2159f305
```

CI #332 (`30376591895`) passed:

- Black;
- isort;
- Ruff;
- mypy;
- public API example mapping;
- strict MkDocs;
- complete pytest suite;
- branch coverage;
- source and wheel distributions;
- Twine and archive verification;
- isolated-wheel installation and smoke test;
- Linux, Windows, and macOS;
- Python 3.11, 3.12, 3.13, and 3.14.

### Guide, API, and executable example

Head:

```text
b18dea683cd4de29ad80bf705fcb6261f06d2fef
```

CI #335 (`30377065654`) passed the same complete repository matrix, including execution of all
numbered examples and strict documentation build.

Temporary formatting, patching, mypy, and quality diagnostic workflows were deleted and must
remain absent from the PR diff.

## Exact next implementation unit: radial network Bootstrap

Implement the ordinary Bootstrap adapter for already prepared, accepted, snapped network
events. Begin with radial `NetworkKDE`; keep heat-equation Bootstrap as a separate unit because
its estimator and memory semantics are materially different.

The next unit must:

1. inspect `NetworkWorkspace`, `NetworkEvents`, `LixelSupport`, distance assets, and estimator
   construction paths at the current branch head;
2. resample accepted event identities after snapping, never raw geometries before snapping;
3. keep the network, lixel geometry, support, rejected-event audit, CRS, unit, and directed
   setting fixed;
4. create new unique replicate-local event IDs while retaining sampled accepted-event indices;
5. reuse or column-reindex prepared distance assets only where mathematically exact;
6. require unit weights;
7. require a finite positive fixed scalar network bandwidth;
8. require built-in string kernel and fixed junction policy;
9. keep target, directed mode, network fingerprint, and support fingerprint fixed;
10. build independent replicate estimators/workspaces without mutating the supplied workspace;
11. include complete ensemble and per-worker network working memory in the pre-execution budget;
12. preserve logical seed and replicate ordering across workers and chunks;
13. add analytical duplicate-event, asset-reindexing, workspace-immutability, memory, and
    cross-scheduling tests;
14. generate a dedicated 02C handoff and pass complete CI before starting heat, space-time,
    network-time, event-rate, or relative-risk Bootstrap.

## Network Bootstrap design cautions

- Resampling must occur after accepted-event snapping.
- Do not snap duplicate sampled events again.
- Rejected input events are not part of the accepted-event sampling population.
- Preserve the original rejected-event audit unchanged.
- Do not recompute network geometry for every replicate.
- Do not assume all prepared assets can be shared unchanged: event-axis assets may require exact
  column reindexing by sampled source indices.
- Duplicate sampled accepted events must remain duplicate contributions.
- Do not allow estimator configuration to vary across replicates.
- Do not expose arbitrary user callbacks.
- Do not introduce heat-equation solver support inside the radial adapter by accident.

## Do not begin in the radial network unit

- heat-equation network Bootstrap;
- spatiotemporal Bootstrap;
- temporal-network Bootstrap;
- fixed-exposure event-rate Bootstrap;
- case-control relative-risk Bootstrap;
- separability diagnostics;
- permutation p-values;
- simultaneous confidence bands;
- BCa, bootstrap-t, or basic intervals;
- adaptive or selected bandwidth Bootstrap;
- uncertain exposure;
- weighted built-in Bootstrap;
- persistence-format changes;
- top-level exports;
- package version bump;
- ready-for-review status or merge.

## Recovery checklist

1. Inspect PR #16, current branch head, changed files, and latest CI.
2. Confirm PR remains open, Draft, and unmerged.
3. Confirm package version remains `0.0.15`.
4. Confirm no temporary workflows or diagnostic logs are present in the PR diff.
5. Read progress 01, 02A, the design, and this 02B handoff.
6. Preserve the execution, seed, support, fail-fast, and full-ensemble contracts exactly.
7. Begin only the radial prepared-network Bootstrap adapter.
8. Do not start heat or later uncertainty/separability units before a successful complete-CI
   02C handoff.
