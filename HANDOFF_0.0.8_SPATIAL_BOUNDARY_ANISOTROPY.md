# pyKDEX 0.0.8 handoff: spatial boundary correction, anisotropy, and balloon bandwidths

## 1. Purpose

This document is the recoverable engineering record for the pyKDEX 0.0.8 development unit.
A new conversation must be able to continue the repository without relying on earlier chat
messages, temporary artifacts, or undocumented design assumptions.

- Repository: `hujinghaoabcd/pyKDEX`
- Development branch: `agent/spatial-boundary-anisotropy`
- Pull request: `#7 Add spatial boundary correction and anisotropic KDE`
- Version developed in this unit: `0.0.8`
- Last stable version before this unit: `0.0.7`

Final CI and squash-merge fields must be updated before this unit is considered complete.

## 2. Project architecture and permanent principles

pyKDEX is a composition-oriented framework for ordinary spatial, network, spatiotemporal,
and network-time kernel density estimation. The public estimator is assembled from explicit
components rather than a single monolithic algorithm:

`data + domain + metric + kernel + bandwidth + correction + measured support + estimator + result`.

The project continues to enforce the following principles:

1. Algorithms are implemented independently inside pyKDEX. External KDE packages are research
   references and validation comparators, not runtime dependencies or source-code donors.
2. OSMnx, NetworkX, GeoPandas, pandas, and NumPy are input ecosystems. They are adapted into
   pyKDEX-owned immutable data objects before numerical estimation.
3. Fitted inputs and returned arrays are copied and made read-only where exposed.
4. Failed `fit()` operations atomically reset the estimator to an unfitted state.
5. CRS, coordinate units, identifiers, study-domain membership, support measures, and content
   fingerprints are validated explicitly. Silent reprojection and silent point deletion are forbidden.
6. One NumPy/SciPy numerical route is public. Future acceleration remains hidden behind internal
   numerical helpers rather than appearing as user-facing backend/device switches.
7. Every public symbol must map to an executable example.
8. Every completed development unit creates a detailed versioned Markdown handoff and updates
   `HANDOFF_NEXT_CONVERSATION.md`.

## 3. Problem solved in 0.0.8

Before this unit, `SpatialKDE` supported scalar, selected, kNN sample-point, and Abramson
sample-point bandwidths, but it did not model a bounded study domain and could not represent
kernel orientation. The following scientific problems remained:

- kernel mass escaped polygonal study boundaries;
- near-edge estimates were systematically biased downward;
- isotropic scalar bandwidths could not represent directional spatial processes;
- the existing kNN strategy varied by source event only and did not provide query-centred
  balloon smoothing;
- result metadata could not distinguish event-specific and support-specific bandwidth vectors.

Version 0.0.8 resolves these issues without changing the numerical definitions of existing
0.0.1-0.0.7 estimators.

## 4. Public API added

### 4.1 Bandwidths

- `BandwidthMatrix`
- `BaseBalloonBandwidth`
- `BalloonKNNBandwidth`

### 4.2 Boundary corrections

- `BaseBoundaryCorrection`
- `NoBoundaryCorrection`
- `RenormalizationCorrection`
- `ReflectionCorrection`

### 4.3 SpatialKDE constructor additions

`SpatialKDE` now accepts:

- `boundary: SpatialBoundary | None`
- `boundary_correction: str | BaseBoundaryCorrection`
- scalar, event-specific, global matrix, or balloon bandwidth strategies.

The fitted metadata field `bandwidth_kind` is one of:

- `scalar`: one scalar source bandwidth;
- `event`: one sample-point bandwidth per source event;
- `matrix`: one global positive-definite matrix;
- `support`: one balloon bandwidth per evaluated support row.

## 5. Numerical definitions

### 5.1 Scalar and sample-point KDE

For source-event bandwidths `h_i`:

\[
\hat f(x)=\sum_i a_i h_i^{-d}K(\|x-x_i\|/h_i),
\]

where `a_i = w_i / sum(w)` for density and `a_i = w_i` for intensity.

This definition is unchanged from earlier versions.

### 5.2 Global bandwidth matrix

`BandwidthMatrix(H)` interprets `H` as the kernel covariance/shape matrix:

\[
K_H(x-x_i)=|H|^{-1/2}
K\left(\left\|H^{-1/2}(x-x_i)\right\|\right).
\]

Requirements:

- `H` is square, finite, symmetric, and positive definite;
- matrix dimension equals event coordinate dimension;
- matrix bandwidths require the Euclidean metric because orientation is defined in coordinate
  space;
- scalar `h` is exactly equivalent to `H = h^2 I`.

The implementation uses a Cholesky factor and triangular linear solve. It does not form an
explicit matrix inverse.

### 5.3 Balloon kNN bandwidth

For support/query location `x`:

\[
h(x)=c\,d(x,x_{(k)}),
\]

where `x_(k)` is the k-th fitted event. No event is excluded because the ranking is between a
query location and the fitted source set. This differs from `KNNBandwidth`, which excludes the
source event index and returns one bandwidth per source event.

The balloon estimator is:

\[
\hat f(x)=h(x)^{-d}\sum_i a_i K(\|x-x_i\|/h(x)).
\]

A positive `minimum_bandwidth` is required when a support location can coincide with an event
and the chosen rank would otherwise be zero.

### 5.4 Boundary renormalization

For study polygon `W`, source event `i`, and its kernel:

\[
c_i=\int_W K_{H_i}(u-x_i)\,du,
\qquad
K^{R}_{H_i}(x-x_i)=K_{H_i}(x-x_i)/c_i.
\]

Each corrected source kernel integrates to one over `W`, subject to numerical quadrature
accuracy.

Two integration routes are implemented:

1. **Analytical rectangular Gaussian route**
   - scalar and event-specific scalar bandwidths use products of univariate normal CDF differences;
   - diagonal matrices use axis-specific standard deviations;
   - full 2D matrices use multivariate-normal rectangle probabilities by corner inclusion-exclusion.
2. **Deterministic general-polygon route**
   - the Polygon/MultiPolygon bounding box is partitioned into a regular cell grid;
   - every cell is intersected with the actual study geometry;
   - the exact clipped-cell area is the quadrature measure;
   - the clipped geometry's representative point is the evaluation location;
   - holes and disconnected polygon components remain excluded/included according to geometry.

`RenormalizationCorrection(cells_per_axis=64)` controls quadrature resolution. The default is a
scientifically explicit accuracy/performance trade-off, not an adaptive hidden heuristic.

### 5.5 Reflection correction

`ReflectionCorrection` implements a one-generation rectangular reflection estimator. In two
dimensions every source event contributes:

- the original event;
- two x-axis side reflections;
- two y-axis side reflections;
- four corner reflections.

Therefore each source has nine image locations. Images retain the original source coefficient.

Restrictions are deliberate:

- only axis-aligned rectangular boundaries;
- only two-dimensional events;
- scalar, event-specific scalar, or diagonal matrix bandwidths;
- full matrices with cross-axis covariance are rejected because covariance orientation must also
  be reflected;
- this is a one-generation estimator, not an infinite reflected heat-kernel series.

Renormalization is the preferred method when per-source in-domain mass conservation is the
primary contract.

## 6. Boundary and metadata contracts

When `boundary` is provided:

- events must be two-dimensional;
- boundary CRS and event CRS must match when both are explicit;
- boundary spatial unit and event spatial unit must match when both are explicit;
- every fitted event must be covered by the polygon, including its boundary line;
- every evaluated support location must also be covered;
- outside events/support cause explicit errors; they are never dropped silently;
- the boundary fingerprint and correction name are stored in fit/result metadata.

A correction other than `none` requires a `SpatialBoundary`.

## 7. Combination rules

Supported combinations:

- scalar + no correction/renormalization/reflection;
- event-specific sample-point scalar + no correction/renormalization/reflection;
- global matrix + no correction/renormalization;
- diagonal global matrix + reflection;
- balloon kNN + no correction;
- boundary domain validation + balloon kNN + no correction.

Deliberately rejected in 0.0.8:

- balloon bandwidth + renormalization;
- balloon bandwidth + reflection;
- full non-diagonal matrix + reflection.

Balloon boundary mass depends on each support-specific bandwidth. It must be implemented later as
a genuinely query-centred correction, not by reusing source-centred renormalization.

## 8. Important implementation files

New source files:

- `src/pykdex/bandwidths/balloon.py`
- `src/pykdex/bandwidths/matrix.py`
- `src/pykdex/corrections/__init__.py`
- `src/pykdex/corrections/spatial.py`
- `src/pykdex/spatial/evaluation.py`
- `src/pykdex/spatial/__init__.py`

Modified source files:

- `src/pykdex/estimators/spatial_kde.py`
- `src/pykdex/bandwidths/__init__.py`
- `src/pykdex/__init__.py`

Tests and examples:

- `tests/test_spatial_boundary_anisotropy.py`
- `examples/10_spatial_boundary_anisotropy.py`
- `examples/API_COVERAGE.csv`

Documentation:

- `docs/guides/spatial-boundary-anisotropy.md`
- `docs/guides/bandwidths.md`
- `docs/estimators/spatial-kde.md`
- `docs/api/corrections.md`
- this versioned handoff and its `docs/development` copy.

## 9. Validation completed locally

Observed local validation before final GitHub Actions:

- pytest: `145 passed`;
- branch coverage: `81.41%`, above the required `80%` minimum;
- matrix Gaussian values match `scipy.stats.multivariate_normal.pdf`;
- `H = h^2 I` matches scalar KDE numerically;
- anisotropic orientation follows matrix eigen/scaling directions;
- rectangular Gaussian renormalization restores measured grid mass near one;
- general polygon quadrature is deterministic across repeated preparation;
- reflection increases boundary density and approximately restores mass for small bandwidths;
- full covariance reflection, unsupported polygon reflection, outside events/support, and invalid
  combinations fail explicitly;
- existing 0.0.1-0.0.7 regression tests pass.

Final Black, isort, Ruff, mypy, strict MkDocs, distributions, installed-wheel checks, platform
matrix, and exact CI run identifiers remain pending until the clean PR workflow completes.

## 10. Deliberate exclusions and known limitations

Not implemented in 0.0.8:

- query-centred boundary correction for balloon bandwidths;
- event-specific full bandwidth matrices;
- automatic plug-in matrix selection;
- constrained triangulation or adaptive polygon quadrature;
- infinite-series rectangular reflection;
- irregular-polygon reflection;
- relative-risk KDE;
- bootstrap confidence bands and significance envelopes;
- heat-equation Gaussian NetworkKDE;
- spatiotemporal and network-time data/estimators;
- persistent Zarr/PostGIS workspaces;
- compiled acceleration.

General-polygon renormalization is deterministic numerical quadrature. Narrow polygon features or
very small compact kernels may require a larger `cells_per_axis`. The chosen value must be reported
in reproducible analyses.

## 11. Next recommended development unit

The next unit should implement **HeatNetworkKDE as a separate numerical engine**, not as an
ordinary radial-kernel alias:

1. define the metric-graph Laplacian and vertex boundary/continuity conditions;
2. establish a discrete finite-element or edge-grid operator with measured edge support;
3. map event mass onto the operator without losing along-edge offsets;
4. solve the heat equation for diffusion time `t` using a stable sparse matrix exponential or
   equivalent validated method;
5. return a `NetworkField` with mass and continuity diagnostics;
6. validate on a line, terminal interval, T-junction, ring, and disconnected network against
   analytical or independently generated references;
7. keep `HeatNetworkKDE` separate from current simple/discontinuous/continuous radial traversal;
8. create `HANDOFF_0.0.9_HEAT_NETWORK_KDE.md` before merge.

After the heat engine, proceed to spatiotemporal data objects and separable STKDE.

## 12. Recovery procedure for a new conversation

1. Open `hujinghaoabcd/pyKDEX` and confirm the default branch and latest commit.
2. Read this file, `HANDOFF_NEXT_CONVERSATION.md`, `CHANGELOG.md`, and
   `BASELINE_VALIDATION.md`.
3. Confirm `src/pykdex/__init__.py` reports version `0.0.8` after merge.
4. Inspect PR #7 and its final GitHub Actions run rather than relying on chat claims.
5. Verify no temporary export, patch, format, diagnostic, or auto-commit workflows remain.
6. Run pytest with branch coverage, Black, isort, Ruff, mypy, strict MkDocs, distribution checks,
   and installed-wheel smoke tests when a local source tree is available.
7. Begin the next unit on a dedicated `agent/...` branch and open a draft PR.
8. Create the next detailed versioned handoff before declaring the unit complete.

## 13. Finalization fields

- Final version: `0.0.8`
- Final test count: `145 passed`
- Final branch coverage: `81.41%`
- Public API/example count: `77 symbols mapped to executable examples`
- Final CI run: GitHub Actions run `#104` (`29974693141`), conclusion `success`
- PR #7 squash merge commit: `9f0aef9e8be57cc9e1c6beb210225b421501a623`
- Temporary workflow removal: completed
