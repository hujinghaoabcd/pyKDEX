# pyKDEX 0.0.1 baseline validation

Validation date: 2026-07-21

## Implemented public baseline

- `SpatialKDE`
- `SpatialKDEResult`
- `FixedBandwidth`
- `EuclideanMetric`
- Gaussian, Epanechnikov, quartic, triangular, uniform, and exponential kernels
- density and intensity targets
- scalar and event-specific bandwidth evaluation paths
- pandas and GeoPandas result export

## Numerical validation

- all six radial kernels numerically integrate to one in dimensions 1, 2, and 3;
- a one-event Gaussian estimate matches its closed-form analytical value;
- spatial density numerically integrates to one;
- weighted spatial intensity numerically integrates to the total event weight;
- density is invariant to a common multiplicative rescaling of event weights;
- chunked and unchunked evaluation produce identical estimates.

## State and API validation

- fit inputs are copied and cannot be mutated externally after fitting;
- a failed refit atomically clears all previous fitted state;
- DataFrame coordinate schemas are recorded and support-column order is checked;
- estimators expose no public backend or device parameter;
- results export to DataFrame and planar GeoDataFrame;
- every top-level public symbol is mapped to a runnable example.

## Quality gates

- pytest: 42 passed;
- branch coverage: 87.3%, threshold 80%;
- Black: passed;
- isort: passed;
- Ruff: passed;
- mypy: passed for the full `src/pykdex` tree;
- MkDocs strict build: passed;
- wheel and sdist build: passed;
- Twine metadata check: passed;
- distribution-content verification: passed;
- installed-wheel smoke test outside the source tree: passed.

## Deliberate exclusions

The following are not yet exposed as working models:

- automatic and adaptive bandwidth selectors;
- spatiotemporal KDE;
- cyclic temporal kernels;
- network topology, snapping, lixels, and arixels;
- simple, discontinuous, continuous, and heat-kernel NKDE;
- temporal network KDE;
- relative-risk, uncertainty, and separability estimators.

These features will be added only with independent mathematical validation and
without runtime calls to external reference packages.
