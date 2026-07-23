# pyKDEX 0.0.12 handoff: network-time foundation

## 1. Purpose and recovery scope

This document is the durable engineering record for pyKDEX 0.0.12. It lets a
new conversation recover the design, mathematics, public contracts,
implementation locations, validation evidence, intentional exclusions, and
recommended next work without relying on chat history.

- Repository: `hujinghaoabcd/pyKDEX`
- Development branch: `agent/network-time-foundation`
- Version developed: `0.0.12`
- Stable version before this unit: `0.0.11`
- Development date: `2026-07-23`
- Pull request: `#12 Add network-time KDE foundation`
- Feature implementation commit:
  `3f3a752202b4a2ff91939a01513d67713074c5e9`
- First complete PR CI: run `#128` (`30011519807`), conclusion `success`
- Final clean PR CI: run `#129` (`30011753378`), conclusion `success`
- Squash merge commit: `f9b9d7e3949ee8688b8829a6b8760f1f3214cd4a`
- Post-merge handoff commit:
  `3cda2582e702963b34bd84f66eb79db84c500429`
- Post-merge `main` CI: run `#131` (`30012065149`), conclusion `success`

The source tree and tests are authoritative. Pending fields must be replaced
only with observed GitHub values. Never infer CI or merge success.

## 2. Permanent project principles

The project remains composition-oriented:

```text
dataset
+ domain
+ prepared data
+ measure
+ metric or operator
+ kernel
+ smoothing parameter
+ correction
+ support
+ compute plan
+ estimator
+ structured result
```

The following rules remain mandatory:

1. Numerical algorithms are independently implemented in pyKDEX. External
   research packages may inform validation but are not runtime computation
   engines.
2. Raw network, event, temporal, and support data are normalized into
   immutable pyKDEX objects before estimation.
3. CRS, spatial units, temporal units, temporal origin, timezone, identifiers,
   provenance, and fingerprints are first-class metadata.
4. Spatial and temporal coordinates never share an unexplained distance or
   bandwidth.
5. Linear and cyclic time are different domain objects.
6. Every integral uses an explicit support measure.
7. Public arrays and reusable assets are owned and read-only.
8. Failed estimator fits clear fitted state atomically.
9. Density and intensity normalization are separate contracts.
10. Ordinary spatiotemporal KDE, traversal NetworkKDE, heat NetworkKDE, and
    temporal-network KDE remain distinct estimator families.
11. Every top-level public symbol maps to an executable example.
12. Every completed development unit leaves a detailed versioned handoff,
    updates the current handoff, and records only observed validation and CI.

## 3. Problem solved in 0.0.12

Version 0.0.11 supplied explicit time domains and ordinary Euclidean
space-time KDE, while earlier versions supplied canonical road networks,
event snapping, measured lixels, exact network distances, and three junction
policies. The missing layer was their principled composition.

Four shortcuts were specifically avoided:

1. Treating a snapped road location as planar `x, y` during time estimation.
   This loses network connectivity, direction, and junction allocation.
2. Rebuilding topology, snapping, and lixels inside every temporal estimator.
   These are reusable preparation decisions.
3. Returning a flat array with no length-times-time measure. Such an array
   cannot support a meaningful network-time integral.
4. Allocating a dense event-by-arixel distance matrix. The network distance
   does not change across temporal slices and should be reused.

The 0.0.12 unit therefore adds explicit network-time events, measured arixels,
a reusable network-time workspace, a factorized distance asset, a fixed
product estimator, and a structured measured field.

## 4. Public data contract: `NetworkTimeEvents`

`NetworkTimeEvents` composes:

- accepted `NetworkEvents`, already snapped to a canonical
  `LinearNetwork`;
- authoritative `TemporalCoordinates`;
- provenance.

The two components must have identical lengths. Event IDs, weights, along-edge
offsets, original coordinates, snapped coordinates, snap distances, and
network identity remain owned by `NetworkEvents`. Time topology, values, unit,
origin, and timezone remain owned by `TemporalCoordinates`.

The combined fingerprint includes both components and provenance. Duplicate
times are allowed and reported as a warning; duplicate observations are not
silently aggregated.

### 4.1 Raw-event time alignment

`NetworkTimeWorkspace.prepare()` accepts raw `SpatialEvents` and one time per
raw event. Network snapping may reject observations. The constructor uses
stable event IDs to select the corresponding times for accepted events.

This is intentionally not a positional prefix or mask inferred after the
fact. A rejected event between two accepted events must not shift the second
accepted time. The implementation normalizes NumPy scalar IDs through
`.tolist()` before stable representation matching; this fixes the difference
between values such as `repr(0)` and `repr(np.int64(0))`.

Rejected observations remain auditable in
`workspace.network_workspace.snap_result`.

## 5. Measured support: `ArixelSupport`

An arixel is the Cartesian product of one lixel and one temporal cell.

For lixel \(j\) with actual length \(\Delta l_j\) and temporal cell \(q\) with
actual width \(\Delta t_q\), the support measure is:

\[
\mu_{qj}=\Delta l_j\Delta t_q.
\]

The implementation retains:

- the original `LixelSupport`;
- strictly increasing temporal cell edges;
- distinct temporal centers and actual widths;
- time-major repeated lixel indices;
- one time and one measure per arixel;
- domain, temporal unit, origin, timezone, provenance, and fingerprint.

Flattened results are time-major:

```text
time 0: lixel 0, lixel 1, ..., lixel J
time 1: lixel 0, lixel 1, ..., lixel J
...
```

The structured shape is always:

```text
(n_time_cells, n_lixels)
```

`from_lixels()` retains a final shorter temporal cell when the interval is not
divisible by the requested resolution. `LixelSupport` already retains shorter
tail lixels, so both factors use actual rather than nominal measure.

For a cyclic domain, temporal edges must begin at the domain origin and cover
exactly one complete period. This makes a full-domain network-time integral
unambiguous.

## 6. Reusable workspace: `NetworkTimeWorkspace`

`NetworkTimeWorkspace` composes:

- an existing `NetworkWorkspace`;
- accepted `NetworkTimeEvents`;
- `ArixelSupport`;
- an optional `NetworkTimeDistanceAsset`.

It does not duplicate the network, snapping report, events, or lixels.

Validation checks:

- the base network workspace is internally valid;
- accepted network events are identical in both layers;
- arixels use the exact workspace lixel partition;
- event and support temporal units match;
- event and support time domains match by fingerprint;
- temporal origin and timezone match;
- an attached distance asset matches every owning object.

`summary()` exposes the number of nodes, edges, events, lixels, times,
arixels, total length-times-time measure, validation state, asset state, and
fingerprint.

Constructors:

- `prepare()` is the high-level raw-event path and safely aligns accepted
  times after snapping;
- `from_network_workspace()` is the lower-level path for callers that already
  possess times in accepted-event order;
- `with_distances()` returns a new frozen workspace with a compatible
  factorized asset.

## 7. Factorized distance contract

`NetworkTimeDistanceAsset` stores:

1. an existing sparse source-event by target-lixel
   `NetworkDistanceAsset`;
2. signed temporal offsets with shape
   `target_time × source_event`;
3. domain-aware temporal distances with the same shape;
4. event, support, time-domain, and base-workspace fingerprints.

It deliberately does not store an event-by-arixel network-distance matrix.
For \(n\) events, \(J\) lixels, and \(Q\) temporal cells, the factorized
representation stores approximately:

```text
sparse reachable network pairs + Q × n temporal offsets
```

instead of:

```text
n × J × Q expanded pairs
```

Signed offsets are retained because cyclic image sums and future directional
time kernels cannot be reconstructed from absolute temporal distance alone.

`build_network_time_distance_asset()` requires length-weighted network
distance. It validates network events, lixels, temporal domain, unit, origin,
timezone, directed mode, and optional cutoff. Assets are read-only and must
pass fingerprint validation before reuse.

## 8. `TemporalNetworkKDE`

### 8.1 Product estimator

For event \(i\), target lixel center \(l_j\), target time \(t_q\), spatial
bandwidth \(h_s>0\), and temporal bandwidth \(h_t>0\):

\[
\hat f(l_j,t_q)
=
\sum_i a_i
K^G_{h_s}(x_i\rightarrow l_j)
K^T_{h_t}(t_q-t_i).
\]

For `target="density"`:

\[
a_i=\frac{w_i}{\sum_r w_r}.
\]

For `target="intensity"`:

\[
a_i=w_i.
\]

The temporal factor is:

\[
K^T_{h_t}(\Delta t)
=
\frac{1}{h_t}K_t\left(\frac{\Delta t}{h_t}\right)
\]

on linear time. On a cyclic domain of period \(P\), pyKDEX reuses the
normalized periodic image sum introduced in 0.0.11:

\[
K^T_{P,h_t}(\Delta t)
=
\sum_{k\in\mathbb Z}
\frac{1}{h_t}
K_t\left(\frac{|\Delta t+kP|}{h_t}\right).
\]

Finite-support images are enumerated exactly. Gaussian and exponential tails
use the existing deterministic tolerance.

### 8.2 Junction-policy semantics

The spatial factor reuses the exact fixed-bandwidth `NetworkKDE` contracts:

- `simple`: shortest-path network distance, finite or infinite-support spatial
  kernels, directed or undirected traversal;
- `discontinuous`: non-backtracking equal-split propagation, finite-support
  spatial kernels only;
- `continuous`: \(2/d\) transmission and \(2/d-1\) reflection correction,
  finite-support spatial kernels and undirected networks only.

Time does not change path coefficients. A temporal kernel multiplies each
event's spatial contribution after the network calculation.

For path-based policies, propagation traces are computed once per event at the
spatial bandwidth and evaluated on lixel centers. For `simple`, a compatible
factorized asset is reused; otherwise an asset with the needed cutoff and
directed mode is rebuilt.

### 8.3 Chunking and state

The estimator evaluates the time-by-lixel product in ordered temporal chunks.
`time_chunk_size` changes memory scheduling, not mathematical results.

The fit is atomic. Any validation, kernel, direction, propagation, or
floating-point failure resets the estimator to an unfitted state. Public
values are clipped only for tiny negative propagation corrections and the raw
minimum before clipping is recorded in metadata, matching `NetworkKDE`.

## 9. Result contract: `NetworkTimeField`

`NetworkTimeField` owns:

- read-only non-negative values, one per arixel;
- the full measured `ArixelSupport`;
- spatial and temporal bandwidths;
- target, kernel names, junction policy, and directed mode;
- network and event fingerprints;
- immutable metadata.

Methods:

- `integral()` computes
  \(\sum_{q,j}\hat f(l_j,t_q)\Delta l_j\Delta t_q\);
- `to_grid()` returns `time × lixel`;
- `to_frame()` appends density or intensity to arixel attributes;
- `to_geodataframe()` repeats lixel geometry for each temporal cell;
- `to_xarray()` returns named `time` and `lixel` dimensions plus lixel
  coordinates.

xarray remains optional through `pyKDEX[array]`.

## 10. Numerical validation

The dedicated tests cover:

- immutable event-time pairing and combined fingerprints;
- duplicate-time warnings;
- stable-ID time filtering when a middle raw event is rejected;
- actual lixel and temporal remainder-cell measure;
- exact full-period cyclic arixel coverage;
- time-major arixel reshape and tabular output;
- factorized asset shapes, signed offsets, sparse network pairs, and ownership;
- temporal metadata and directed-type rejection;
- workspace copy and fingerprint behavior;
- exact zero-distance Epanechnikov × Gaussian product value;
- equality between a one-time temporal slice and the corresponding
  `NetworkKDE` field multiplied by its temporal factor;
- both discontinuous and continuous junction policies;
- exact density/intensity scaling by total event weight;
- chunked and unchunked numerical identity;
- reuse of a compatible workspace distance asset;
- cyclic equality across the period boundary;
- full-period cyclic network-time mass conservation;
- directed `simple` propagation with zero upstream values;
- rejection of infinite-support kernels for path policies;
- atomic failed-fit reset;
- xarray time/lixel dimensions and attributes.

Existing spatial, ordinary spatiotemporal, radial network, and heat-network
tests remain unchanged and are run in the full suite.

## 11. Implementation map

Core network-time objects:

- `src/pykdex/network_time/events.py`;
- `src/pykdex/network_time/support.py`;
- `src/pykdex/network_time/distance.py`;
- `src/pykdex/network_time/workspace.py`;
- `src/pykdex/network_time/__init__.py`.

Estimator and result:

- `src/pykdex/estimators/temporal_network_kde.py`;
- `src/pykdex/core/network_time_results.py`.

Public exports and version:

- `src/pykdex/__init__.py`;
- `src/pykdex/core/__init__.py`;
- `src/pykdex/estimators/__init__.py`;
- `CITATION.cff`;
- `tools/smoke_installed_distribution.py`.

Tests:

- `tests/test_network_time_data.py`;
- `tests/test_temporal_network_kde.py`.

User and developer material:

- `examples/14_temporal_network_kde.py`;
- `examples/API_COVERAGE.csv`;
- `docs/api/network-time.md`;
- `docs/estimators/temporal-network-kde.md`;
- `docs/guides/network-time-data.md`;
- `docs/development/handoff-0.0.12-network-time-foundation.md`;
- README, changelog, roadmap, architecture, project structure, baseline, and
  current handoff.

## 12. Rejected alternatives

1. **Planar distance after snapping.** A snapped coordinate does not make
   Euclidean distance a valid road-network metric.
2. **A single generic `SpatiotemporalEvents` object.** Network events require
   edge identity, along-edge offset, snap audit, and network fingerprint.
3. **A NumPy array as the arixel result.** Without actual
   length-times-time measure, integration and resampling semantics are lost.
4. **Expanded event-by-arixel distances.** Network distance is invariant over
   time cells; expanding it wastes memory and weakens cache reuse.
5. **Minimum circular distance as a cyclic Gaussian kernel.** The normalized
   periodic image sum is already the correct project contract.
6. **A string-only engine switch for heat smoothing.** Heat equations use a
   different numerical operator and remain a separate estimator.
7. **Calling ordinary Euclidean `SpatiotemporalKDE` TNKDE.** Only the present
   network plus time estimator uses temporal-network semantics.
8. **Silently accepting continuous propagation on directed networks.** The
   current \(2/d\) continuity definition is an undirected metric-graph
   contract.
9. **Automatic unit conversion.** Spatial and temporal metadata are validated
   but never guessed or converted implicitly.

## 13. Deliberate limitations

The following are intentionally outside 0.0.12:

- event-specific, balloon, or adaptive network-time bandwidths;
- network-time bandwidth selection or cross-validation;
- heat-equation diffusion in network-time;
- nonseparable, causal, or advection-aware temporal kernels;
- time-dependent road topology, costs, closures, or direction;
- marks, conditional densities, relative risk, or exposure offsets;
- bootstrap uncertainty and separability tests;
- persistence to Zarr, GeoPackage, or PostGIS;
- dask/distributed execution and compiled acceleration;
- interpolation or resampling of `NetworkTimeField`;
- arbitrary query times outside a prepared arixel support.

These exclusions prevent the fixed estimator from becoming a container for
unrelated semantics.

## 14. Final observed local validation

Before publication, the following were observed:

- pytest: `217 passed`;
- branch coverage: `81.14%`, above the required `80%`;
- new focused tests: `17 passed`;
- public API/example map: `112 public symbols`;
- executable examples: `14`;
- Black, isort, Ruff, and mypy: passed;
- strict MkDocs build: passed;
- all `14` examples executed successfully in isolated subprocesses;
- wheel and sdist build: passed;
- Twine and distribution archive-content verification: passed;
- isolated wheel installation and smoke test outside the source tree: passed.

## 15. GitHub and merge state

- PR: `#12 Add network-time KDE foundation`;
- feature implementation commit:
  `3f3a752202b4a2ff91939a01513d67713074c5e9`;
- first complete PR CI run `#128` (`30011519807`): success across quality,
  coverage, distributions, Linux/Windows/macOS, and Python 3.11-3.14;

- final clean PR CI run `#129` (`30011753378`): success;
- squash merge commit:
  `f9b9d7e3949ee8688b8829a6b8760f1f3214cd4a`;
- post-merge handoff/status commit:
  `3cda2582e702963b34bd84f66eb79db84c500429`;
- post-merge `main` CI run `#131` (`30012065149`): success.

PR #12 was merged and closed successfully.

No temporary diagnostic, transfer, formatting, or auto-fix workflow may enter
`main`.

## 16. Next recommended development unit

Build network-time bandwidth selection and adaptive temporal-network KDE as
0.0.13:

1. introduce a `NetworkTimeSelectionCache` containing exact event-event
   network distances, signed time offsets, and reusable maximum-bandwidth
   propagation traces;
2. implement deterministic ordered candidate handling for spatial and
   temporal bandwidths;
3. implement weighted network-time leave-one-out likelihood;
4. implement arixel-measured network-time least-squares cross-validation;
5. support joint and separate bandwidth searches while recording the complete
   score surface;
6. define sample-point spatial and temporal bandwidth ownership explicitly;
7. reuse network and temporal assets across every candidate pair;
8. validate duplicate event locations, cyclic time, direction, junction
   policies, deterministic ties, weight scaling, and cache mismatch;
9. add performance benchmarks that compare factorized reuse with repeated
   construction;
10. write `HANDOFF_0.0.13_NETWORK_TIME_BANDWIDTHS.md`.

Do not add exposure-adjusted risk, persistence, or heat network-time diffusion
inside the selection unit. Those require independent data and numerical
contracts.

## 17. Recovery procedure

1. Read `HANDOFF_NEXT_CONVERSATION.md`.
2. Read this entire document.
3. Confirm `src/pykdex/__init__.py` reports `0.0.12`.
4. Inspect `git status`, current branch, remote `main`, recorded PR, and CI.
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

6. Confirm a cyclic full-period continuous network-time density integrates to
   approximately one within the documented quadrature tolerance.
7. Confirm factorized assets and fields are read-only.
8. Confirm a directed simple estimate has zero upstream support.
9. Start 0.0.13 only from the final merged `main`.
