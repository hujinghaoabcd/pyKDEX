# pyKDEX 0.0.9 validation

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
- public finite-element `HeatNetworkKDE` for undirected metric graphs;
- reusable sparse `NetworkHeatOperator` assets;
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

## Heat-network numerical validation

- finite-interval lixel averages agree with the analytical Neumann heat kernel;
- square-ring lixel averages agree with the analytical periodic heat kernel;
- shared junction degrees of freedom enforce exact vertex continuity;
- the weak form supplies Kirchhoff junction balance and Neumann terminals;
- accepted event offsets are inserted exactly in the heat mesh;
- near-duplicate floating breakpoints are coalesced before element assembly;
- density and intensity conserve mass independently in each connected component;
- empty disconnected components remain exactly zero;
- heat outputs are exact piecewise-linear lixel cell averages;
- directed networks and unsupported self-loop records fail explicitly;
- failed fits atomically clear all heat-estimator state.

## Final observed validation

- pytest: `161 passed` in the latest development run;
- branch coverage: `81.76%`, above the required `80%` minimum;
- public API/example map: `80 symbols mapped to executable examples`;
- Black, isort, Ruff, mypy, strict MkDocs, all examples, distributions, and
  isolated installed-wheel checks: passed;
- PR #9 GitHub Actions run `#113` (`29979483652`): success across quality,
  coverage, distributions, Linux/Windows/macOS, and Python 3.11-3.14;
- final clean metadata CI and squash merge commit: pending;
- existing 0.0.1-0.0.8 regression suite: passed.

## Deliberate exclusions

- balloon boundary correction;
- event-specific full matrices and plug-in matrix selectors;
- infinite-series or irregular-polygon reflection;
- directed heat flow, self-loop heat elements, variable diffusivity, and
  alternative terminal boundary conditions;
- heat-time selection, batched heat evaluation, and reusable decompositions;
- spatiotemporal and network-time KDE;
- relative risk, bootstrap uncertainty, persistent workspace serialization, and compiled acceleration.
