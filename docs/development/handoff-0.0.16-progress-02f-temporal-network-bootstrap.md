# pyKDEX 0.0.16 progress 02F: temporal-network Bootstrap

## Completion record

The temporal-network ordinary-Bootstrap adapter is complete on Draft PR #16.
The package version remains `0.0.15`; the PR remains Draft and unmerged.

Validated implementation head:

```text
2636e6c542359ef89decb6896cfadb267460bd03
```

Full validation:

```text
CI #404
run id 30415551843
conclusion: success
```

## Public dispatch

```text
TemporalNetworkKDE + NetworkTimeWorkspace -> bootstrap_kde
```

The adapter uses `workspace.arixels` as the exact measured support and rejects a
separate support argument.

## Statistical contract

Each replicate samples complete accepted snapped-network-location-plus-time
event identities with replacement. The accepted-event count, snapping outcome,
rejection audit, network, lixels, arixels, time domain, and fixed estimator
contract remain conditional and unchanged.

The same sampled-index sequence selects:

- network edge and offset;
- snapped/original coordinates and marks;
- event time;
- event-to-lixel distance rows;
- temporal-offset and temporal-distance columns.

Time is never independently shuffled. The later separability permutation test is
a separate statistical operation.

## Supported fixed components

- unit accepted-event weights;
- scalar spatial and temporal bandwidths;
- built-in spatial and temporal kernels;
- `simple`, `discontinuous`, or `continuous` junction policy;
- fixed density/intensity target;
- fixed direction and cyclic-tail settings;
- linear or cyclic time domain.

Adaptive arrays, selector objects, custom components, and weighted ordinary
resampling are rejected.

## Execution and fingerprints

Outer replicate ranges may use the thread backend. Each inner estimator is
sequential and chunks only target time rows.

Seed streams, replicate rows, event fingerprints, and workspace fingerprints are
independent of worker count and chunk choices. The observed-field fingerprint is
based on the fixed estimator contract, events, network, and arixel support rather
than raw floating-point output bytes. Operational chunk metadata remains outside
the statistical identity.

## Memory and failure behaviour

Memory preflight covers the complete ensemble, source and reconstructed
network-time workspaces, factorized assets, temporal and spatial kernel blocks,
propagation bounds, outputs, and requested concurrent workers. Insufficient
budgets fail before replicate scheduling. Replicate failure is fail-fast and no
partial result is returned.

## Test coverage

`tests/test_bootstrap_temporal_network_kde.py` verifies manual replay, paired
identity, factorized asset reindexing, all three policies, linear and cyclic time,
thread/chunk invariance, source immutability, legacy time chunks, closed component
rejection, and memory failure.

## Next development unit

02G should implement fixed-exposure event-rate Bootstrap only. Inspect the current
`pykdex.risk` contracts before coding. Exposure must remain explicitly fixed,
measured support must match exactly, zero-denominator handling must follow the
existing policy without hidden epsilon, and the result must not claim exposure
uncertainty.

Independent case-control relative-risk Bootstrap and first-order separability
remain later units.
