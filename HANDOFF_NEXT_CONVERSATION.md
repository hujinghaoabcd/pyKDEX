# pyKDEX handoff

## Current status

- development version: `0.0.3`;
- public estimator: `SpatialKDE`;
- scalar bandwidths: fixed, likelihood CV, and Gaussian LSCV;
- event-specific bandwidths: kNN and Abramson;
- structured data: events, point support, measured grid support, boundaries,
  datasets, validation reports, provenance, and fingerprints;
- tests: 75 passed;
- branch coverage: 81.0%;
- formatting, linting, typing, strict documentation, build, and installation
  checks pass locally;
- no runtime dependency on external KDE implementations.

## Next recommended development unit

Build the road-network data foundation before exposing any network estimator:

1. `LinearNetwork` with stable node and edge tables;
2. GeoDataFrame, NetworkX, and OSMnx adapters;
3. topology validation, connected components, and directed parallel edges;
4. `NetworkEvents` and auditable event snapping;
5. `LixelSupport` with exact segment measures;
6. `NetworkWorkspace` and reusable distance/topology fingerprints;
7. T-junction, cross, ring, disconnected, and OSMnx-derived fixtures.

Do not expose `NetworkKDE` until network-distance, junction, mass-conservation,
and lixel integration contracts are implemented and tested.
