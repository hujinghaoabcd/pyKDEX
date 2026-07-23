# Changelog

## 0.0.13 - 2026-07-23

- Add reusable `NetworkTimeSelectionCache` factorized over network and time.
- Add weighted network-time leave-one-out likelihood candidate experiments.
- Add arixel-measured network-time least-squares cross-validation.
- Add deterministic joint and separate scalar bandwidth selection.
- Add immutable `NetworkTimeBandwidths` with explicit source-event ownership.
- Add independent spatial and temporal `NetworkTimeKNNBandwidth`.
- Extend `TemporalNetworkKDE` and `NetworkTimeField` to event-specific bandwidths.
- Add duplicate, cyclic, path-policy, cache, benchmark, and recovery contracts.

## 0.0.12 - 2026-07-23

- Add immutable `NetworkTimeEvents` with stable accepted-event time alignment.
- Add measured `ArixelSupport` as lixel × temporal-cell support.
- Add reusable `NetworkTimeWorkspace` preparation and validation.
- Add factorized sparse network distances and signed temporal offsets.
- Add fixed-bandwidth separable `TemporalNetworkKDE`.
- Reuse simple, discontinuous, and continuous network junction semantics.
- Support linear and normalized cyclic temporal kernels.
- Add measured `NetworkTimeField` results with frame, geospatial, and xarray exports.
- Add analytical product, direction, chunking, cyclic, and mass tests.
- Add an executable example, API documentation, estimator guide, and detailed handoff.

## 0.0.11 - 2026-07-23

- Add explicit `LinearTimeDomain` and `CyclicTimeDomain` contracts.
- Add immutable temporal coordinates, space-time events, point support, and
  measured space-time grids with independent spatial and temporal units.
- Add reusable target-by-source spatial/temporal distance assets.
- Add separable `SpatiotemporalKDE` for density and intensity.
- Normalize cyclic kernels through periodic image summation.
- Add structured measured results with optional xarray export.
- Add deterministic joint and separate weighted LOO bandwidth experiments.
- Add a moving-hotspot generator, executable example, API docs, and detailed
  recovery handoff.

## 0.0.10 - 2026-07-23

- Add reusable `HeatComputePlan` generator and dense spectral assets.
- Add ordered multi-source, multi-time heat evolution with sparse Krylov fallback.
- Add `HeatNetworkExperiment` and immutable `HeatNetworkBatchResult`.
- Add weighted heat leave-one-out likelihood diffusion-time selection.
- Add exact finite-element heat least-squares cross-validation.
- Add fixed, likelihood-selected, and LSCV-selected heat-time strategies.
- Validate plan compatibility through network, event, support, and mesh fingerprints.
- Add a deterministic grid benchmark, executable example, API docs, and detailed handoff.

## 0.0.9 - 2026-07-23

- Add `HeatNetworkKDE` as a separate metric-graph heat-equation estimator.
- Add measured piecewise-linear finite elements with shared vertex degrees of freedom.
- Add reusable read-only `NetworkHeatOperator` sparse assets and fingerprints.
- Insert event offsets and lixel boundaries exactly in the heat discretization.
- Enforce Kirchhoff junction balance and natural Neumann terminal conditions.
- Return exactly integrated lixel cell averages with per-component mass checks.
- Add interval, ring, T-junction, disconnected-network, weighting, and failure tests.
- Add a runnable example, API documentation, estimator guide, and versioned handoff.

## 0.0.8 - 2026-07-23

- Add polygon boundary renormalization with analytical rectangular Gaussian mass and deterministic measured-cell quadrature.
- Add explicit one-generation reflection correction for axis-aligned rectangular boundaries.
- Add global symmetric positive-definite `BandwidthMatrix` anisotropic kernels.
- Add query-centred `BalloonKNNBandwidth` and support-bandwidth result metadata.
- Enforce boundary CRS, units, event containment, support containment, and atomic failure contracts.
- Add analytical equivalence, multivariate-normal, mass, orientation, and restriction tests.
- Add examples, API documentation, guides, and a versioned recovery handoff.

## 0.0.7 - Unreleased

- Add exact reusable event-to-event network-distance assets.
- Add source-centred `NetworkKNNBandwidth` with duplicate-location floors.
- Add weighted network leave-one-out likelihood bandwidth selection.
- Add lixel-integrated network least-squares cross-validation.
- Add reusable `NetworkSelectionCache` distances and propagation traces.
- Allow scalar or event-specific bandwidths in `NetworkKDE` and `NetworkField`.
- Add network bandwidth examples, API documentation, benchmarks, and recovery handoffs.

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
