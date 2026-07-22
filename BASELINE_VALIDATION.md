# pyKDEX 0.0.7 validation

Validation date: 2026-07-22

## Implemented public functionality

- fixed, cross-validated, kNN, and Abramson spatial KDE bandwidths;
- public `SpatialKDE` and `NetworkKDE` estimators;
- weighted density and event-intensity targets;
- structured events, measured supports, boundaries, datasets, and provenance;
- canonical geometric `LinearNetwork` objects with directed and parallel edges;
- GeoDataFrame, NetworkX, and OSMnx adapters;
- auditable event snapping and measured lixel partitions;
- exact directed and undirected event-to-lixel and event-to-event distance assets;
- simple geodesic, discontinuous equal-split, and continuous equal-split policies;
- scalar network likelihood CV and lixel-integrated network LSCV;
- source-centred event-specific network kNN bandwidths;
- reusable network selection distances and upper-bound propagation traces;
- scalar or adaptive `NetworkField` results with measured integration and exports.

## Network bandwidth validation

- event self-pairs remain explicit zero distances;
- coincident but distinct events remain off-diagonal zero-distance neighbours;
- source-event exclusion in LOO uses index rather than zero-distance filtering;
- weighted LOO denominators use total weight minus the target event weight;
- directed event-distance assets retain asymmetric reachability;
- network kNN reports unavailable neighbour ranks instead of using infinite values;
- duplicate locations require an explicit positive bandwidth floor;
- sample-point bandwidths use each source event's own scaling and normalization;
- network LSCV integrates squared density with each lixel's actual length;
- simple-policy objectives reuse distance assets;
- path-policy objectives reuse traces prepared at the upper search bound;
- selector wrappers retain complete deterministic optimization traces;
- failed adaptive or selection fits atomically reset estimator state.

## Current observed local validation

- pytest: 129 passed;
- branch coverage: 80.5%, above the required 80% minimum;
- public API/example coverage: 70 symbols mapped;
- source, tests, and examples compile successfully;
- deterministic grid-network benchmark completed successfully.

## Required final release checks

The following must be copied here after the final clean pull-request CI:

- Black, isort, Ruff, and mypy;
- MkDocs strict build;
- wheel and sdist build and Twine metadata checks;
- installed-wheel smoke test;
- Linux, Windows, and macOS with Python 3.11-3.14;
- final test and branch-coverage counts from GitHub Actions;
- removal of temporary source-export and diagnostic workflows;
- merge commit for PR #6.

## Deliberate exclusions

- network Abramson pilot adaptation and balloon network bandwidths;
- heat-equation Gaussian network KDE;
- temporal and network-time data objects and estimators;
- spatial boundary correction and bandwidth matrices;
- relative risk, bootstrap uncertainty, and significance envelopes;
- persistent Zarr/PostGIS workspace serialization and compiled acceleration.
