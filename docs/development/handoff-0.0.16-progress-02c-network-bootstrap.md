# pyKDEX 0.0.16 progress 02C: radial network Bootstrap

## Status

The closed ordinary-Bootstrap adapter for radial `NetworkKDE` is implemented on Draft PR #16.
The stable merged release remains 0.0.15 and the package version has not been bumped.

Implemented domain:

```text
NetworkWorkspace + NetworkKDE -> bootstrap_kde
```

Supported built-in junction policies:

```text
simple
discontinuous
continuous
```

`HeatNetworkKDE`, space-time, network-time, event-rate, relative-risk, separability, and
permutation work remain incomplete.

## Public call

```python
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde

result = bootstrap_kde(
    NetworkKDE(
        bandwidth=0.8,
        kernel="epanechnikov",
        junction_policy="simple",
        target="density",
    ),
    workspace,
    plan=BootstrapPlan(n_resamples=999, random_state=20260728),
)
```

The dispatcher retains the second parameter name `events` so the previously published spatial
call using `events=` remains valid. For `NetworkKDE`, the value is a prepared
`NetworkWorkspace` containing accepted snapped events.

## Statistical contract

The adapter performs ordinary resampling of accepted snapped-event identities with replacement,
conditional on:

- the observed accepted-event count;
- the observed snapping and rejection outcome;
- the fixed network and lixel support;
- the fixed estimator contract.

It does not repeat raw-geometry snapping and does not represent snapping, topology, count, or
bandwidth-selection uncertainty.

Each replicate receives new unique event IDs and retains the sampled accepted-event indices,
source event fingerprint, and source workspace fingerprint in provenance.

## Workspace and asset rules

Replicates preserve:

- network and lixel objects;
- exact network/support fingerprints;
- CRS and spatial units;
- snapping parameters and rejected-event table;
- edge indices, offsets, coordinates, snap distances, statuses, and marks selected by the
  Bootstrap index sequence.

Prepared assets are reindexed exactly:

- event-to-lixel assets along the source-event axis;
- event-to-event assets along both event axes;
- duplicate selections create duplicate logical rows and columns;
- network, target, weight, direction, cutoff, and stored distances remain fixed.

Path-based policies rebuild propagation traces from the resampled snapped events but retain the
same network, support, kernel, bandwidth, direction, coefficient tolerance, and record limit.

## Closed estimator contract

Built-in network Bootstrap requires:

- `NetworkWorkspace` with accepted events;
- exact unit weights;
- finite positive numeric scalar bandwidth;
- built-in kernel and junction-policy string names;
- fixed density/intensity target;
- fixed direction and propagation safety settings;
- no bandwidth selection inside replicates.

Raw arrays, raw `SpatialEvents`, custom estimator components, adaptive bandwidths, arbitrary
callbacks, separate support arguments, and changing network/support are rejected.

## Determinism and execution

The common `SeedLedger` assigns one NumPy `SeedSequence`/`PCG64` stream to each logical
replicate before scheduling. Replicate identity is invariant to worker count, backend, target
chunks, replicate chunks, and completion order.

Outer replicate ranges may run with threads. Each inner `NetworkKDE` runs sequentially with one
worker to avoid nested thread pools. The first replicate error aborts the operation.

## Memory model

The preflight audit includes:

- complete replicate ensemble;
- observed field and validity mask;
- accepted-event and lixel arrays;
- source and reindexed distance assets;
- reconstructed events/workspace and output per worker;
- target-by-event kernel working storage;
- thread concurrency and safety factor.

For path-based policies it reserves the conservative propagation upper bound:

```text
n_events * max_records_per_event * 96 bytes
```

per concurrent worker. Too-small budgets raise `MemoryError` before replicate scheduling.

## Validation evidence

Implementation commit:

```text
d6fcfefa55e1095d280735e3c056f92ab4008c98
```

CI #343 (`30379267533`) passed full pytest, branch coverage, distributions, and completed
Linux/Windows/macOS jobs. Its only failure was Black formatting.

Exact formatting commit:

```text
78ac248d193fec62c858074dc65c8b5daf53dfac
```

Temporary workflow deletion:

```text
d23e8e28f04b65dd9de57e8a14141b9366fa1f1e
```

At that clean head, Black, isort, Ruff, mypy, API example mapping, and strict MkDocs passed in
CI #346. The latest documentation/handoff head must pass its own complete CI before the unit is
called fully closed.

## Tests

The test suite covers all three radial policies, density/intensity, degenerate and manual
replicates, both asset-reindexing modes, duplicate selections, provenance, source immutability,
thread/chunk invariance, contract rejections, memory failure, and spatial `events=` keyword
compatibility.

## Durable record

The complete recovery record is:

```text
HANDOFF_0.0.16_PROGRESS_02C_NETWORK_BOOTSTRAP.md
```

## Exact next unit

Implement only ordinary Bootstrap for:

```text
NetworkWorkspace + HeatNetworkKDE
```

The heat unit must preserve accepted snapped events, network, support, and audit; require fixed
numeric heat configuration and unit weights; create a fresh global finite-element solve per
replicate; keep inner solves sequential/non-chunked; conservatively account for full solver state
per concurrent replicate; and generate progress 02D before any space-time or risk-derived work.
