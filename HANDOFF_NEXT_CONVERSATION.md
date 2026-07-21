# pyKDEX handoff

## Current status

- development version: `0.0.5`;
- public estimator: `SpatialKDE`;
- scalar bandwidths: fixed, likelihood CV, and Gaussian LSCV;
- event-specific bandwidths: kNN and Abramson;
- structured spatial data, measured support, boundaries, provenance, and datasets;
- canonical `LinearNetwork` with directed and parallel edges;
- GeoDataFrame, NetworkX, and OSMnx conversion;
- auditable event snapping, measured lixels, and reusable `NetworkWorkspace`;
- arbitrary along-edge `NetworkLocations`;
- exact directed and undirected event-to-support distances;
- sparse cutoff neighbourhood assets preserving zero-distance pairs;
- explicit truncated traversal states retaining parallel and partial edges;
- tests: 106 passed;
- branch-coverage gate: passed at the required 80% minimum;
- formatting, linting, typing, documentation, build, and installation checks pass;
- Linux, Windows, and macOS CI passes on Python 3.11-3.14;
- no runtime dependency on external KDE implementations.

## Next recommended development unit

Implement junction propagation and the first public network-density result without
mixing topology policy into the radial kernel implementation:

1. define a `JunctionPolicy` protocol and immutable propagation records;
2. implement the simple shortest-path policy as an explicit baseline;
3. implement discontinuous equal-split propagation with mass accounting;
4. implement continuous propagation with node-continuity tests;
5. add a measured `NetworkField` result with `integral()`, `to_frame()`, and
   `to_geodataframe()`;
6. implement fixed-bandwidth `NetworkKDE` for density and intensity targets;
7. validate single-line analytical values, T-junction allocation, continuity,
   lixel mass integration, weighted intensity, disconnected components, and
   directed networks;
8. compare independent fixtures against published NKDE definitions without
   runtime calls to external packages.

Heat-equation NKDE, adaptive network bandwidths, and temporal-network KDE should
remain separate later development units.
