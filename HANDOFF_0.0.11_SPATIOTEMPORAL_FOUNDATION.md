# pyKDEX 0.0.11 handoff: ordinary spatiotemporal foundation

## 1. Purpose and recovery scope

This is the recoverable engineering record for pyKDEX 0.0.11. It is intended
to let a new conversation reconstruct the architecture, mathematical
definitions, public contracts, implementation locations, validation evidence,
deliberate limitations, and next development order without relying on previous
chat history.

- Repository: `hujinghaoabcd/pyKDEX`
- Development branch: `agent/spatiotemporal-foundation`
- Version developed: `0.0.11`
- Stable version before this unit: `0.0.10`
- Development date: `2026-07-23`
- Pull request: `#11 Add ordinary spatiotemporal KDE foundation`
- Feature implementation commit:
  `f3cd409ea84508bf7218ba842dddd4b15b5e3138`
- First complete PR CI: run `#123` (`29999198427`), conclusion `success`
- Final clean PR CI: run `#124` (`29999408464`), conclusion `success`
- Squash merge commit: `0ab1291a41eddd8dd4e6709ed92c5307b3e4b3e0`

The source tree and tests are authoritative. The GitHub fields above must be
replaced with observed values after the final clean CI and merge.

## 2. Permanent project principles

pyKDEX remains a composition-oriented research framework:

`data + domain + prepared assets + measure + metric/operator + kernel + smoothing parameter + correction + support + compute plan + estimator + result`.

The following rules remain mandatory:

1. Numerical algorithms are implemented independently in pyKDEX. External
   research libraries may inform validation but are not runtime computation
   dependencies.
2. Spatial and temporal coordinates retain independent units and metadata.
   They are not concatenated into an unexplained Euclidean vector.
3. Time topology is explicit. Linear time and cyclic time are different domain
   objects, not flags hidden inside a distance function.
4. CRS, units, temporal origins, timezones, support measures, identifiers,
   provenance, and fingerprints are first-class data.
5. Public arrays and reusable numerical assets are owned and read-only.
6. Failed fits reset estimator state atomically.
7. Density and intensity normalization are distinct and documented.
8. Every public symbol maps to an executable example.
9. Ordinary Euclidean space-time KDE, traversal NetworkKDE, heat NetworkKDE,
   and future network-time KDE remain separate estimator families.
10. Every completed unit writes a versioned root handoff, a development-doc
    handoff, updated baseline/changelog/current handoff, and actual CI state.

## 3. Problem solved in 0.0.11

Before this unit, pyKDEX had mature spatial and network data objects but no
authoritative temporal domain or ordinary space-time estimator. Treating time
as an extra coordinate would have created four errors:

1. kilometres and hours would silently share one metric and one bandwidth;
2. time-of-day observations near midnight would be falsely far apart;
3. support integration would omit temporal cell widths;
4. cyclic Gaussian kernels based only on minimum circular distance would not
   integrate to one over a period.

Version 0.0.11 adds an ordinary Euclidean space-time path with explicit data,
domain, measure, distance, estimator, result, and selection layers. It does not
reuse network paths or heat-equation semantics.

## 4. Public data and domain API

### 4.1 `BaseTimeDomain`, `LinearTimeDomain`, and `CyclicTimeDomain`

`LinearTimeDomain` uses absolute temporal differences on an unbounded numeric
axis.

`CyclicTimeDomain(period, origin)` canonicalizes coordinates to
`[origin, origin + period)` and defines circular distances:

\[
d_C(t,s)=\min(r,P-r),\qquad r=|t-s|\bmod P.
\]

Domain fingerprints include topology and parameters. A 24-hour cycle and a
7-day cycle can never reuse the same distance asset accidentally.

### 4.2 `TemporalCoordinates`

This immutable object owns:

- read-only numeric time coordinates;
- a time domain;
- mandatory `temporal_unit`;
- optional `temporal_origin`;
- optional timezone;
- provenance and a deterministic fingerprint.

`from_datetime()` requires an explicit timezone for naive datetimes, converts
aware values to numeric seconds/minutes/hours/days from an explicit origin, and
then stores only validated numeric values and metadata.

### 4.3 `SpatiotemporalEvents`

`SpatiotemporalEvents` composes, rather than subclasses:

- `SpatialEvents`;
- `TemporalCoordinates`;
- shared provenance.

The two components must contain the same number of observations. Event IDs and
weights remain owned by the spatial event component. The object exposes
`spatial_coordinates`, `times`, `weights`, `weight_sum`, `ids`, validation,
tabular output, and a combined fingerprint.

### 4.4 Space-time support

`SpatiotemporalPointSupport` pairs spatial query points with times and may own a
positive measure per query.

`SpatiotemporalGridSupport` takes the Cartesian product of a measured 2D
`GridSupport` and temporal cells. Flattening is time-major and its shape is:

```text
(n_time_cells, n_y_cells, n_x_cells)
```

Its cell measure is:

\[
\Delta \mu_{j,k}=\Delta A_j\,\Delta t_k.
\]

Actual spatial and temporal remainder-cell sizes are retained. A cyclic grid
must cover exactly one complete period, which makes the result integral
mathematically interpretable.

## 5. Reusable distance asset

`SpatiotemporalDistanceAsset` stores target-by-source arrays:

- spatial metric distances;
- signed temporal offsets `target - source`;
- domain temporal distances;
- source and target fingerprints;
- time-domain fingerprint;
- spatial metric name.

Signed offsets are retained even though ordinary linear kernels are symmetric.
They are needed to evaluate periodic images correctly and preserve a future
route to directional temporal kernels.

`build_spatiotemporal_distance_asset()` validates:

- spatial dimension;
- CRS and spatial units;
- temporal units;
- time-domain fingerprint;
- temporal origin;
- timezone.

Assets are validated again when passed into an estimator or bandwidth
experiment. Shape equality alone is never considered sufficient.

## 6. `SpatiotemporalKDE`

### 6.1 Product estimator

For spatial dimension \(d\), spatial bandwidth \(h_s>0\), temporal bandwidth
\(h_t>0\), and event weights \(w_i\):

\[
\hat f(x,t)
=
\sum_i a_i
\frac{1}{h_s^d}K_s\left(\frac{d_s(x,x_i)}{h_s}\right)
\frac{1}{h_t}K_t\left(\frac{t-t_i}{h_t}\right).
\]

For `target="density"`:

\[
a_i=\frac{w_i}{\sum_r w_r}.
\]

For `target="intensity"`:

\[
a_i=w_i.
\]

The estimator accepts independent spatial and temporal kernel objects, an
independent spatial metric, scalar spatial and temporal bandwidths, optional
support chunking, and a periodic tail tolerance.

### 6.2 Cyclic kernel normalization

Minimum circular distance is correct for nearest-distance reporting but is not
by itself a normalized periodic kernel. On a period \(P\), pyKDEX evaluates:

\[
K_{P,h}(\Delta t)
=
\sum_{k\in\mathbb Z}
\frac{1}{h}K\left(\frac{|\Delta t+kP|}{h}\right).
\]

Finite-support kernels include every intersecting image. Gaussian and
exponential kernels derive a deterministic finite image range from
`cyclic_tail_tolerance`. Unknown custom infinite-support temporal kernels are
rejected on cyclic domains because pyKDEX cannot invent a valid tail bound.

This design was chosen over minimum-distance substitution because the latter
overlaps tails without renormalization and breaks mass conservation for
bandwidths that are not small relative to the period.

### 6.3 Chunking and fitted state

Chunked evaluation constructs compatible point-support chunks and never changes
the mathematical result. A supplied full distance asset bypasses repeated
distance calculation. A failed first fit or refit clears all fitted state
before propagating the exception.

## 7. Results and array interoperability

`SpatiotemporalKDEResult` stores:

- read-only values;
- the validated support object;
- spatial and temporal bandwidths;
- estimator target, kernels, and spatial metric;
- immutable metadata.

It provides:

- `integral()` on measured support;
- `to_frame()`;
- `to_grid()` for the time/y/x grid;
- `to_xarray()`.

xarray remains an optional dependency exposed by `pyKDEX[array]`; the
estimator and result core do not import it until export is requested.

## 8. Bandwidth experiments

`SpatiotemporalBandwidthExperiment` accepts ordered positive candidate vectors
for space and time and reuses one event-event distance asset.

For candidate pair \((h_s,h_t)\), weighted leave-one-out density at event \(i\)
is:

\[
\hat f_{-i}(x_i,t_i)
=
\frac{
  \sum_{r\ne i} w_r K_{s,h_s}(x_i,x_r)K_{t,h_t}(t_i,t_r)
}{
  W-w_i
}.
\]

The minimized objective is:

\[
-\sum_i\frac{w_i}{W}
\log\left(\max(\hat f_{-i}(x_i,t_i),\varepsilon)\right).
\]

Only an event's own diagonal contribution is deleted. Other observations at an
identical space-time position remain valid contributors.

Modes:

- `joint`: evaluates every Cartesian candidate pair and selects the first
  deterministic global minimum in row-major candidate order;
- `separate`: minimizes spatial and temporal marginal LOO objectives
  independently, then reports the joint product score at the selected pair.

`SpatiotemporalBandwidthSelectionResult` retains candidates, the full joint
score matrix, selected pair, objective, mode, and distance-asset fingerprint.

## 9. Moving-hotspot fixture

`make_moving_hotspot_events()` creates deterministic planar events with:

\[
x(t)=v(t-t_0)+\epsilon,
\]

where velocity, spatial noise, temporal bounds, event count, and random seed
are explicit. It is a tutorial and regression fixture, not a statistical
simulation model hidden inside the estimator.

## 10. Implementation map

Core implementation:

- `src/pykdex/temporal/domain.py`;
- `src/pykdex/data/spatiotemporal.py`;
- `src/pykdex/spatiotemporal/distance.py`;
- `src/pykdex/spatiotemporal/evaluation.py`;
- `src/pykdex/estimators/spatiotemporal_kde.py`;
- `src/pykdex/core/spatiotemporal_results.py`;
- `src/pykdex/selection/spatiotemporal.py`;
- `src/pykdex/datasets/synthetic.py`.

Public exports:

- `src/pykdex/temporal/__init__.py`;
- `src/pykdex/spatiotemporal/__init__.py`;
- `src/pykdex/data/__init__.py`;
- `src/pykdex/core/__init__.py`;
- `src/pykdex/estimators/__init__.py`;
- `src/pykdex/selection/__init__.py`;
- `src/pykdex/datasets/__init__.py`;
- `src/pykdex/__init__.py`.

Tests:

- `tests/test_spatiotemporal_data.py`;
- `tests/test_spatiotemporal_kde.py`;
- `tests/test_spatiotemporal_selection.py`;
- moving-hotspot coverage in `tests/test_datasets.py`.

User material:

- `examples/13_spatiotemporal_kde.py`;
- `docs/estimators/spatiotemporal-kde.md`;
- `docs/api/spatiotemporal.md`;
- API data/result/selection pages;
- README and changelog entries.

## 11. Validation contract

The unit includes tests for:

- linear and cyclic canonicalization and distance;
- invalid domains and datetime timezone requirements;
- read-only ownership and stable fingerprints;
- independent spatial/temporal units;
- measured point support and remainder grid cells;
- full-period cyclic grid validation;
- signed temporal offsets and circular distances;
- temporal metadata and distance-asset compatibility;
- exact product-Gaussian analytical values;
- density/intensity weight scaling;
- chunk and distance-asset invariance;
- cyclic periodic equality and image-sum behavior;
- full-period cyclic mass conservation;
- measured/unmeasured result behavior;
- xarray time/y/x axes;
- atomic failed-refit reset;
- deterministic joint and separate LOO experiments;
- invalid candidates and insufficient LOO samples;
- deterministic moving-hotspot motion.

Final observed local and GitHub results are recorded in sections 14 and 15
after validation.

## 12. Rejected alternatives

The following designs were deliberately rejected:

1. Appending time as a third spatial coordinate. This hides dimensional units,
   forces one metric/bandwidth, and cannot express cyclic topology.
2. A boolean `cyclic=True` argument scattered across estimators. Domain objects
   provide canonicalization, distances, fingerprints, and reuse.
3. Minimum circular distance as the complete periodic Gaussian kernel. It does
   not preserve normalization for moderate or large bandwidths.
4. Making xarray a core dependency. Array export is optional and isolated.
5. User-written loops for bandwidth pairs. The experiment shares one distance
   asset and records the complete deterministic grid.
6. Calling this estimator `TNKDE`. The implemented domain is Euclidean space
   plus time, not a linear network plus time.

## 13. Deliberate limitations

The following are intentionally not part of 0.0.11:

- event-specific or balloon space-time bandwidths;
- nonseparable space-time kernels and advection-aware kernels;
- causal/one-sided temporal kernels;
- spatiotemporal boundaries and exposure-adjusted risk;
- persistent distance-asset serialization;
- dask/chunked xarray execution;
- network-time events, arixels, `NetworkTimeWorkspace`, or TNKDE;
- directed temporal-network propagation;
- PostGIS/Zarr workspace persistence;
- bootstrap uncertainty and compiled acceleration.

## 14. Final observed local validation

- pytest: `200 passed`;
- branch coverage: `81.41%`, above the required `80%`;
- public API/example map: `105 public symbols`;
- executable examples: `13`;
- Black, isort, Ruff, mypy, and strict MkDocs: passed;
- wheel and sdist build: passed;
- Twine and distribution-content verification: passed;
- isolated wheel installation and ordinary/spatiotemporal smoke: passed;
- cyclic full-period Gaussian density integral: approximately one within
  `2e-4` deterministic quadrature tolerance.

## 15. GitHub and merge state

- PR: `#11 Add ordinary spatiotemporal KDE foundation`;
- feature implementation commit:
  `f3cd409ea84508bf7218ba842dddd4b15b5e3138`;
- first complete PR CI run `#123` (`29999198427`): success across
  quality, coverage, distributions, Linux/Windows/macOS, and Python 3.11-3.14;
- final clean CI run `#124` (`29999408464`): success;
- squash merge commit: `0ab1291a41eddd8dd4e6709ed92c5307b3e4b3e0`;
- post-merge handoff update: pending.

No temporary repository workflow should be added. If any diagnostic workflow
is needed, it must be removed before merge and documented here.

## 16. Next recommended unit

Build the network-time data and measured support foundation before adding
advanced TNKDE variants:

1. `NetworkTimeEvents` pairing accepted network locations with authoritative
   temporal coordinates;
2. `ArixelSupport` as lixel-by-time cells with
   `length × temporal_width` measure;
3. `NetworkTimeWorkspace` reusing topology, snapping, lixels, event-event
   network distances, and time-domain metadata;
4. reusable separable network-distance/temporal-offset assets;
5. fixed-bandwidth product `TemporalNetworkKDE` with an explicit junction
   policy;
6. cyclic and linear time, disconnected components, direction, weight, mass,
   and chunk-invariance references;
7. optional xarray representation over time and lixel dimensions;
8. `HANDOFF_0.0.12_NETWORK_TIME_FOUNDATION.md`.

Heat-equation network-time smoothing, adaptive TNKDE, persistence, and
exposure-adjusted risk should remain later independent units.

## 17. Recovery procedure for a new conversation

1. Read `HANDOFF_NEXT_CONVERSATION.md`.
2. Read this entire file.
3. Confirm `src/pykdex/__init__.py` reports `0.0.11`.
4. Inspect `git status`, the default branch, the recorded PR, and CI.
5. Run:

   ```bash
   python -m pip install -e ".[dev,docs]"
   python -m black --check src tests tools examples
   python -m isort --check-only src tests tools examples
   python -m ruff check src tests tools examples
   python -m mypy
   python -m pytest --cov=pykdex --cov-branch --cov-report=term-missing -q
   python examples/validate_coverage.py
   python examples/run_all.py
   python -m mkdocs build --strict
   python -m build
   python -m twine check dist/*
   python tools/verify_distributions.py dist
   ```

6. Verify a cyclic full-period density integral is approximately one.
7. Confirm public arrays and distance assets are read-only.
8. Start 0.0.12 only from the final merged `main`.
