# pyKDEX current handoff

The latest implemented development unit is **0.0.13 network-time bandwidth
selection and adaptive TemporalNetworkKDE**. Read
`HANDOFF_0.0.13_NETWORK_TIME_BANDWIDTHS.md` first for the complete design,
mathematics, implementation, validation, limitations, recovery procedure, and
next-unit record.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- development branch: `agent/network-time-bandwidths`;
- version implemented in this branch: `0.0.13`;
- latest stable merged version: `0.0.12` until PR merge is observed;
- pull request: `#13 Add network-time bandwidth selection and adaptive KDE`;
- feature implementation commit:
  `1fd7c07902daf14e061491e7af313b1833ea6de3`;
- first complete PR CI run `#133` (`30014407093`): success;
- final clean PR CI: pending;
- squash merge commit: pending;
- post-merge `main` CI: pending;
- focused neighboring validation: `22 passed`;
- full local regression: `226 passed`;
- branch coverage: `81.15%`;
- public API/example map: `117 public symbols`, all mapped;
- executable examples: `15`;
- Black, isort, Ruff, mypy, and strict MkDocs: passed;
- wheel/sdist, Twine, archive verification, and isolated wheel smoke: passed;
- Linux, Windows, macOS, and Python 3.11-3.14 PR CI: passed;
- no temporary repository workflow has been added.

## Implemented in 0.0.13

- immutable scalar or event-specific `NetworkTimeBandwidths`;
- independent spatial and temporal source-event kNN bandwidths;
- duplicate-location and duplicate-time floors;
- exact directed reachability failure for spatial kNN;
- reusable `NetworkTimeSelectionCache`;
- cached event-event network distances;
- cached signed event-event and support-event time offsets;
- cached event-lixel distances for simple propagation;
- maximum-candidate path traces for discontinuous and continuous propagation;
- weighted network-time LOO likelihood;
- arixel-measured network-time LSCV;
- deterministic joint and separate candidate experiments;
- immutable `NetworkTimeBandwidthSelectionResult`;
- adaptive simple, discontinuous, and continuous `TemporalNetworkKDE`;
- source-specific normalized cyclic temporal images;
- adaptive bandwidth metadata and xarray-safe summaries;
- executable example, factorization benchmark, API docs, estimator guide, and
  detailed recovery handoff.

## Numerical rules that must not change accidentally

1. Network matrices are `source_event × target`.
2. Temporal support matrices are `target_time × source_event`.
3. Event-specific spatial and temporal bandwidths belong to source events.
4. kNN and LOO exclude only the event's own diagonal index.
5. Other colocated events and duplicate times remain valid observations.
6. Network-time LSCV integrates actual lixel length × temporal-cell width.
7. Joint candidate ties use the first row-major minimum.
8. Separate mode selects marginal spatial and temporal minima and reports the
   product score at that pair.
9. Path policies reuse traces at the maximum spatial candidate.
10. No event-by-arixel distance cube may be introduced.

## Next recommended development unit

Build **0.0.14 persistent workspaces and precomputed assets**:

1. versioned `WorkspaceManifest`;
2. portable schemas for networks, snapped events, lixels, arixels, provenance,
   and sparse distances;
3. safe local directory/archive backend;
4. checksums, schema-version guards, and atomic writes;
5. `NetworkWorkspace.save/load`;
6. `NetworkTimeWorkspace.save/load`;
7. exact sparse-asset round trips;
8. fingerprint, CRS, unit, time-domain, and directed-mode validation;
9. corruption and cross-process reuse tests;
10. size/reload benchmark;
11. `HANDOFF_0.0.14_WORKSPACE_PERSISTENCE.md`.

Do not fold exposure risk, PostGIS, Zarr, distributed execution, or remote
storage into the portable local persistence foundation.

## Permanent process rule

Every completed development unit must create a detailed versioned root
Markdown handoff, add or update the corresponding `docs/development` page,
update this file, and record actual validation, CI, PR, and merge state. See
`docs/development/handoff-policy.md`.
