# pyKDEX 0.0.4 validation

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
- deterministic analytical network datasets and grid-network generators.

## Network validation

- directed edge orientation is retained;
- parallel OSM-style edges remain distinct while sparse adjacency uses minimum cost;
- geographic OSMnx graphs are rejected by default until projected;
- disconnected components, self-loops, endpoint mismatches, and parallel edges are reported;
- event offsets and network fingerprints are checked;
- equal-distance snapping ties are deterministic and auditable;
- events beyond a maximum distance are returned as rejected records;
- lixel measures exactly cover total network length, including remainder segments;
- workspace fingerprints are deterministic for identical prepared inputs.

## Engineering validation

- pytest: 95 passed;
- branch coverage: 81.0%, threshold 80%;
- Black, isort, Ruff, and mypy: passed;
- MkDocs strict build: passed;
- public API/example coverage: complete;
- wheel and sdist build and Twine metadata checks: passed;
- installed-wheel smoke test: passed.

## Deliberate exclusions

- event-to-lixel shortest-path distance assets;
- junction traversal and mass-allocation policies;
- simple, discontinuous, continuous, and heat-kernel NKDE;
- temporal and network-time data objects and estimators;
- boundary correction, bandwidth matrices, relative risk, and uncertainty.
