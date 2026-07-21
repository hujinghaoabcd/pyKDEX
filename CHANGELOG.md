# Changelog

## 0.0.6 - Unreleased

- Add public fixed-bandwidth `NetworkKDE` for network density and intensity.
- Add simple geodesic, discontinuous equal-split, and continuous equal-split junction policies.
- Add signed immutable propagation records and traces.
- Add measured `NetworkField` integration and DataFrame/GeoDataFrame exports.
- Enforce explicit directed-network and compact-kernel policy constraints.
- Add analytical branch allocation, continuity, mass, weighting, and state-safety tests.

## 0.0.5

- Add immutable `NetworkLocations` for arbitrary along-edge positions.
- Add exact directed and undirected network-distance assets.
- Support same-edge travel, endpoint offsets, disconnected components, and edge costs.
- Add sparse cutoff neighbourhoods that preserve reachable zero-distance pairs.
- Add explicit truncated traversal states with parallel-edge and partial-edge retention.
- Integrate reusable event-to-lixel distances with `NetworkWorkspace`.
- Add analytical distance, direction, ring, cutoff, traversal, and compatibility tests.

## 0.0.4

- Add canonical `LinearNetwork` geometry and topology objects.
- Preserve directed and parallel edges from NetworkX and OSMnx graphs.
- Add projected-OSM validation and optional OSM place downloads.
- Add auditable `NetworkEvents` snapping with accepted and rejected records.
- Add measured `LixelSupport` partitions and `NetworkWorkspace` preparation.
- Add T-junction, cross, ring, disconnected, OSMnx-like, and grid datasets.

## 0.0.3

- Add immutable `SpatialEvents`, `PointSupport`, and `GridSupport` objects.
- Add polygonal `SpatialBoundary` and structured `KDEDataset` bundles.
- Add validation reports, provenance records, and deterministic fingerprints.
- Integrate structured CRS, unit, identifier, and support-measure metadata with `SpatialKDE`.
- Add deterministic synthetic datasets for tutorials and boundary validation.

## 0.0.2

- Add weighted leave-one-out likelihood bandwidth selection.
- Add exact Gaussian least-squares cross-validation.
- Add k-nearest-neighbour event-specific bandwidths.
- Add Abramson sample-point adaptive bandwidths.
- Add immutable bandwidth-selection traces and estimator integration.

## 0.0.1

- Establish the pyGWRx-aligned engineering baseline.
- Add composition-oriented kernel, bandwidth, and metric protocols.
- Add fixed-bandwidth `SpatialKDE` for density and intensity estimation.
- Add structured `SpatialKDEResult` exports.
- Add numerical, state-safety, API, example, and build tests.
