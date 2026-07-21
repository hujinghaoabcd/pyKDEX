# pyKDEX 0.0.3 validation

Validation date: 2026-07-22

## Implemented public functionality

- fixed, cross-validated, kNN, and Abramson spatial KDE bandwidths;
- weighted density and event-intensity estimation;
- immutable `SpatialEvents`, `PointSupport`, and `GridSupport` objects;
- polygonal `SpatialBoundary` objects;
- structured `KDEDataset` bundles;
- validation reports with stable error and warning codes;
- provenance records and deterministic content fingerprints;
- CRS, spatial-unit, coordinate-schema, and support-measure propagation;
- deterministic bimodal and bounded-square datasets.

## Numerical and data validation

- every radial kernel integrates to one in dimensions 1, 2, and 3;
- one-event Gaussian estimates match closed-form values;
- fixed, kNN, and Abramson density estimates conserve unit mass;
- weighted intensity integrates to total event weight;
- measured `GridSupport` results expose `integral()` and `to_grid()`;
- remainder grid cells preserve the exact requested bounding-box area;
- structured event weights are used without ambiguous duplication;
- CRS, coordinate-unit, dimension, identifier, duplicate, and boundary checks
  are tested;
- synthetic datasets and fingerprints are deterministic for a fixed random seed.

## Engineering validation

- pytest: 75 passed;
- branch coverage: 81.0%, threshold 80%;
- Black, isort, Ruff, and mypy: passed;
- MkDocs strict build: passed;
- public API/example coverage: complete;
- wheel and sdist build and Twine metadata check: passed;
- installed-wheel smoke test: passed;
- failed refits atomically clear all previous fitted state.

## Deliberate exclusions

The following remain future work:

- linear-network topology, snapping, lixels, and workspaces;
- NetworkX and OSMnx adapters;
- simple, discontinuous, continuous, and heat-kernel NKDE;
- boundary correction and bandwidth matrices;
- balloon adaptive bandwidths;
- spatiotemporal and cyclic temporal KDE;
- temporal network KDE;
- relative-risk, uncertainty, and separability estimators.
