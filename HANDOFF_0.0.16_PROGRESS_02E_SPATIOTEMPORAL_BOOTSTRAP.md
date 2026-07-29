# pyKDEX 0.0.16 progress 02E: ordinary spatiotemporal Bootstrap

## Purpose

This is the durable recovery record for the closed ordinary-Bootstrap adapter for measured
`SpatiotemporalKDE` fields. It records the statistical resampling unit, exact product-support
boundary, linear and cyclic time semantics, fixed estimator contract, deterministic execution,
conservative memory model, test coverage, validation evidence, and exact continuation boundary.

This unit implements only:

```text
SpatiotemporalEvents + SpatiotemporalKDE + SpatiotemporalGridSupport
    -> bootstrap_kde
```

It does not implement temporal-network Bootstrap, fixed-exposure event-rate Bootstrap,
case-control relative-risk Bootstrap, separability diagnostics, or time permutation.

## Repository state

- repository: `hujinghaoabcd/pyKDEX`;
- latest merged release: `0.0.15`;
- stable base commit: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: #16;
- package version remains `0.0.15`;
- PR remains open, Draft, and unmerged;
- no provisional 0.0.16 top-level exports;
- uncertainty API remains in `pykdex.uncertainty`.

Validated clean numerical implementation head:

```text
eb650cd371f1da7838103aad3e114d7d9d884949
```

CI #390, run ID `30386883100`, passed the complete repository matrix at that head.

The later example, guide, API, handoff, navigation, and PR-description commits require their own
final CI inspection before the complete 02E state is called validated.

## Required reading

Read in this order:

1. `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md`;
2. `HANDOFF_0.0.16_PROGRESS_02A_BOOTSTRAP_FOUNDATION.md`;
3. `HANDOFF_0.0.16_PROGRESS_02B_SPATIAL_BOOTSTRAP.md`;
4. `HANDOFF_0.0.16_PROGRESS_02C_NETWORK_BOOTSTRAP.md`;
5. `HANDOFF_0.0.16_PROGRESS_02D_HEAT_BOOTSTRAP.md`;
6. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
7. this file.

## Public call

The existing dedicated-namespace dispatch now accepts:

```python
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde

result = bootstrap_kde(
    estimator=spatiotemporal_estimator,
    events=spatiotemporal_events,
    support=spatiotemporal_grid_support,
    plan=bootstrap_plan,
)
```

The public parameter name `events=` remains unchanged for compatibility with the original spatial
adapter.

The built-in adapter accepts only:

```text
SpatiotemporalKDE
SpatiotemporalEvents
SpatiotemporalGridSupport
```

`SpatiotemporalPointSupport`, raw arrays, DataFrames, arbitrary measured point supports, arbitrary
estimators, and external resampling callbacks are rejected.

## Statistical resampling unit

The ordinary Bootstrap unit is one complete observed space-time event identity:

```text
(spatial coordinates, time, optional mark)
```

For logical replicate `b`, pyKDEX:

1. draws `n` source-event row indices independently with replacement;
2. uses the same sampled index sequence for spatial coordinates and time;
3. preserves the observed event count `n`;
4. preserves optional marks with the same row identity;
5. creates new unique replicate-local IDs `0, ..., n - 1`;
6. creates a fresh immutable `SpatiotemporalEvents` object;
7. fits a fresh fixed-contract `SpatiotemporalKDE`;
8. evaluates on the exact original measured product grid;
9. writes the result into preassigned ensemble row `b`.

The implementation never samples spatial locations and times independently. It never permutes
times among observed locations. Independent time permutation would define a separability null
distribution, not an ordinary event Bootstrap.

Interpretation:

- density uncertainty is conditional on the observed event count;
- intensity uncertainty is conditional on the observed event count;
- spatial-time pairing is treated as observed event identity;
- unconditional Poisson event-count uncertainty is not represented;
- bandwidth-selection uncertainty is not represented;
- intervals are pointwise percentile intervals, not simultaneous bands.

## Replicate event reconstruction

Every replicate preserves selected source-row values for:

- spatial coordinates;
- normalized temporal coordinates;
- optional marks;
- spatial coordinate names;
- CRS;
- spatial unit;
- temporal unit;
- temporal origin;
- timezone;
- exact `TimeDomain` object and fingerprint.

Replicate-local event IDs are new and unique because one source row may be selected multiple
times. The selected source-index sequence preserves source identity and multiplicity for replay.

The spatial, temporal, and joint provenance objects each append:

```text
ordinary_bootstrap_resample
replicate_index
sampled_source_indices
source_event_fingerprint
resampling_unit = paired_space_time_event_identity
```

## Exact measured support

The first built-in adapter requires `SpatiotemporalGridSupport`, which is a complete measured
spatial-grid-by-time-bin product support.

The support is fixed across observed and replicate estimates, including:

- spatial coordinates and cell measures;
- spatial IDs and provenance;
- time edges;
- time centers;
- time widths;
- temporal unit;
- temporal origin;
- timezone;
- linear or cyclic time-domain fingerprint;
- flattened product coordinates, times, IDs, and measures.

The result descriptor fingerprint must equal the exact support fingerprint.

`SpatiotemporalPointSupport` is deliberately excluded from the first built-in adapter even when a
caller supplies support measures. This keeps the initial statistical contract restricted to a
complete measured product grid whose integration semantics are already explicit and validated.

## Event-support compatibility

Before observed estimation or replicate scheduling, the adapter requires exact compatibility for:

- spatial dimension;
- CRS label;
- spatial unit;
- temporal unit;
- time-domain fingerprint;
- temporal origin;
- timezone.

A mismatch is rejected explicitly. The adapter does not silently relabel units, convert temporal
origins, wrap times into a different period, or reinterpret timezones.

## Linear time semantics

For a linear time domain:

- observed event times remain their normalized numeric values;
- each replicate draws complete event rows;
- no time sorting is required or performed;
- the exact product time-bin support remains fixed;
- the estimator uses the fixed temporal kernel and bandwidth.

## Cyclic time semantics

For a cyclic time domain:

- the original cyclic period and domain fingerprint remain fixed;
- temporal values selected by the event-row sample remain paired with their spatial coordinates;
- temporal origin and timezone remain fixed;
- the fixed cyclic tail tolerance remains part of the estimator contract;
- wrapped-kernel evaluation remains the responsibility of `SpatiotemporalKDE`;
- no independent cyclic shift or phase randomization occurs.

Tests include events near the cycle boundary and verify finite replicate fields and exact cyclic
support identity.

## Fixed estimator contract

The built-in adapter reads constructor configuration only and constructs a fresh estimator for the
observed field and every replicate.

Fixed values are:

- finite positive numeric scalar spatial bandwidth;
- finite positive numeric scalar temporal bandwidth;
- built-in spatial-kernel string name;
- built-in temporal-kernel string name;
- built-in spatial-metric string name;
- density or intensity target;
- cyclic tail tolerance;
- exact event time-domain fingerprint;
- exact measured product-support fingerprint.

Custom kernel or metric objects are rejected, even if they expose a `.name`, because arbitrary
object semantics cannot be reconstructed safely from a label.

The current `SpatiotemporalKDE` constructor already requires numeric scalar bandwidths. The adapter
therefore does not expose selectors, adaptive event bandwidth arrays, balloon bandwidths, or
bandwidth matrices.

No bandwidth is reselected inside a replicate.

## Weight rule

Built-in ordinary space-time Bootstrap requires exact unit event weights:

```text
weights == [1, 1, ..., 1]
```

Non-unit weights are rejected because pyKDEX does not yet distinguish frequency, probability,
exposure, and analytic weighting semantics for resampling.

## Source estimator state

A fitted or unfitted source estimator may be supplied. The adapter does not reuse or mutate:

- fitted spatial event arrays;
- fitted times;
- fitted weights;
- event fingerprints;
- fitted kernel or metric objects;
- stored bandwidth state;
- fit metadata;
- execution state.

Tests fit the source estimator before calling Bootstrap and verify that its stored coordinates,
times, and fingerprint are unchanged.

## Deterministic random streams

The adapter uses the shared immutable seed ledger:

- one NumPy `SeedSequence` root;
- one child sequence per logical replicate;
- `PCG64` generators;
- child streams assigned before scheduling;
- generated root entropy retained when `random_state=None`.

Logical replicate `b` therefore receives the same sampled event-index sequence regardless of:

- sequential or thread outer backend;
- `n_jobs`;
- replicate chunk size;
- target chunk size;
- worker completion order.

Replicate fields are written to fixed logical ensemble rows, not completion-order rows.

## Execution model

The outer level schedules independent logical replicate ranges through the shared replicate
execution layer.

Every observed or replicate `SpatiotemporalKDE` receives an inner execution plan with:

```text
backend = sequential
n_jobs = 1
target_chunk_size = caller target chunk
```

This prevents nested outer-replicate and inner-target thread pools.

The target chunk remains an operational memory control for the space-time kernel block. It is not
a statistical parameter. Tests verify identical observed fingerprints and replicate fields across
different target chunks and outer worker configurations.

## Statistical fingerprints versus execution metadata

The observed field fingerprint includes:

- numerical values;
- support fingerprint;
- spatial and temporal bandwidths;
- target;
- kernel names;
- metric name;
- time-domain label.

It deliberately excludes execution metadata such as target chunk size and backend. Execution
choices may change audit metadata but must not change the statistical identity of an otherwise
identical observed field.

A dedicated regression assertion verifies identical observed-field fingerprints across sequential
and threaded outer execution with different target chunks.

## Conservative memory model

Before any replicate is scheduled, the adapter accounts for:

- complete `(B, M)` ensemble storage;
- observed field storage;
- validity mask;
- source spatial coordinates;
- source times;
- source weights and IDs;
- optional source marks;
- spatial-grid coordinates and measures;
- time edges, centers, and widths;
- flattened product spatial coordinates, times, measures, and IDs;
- one sampled-index array per requested concurrent worker;
- one reconstructed space-time event container per worker;
- one full replicate output field per worker;
- target-chunk spatial and temporal distance/kernel working blocks;
- target coordinate working arrays;
- a 1.25 safety factor;
- requested concurrent workers.

The complete ensemble is fixed overhead and must fit before scheduling. If fixed overhead or one
replicate chunk cannot fit, `MemoryError` is raised before replicate execution begins.

The resolved execution and memory model are retained in ensemble metadata.

## Result contract

The returned `BootstrapResult` contains:

```text
operation = bootstrap_kde
estimator_family = spatiotemporal
field_family = density or intensity
support = exact SpatiotemporalGridSupport
resampling_method = ordinary
```

Metadata includes:

- estimator-contract fingerprint;
- source event fingerprint;
- support fingerprint;
- time-domain fingerprint and name;
- temporal unit;
- temporal origin;
- timezone;
- `conditional_on_observed_event_count=True`;
- `resampling_unit=paired_space_time_event_identity`;
- `unit_event_weights=True`;
- event count;
- resolved execution metadata;
- conservative memory model.

The default interval is produced by `pointwise_percentile_interval` at the confidence level stored
in `BootstrapPlan`.

## Files added or changed

```text
src/pykdex/uncertainty/spatiotemporal.py
src/pykdex/uncertainty/api.py
tests/test_bootstrap_spatiotemporal_kde.py
examples/21_spatiotemporal_bootstrap.py
docs/guides/bootstrap.md
docs/api/uncertainty.md
HANDOFF_0.0.16_PROGRESS_02E_SPATIOTEMPORAL_BOOTSTRAP.md
docs/development/handoff-0.0.16-progress-02e-spatiotemporal-bootstrap.md
HANDOFF_NEXT_CONVERSATION.md
mkdocs.yml
```

The dedicated public symbol set is unchanged; `bootstrap_kde` gained one closed overload.

## Test coverage

Tests cover:

- complete immutable measured product-grid result;
- exact support and descriptor identity;
- density and intensity field-family propagation;
- manual first-replicate reconstruction from the seed ledger;
- exact spatial-coordinate and time pairing from one sampled-index sequence;
- unique replicate-local IDs;
- sampled-source-index and paired-unit provenance;
- deterministic seed replay;
- sequential/thread outer execution equivalence;
- target-chunk and replicate-chunk equivalence;
- observed-field fingerprint invariance to execution choices;
- linear time-domain metadata;
- cyclic time domain, period boundary, origin, timezone, and support identity;
- one-event cyclic degenerate ensemble;
- fitted source-estimator immutability;
- non-unit-weight rejection;
- measured point-support rejection;
- custom kernel-object rejection;
- temporal-unit mismatch rejection;
- public `events=` keyword compatibility;
- memory failure before replicate scheduling;
- complete repository regression and branch coverage.

## Validation evidence

### Numerical and platform evidence before final quality cleanup

CI #383, run ID `30385370365`, demonstrated that:

- complete tests and branch coverage passed;
- distributions and installed-wheel smoke passed;
- Linux, Windows, and macOS tests passed;
- Python 3.11, 3.12, 3.13, and 3.14 tests passed;
- the only failure was a Black-formatting difference.

### Clean implementation evidence

Clean numerical implementation head:

```text
eb650cd371f1da7838103aad3e114d7d9d884949
```

CI #390, run ID `30386883100`, passed:

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

During formatting diagnosis, the repository's floating `black>=24.0.0` dependency resolved to
Black 26.5.1. Temporary formatting and diagnostic workflows were removed. Do not leave any of
those workflows in the final PR diff.

## Exact next implementation unit: 02F temporal-network Bootstrap

Before coding, inspect the current temporal-network data and workspace contracts and the original
0.0.16 design. Implement only ordinary event-identity Bootstrap for the existing
`TemporalNetworkKDE` family.

The next unit must at minimum decide and enforce:

1. the exact accepted temporal-network event container and workspace input type;
2. post-snapping resampling of complete network-location-plus-time event identities;
3. one shared sampled-index sequence for edge/offset/location attributes and time;
4. fixed accepted-event count and rejection audit;
5. unique replicate-local event IDs and source-index provenance;
6. unit weights;
7. fixed numeric scalar network and temporal bandwidths;
8. fixed network kernel, temporal kernel, junction policy, direction, time domain, cyclic period,
   origin, target, network, lixels, and arixel support;
9. exact reindexing of reusable event-axis distance assets where mathematically valid;
10. preservation of cyclic time semantics without independent time permutation;
11. outer replicate scheduling separated from inner sequential network-time evaluation;
12. deterministic identity across workers, lixel/time chunks, and replicate chunks;
13. preflight accounting for the complete ensemble, network-time workspace, spatial assets,
    temporal kernel blocks, reconstructed events, and concurrent outputs;
14. analytical/manual, cyclic-time, asset, scheduling, immutability, memory, and failure tests;
15. `HANDOFF_0.0.16_PROGRESS_02F_TEMPORAL_NETWORK_BOOTSTRAP.md` and complete CI.

Time permutation remains reserved for the later explicitly Poisson first-order separability test.

## Excluded until later

- fixed-exposure event-rate Bootstrap;
- independent case-control relative-risk Bootstrap;
- separability diagnostics and permutation p-values;
- weighted, adaptive, smoothed, parametric, block, Bayesian, or wild Bootstrap;
- bandwidth selection inside replicates;
- BCa, bootstrap-t, basic, or simultaneous intervals;
- uncertain exposure;
- streaming or disk-backed ensembles;
- persistence changes;
- package version bump;
- ready-for-review transition or merge.
