# pyKDEX 0.0.2 validation

Validation date: 2026-07-22

## Implemented public functionality

- fixed-bandwidth spatial density and intensity estimation;
- six normalized radial kernels in arbitrary Euclidean dimension;
- weighted leave-one-out likelihood bandwidth selection;
- exact weighted Gaussian least-squares cross-validation;
- k-nearest-neighbour sample-point bandwidths;
- Abramson sample-point adaptive bandwidths;
- immutable bandwidth-selection traces;
- pandas and GeoPandas result export.

## Numerical validation

- every radial kernel integrates to one in dimensions 1, 2, and 3;
- one-event Gaussian estimates match their closed-form values;
- fixed, kNN, and Abramson density estimates numerically conserve unit mass;
- weighted intensity integrates to the total event weight;
- likelihood CV matches a hand-calculated two-event Gaussian value;
- Gaussian LSCV matches direct high-resolution numerical integration;
- weighted selectors, duplicate-location handling, optimizer traces, and
  deterministic repeated selection are tested.

## Engineering validation

- pytest: 57 passed;
- branch coverage: 84.1%, threshold 80%;
- Black, isort, Ruff, and mypy: passed;
- MkDocs strict build: passed;
- public API/example coverage: complete;
- wheel and sdist build and Twine metadata check: passed;
- installed-wheel smoke test: passed;
- failed refits atomically clear all previous fitted state.

## Deliberate exclusions

The following remain future work:

- boundary correction and bandwidth matrices;
- balloon adaptive bandwidths;
- spatiotemporal and cyclic temporal KDE;
- network topology, snapping, lixels, and arixels;
- simple, discontinuous, continuous, and heat-kernel NKDE;
- temporal network KDE;
- relative-risk, uncertainty, and separability estimators.
