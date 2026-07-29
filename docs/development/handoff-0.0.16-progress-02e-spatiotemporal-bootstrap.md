# pyKDEX 0.0.16 progress 02E: ordinary spatiotemporal Bootstrap

Status: numerical implementation complete; release remains incomplete.

The detailed durable record is:

```text
HANDOFF_0.0.16_PROGRESS_02E_SPATIOTEMPORAL_BOOTSTRAP.md
```

## Completed domain

```text
SpatiotemporalEvents + SpatiotemporalKDE + SpatiotemporalGridSupport
    -> bootstrap_kde
```

The built-in adapter performs ordinary event-identity resampling with replacement while keeping
spatial coordinates, time, and optional marks paired as one source row.

## Fixed contract

The adapter requires:

- exact unit event weights;
- finite positive numeric scalar spatial and temporal bandwidths;
- built-in spatial-kernel, temporal-kernel, and metric string names;
- fixed density/intensity target and cyclic tail tolerance;
- exact spatial dimension, CRS, spatial unit, temporal unit, temporal origin, timezone, and
  time-domain compatibility;
- exact measured `SpatiotemporalGridSupport`;
- no selector, adaptive bandwidth, point support, arbitrary callback, or weighted resampling.

## Linear and cyclic time

Linear and cyclic domains are both supported. Replicate rows preserve the source `TimeDomain`
fingerprint, temporal origin, timezone, and paired spatial-time event identity. No independent time
permutation or phase randomization occurs.

## Execution and memory

Outer replicate ranges may be threaded. Every inner `SpatiotemporalKDE` is sequential and uses the
caller's target chunk solely for operational memory control. Statistical field fingerprints exclude
execution metadata.

Preflight memory accounting includes the complete ensemble, source event arrays, full product
support, reconstructed event containers, output fields, and spatial/temporal kernel working blocks
for every requested concurrent worker.

## Validation

Clean numerical implementation head:

```text
eb650cd371f1da7838103aad3e114d7d9d884949
```

CI #390 (`30386883100`) passed quality, strict documentation, complete tests, branch coverage,
distributions, installed-wheel smoke, Linux, Windows, macOS, and Python 3.11-3.14.

The later example, guide, API, handoff, navigation, and PR-description state requires its own final
CI before it is called validated.

## Exact next unit

```text
02F: ordinary TemporalNetworkKDE Bootstrap
```

Before coding, inspect the exact current network-time event and workspace contracts. The next
adapter must resample complete snapped-network-location-plus-time event identities after snapping,
preserve cyclic time and exact arixel support, require unit weights and fixed scalar network and
temporal bandwidths, reindex reusable event-axis assets where valid, preserve deterministic
replicate identity, and pass complete CI.

Time permutation remains reserved for the later explicitly Poisson separability test.
