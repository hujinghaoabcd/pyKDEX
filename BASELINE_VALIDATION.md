# pyKDEX 0.0.8 validation

Validation date: 2026-07-23

## Implemented public functionality

- scalar, cross-validated, sample-point kNN, and Abramson spatial bandwidths;
- global positive-definite bandwidth matrices;
- query-centred balloon kNN bandwidths;
- polygon study-domain validation;
- rectangular analytical Gaussian boundary renormalization;
- deterministic measured-cell Polygon/MultiPolygon renormalization;
- one-generation axis-aligned rectangular reflection correction;
- public `SpatialKDE` and fixed/adaptive `NetworkKDE` estimators;
- structured spatial/network data, support measures, provenance, snapping, distance assets,
  network policies, network CV, and network kNN bandwidths from 0.0.1-0.0.7.

## Spatial numerical validation

- scalar `h` and matrix `H = h**2 I` agree numerically;
- full covariance Gaussian KDE agrees with SciPy multivariate-normal density;
- anisotropic matrices produce the expected directional decay;
- bandwidth matrices reject non-square, non-finite, asymmetric, and non-positive-definite input;
- balloon kNN uses the k-th fitted-event distance at every support row;
- balloon duplicate/coincident zero bandwidth requires an explicit positive floor;
- rectangular Gaussian renormalization restores in-domain measured mass near one;
- general polygon quadrature is deterministic and uses exact clipped-cell area measures;
- reflection increases near-boundary density and approximately preserves mass at small bandwidth;
- unsupported reflection geometry/covariance combinations fail explicitly;
- boundary CRS, units, event coverage, and support coverage are enforced;
- failed fits atomically clear fitted state.

## Final observed validation

- pytest: `145 passed`;
- branch coverage: `81.41%`, above the required `80%` minimum;
- public API/example map: `77 symbols mapped to executable examples`;
- Black, isort, Ruff, and mypy: passed;
- strict MkDocs build: passed;
- wheel, sdist, Twine metadata, distribution-content, and installed-wheel smoke checks: passed;
- Linux, Windows, and macOS passed on Python 3.11-3.14;
- final clean pull-request CI: run `#104` (`29974693141`), conclusion `success`;
- temporary transfer, apply, export, formatter, Ruff-fix, and finalizer infrastructure: removed;
- existing 0.0.1-0.0.7 regression suite: passed;
- PR #7 squash merge commit: `9f0aef9e8be57cc9e1c6beb210225b421501a623`.

## Deliberate exclusions

- balloon boundary correction;
- event-specific full matrices and plug-in matrix selectors;
- infinite-series or irregular-polygon reflection;
- heat-equation Gaussian NetworkKDE;
- spatiotemporal and network-time KDE;
- relative risk, bootstrap uncertainty, persistent workspace serialization, and compiled acceleration.
