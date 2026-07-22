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

## Final observed validation

- pytest: 137 passed;
- branch coverage: 81.97%, above the required 80% minimum;
- public API/example coverage: 70 symbols mapped;
- Black, isort, Ruff, and mypy: passed;
- MkDocs strict build: passed;
- wheel, sdist, Twine metadata, and installed-wheel smoke tests: passed;
- Linux, Windows, and macOS passed with Python 3.11-3.14;
- deterministic grid-network benchmark completed successfully;
- final pull-request CI: run #74 (29902449039), conclusion success;
- temporary patch, source-export, formatter, and diagnostic workflows: removed;
- PR #6 squash merge commit: `eec1bbee65e6131c942f67adb8286e6a4a56af26`.

## Deliberate exclusions

- network Abramson pilot adaptation and balloon network bandwidths;
- heat-equation Gaussian network KDE;
- temporal and network-time data objects and estimators;
- spatial boundary correction and bandwidth matrices;
- relative risk, bootstrap uncertainty, and significance envelopes;
- persistent Zarr/PostGIS workspace serialization and compiled acceleration.
