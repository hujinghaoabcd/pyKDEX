# pyKDEX 0.0.16 progress 02B: spatial Bootstrap

## Scope

This development handoff records the first complete estimator adapter in the pyKDEX 0.0.16
empirical uncertainty work:

```text
SpatialEvents + GridSupport + SpatialKDE -> bootstrap_kde
```

It includes the immutable `BootstrapResult`, closed spatial ordinary-Bootstrap adapter,
pointwise percentile summary, deterministic replicate scheduling, conservative memory audit,
tests, user guide, API page, and executable example.

It does not include network, heat, space-time, network-time, event-rate, relative-risk,
separability, or permutation APIs.

The more exhaustive root recovery record is:

```text
HANDOFF_0.0.16_PROGRESS_02B_SPATIAL_BOOTSTRAP.md
```

## Repository state

- stable release: pyKDEX `0.0.15`;
- base commit: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: #16;
- package version remains `0.0.15`;
- PR remains open, Draft, and unmerged;
- uncertainty symbols remain under `pykdex.uncertainty` only.

Validated clean implementation head:

```text
957c8551744f52a642103e83c91f1fdb2159f305
```

CI #332 (`30376591895`) passed the complete repository matrix.

Validated guide/API/example head:

```text
b18dea683cd4de29ad80bf705fcb6261f06d2fef
```

CI #335 (`30377065654`) passed the complete repository matrix.

This handoff and later navigation/status commits require inspection of their own latest CI.

## Public dedicated-namespace API

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

No incomplete 0.0.16 uncertainty object is exported from top-level `pykdex`.

## `BootstrapResult`

`BootstrapResult` is an immutable fail-fast aggregate containing:

- a complete `FieldEnsemble`;
- its default `PointwiseInterval`;
- the exact `BootstrapPlan`;
- operation and estimator-family labels;
- seed-ledger metadata;
- immutable operation metadata.

Construction verifies exact agreement among:

- ensemble and interval support fingerprints;
- field-family labels;
- interval source and ensemble fingerprints;
- plan and ensemble replicate counts;
- plan and interval confidence levels;
- ensemble and seed-ledger fingerprints;
- seed logical-task count and ensemble replicate count.

The built-in policy does not drop failed replicates. A replicate error aborts the operation.
Partial ensembles remain outside 0.0.16.

## Spatial adapter contract

Signature:

```python
bootstrap_kde(
    estimator: SpatialKDE,
    events: SpatialEvents,
    support: GridSupport,
    *,
    plan: BootstrapPlan | None = None,
) -> BootstrapResult
```

Accepted types are closed to `SpatialKDE`, `SpatialEvents`, and `GridSupport`.

The adapter requires:

- exact unit event weights;
- finite positive numeric scalar bandwidth;
- built-in string kernel name;
- built-in string metric name;
- built-in string boundary-correction name;
- fixed target;
- fixed optional immutable `SpatialBoundary`;
- fixed exact measured grid support.

It rejects:

- raw arrays and DataFrames;
- arbitrary estimators and callbacks;
- non-unit weights;
- selector objects;
- adaptive, matrix, and balloon bandwidths;
- Boolean, non-finite, zero, and negative bandwidths;
- custom kernel, metric, or correction objects;
- correction without a boundary;
- changing support or estimator configuration.

## Statistical meaning

The method is the ordinary nonparametric event Bootstrap conditional on the observed event
count.

For each logical replicate:

1. draw the observed number of event indices with replacement;
2. build a new immutable event collection from the selected rows;
3. preserve duplicate selections as duplicate event contributions;
4. preserve event count and unit weights;
5. fit a new estimator with the same fixed contract;
6. evaluate the same support;
7. write the field to its preassigned logical replicate row.

The result describes conditional field uncertainty. It excludes unconditional Poisson-count
uncertainty and bandwidth-selection uncertainty.

The default interval is a pointwise empirical percentile interval. It is not a simultaneous
confidence band.

## Replicate event provenance

Each resampled `SpatialEvents` object:

- has new unique local IDs `0, ..., n - 1`;
- retains sampled source indices in provenance;
- retains the logical replicate index;
- retains the source-event fingerprint;
- preserves coordinate names, CRS, unit, and optional marks;
- appends `ordinary_bootstrap_resample` to its provenance.

New IDs prevent duplicate selected source IDs from violating immutable event-ID uniqueness.
The source-index sequence preserves multiplicity and replay audit.

## Estimator isolation

The supplied estimator may be fitted or unfitted. Bootstrap reads constructor configuration
only. It never mutates or reuses fitted event arrays, selected bandwidth state, result arrays,
or last-execution state.

The observed field and every replicate use separately constructed `SpatialKDE` instances with
the same fixed contract.

## Seed determinism

The adapter uses the 02A seed ledger:

- NumPy `SeedSequence`;
- one child stream per logical replicate;
- `PCG64`;
- child assignment before scheduling;
- stored generated entropy when no root seed is supplied.

Replicate `b` is unchanged by:

- sequential versus thread execution;
- worker completion order;
- number of workers;
- target chunk size;
- replicate chunk size.

Results are stored by logical replicate index rather than completion order.

## Execution and nested threading

Outer execution schedules independent replicate ranges. Inner estimators always use sequential
execution with one worker, while retaining the requested target chunk size.

This prevents nested thread pools and separates:

- outer replicate concurrency;
- inner target-memory chunking.

The first replicate-chunk error aborts the operation.

## Memory audit

Before work begins, the adapter accounts for:

- the complete `(B, M)` ensemble;
- observed field and validity mask;
- event and support inputs;
- per-worker sampled indices;
- per-worker resampled event arrays;
- optional marks;
- per-worker replicate output;
- target-block by event kernel working memory;
- safety factor and concurrent workers.

The full ensemble belongs to fixed overhead. Insufficient memory raises `MemoryError` before
replicate scheduling.

Resolved execution and memory-model details are retained in ensemble metadata.

## Result metadata

The ensemble retains:

- exact support identity;
- estimator target as field family;
- observed-result fingerprint;
- one resampled-event fingerprint per replicate;
- ordinary-Bootstrap method label;
- seed-ledger fingerprint;
- resolved execution metadata;
- estimator-contract fingerprint;
- original event fingerprint;
- support fingerprint;
- event count;
- fixed-count and unit-weight labels;
- memory audit.

## Files

Implementation:

```text
src/pykdex/uncertainty/results.py
src/pykdex/uncertainty/spatial.py
src/pykdex/uncertainty/__init__.py
```

Tests:

```text
tests/test_bootstrap_spatial_kde.py
tests/test_bootstrap_spatial_closed_components.py
```

User documentation and example:

```text
docs/guides/bootstrap.md
docs/api/uncertainty.md
examples/18_spatial_bootstrap.py
```

Durable records:

```text
HANDOFF_0.0.16_PROGRESS_02B_SPATIAL_BOOTSTRAP.md
docs/development/handoff-0.0.16-progress-02b-spatial-bootstrap.md
```

## Test coverage

Tests establish:

- valid immutable result aggregation;
- one-event degenerate fields;
- exact first-replicate agreement with manual seed replay;
- source-index provenance and local unique IDs;
- sequential/thread equality;
- target/replicate chunk equality;
- logical ordering;
- source estimator immutability;
- density and intensity labels;
- exact support identity;
- read-only arrays and immutable mappings;
- unit-weight enforcement;
- closed input types;
- closed bandwidth contract;
- closed built-in component contract;
- boundary-correction validation;
- fail-before-work memory errors.

## Validation

CI #332 validated the clean spatial implementation on:

- Black, isort, Ruff, mypy;
- public API mapping;
- strict MkDocs;
- full pytest and branch coverage;
- source and wheel builds;
- Twine, archive verification, and isolated-wheel smoke;
- Linux, Windows, macOS;
- Python 3.11, 3.12, 3.13, 3.14.

CI #335 repeated the complete successful matrix after adding the guide, API page, and numbered
example.

Temporary formatting, patching, mypy, and diagnostic workflows were deleted and must remain
absent from the PR diff.

## Exact next unit: radial prepared-network Bootstrap

Continue with an ordinary Bootstrap adapter for accepted, already snapped network events and
radial `NetworkKDE` only.

Required design:

1. inspect current `NetworkWorkspace`, accepted `NetworkEvents`, `LixelSupport`, distance
   assets, and estimator constructors;
2. sample accepted event identities after snapping;
3. preserve the network, lixels, support, rejection audit, CRS, unit, direction, and topology;
4. never re-snap duplicate selections;
5. create new unique replicate event IDs and retain sampled accepted-event indices;
6. exactly reindex event-axis distance assets where valid;
7. keep unit weights and a fixed scalar network bandwidth;
8. keep built-in kernel, junction policy, target, direction, network fingerprint, and support
   fingerprint fixed;
9. build independent replicate state without mutating the supplied workspace;
10. pre-account for complete ensemble and per-worker network memory;
11. preserve seed and logical ordering across workers and chunks;
12. add analytical, asset-reindex, immutability, memory, and scheduling tests;
13. write a 02C handoff and pass complete CI.

Heat-equation Bootstrap must remain a separate later unit.

## Excluded from 02C

- heat-equation Bootstrap;
- spatiotemporal Bootstrap;
- network-time Bootstrap;
- event-rate and relative-risk Bootstrap;
- separability and permutation testing;
- weighted, adaptive, selected-bandwidth, BCa, bootstrap-t, basic, or simultaneous methods;
- uncertain exposure;
- persistence changes;
- top-level exports;
- version bump, ready status, or merge.
