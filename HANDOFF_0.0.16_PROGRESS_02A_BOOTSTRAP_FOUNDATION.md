# pyKDEX 0.0.16 progress 02A: bootstrap foundation

## Purpose

This is the durable recovery record for the first half of the pyKDEX 0.0.16 empirical
uncertainty subunit. It records the completed random-stream, replicate-execution, ensemble,
and pointwise-interval foundation.

This record does **not** claim that `bootstrap_kde`, `bootstrap_event_rate`, or
`bootstrap_relative_risk` is implemented. The next implementation unit begins with
`BootstrapResult` and the spatial `bootstrap_kde` adapter.

## Repository state

- repository: `hujinghaoabcd/pyKDEX`;
- stable merged release: `0.0.15`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: #16;
- package version remains `0.0.15`;
- PR remains open, Draft, unmerged;
- no release/version bump;
- no top-level provisional uncertainty exports.

Clean Bootstrap foundation head:

```text
b9d5110f7ea1879311b4edcdbd588a18c5662ca3
```

CI #314, run ID `30374221919`, passed the complete repository matrix at that head.

## Required reading

1. `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md`;
2. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
3. this file.

## Completed public contracts

### `BootstrapPlan`

Dedicated import:

```python
from pykdex.uncertainty import BootstrapPlan
```

Initial contract:

```python
BootstrapPlan(
    n_resamples=999,
    confidence_level=0.95,
    random_state=None,
    method="ordinary",
    store_replicates=True,
    execution_plan=None,
)
```

Rules:

- at least two replicates;
- confidence level strictly inside `(0, 1)`;
- optional non-negative integer root seed;
- only `method="ordinary"`;
- complete replicate storage is mandatory;
- `store_replicates=False` is rejected;
- optional `ExecutionPlan` controls replicate scheduling and memory;
- immutable with a stable fingerprint.

### `FieldEnsemble`

Dedicated import:

```python
from pykdex.uncertainty import FieldEnsemble
```

It stores:

- complete replicate matrix with shape `(B, M)`;
- observed field with shape `(M,)`;
- exact measured support;
- closed field family;
- observed-field fingerprint;
- one replicate-source fingerprint per logical replicate;
- ordinary-bootstrap method label;
- seed-ledger fingerprint;
- resolved replicate-execution metadata;
- a support validity mask;
- immutable metadata.

Supported field-family labels are:

```text
density
intensity
event_rate
relative_risk
log_relative_risk
```

Support identity reuses the existing closed measured-support descriptor from
`pykdex.risk.support`; no second support identity system was introduced.

### `PointwiseInterval`

Dedicated imports:

```python
from pykdex.uncertainty import PointwiseInterval, pointwise_percentile_interval
```

The immutable object stores:

- lower pointwise percentile;
- observed estimate;
- upper pointwise percentile;
- replicate standard error using `ddof=1`;
- empirical bootstrap bias;
- exact support and validity mask;
- field family;
- confidence level;
- source ensemble fingerprint;
- `method="percentile"`.

These are pointwise empirical summaries. They are not simultaneous confidence bands.

## Validity and non-finite rules

A single support-level validity mask applies to the observed field and every replicate.
Invalid support elements must be `NaN` everywhere.

For density, intensity, event rate, and relative risk:

- valid values must be finite;
- valid values must be non-negative;
- positive or negative infinity is rejected.

For log relative risk:

- finite values and `-inf` are permitted;
- `+inf` is rejected;
- columns containing `-inf` use empirical order-statistic quantiles via
  `method="inverted_cdf"`;
- standard error and bias remain `NaN` for such non-finite columns because ordinary moments
  are not defined.

Finite columns continue to use NumPy's ordinary linear percentile interpolation.

## Deterministic seed ledger

Private module:

```text
src/pykdex/uncertainty/seeds.py
```

`SeedLedger` records:

- root entropy;
- one unique `SeedSequence.spawn_key` per logical task;
- `PCG64` as the initial bit generator;
- stable metadata and fingerprint.

All child seed sequences are created in logical replicate order before work is scheduled.
A random generator can be reconstructed from the root entropy and logical replicate index.

Therefore replicate `b` is independent of:

- worker completion order;
- `n_jobs`;
- replicate chunk size;
- target chunk size;
- sequential versus thread scheduling.

When `random_state=None`, NumPy generates root entropy once. The generated entropy is stored
in the ledger metadata and can reproduce the run exactly.

## Replicate execution foundation

Private module:

```text
src/pykdex/execution/replicates.py
```

Implemented:

```text
ResolvedReplicateExecution
resolve_replicate_execution
replicate_chunk_ranges
execute_replicate_chunks
```

The replicate resolver uses the completed `ExecutionPlan` contract but keeps target and
replicate resolution separate.

Memory estimate:

```text
fixed_overhead
+ replicate_chunk_size
  * bytes_per_replicate
  * safety_factor
  * concurrent_workers
```

Future callers must include the complete `(B, M)` ensemble array in `fixed_overhead` before
replicate work is scheduled.

Rules:

- `execution_plan=None` for bootstrap uses explicit default execution semantics, including
  the 256 MiB default budget;
- a requested replicate chunk must fit the budget;
- fixed overhead must fit before work begins;
- at least one replicate must fit;
- thread execution runs independent logical replicate ranges;
- yielded results always follow logical range order;
- work is fail-fast: the first replicate-chunk exception aborts the operation.

No process pools, distributed scheduler, streaming quantiles, or disk-backed ensemble is
implemented.

## Files added

```text
src/pykdex/execution/replicates.py
src/pykdex/uncertainty/__init__.py
src/pykdex/uncertainty/plan.py
src/pykdex/uncertainty/seeds.py
src/pykdex/uncertainty/fields.py
tests/test_bootstrap_plan_seed_execution.py
tests/test_uncertainty_fields.py
```

## Test coverage

The foundation tests cover:

- plan normalization and invalid requests;
- stable plan fingerprints;
- deterministic child streams;
- replay of automatically generated root entropy;
- invalid seed entropy and logical indices;
- worker-aware replicate memory resolution;
- explicit replicate chunk failures;
- fixed-overhead and one-replicate failures;
- logical result ordering under intentionally reversed thread completion;
- seed identity across sequential and threaded schedules;
- exact measured-support ensemble validation;
- read-only arrays and immutable mappings;
- ensemble memory accounting;
- ordinary finite percentile, standard error, and bias calculations;
- shared `NaN` support validity;
- closed field families;
- log-risk `-inf` handling and `+inf` rejection;
- empirical order quantiles for non-finite log-risk columns;
- interval shape and confidence-level validation.

## Validation evidence

Clean head:

```text
b9d5110f7ea1879311b4edcdbd588a18c5662ca3
```

CI #314 (`30374221919`) passed:

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
- isolated wheel installation and smoke test;
- Linux, Windows, and macOS;
- Python 3.11, 3.12, 3.13, and 3.14.

Temporary Black and mypy diagnostic workflows were deleted. They must remain absent from
the PR diff.

## Exact next implementation unit

Implement only:

1. immutable fail-fast `BootstrapResult`;
2. a closed spatial adapter for `SpatialEvents + GridSupport + SpatialKDE`;
3. `bootstrap_kde` for the spatial domain;
4. ordinary event-index resampling with replacement;
5. new unique replicate event IDs while retaining sampled source indices in provenance;
6. fixed scalar numeric bandwidth only;
7. unit event weights only;
8. fixed kernel, metric, target, boundary, and boundary correction;
9. fixed exact GridSupport;
10. complete ensemble storage accounted before scheduling;
11. observed field estimated once with the same fixed estimator contract;
12. fail-fast replicate behaviour;
13. sequential/thread and replicate-chunk invariance tests;
14. analytical duplicate-event tests;
15. memory failure tests;
16. progress handoff for the spatial bootstrap adapter before adding other domains.

## Spatial bootstrap restrictions

The first adapter must accept only:

```text
SpatialEvents
GridSupport
SpatialKDE
```

Reject:

- raw arrays or DataFrames;
- non-unit weights;
- adaptive sample-point bandwidths;
- balloon bandwidths;
- bandwidth matrices;
- bandwidth-selection strategies;
- changing support;
- changing boundary or correction;
- arbitrary external estimator objects;
- user-supplied replicate callback functions.

The configured estimator must use a finite positive scalar numeric bandwidth. Replicate
estimators must be constructed from the fixed configuration rather than mutating or reusing
fitted estimator state.

## Do not begin yet

Until the spatial `bootstrap_kde` unit passes complete CI, do not implement:

- network, heat, space-time, or network-time bootstrap adapters;
- fixed-exposure event-rate bootstrap;
- case-control relative-risk bootstrap;
- separability diagnostics;
- permutation p-values;
- simultaneous intervals;
- BCa, bootstrap-t, or basic intervals;
- bandwidth reselection;
- adaptive bandwidth uncertainty;
- uncertain exposure;
- streaming or approximate quantiles;
- persistence changes;
- version bump or merge.
