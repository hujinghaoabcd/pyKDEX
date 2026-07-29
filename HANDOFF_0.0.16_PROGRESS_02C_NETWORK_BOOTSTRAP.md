# pyKDEX 0.0.16 progress 02C: radial network Bootstrap

## Purpose

This is the durable recovery record for the closed ordinary-Bootstrap adapter for radial
`NetworkKDE`. It follows the completed execution foundation, common Bootstrap foundation, and
spatial Bootstrap adapter.

This unit implements only:

```text
NetworkWorkspace + NetworkKDE -> bootstrap_kde
```

Supported junction policies are:

```text
simple
discontinuous
continuous
```

`HeatNetworkKDE`, `SpatiotemporalKDE`, `TemporalNetworkKDE`, event-rate Bootstrap,
relative-risk Bootstrap, separability diagnostics, and permutation testing remain outside this
unit.

## Repository state

- repository: `hujinghaoabcd/pyKDEX`;
- stable merged release: `0.0.15`;
- stable base commit: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: #16;
- package version remains `0.0.15`;
- PR remains open, Draft, and unmerged;
- no release/version bump;
- uncertainty APIs remain under `pykdex.uncertainty`.

The implementation and tests first entered the branch at:

```text
d6fcfefa55e1095d280735e3c056f92ab4008c98
```

CI #343 (`30379267533`) proved that the full pytest matrix, branch coverage, distributions,
and all completed operating-system/Python jobs passed. Its only failure was Black formatting.

The exact Black/isort formatting commit was:

```text
78ac248d193fec62c858074dc65c8b5daf53dfac
```

The temporary formatting workflow was deleted at:

```text
d23e8e28f04b65dd9de57e8a14141b9366fa1f1e
```

At that clean head, Black, isort, Ruff, mypy, public API example mapping, and strict MkDocs all
passed in CI #346. Later compatibility, guide, example, handoff, navigation, and status commits
must be checked through the latest PR head before being called fully validated.

## Required reading

Read in this order:

1. `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md`;
2. `HANDOFF_0.0.16_PROGRESS_02A_BOOTSTRAP_FOUNDATION.md`;
3. `HANDOFF_0.0.16_PROGRESS_02B_SPATIAL_BOOTSTRAP.md`;
4. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
5. this file.

## Public API

Dedicated import:

```python
from pykdex.uncertainty import bootstrap_kde
```

The closed dispatcher accepts either:

```python
bootstrap_kde(
    estimator: SpatialKDE,
    events: SpatialEvents,
    support: GridSupport,
    *,
    plan: BootstrapPlan | None = None,
)
```

or:

```python
bootstrap_kde(
    estimator: NetworkKDE,
    events: NetworkWorkspace,
    support: None = None,
    *,
    plan: BootstrapPlan | None = None,
)
```

The second public parameter deliberately retains the name `events` so existing spatial calls
using `events=` remain valid. For `NetworkKDE` the value is a prepared `NetworkWorkspace`
containing already-snapped accepted events.

A regression test protects the spatial keyword compatibility.

## Closed network adapter boundary

The network adapter accepts only:

```text
NetworkKDE
NetworkWorkspace
BootstrapPlan or None
```

The workspace must contain at least one accepted `NetworkEvents` collection and a valid exact
`LixelSupport` on the same network.

Rejected inputs include:

- raw coordinate arrays or DataFrames;
- raw `SpatialEvents` requiring snapping;
- arbitrary estimator or workspace objects;
- explicit separate support arguments;
- non-unit accepted-event weights;
- bandwidth strategies;
- adaptive event-specific bandwidths;
- custom kernel objects;
- custom junction-policy objects;
- changing network, lixel support, direction, or estimator contract;
- user-defined resampling callbacks.

## Statistical semantics

The method is ordinary nonparametric resampling of **accepted snapped event identities** with
replacement, conditional on the observed accepted-event count.

For logical replicate `b`:

1. draw `n` accepted-event indices with replacement;
2. keep sample size `n` fixed;
3. create new unique replicate-local event IDs `0, ..., n - 1`;
4. preserve the selected accepted events' network positions and attributes;
5. create a new immutable replicate workspace;
6. construct a fresh `NetworkKDE` from the fixed estimator configuration;
7. evaluate on the exact original lixel support;
8. write the result to logical ensemble row `b`.

The adapter does not repeat geometric snapping. It therefore conditions on the observed
snapping and acceptance result as well as the observed accepted-event count.

It does not represent:

- uncertainty in raw geometry;
- snapping-distance or tie uncertainty;
- rejected-event uncertainty;
- network topology uncertainty;
- unconditional Poisson event-count uncertainty;
- bandwidth-selection uncertainty.

## Accepted-event reconstruction

Each replicate `NetworkEvents` object preserves selected rows from:

```text
edge_indices
edge_ids
offsets
coordinates
original_coordinates
snap_distances
snap_status
marks
```

It also preserves:

```text
network_fingerprint
crs
spatial_unit
```

Weights remain exactly one. Event IDs are regenerated to remain unique when a source event is
selected multiple times.

Replicate provenance records:

- `ordinary_bootstrap_resample`;
- logical replicate index;
- complete sampled accepted-event index sequence;
- original accepted-event fingerprint;
- original workspace fingerprint.

## Snap audit preservation

The replicate `SnapResult` preserves the source workspace's:

- rejected-event table;
- validation report;
- snapping parameter mapping.

Only the accepted `events` member changes. The rejected records are not resampled, removed, or
re-snapped.

## Exact prepared-asset reindexing

### Event-to-lixel asset

For `NetworkDistanceAsset` representing accepted events to lixel centres:

- target IDs and target fingerprint remain unchanged;
- each new bootstrap source row copies the stored finite pairs from its selected source row;
- duplicate selected source events create duplicate logical rows;
- row indices are rewritten to replicate-local event order;
- distances, weight mode, direction, cutoff, network fingerprint, and target fingerprint remain
  fixed;
- source IDs and source fingerprint are replaced with those of the reconstructed replicate
  events.

### Event-to-event asset

For accepted-event to accepted-event assets:

- both axes are reindexed by the sampled accepted-event sequence;
- duplicate selected events create duplicate logical rows and columns;
- a stored old pair `(i, j)` is expanded to every new row selecting `i` and every new column
  selecting `j`;
- zero-distance and duplicate-location pairs remain explicit;
- source and target IDs/fingerprints are replaced by the same reconstructed replicate event
  locations;
- network, weight, direction, cutoff, and distance values remain fixed.

The reconstructed assets are validated through `NetworkWorkspace.validate()` before estimator
execution.

## Junction-policy behaviour

### `simple`

The simple radial estimator uses event-to-lixel shortest-path distance assets. A compatible
prepared source asset is reindexed and reused for every replicate rather than recomputed.

### `discontinuous` and `continuous`

Path-based estimators rebuild propagation traces from the resampled accepted event positions.
They preserve the network, lixels, kernel, bandwidth, direction, coefficient tolerance, and
record limit.

They do not use event-to-lixel assets as their numerical evaluation path, but compatible assets
are still reindexed when retained in the replicate workspace so workspace identity and audit
remain complete.

## Fixed estimator contract

Every observed or replicate fit uses a newly constructed `NetworkKDE` with fixed:

- built-in kernel string;
- finite positive numeric scalar bandwidth;
- built-in junction-policy string;
- density or intensity target;
- requested/effective direction;
- coefficient tolerance;
- maximum records per event;
- `store_propagation` setting;
- exact network fingerprint;
- exact lixel-support fingerprint.

No fitted state from the supplied estimator is reused. The supplied estimator and source
workspace remain unchanged after Bootstrap.

## Seed and scheduling determinism

The adapter uses the common `SeedLedger`:

- NumPy `SeedSequence`;
- one child sequence per logical replicate;
- `PCG64` generators;
- child streams assigned before scheduling;
- generated root entropy retained when no explicit seed is supplied.

Replicate `b` is invariant to:

- sequential versus thread backend;
- worker count;
- target chunk size;
- replicate chunk size;
- worker completion order.

Results are stored in logical replicate order.

## Execution model

Outer execution may parallelize independent logical replicate ranges. Every inner `NetworkKDE`
uses one worker with sequential target execution, while retaining the requested target chunk
size for memory control. Nested replicate and target thread pools are not created.

The first replicate-chunk exception aborts the operation. Partial ensembles are not returned.

## Memory model

Before scheduling, the adapter conservatively accounts for:

- complete `(B, M)` ensemble storage;
- observed field and validity mask;
- accepted-event arrays and optional marks;
- lixel support arrays;
- source event-to-lixel and event-to-event assets;
- one sampled-index vector per concurrent worker;
- one reconstructed accepted-event container per worker;
- one reconstructed output field per worker;
- reindexed asset storage per worker;
- target-chunk by event kernel working storage;
- thread concurrency and safety factor.

For path-based policies, it additionally reserves the hard upper bound:

```text
n_events * max_records_per_event * 96 bytes
```

per concurrent worker for propagation records. This is intentionally conservative and may
require users to lower `max_records_per_event`, reduce workers, or increase the explicit memory
budget.

If fixed overhead or one replicate cannot fit, `MemoryError` is raised before replicate
scheduling.

## Result metadata

The `FieldEnsemble` and `BootstrapResult` record:

- field family;
- exact lixel support descriptor;
- observed field fingerprint;
- original accepted-event fingerprint;
- original workspace fingerprint;
- network and support fingerprints;
- fixed estimator-contract fingerprint;
- kernel, bandwidth, junction policy, target, and directedness;
- conditional-on-observed-event-count flag;
- conditional-on-observed-snapping flag;
- one replicate event fingerprint per logical replicate;
- one replicate workspace fingerprint per logical replicate;
- seed-ledger fingerprint and metadata;
- resolved replicate execution;
- target execution plan;
- conservative memory model.

## Files added or changed

```text
src/pykdex/uncertainty/api.py
src/pykdex/uncertainty/network.py
src/pykdex/uncertainty/__init__.py
tests/test_bootstrap_network_kde.py
tests/test_bootstrap_api_compatibility.py
docs/guides/bootstrap.md
examples/19_network_bootstrap.py
HANDOFF_0.0.16_PROGRESS_02C_NETWORK_BOOTSTRAP.md
docs/development/handoff-0.0.16-progress-02c-network-bootstrap.md
HANDOFF_NEXT_CONVERSATION.md
mkdocs.yml
```

## Test coverage

Network tests cover:

- simple, discontinuous, and continuous policies;
- density and intensity targets;
- one-event degenerate Bootstrap;
- manual first-replicate reconstruction from the seed ledger;
- exact event-to-lixel asset row reindexing;
- exact event-to-event asset row-and-column reindexing;
- duplicate selected source events;
- unique replicate-local IDs;
- accepted-event and workspace provenance;
- unchanged rejected snap audit;
- source estimator and workspace immutability;
- equality across sequential/thread execution;
- equality across target and replicate chunk sizes;
- logical replicate ordering;
- non-unit weight rejection;
- fixed scalar bandwidth enforcement;
- custom kernel and junction-policy rejection;
- wrong input and support rejection;
- memory-budget failure before work;
- spatial `events=` keyword compatibility.

## Validation evidence

CI #343 (`30379267533`) demonstrated that the new network implementation passed:

- full pytest on completed Linux, Windows, and macOS matrix jobs;
- branch coverage;
- source and wheel distributions;
- Twine and archive verification;
- isolated wheel installation.

Its quality job stopped only at Black. No network numerical or platform failure was observed.

The exact formatting commit changed only layout in `src/pykdex/uncertainty/network.py`.
At the clean post-format head, the quality chain passed:

- Black;
- isort;
- Ruff;
- mypy;
- public API example mapping;
- strict MkDocs.

The latest head after compatibility, docs, example, and this handoff must pass its own complete
CI before 02C is considered fully closed.

All temporary formatting workflows must remain absent from the final PR diff.

## Exact next implementation unit: heat-equation Bootstrap

Implement only ordinary Bootstrap for:

```text
NetworkWorkspace + HeatNetworkKDE
```

The next unit must:

1. resample accepted snapped events after snapping;
2. preserve the exact network, lixel support, snapping audit, CRS, units, and topology;
3. require unit accepted-event weights;
4. require fixed numeric heat time/bandwidth configuration with no selector;
5. construct a fresh heat estimator and global finite-element solve per replicate;
6. preserve deterministic seed and logical replicate ordering;
7. keep inner solves sequential and non-chunked;
8. conservatively account for full solver state per concurrent replicate;
9. reject unsupported target threading rather than simulating it;
10. add analytical/degenerate, scheduling, memory, immutability, and contract tests;
11. generate `HANDOFF_0.0.16_PROGRESS_02D_HEAT_BOOTSTRAP.md` before moving on.

## Do not begin in the heat unit

- spatiotemporal Bootstrap;
- temporal-network Bootstrap;
- event-rate Bootstrap;
- relative-risk Bootstrap;
- separability diagnostics;
- permutation p-values;
- weighted or adaptive built-in Bootstrap;
- bandwidth/time selection inside replicates;
- simultaneous intervals, BCa, bootstrap-t, or basic intervals;
- uncertain exposure;
- streaming or disk-backed ensembles;
- persistence changes;
- package version bump, ready-for-review status, or merge.
