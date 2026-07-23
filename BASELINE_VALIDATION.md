# pyKDEX 0.0.12 validation

Validation date: 2026-07-23

## Implemented public functionality

- scalar, cross-validated, sample-point kNN, Abramson, matrix, and balloon
  spatial bandwidths;
- polygon boundary validation, renormalization, and rectangular reflection;
- explicit linear and cyclic time domains;
- ordinary space-time events, measured space-time grids, product KDE, and
  joint/separate bandwidth experiments;
- canonical linear networks, auditable snapping, measured lixels, exact
  distances, traversal, and three junction policies;
- fixed/adaptive traversal `NetworkKDE`;
- measured finite-element `HeatNetworkKDE`, reusable plans, batch experiments,
  and heat-time selection;
- network-time events, measured arixels, factorized assets, reusable
  workspaces, and fixed product `TemporalNetworkKDE`;
- structured provenance, units, support measures, identifiers, and
  fingerprints.

## Network-time data validation

- raw spatial events and times must have equal lengths;
- accepted event times are aligned after snapping by stable event ID;
- rejected event records remain in the snap report;
- accepted network events and temporal coordinates remain distinct immutable
  components;
- temporal units are mandatory and independent from spatial units;
- arixel support uses actual lixel length × actual temporal-cell width;
- spatial and temporal remainder cells retain actual measure;
- cyclic arixels cover exactly one complete period from the domain origin;
- flat arixel order is time-major and reshapes to `time × lixel`;
- event, lixel, workspace, time-domain, unit, origin, timezone, and directed
  fingerprints are checked before distance-asset reuse;
- public arrays and measures are owned and read-only.

## Network-time numerical validation

- the exact zero-distance Epanechnikov × Gaussian product is recovered;
- one-time discontinuous and continuous slices equal the corresponding
  `NetworkKDE` field times the temporal factor;
- density and intensity differ exactly by total event weight;
- time-chunked and unchunked evaluation agree;
- a compatible sparse network-time asset is reused;
- cyclic values agree across the period boundary;
- full-period cyclic continuous density integrates to one within deterministic
  quadrature tolerance;
- directed simple propagation is zero on upstream lixels;
- path policies reject infinite-support spatial kernels;
- failed fits clear state atomically;
- optional xarray export preserves `time` and `lixel` axes.

## Existing numerical validation retained

- scalar and matrix spatial bandwidth equivalence;
- SciPy multivariate-normal agreement for anisotropic Gaussian KDE;
- analytical and measured boundary correction behavior;
- ordinary space-time product values, cyclic periodic images, mass, chunking,
  and bandwidth experiments;
- exact event/lixel network distances and propagation contracts;
- simple, discontinuous, and continuous `NetworkKDE` references;
- finite-interval Neumann and periodic-ring heat references;
- Kirchhoff/Neumann heat conditions and per-component mass conservation;
- heat likelihood and exact finite-element heat LSCV;
- reusable heat plans and multi-time batch invariance.

## Final observed local validation

- focused network-time tests: `17 passed`;
- final full regression: `217 passed`;
- branch coverage: `81.14%`, above required `80%`;
- public API/example map: `112 public symbols`;
- executable examples: all `14` passed;
- Black, isort, Ruff, mypy, and strict MkDocs: passed;
- wheel and sdist build, Twine, archive verification, and isolated wheel
  installation smoke: passed.

## GitHub state

- PR: `#12 Add network-time KDE foundation`;
- feature implementation commit:
  `3f3a752202b4a2ff91939a01513d67713074c5e9`;
- first complete PR CI run `#128` (`30011519807`): success across quality,
  coverage, distributions, Linux/Windows/macOS, and Python 3.11-3.14;
- final clean PR CI run `#129` (`30011753378`): success;
- PR #12 squash merge commit:
  `f9b9d7e3949ee8688b8829a6b8760f1f3214cd4a`;
- post-merge handoff commit:
  `3cda2582e702963b34bd84f66eb79db84c500429`;
- post-merge `main` CI run `#131` (`30012065149`): success.

PR #12 was merged and closed successfully.

## Deliberate exclusions

- network-time bandwidth selection and adaptive bandwidths;
- heat-equation network-time diffusion;
- nonseparable, causal, and advection-aware temporal kernels;
- time-dependent network topology or cost;
- exposure, relative risk, uncertainty, and separability tests;
- persistent workspaces and distance assets;
- PostGIS/Zarr storage, distributed execution, and compiled acceleration.
