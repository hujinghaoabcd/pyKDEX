# 0.0.12 network-time foundation handoff

The complete recoverable engineering record is maintained at the repository
root in `HANDOFF_0.0.12_NETWORK_TIME_FOUNDATION.md`. This documentation page
summarizes the public architecture and routes maintainers to that authoritative
record.

## Delivered architecture

Version 0.0.12 composes the existing network and temporal layers:

```text
NetworkWorkspace
+ accepted TemporalCoordinates
→ NetworkTimeEvents

LixelSupport × temporal cells
→ ArixelSupport

sparse event→lixel distances
+ target-time×event signed offsets
→ NetworkTimeDistanceAsset

NetworkTimeWorkspace
+ spatial junction policy
+ temporal kernel
→ TemporalNetworkKDE
→ NetworkTimeField
```

The estimator is a fixed-bandwidth separable product on a network and time.
It preserves `simple`, `discontinuous`, and `continuous` junction semantics
and reuses the normalized cyclic temporal image sum introduced in 0.0.11.

## Permanent numerical rules

- Arixel measure is actual lixel length multiplied by actual temporal-cell
  width.
- Flat results are time-major and reshape to `time × lixel`.
- Density weights divide by total event weight; intensity weights do not.
- Rejected raw events retain snap audit records and their times are removed by
  stable event ID, never by positional shifting.
- A cyclic arixel support covers exactly one period from the domain origin.
- Network distance is factorized over time, not expanded per arixel.
- `simple` supports directed networks and infinite-support spatial kernels.
- Path policies require finite support; `continuous` remains undirected.
- Assets validate network, events, lixels, time metadata, directed mode,
  cutoff, and fingerprints before reuse.
- Public arrays are read-only and failed fits clear state atomically.

## Primary files

- `src/pykdex/network_time/`
- `src/pykdex/estimators/temporal_network_kde.py`
- `src/pykdex/core/network_time_results.py`
- `tests/test_network_time_data.py`
- `tests/test_temporal_network_kde.py`
- `examples/14_temporal_network_kde.py`
- `docs/estimators/temporal-network-kde.md`
- `docs/guides/network-time-data.md`

## Validation and publication

The authoritative root handoff records final test, coverage, distribution, PR,
CI, and merge evidence. Values are updated only after they are observed.

## Next unit

The recommended 0.0.13 unit is network-time bandwidth selection and adaptive
temporal-network KDE: reusable event-event/time caches, weighted LOO
likelihood, arixel LSCV, deterministic joint/separate candidate experiments,
and explicit sample-point bandwidth ownership.
