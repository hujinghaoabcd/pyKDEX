# pyKDEX handoff

## Current status

- development version: `0.0.4`;
- public estimator: `SpatialKDE`;
- scalar bandwidths: fixed, likelihood CV, and Gaussian LSCV;
- event-specific bandwidths: kNN and Abramson;
- structured spatial data, measured grid support, boundaries, provenance, and datasets;
- canonical `LinearNetwork` with directed and parallel edges;
- GeoDataFrame, NetworkX, and OSMnx conversion;
- auditable event snapping, measured lixels, and reusable `NetworkWorkspace`;
- tests: 95 passed;
- branch coverage: 81.0%;
- formatting, linting, typing, documentation, build, and installation checks pass;
- no runtime dependency on external KDE implementations.

## Next recommended development unit

Build the numerical network-distance and traversal contract before publishing
`NetworkKDE`:

1. explicit network-location objects for events and lixel centres;
2. exact event-to-support network distance including along-edge offsets;
3. directed and undirected truncated shortest-path search;
4. reusable sparse distance/neighbourhood assets in `NetworkWorkspace`;
5. traversal states that preserve parallel-edge and branch information;
6. independent single-line, T-junction, ring, and directed reference fixtures;
7. memory and cutoff tests for sparse network neighbourhood queries.

Only after these contracts pass should simple, discontinuous, and continuous
junction policies and a `NetworkField` result enter the public API.
