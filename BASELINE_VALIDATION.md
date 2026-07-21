# pyKDEX 0.0.6 validation

Validation date: 2026-07-22

## Implemented public functionality

- fixed, cross-validated, kNN, and Abramson spatial KDE bandwidths;
- public `SpatialKDE` and fixed-bandwidth `NetworkKDE` estimators;
- weighted density and event-intensity targets;
- structured events, measured supports, boundaries, datasets, and provenance;
- canonical geometric `LinearNetwork` objects with directed and parallel edges;
- GeoDataFrame, NetworkX, and OSMnx adapters;
- auditable event snapping and measured lixel partitions;
- exact directed and undirected network-distance assets;
- simple geodesic, discontinuous equal-split, and continuous equal-split junction policies;
- immutable signed propagation records and traces;
- measured `NetworkField` integration and tabular/geospatial exports.

## NetworkKDE validation

- the simple policy matches the one-dimensional kernel value at zero network distance;
- discontinuous propagation divides amplitude equally among valid forward branches;
- continuous propagation applies transmission coefficient `2/d` and reflection coefficient `2/d - 1`;
- limiting estimates agree across incident edges at a T-junction;
- terminal vertices provide reflecting boundaries for continuous propagation;
- lixel-length integration recovers unit density mass within midpoint-rule tolerance;
- weighted intensity equals total event weight times the corresponding weighted density;
- accepted snapped-event weights, network fingerprints, and lixel measures are retained;
- continuous propagation rejects directed metric networks explicitly;
- recursive path policies reject infinite-support kernels explicitly;
- simple geodesic estimation accepts Gaussian kernels;
- propagation record limits fail explicitly rather than silently truncating cyclic walks;
- failed fits atomically reset all fitted estimator state.

## Engineering validation

- pytest: 118 passed;
- branch-coverage gate: passed at the required 80% minimum;
- Black, isort, Ruff, and mypy: passed;
- MkDocs strict build: passed;
- public API/example coverage: complete;
- wheel and sdist build and Twine metadata checks: passed;
- installed-wheel smoke test: passed;
- GitHub Actions: passed on Linux, Windows, and macOS with Python 3.11-3.14.

## Deliberate exclusions

- network bandwidth selection and adaptive network bandwidths;
- heat-equation Gaussian network KDE;
- temporal and network-time data objects and estimators;
- spatial boundary correction, bandwidth matrices, relative risk, and uncertainty.
