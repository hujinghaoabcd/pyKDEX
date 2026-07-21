# pyKDEX 0.0.5 validation

Validation date: 2026-07-22

## Implemented public functionality

- fixed, cross-validated, kNN, and Abramson spatial KDE bandwidths;
- weighted density and event-intensity estimation;
- structured events, measured supports, boundaries, datasets, and provenance;
- canonical geometric `LinearNetwork` objects;
- directed and undirected multigraph topology with stable IDs;
- GeoDataFrame, NetworkX, and OSMnx adapters;
- auditable event snapping with rejected-event records;
- measured lixel partitions and reusable `NetworkWorkspace` objects;
- immutable `NetworkLocations` for arbitrary along-edge positions;
- exact directed and undirected `NetworkDistanceAsset` objects;
- cutoff-based finite distance neighbourhoods;
- explicit truncated traversal states retaining parallel and partial edges.

## Network-distance validation

- direct same-edge distance is considered independently of endpoint routes;
- arbitrary event and lixel offsets are included in path length;
- directed routes obey edge orientation;
- undirected overrides permit reverse travel on directed source networks;
- geometric offsets are converted proportionally for custom edge costs;
- ring networks select the shorter valid route;
- disconnected pairs remain unreachable;
- finite cutoffs omit distant pairs without losing reachable zero distances;
- parallel edges remain separate traversal states;
- a cutoff inside an edge records the exact reached fraction;
- distance, location, network, and workspace fingerprints are validated;
- Python 3.11 dataclass compatibility is explicitly covered.

## Engineering validation

- pytest: 106 passed;
- branch-coverage gate: passed at the required 80% minimum;
- Black, isort, Ruff, and mypy: passed;
- MkDocs strict build: passed;
- public API/example coverage: complete;
- wheel and sdist build and Twine metadata checks: passed;
- installed-wheel smoke test: passed;
- GitHub Actions: passed on Linux, Windows, and macOS with Python 3.11-3.14.

## Deliberate exclusions

- simple, discontinuous, and continuous junction mass-allocation policies;
- `NetworkField` and public `NetworkKDE` estimators;
- heat-equation network KDE;
- temporal and network-time data objects and estimators;
- spatial boundary correction, bandwidth matrices, relative risk, and uncertainty.
