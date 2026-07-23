# pyKDEX current handoff

The latest completed local development unit is **0.0.11 ordinary
spatiotemporal foundation**. Read
`HANDOFF_0.0.11_SPATIOTEMPORAL_FOUNDATION.md` first for the complete design,
mathematics, implementation, validation, limitations, recovery procedure, and
next-unit record.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- default branch: `main`;
- development branch: `agent/spatiotemporal-foundation`;
- version prepared: `0.0.11`;
- stable merged version before publication: `0.0.10`;
- pull request: pending;
- feature commit: pending;
- final clean CI: pending;
- merge commit: pending;
- observed local validation: `200 passed`, branch coverage `81.41%`;
- public API/example map: `105 public symbols`, all `13` examples executable;
- Black, isort, Ruff, mypy, strict docs, distributions, and archive checks:
  passed;
- isolated wheel ordinary/spatiotemporal smoke: passed;
- no temporary repository workflow was added.

## Implemented in 0.0.11

- explicit `LinearTimeDomain` and `CyclicTimeDomain`;
- immutable temporal coordinates and weighted space-time events;
- point support and measured space-time grids;
- independent spatial and temporal units, origins, timezones, and fingerprints;
- reusable spatial-distance/signed-temporal-offset assets;
- separable density/intensity `SpatiotemporalKDE`;
- normalized periodic image sums on cyclic time;
- structured results with measured integration, grid reshape, and optional
  xarray export;
- joint and separate weighted LOO bandwidth experiments;
- deterministic moving-hotspot generator;
- full example, API, estimator, validation, and recovery documentation.

## Next recommended development unit

Build the network-time foundation:

1. `NetworkTimeEvents`;
2. measured lixel-by-time `ArixelSupport`;
3. `NetworkTimeWorkspace`;
4. reusable network-distance/temporal-offset assets;
5. fixed product `TemporalNetworkKDE`;
6. linear/cyclic time, junction, direction, mass, weight, and chunk references;
7. xarray-compatible time/lixel output;
8. `HANDOFF_0.0.12_NETWORK_TIME_FOUNDATION.md`.

Do not fold heat-equation network-time smoothing, adaptive TNKDE, persistence,
or exposure-adjusted risk into this first network-time unit.

## Permanent process rule

Every completed development unit must create a detailed versioned root Markdown
handoff, add/update the corresponding `docs/development` page, update this file,
and record actual validation, CI, PR, and merge state. See
`docs/development/handoff-policy.md`.
