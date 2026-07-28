# pyKDEX 0.0.16 progress 01: deterministic execution foundation

## Purpose of this record

This file is the durable recovery record for the first implementation subunit of pyKDEX
0.0.16. It must be read before starting bootstrap uncertainty or separability work.

The completed subunit adds a common deterministic, memory-bounded execution contract to
the existing estimator families. It does **not** complete pyKDEX 0.0.16 and it does not add
bootstrap or permutation inference.

## Repository state

- repository: `hujinghaoabcd/pyKDEX`;
- stable merged release: `0.0.15`;
- stable base commit: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: `#16 Design pyKDEX 0.0.16 uncertainty, separability, and scalable execution`;
- package version remains `0.0.15`;
- PR remains Draft;
- PR is not merged;
- no provisional 0.0.16 top-level exports were added;
- public execution import is `from pykdex.execution import ExecutionPlan`.

The clean implementation head before user-guide and handoff additions is:

```text
cef94f9b26c3faab6aaeab85dadf0740bcc34078
```

That head passed CI #281, run ID `30369196085`.

## Required reading order

1. `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`;
2. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
3. `HANDOFF_0.0.16_DESIGN_UNCERTAINTY_SEPARABILITY_SCALABLE.md`;
4. `HANDOFF_0.0.16_DESIGN_VALIDATION.md`;
5. this file.

## Completed architecture

The first subunit implements:

```text
ExecutionPlan
ResolvedExecutionPlan (private)
conservative target-execution resolution
logical target-chunk execution
sequential backend
thread backend
execution audit metadata
legacy chunk normalization
operation-specific memory models
```

The execution layer lives in:

```text
src/pykdex/execution/__init__.py
src/pykdex/execution/plan.py
src/pykdex/execution/chunks.py
```

## Public `ExecutionPlan`

The immutable public object is:

```python
ExecutionPlan(
    memory_budget_bytes=256 * 1024 * 1024,
    target_chunk_size=None,
    replicate_chunk_size=None,
    n_jobs=1,
    backend="sequential",
)
```

Current backend values are closed to:

```text
sequential
thread
```

Validation rules:

- `memory_budget_bytes` is a positive integer or `None`;
- target and replicate chunks are positive integers or `None`;
- `n_jobs` is a positive integer;
- boolean values are rejected as integers;
- backend names are normalized to lower case;
- `backend="sequential"` requires `n_jobs=1`;
- unknown backend strings are rejected;
- the object is immutable;
- requested plans have a stable fingerprint.

`replicate_chunk_size` is validated and fingerprinted now, but ordinary estimators do not
use it. It exists so bootstrap and permutation can share the same execution object in later
subunits.

## Default compatibility rule

Omitting an execution plan preserves historical estimator defaults:

```python
SpatialKDE(bandwidth=1.0)
```

is internally resolved as an implicit, unbounded plan for compatibility.

Creating `ExecutionPlan()` explicitly is different: it requests the default 256 MiB memory
budget. Use:

```python
ExecutionPlan(memory_budget_bytes=None)
```

when an explicit plan and audit record are desired without budget-based resolution.

Do not change this distinction during later subunits.

## Private resolved contract

Each operation resolves the public request into an immutable private
`ResolvedExecutionPlan`. The record contains:

```text
operation_name
source: implicit | legacy | explicit
memory_budget_bytes
requested_target_chunk_size
resolved_target_chunk_size
requested_replicate_chunk_size
n_targets
n_sources
bytes_per_pair
fixed_overhead_bytes
safety_factor
requested_n_jobs
resolved_n_jobs
backend
parallel_axis
estimated_peak_bytes
execution_plan_fingerprint
resolved_execution_fingerprint
n_target_chunks
```

The record is exposed only as result metadata or fitted estimator state. It is not a public
statistical estimator object.

## Conservative memory model

For chunkable target-axis operations, the analytical peak estimate is:

```text
fixed_overhead
+ resolved_chunk_rows
  * n_sources
  * bytes_per_pair
  * safety_factor
  * resolved_concurrent_workers
```

The resolver:

1. validates fixed overhead and pair estimates;
2. subtracts fixed overhead from the budget;
3. computes the largest target chunk fitting concurrent workers;
4. rejects an explicit target chunk that exceeds the budget;
5. reduces resolved workers to the number of logical chunks;
6. verifies the final estimated peak against the budget.

Failure occurs before the main dense pair block is allocated when:

- fixed overhead alone exceeds the budget;
- one target row cannot fit;
- an explicit target chunk cannot fit; or
- the final conservative peak exceeds the budget.

For non-chunkable operations, the estimate includes the complete global operation. Such
operations reject partial target chunks and threaded target execution rather than silently
ignoring them.

The estimate covers pyKDEX-managed arrays and known reusable assets. It is not a total RSS
guarantee because Python, NumPy, SciPy, BLAS, the operating system, and memory allocators
may retain additional memory.

## Deterministic execution rule

Only independent target chunks execute concurrently in this subunit.

The implementation preserves:

- stable source-event reduction order inside every target chunk;
- fixed logical target slices;
- output ordering independent of worker completion order;
- one preallocated result destination;
- atomic estimator state reset on failure.

Changing target chunk size or `n_jobs` must not change the statistical estimate beyond
repository numerical tolerance.

The contract does not promise cross-platform bitwise equality across BLAS, operating
systems, or floating-point hardware.

## Integrated estimator families

### `SpatialKDE`

Integration file:

```text
src/pykdex/estimators/spatial_kde.py
```

Behaviour:

- target axis is support points or grid cells;
- independent target chunks may use threads;
- source-event contribution order is preserved within each block;
- a supplied full spatial distance asset is counted as fixed overhead;
- legacy `chunk_size` remains supported;
- `chunk_size` and `execution_plan.target_chunk_size` cannot both be explicit;
- resolved metadata is stored under `result.metadata["execution"]`;
- fitted estimator state retains `last_execution_`.

### `SpatiotemporalKDE`

Integration file:

```text
src/pykdex/estimators/spatiotemporal_kde.py
```

Behaviour:

- target axis is the ordinary space-time support row;
- target chunks may use threads;
- event reduction order is preserved;
- supplied space-time distance assets are counted as fixed overhead;
- legacy `chunk_size` remains supported;
- execution metadata is retained in the immutable result.

### `NetworkKDE`

Integration files:

```text
src/pykdex/estimators/network_kde.py
src/pykdex/network/evaluation.py
```

The same execution contract covers:

```text
simple
discontinuous
continuous
```

For `simple` shortest-path estimation:

- the sparse event-lixel distance asset remains sparse;
- finite distance pairs are grouped by target lixel for block evaluation;
- the implementation does not materialize a full dense global distance matrix;
- per-target event contributions retain source order.

For path-based policies:

- propagation traces are created sequentially in event order;
- trace generation is not parallelized;
- lixel target chunks may execute concurrently;
- each target chunk accumulates traces in original event order;
- optional stored propagation traces retain existing identity and order.

### `TemporalNetworkKDE`

Integration file:

```text
src/pykdex/estimators/temporal_network_kde.py
```

Behaviour:

- target axis is temporal cells;
- threads execute independent time blocks;
- the event-by-lixel spatial kernel matrix is a fixed asset;
- the network-time distance asset is counted as fixed overhead;
- the previous complete temporal kernel matrix is no longer required;
- temporal offsets and temporal kernels are created only for the active time block;
- legacy `time_chunk_size` remains supported;
- `time_chunk_size` conflicts with an explicit plan target chunk;
- simple and path-based spatial policies use the same time-block contract.

This change is important: the requested memory budget now constrains the temporary temporal
matrix instead of permitting an unbudgeted complete time-by-event matrix.

### `HeatNetworkKDE`

Integration file:

```text
src/pykdex/estimators/heat_network_kde.py
```

The heat estimator is a global finite-element solve, not a target-independent kernel block
calculation. Its execution contract therefore performs audit and budget validation only.

Fixed memory includes:

- heat operator sparse arrays;
- compute-plan arrays;
- dense spectral assets where used;
- source mass and evolved state arrays;
- lixel output arrays.

The estimator explicitly rejects:

- a multi-worker thread target axis; and
- a partial target chunk.

This is intentional. Do not add fake target parallelism around the global solver.

## Legacy constructor compatibility

These existing parameters remain supported:

```text
SpatialKDE.chunk_size
SpatiotemporalKDE.chunk_size
TemporalNetworkKDE.time_chunk_size
```

Resolution sources are recorded as:

```text
implicit
legacy
explicit
```

A legacy explicit chunk and an explicit plan target chunk are mutually exclusive. No
deprecation warning has been added.

## Metadata boundary

Execution metadata is operational provenance. It must not alter:

- estimator compatibility;
- density-result compatibility;
- relative-risk estimator contracts;
- support fingerprints;
- event fingerprints;
- distance-asset fingerprints;
- propagation-trace fingerprints;
- heat-plan fingerprints.

Different safe chunk sizes and worker counts remain the same statistical estimator.

## Tests added

```text
tests/test_execution_plan.py
tests/test_execution_spatial_integration.py
tests/test_execution_network_integration.py
tests/test_execution_network_time_integration.py
tests/test_execution_heat_integration.py
```

The focused execution suite contains 39 tests and covers:

- immutable plan normalization and fingerprints;
- invalid input types and values;
- concurrent-worker memory accounting;
- explicit chunk budget failure;
- legacy/plan chunk conflicts;
- non-chunkable operation rejection;
- logical thread-completion ordering;
- spatial thread/sequential equivalence;
- ordinary space-time thread/sequential equivalence;
- supplied distance-asset budgeting;
- all three radial/path network policies;
- propagation-trace stability;
- network-time simple and continuous routes;
- time-block asset reuse;
- heat numerical equivalence;
- heat global-solver restrictions;
- atomic fitted-state reset after failure.

A temporary focused workflow showed 38 passing tests and one overly narrow error-message
assertion. The implementation correctly raised `MemoryError`; the test expected only the
phrase `fixed overhead` while the resolver reported `estimated peak memory exceeds`. The
test was changed to assert the stable budget-exceeded semantic. The temporary workflow and
its diagnostic artifact are not part of the branch diff.

## Validation evidence

Clean implementation head:

```text
cef94f9b26c3faab6aaeab85dadf0740bcc34078
```

CI #281 (`30369196085`) passed:

- Black;
- isort;
- Ruff;
- mypy;
- public API example mapping;
- strict MkDocs;
- complete pytest suite;
- branch coverage;
- source and wheel builds;
- Twine checks;
- distribution archive verification;
- isolated wheel installation and smoke test;
- Linux, Windows, and macOS;
- Python 3.11, 3.12, 3.13, and 3.14.

Earlier useful validation:

- CI #268 passed the spatial, ordinary space-time, and network execution integration before
  the network-time and heat additions;
- CI #277 confirmed all quality and distribution checks, then exposed only the heat test
  message mismatch described above.

Do not claim a later documentation or handoff head is validated without checking its own
workflow.

## Documentation and benchmark

Added:

```text
docs/guides/execution.md
docs/api/execution.md
benchmarks/benchmark_execution_plan.py
```

The benchmark compares deterministic sequential and threaded `SpatialKDE` target plans and
asserts numerical equivalence before reporting descriptive timings. Timing is not a
cross-platform performance guarantee.

## Temporary workflow audit

Temporary formatting, patching, and diagnostic workflows were used during connector-only
development because the local container could not resolve `github.com` and did not contain
`gh`.

Every temporary workflow was deleted after use. Before continuing, verify that no files
under `.github/workflows/` other than the repository's permanent workflows appear in PR
#16, and verify that `DEBUG_EXECUTION_TESTS.txt` is absent.

## Explicit exclusions retained

Subunit 01 did not add:

- bootstrap resampling;
- permutation tests;
- confidence intervals or bands;
- process pools;
- Dask, Joblib, or Ray runtime dependencies;
- GPU or approximate kernels;
- parallel source-event reductions;
- Zarr or disk-backed result arrays;
- PostGIS execution;
- persistence-schema changes;
- version bump;
- top-level provisional execution exports.

## Exact next subunit

The next subunit is **empirical field uncertainty foundation**.

Implement only the fixed-boundary ordinary bootstrap defined in the 0.0.16 design.

Required sequence:

1. inspect current immutable event objects and workspace reconstruction paths;
2. implement immutable `BootstrapPlan` with only `method="ordinary"`;
3. implement a private NumPy `SeedSequence` ledger derived in logical replicate order;
4. ensure replicate seed identity is independent of worker scheduling, `n_jobs`, target
   chunks, and replicate chunks;
5. implement immutable exact-support `FieldEnsemble` with full in-memory replicate storage;
6. implement explicit `PointwiseInterval` percentile summaries;
7. implement immutable `BootstrapResult` with fail-fast replicate semantics;
8. implement closed adapters for supported estimator/event pairs;
9. implement `bootstrap_kde` first;
10. implement `bootstrap_event_rate` with fixed `ExposureField`;
11. implement `bootstrap_relative_risk` with independent within-group case/control
    resampling and default log-risk intervals;
12. reject non-unit weights, adaptive bandwidths, bandwidth matrices, bandwidth reselection,
    changing support, changing estimator contracts, and ambiguous external objects;
13. use `ExecutionPlan.replicate_chunk_size` and deterministic logical replicate slices;
14. account for complete ensemble storage before scheduling replicates;
15. add analytical, seed-invariance, ordering, denominator-policy, support-compatibility,
    failure, and cross-domain tests;
16. add guide, API, executable example, benchmark, and
    `HANDOFF_0.0.16_PROGRESS_02_BOOTSTRAP.md`;
17. pass complete repository CI before beginning separability.

## Bootstrap interpretation boundary

The built-in bootstrap must remain restricted to:

- immutable pyKDEX events or prepared workspaces;
- unit event weights;
- fixed support;
- fixed scalar bandwidths;
- fixed kernels, metrics, boundary corrections, junction policy, direction, network, and
  time domain;
- fixed accepted-event count inside each resampled group;
- no bandwidth reselection inside replicates.

`bootstrap_kde` is conditional on observed event count.

`bootstrap_event_rate` resamples only event intensity and labels exposure as fixed.

`bootstrap_relative_risk` independently resamples cases and controls within groups and
produces pointwise log-risk percentile intervals by default.

Pointwise percentile intervals are not simultaneous confidence bands.

## Do not add in the next subunit

- smoothed, parametric, Bayesian, block, wild, or weighted bootstrap;
- arbitrary non-unit event weights;
- adaptive bandwidth bootstrap;
- replicate-wise bandwidth selection;
- unconditional Poisson count bootstrap;
- uncertain-exposure resampling;
- pooled case/control resampling;
- BCa, bootstrap-t, basic, or simultaneous intervals;
- streaming or approximate quantiles;
- Zarr-backed ensembles;
- separability diagnostics;
- permutation p-values;
- local significance maps;
- global envelopes.

## Recovery checklist

1. Inspect PR #16 and current branch head.
2. Confirm the PR remains open, Draft, and unmerged.
3. Confirm package version remains `0.0.15`.
4. Confirm `ExecutionPlan` is imported only from `pykdex.execution`.
5. Confirm temporary workflows and diagnostic files are absent from the PR diff.
6. Check the latest CI before claiming validation.
7. Read the detailed 0.0.16 design bootstrap sections.
8. Begin only Subunit 02.
9. Preserve the deterministic execution and seed-ordering contract.
10. Do not begin separability until Bootstrap receives its own successful full-CI handoff.
