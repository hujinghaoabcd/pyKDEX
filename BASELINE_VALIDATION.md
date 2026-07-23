# pyKDEX 0.0.11 validation

Validation date: 2026-07-23

## Implemented public functionality

- scalar, cross-validated, sample-point kNN, Abramson, matrix, and balloon
  spatial bandwidths;
- polygon boundary validation, renormalization, and rectangular reflection;
- explicit linear and cyclic time domains;
- immutable temporal coordinates, ordinary space-time events, point support,
  and measured space-time grids;
- reusable spatial-distance and signed-temporal-offset assets;
- separable product-kernel `SpatiotemporalKDE`;
- cyclic kernel normalization by periodic image summation;
- deterministic joint and separate weighted LOO bandwidth experiments;
- optional xarray-compatible time/y/x results;
- fixed/adaptive traversal `NetworkKDE` with three junction policies;
- measured finite-element `HeatNetworkKDE`, reusable plans, batch experiments,
  and heat-time selection;
- structured provenance, support measures, snapping, and fingerprints.

## Spatiotemporal data validation

- spatial and temporal observations must have equal lengths;
- temporal units are mandatory and independent from spatial units;
- datetime conversion requires a timezone for naive values;
- cyclic coordinates canonicalize to one explicit period;
- cyclic grids cover exactly one full period;
- remainder spatial and temporal cells retain their actual measure;
- distance assets retain both signed offsets and domain distances;
- CRS, spatial unit, temporal unit, domain, origin, timezone, source, and target
  fingerprints are validated before asset reuse;
- public arrays and measures are owned and read-only.

## Spatiotemporal numerical validation

- product Gaussian values match analytical normalization;
- density and intensity differ exactly by total event weight;
- chunked, unchunked, and precomputed-asset evaluation agree;
- cyclic values are periodic across the period boundary;
- cyclic Gaussian evaluation includes periodic images, not only minimum
  circular distance;
- a full-period cyclic density integrates to one on measured support within
  deterministic quadrature tolerance;
- unmeasured results reject `integral()`;
- grid values reshape to time/y/x;
- optional xarray export preserves named time/y/x axes;
- failed refits clear fitted state atomically.

## Bandwidth-experiment validation

- joint mode evaluates the complete ordered Cartesian candidate grid;
- separate mode selects marginal spatial and temporal objectives independently;
- the selected separate pair reports its product-kernel joint score;
- weighted LOO removes only the observation's own diagonal contribution;
- distance assets are reused and fingerprinted;
- repeated runs are deterministic;
- invalid, duplicate, empty, or nonpositive candidates are rejected;
- selection requires at least two events.

## Existing numerical validation retained

- scalar and matrix spatial bandwidth equivalence;
- SciPy multivariate-normal agreement for anisotropic Gaussian KDE;
- analytical and measured boundary correction behavior;
- exact event/lixel network distances and propagation contracts;
- simple, discontinuous, and continuous `NetworkKDE` references;
- finite-interval Neumann and periodic-ring heat references;
- Kirchhoff/Neumann heat conditions and per-component mass conservation;
- heat likelihood and exact finite-element heat LSCV;
- reusable heat plans and multi-time batch invariance.

## Final observed local validation

- pytest: `200 passed`;
- branch coverage: `81.41%`, above required `80%`;
- public API/example map: `105 public symbols`;
- executable examples: `13`;
- Black, isort, Ruff, mypy, and strict MkDocs: passed;
- wheel and sdist build, Twine, and archive-content verification: passed;
- isolated wheel installation and ordinary/spatiotemporal smoke: passed.

## GitHub state

- PR: pending;
- final clean CI: pending;
- merge commit: pending.

These fields must be replaced after the feature branch is published, verified,
and merged.

## Deliberate exclusions

- adaptive or balloon space-time bandwidths;
- nonseparable, causal, and advection-aware temporal kernels;
- spatiotemporal boundaries, exposure, risk, and uncertainty;
- persistent distance assets and distributed xarray execution;
- network-time events, arixels, `NetworkTimeWorkspace`, and TNKDE;
- directed network-time propagation;
- PostGIS/Zarr persistence and compiled acceleration.
