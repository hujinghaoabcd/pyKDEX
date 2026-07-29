# pyKDEX 0.0.16 progress 02F: temporal-network Bootstrap

## Status

This development unit is complete on Draft PR #16.

Validated numerical implementation head:

```text
2636e6c542359ef89decb6896cfadb267460bd03
```

Validation:

```text
CI #404
run id 30415551843
conclusion: success
```

The package version remains `0.0.15`. PR #16 remains open, Draft, unmerged, and mergeable.

## Closed public domain

The shared uncertainty dispatcher now supports:

```text
NetworkTimeWorkspace + TemporalNetworkKDE -> bootstrap_kde
```

Public usage:

```python
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde

result = bootstrap_kde(
    temporal_network_estimator,
    network_time_workspace,
    plan=BootstrapPlan(...),
)
```

No separate public support argument is accepted. The exact support is
`workspace.arixels`.

## Statistical meaning

This is an ordinary event-identity Bootstrap conditional on:

- the observed accepted-event count;
- the network snapping result;
- the rejected-event audit;
- the network and lixel partition;
- the arixel product support;
- the selected fixed estimator contract.

Every replicate draws accepted event indices with replacement. One sampled-index
sequence selects the complete paired identity:

```text
snapped network location + event time + optional mark
```

Network location and time are never sampled independently. This unit is not the
later time-permutation separability test.

## Exact preserved state

Every replicate preserves:

- network fingerprint;
- lixel and arixel support fingerprints;
- accepted-event count;
- rejected-event table and snapping parameters;
- CRS and spatial unit;
- temporal unit, temporal origin, timezone, and `TimeDomain` fingerprint;
- requested/effective directedness;
- spatial and temporal kernel names;
- junction policy;
- density/intensity target;
- cyclic tail tolerance;
- coefficient tolerance and propagation-record limit.

Replicate-local event IDs are unique and deterministic. Sampled source indices,
source fingerprints, the resampling stage, and the paired resampling unit are
retained in provenance and result metadata.

## Fixed estimator contract

The first built-in adapter requires:

- unit accepted-event weights;
- a finite positive numeric scalar spatial bandwidth;
- a finite positive numeric scalar temporal bandwidth;
- built-in string names for spatial kernel, temporal kernel, and junction policy;
- fixed target and direction settings;
- no `NetworkTimeBandwidths` strategy object;
- no `NetworkTimeKNNBandwidth` selection;
- no adaptive bandwidth arrays;
- no custom kernel or junction-policy objects.

Supported junction policies:

```text
simple
discontinuous
continuous
```

Path-based policies rebuild propagation traces from the sampled snapped events.

## Network-time asset resampling

The adapter reuses the validated network Bootstrap reconstruction from 02C.

For a prepared factorized `NetworkTimeDistanceAsset`:

1. event-to-lixel network-distance rows are reindexed by sampled event identity;
2. temporal-offset columns are reindexed by the same sampled event identity;
3. temporal-distance columns are reindexed identically;
4. target time rows and fixed lixel columns remain unchanged;
5. event, support, time-domain, and base-workspace fingerprints are rebuilt for
   the replicate.

Duplicate Bootstrap selections therefore create duplicate logical event rows and
matching duplicate temporal columns without changing the underlying distances.

## Linear and cyclic time

Both linear and cyclic time domains are supported.

Cyclic replicates retain the same:

- period;
- origin;
- temporal origin label;
- timezone;
- cyclic tail tolerance;
- complete-period arixel support.

No independent time permutation, phase shift, or reassignment is performed.

## Deterministic execution

The outer execution plan schedules logical replicate ranges. Each replicate has a
stable `SeedSequence`/`PCG64` stream assigned before scheduling.

The inner `TemporalNetworkKDE` is always sequential. Target chunks apply only to
the time-row axis and are operational memory controls.

Precedence:

```text
BootstrapPlan.execution_plan.target_chunk_size
    over source TemporalNetworkKDE.time_chunk_size
```

Replicate values and source fingerprints are invariant, to documented numerical
tolerance, across:

- sequential versus thread outer execution;
- worker count;
- replicate chunk size;
- target time-row chunk size;
- worker completion order.

The observed-field fingerprint is a statistical identity derived from the fixed
estimator contract, event fingerprint, network fingerprint, and support
fingerprint. It does not hash floating-point output bytes or operational execution
metadata. This prevents harmless last-bit differences from time-row matrix
chunking from changing statistical identity.

## Memory preflight

Before replicate scheduling, the adapter conservatively accounts for:

- complete `(B, M)` ensemble storage;
- observed field and validity storage;
- source network, snapped events, times, lixels, and arixels;
- rejected-event audit;
- base event-to-lixel and event-to-event assets;
- factorized network-time assets;
- replicate event reconstruction;
- reindexed network-distance rows;
- reindexed temporal offset and distance columns;
- spatial kernel matrices;
- temporal kernel blocks;
- output fields;
- path-propagation record upper bounds;
- all requested concurrent replicate workers.

A budget that cannot hold fixed overhead or one replicate fails with
`MemoryError` before replicate execution.

## Tests added

```text
tests/test_bootstrap_temporal_network_kde.py
```

Coverage includes:

- complete `ArixelSupport` result structure;
- manual first-replicate reconstruction from the seed ledger;
- paired edge/offset/time resampling;
- unique replicate-local IDs and provenance;
- factorized network-row and time-column asset reindexing;
- sequential/thread and dual-chunk invariance;
- simple, discontinuous, and continuous policies;
- linear and cyclic time domains;
- one-event cyclic degeneracy;
- source estimator and workspace immutability;
- legacy `time_chunk_size` compatibility;
- weighted, adaptive, custom-component, and support-argument rejection;
- pre-execution memory failure.

Focused repair validation passed all 13 tests before the final repository run.

## Files added or changed in 02F

```text
src/pykdex/uncertainty/network_time.py
src/pykdex/uncertainty/api.py
tests/test_bootstrap_temporal_network_kde.py
examples/22_temporal_network_bootstrap.py
HANDOFF_0.0.16_PROGRESS_02F_TEMPORAL_NETWORK_BOOTSTRAP.md
docs/development/handoff-0.0.16-progress-02f-temporal-network-bootstrap.md
docs/guides/bootstrap.md
docs/api/uncertainty.md
HANDOFF_NEXT_CONVERSATION.md
mkdocs.yml
```

## CI evidence

Clean implementation head `2636e6c542359ef89decb6896cfadb267460bd03`
passed CI #404 (`30415551843`), including:

- Black;
- isort;
- Ruff;
- mypy;
- public API example coverage;
- strict MkDocs;
- full tests and branch coverage;
- source and wheel builds;
- Twine and archive verification;
- installed-wheel smoke;
- Linux, Windows, and macOS;
- Python 3.11, 3.12, 3.13, and 3.14.

## Exact next unit

Begin 02G with design and implementation of fixed-exposure event-rate Bootstrap
only after inspecting the current risk contracts.

Likely closed domain:

```text
KDE event intensity ensemble + fixed measured ExposureField
    -> EventRateField ensemble and pointwise interval
```

The next unit must answer before coding:

1. which spatial, network, space-time, and network-time intensity Bootstrap
   adapters can feed event-rate uncertainty;
2. how a fixed `ExposureField` is validated against every ensemble support;
3. how zero exposure and invalid support cells follow the existing explicit
   denominator policy without hidden epsilon;
4. whether event-rate replicates are produced by transforming a completed
   intensity ensemble or by a dedicated wrapper;
5. which fingerprints distinguish event uncertainty from exposure uncertainty;
6. how memory accounting includes the transformed complete ensemble;
7. how intensity and rate intervals are kept distinct;
8. how the API prevents users from interpreting fixed-exposure intervals as
   uncertainty in measured exposure.

Do not begin independent case-control relative-risk Bootstrap, uncertain-exposure
Bootstrap, separability diagnostics, or permutation testing during 02G.
