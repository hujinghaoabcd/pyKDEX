# pyKDEX 0.0.13 handoff: network-time bandwidths

## 1. Purpose and recovery scope

This is the durable engineering record for pyKDEX 0.0.13. It is designed so a
new conversation can recover the architecture, mathematics, source changes,
validation evidence, exclusions, and next implementation order without access
to chat history.

- Repository: `hujinghaoabcd/pyKDEX`
- Development branch: `agent/network-time-bandwidths`
- Version developed: `0.0.13`
- Stable version before this unit: `0.0.12`
- Development date: `2026-07-23`
- Pull request: `#13 Add network-time bandwidth selection and adaptive KDE`
- Feature implementation commit:
  `1fd7c07902daf14e061491e7af313b1833ea6de3`
- First complete pull-request CI: run `#133` (`30014407093`), conclusion
  `success`
- Final clean pull-request CI: pending
- Squash merge commit: pending
- Post-merge `main` CI: pending

The source tree and tests are authoritative. Pending GitHub fields must be
replaced only after the corresponding event is observed.

## 2. Permanent project principles

The project remains data-first and composition-oriented:

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

1. pyKDEX owns its numerical algorithms. External research packages may inform
   validation but are not runtime computation engines.
2. External arrays, graphs, and geospatial objects are converted to immutable
   pyKDEX objects before estimation.
3. CRS, spatial and temporal units, domain, temporal origin, timezone, IDs,
   provenance, and fingerprints remain explicit.
4. Network distance and time are separate factors. They never share an
   unexplained composite unit.
5. Every numerical integral uses the actual support measure.
6. Public arrays and reusable assets are copied, contiguous, and read-only.
7. Failed fits clear all fitted state atomically.
8. Density and intensity have different normalization contracts.
9. Query-centred balloon bandwidths and source-centred sample-point
   bandwidths remain different APIs.
10. Simple radial, path-propagation, heat-equation, ordinary space-time, and
    network-time estimators remain separate numerical families.
11. Every public top-level symbol maps to an executable example.
12. Every completed development unit creates a versioned Markdown handoff,
    updates `HANDOFF_NEXT_CONVERSATION.md`, and records only observed results.

## 3. Problem solved in 0.0.13

Version 0.0.12 supplied a fixed-bandwidth product estimator on measured
lixel-by-time support. Three missing capabilities prevented serious bandwidth
analysis:

1. repeated candidate evaluation rebuilt event distances and path traces;
2. there was no network-time leave-one-out likelihood;
3. there was no LSCV integral over actual arixel measure;
4. `TemporalNetworkKDE` could not assign source-event spatial and temporal
   bandwidths.

This unit adds a reusable factorized selection cache, deterministic scalar
candidate experiments, independent network/time kNN sample-point bandwidths,
and adaptive evaluation without allocating a dense event-by-arixel distance
cube.

## 4. Matrix orientation and bandwidth ownership

The implementation uses two explicit orientations:

- network kernel matrices: `source_event × target_location`;
- temporal support matrices: `target_time × source_event`.

Event-event temporal offsets use:

```python
times[None, :] - times[:, None]
```

so the row is the source and the column is the target. Support offsets use:

```python
support_times[:, None] - event_times[None, :]
```

so rows are target time cells and columns are source events.

An event-specific bandwidth always belongs to the source event. For source
\(i\), the product contribution is:

\[
K^{G}_{h_{s,i}}(x_i\rightarrow l)
\frac{1}{h_{t,i}}
K_t\left(\frac{t-t_i}{h_{t,i}}\right).
\]

This is sample-point adaptation. It is not balloon KDE.

## 5. `NetworkTimeBandwidths`

`NetworkTimeBandwidths` is an immutable pair:

```python
NetworkTimeBandwidths(
    spatial=float_or_event_array,
    temporal=float_or_event_array,
)
```

Each component may be:

- one finite positive scalar; or
- one finite positive value per source event.

Array inputs are copied and made read-only. `validate_for(n_events)` enforces
source count. The object exposes:

- `adaptive_spatial`;
- `adaptive_temporal`;
- `adaptive`.

This object is accepted by `TemporalNetworkKDE(bandwidths=...)`. Existing
`spatial_bandwidth=` and `temporal_bandwidth=` scalar calls remain valid.

## 6. `NetworkTimeKNNBandwidth`

The adaptive strategy resolves spatial and temporal bandwidths independently:

\[
h_{s,i}=c_s d_G(x_i,x_{i,(k_s)}),
\qquad
h_{t,i}=c_t d_T(t_i,t_{i,(k_t)}).
\]

The spatial distance is exact along the canonical network. The temporal
distance follows the event time domain, including cyclic distance.

Rules:

1. Exclude only the event's own diagonal index.
2. Do not exclude another event merely because its distance is zero.
3. Duplicate network locations may therefore produce zero spatial bandwidth.
4. Duplicate times may produce zero temporal bandwidth.
5. A meaningful positive floor must be explicit in those cases.
6. Directed kNN fails if an event cannot reach the requested neighbour rank.
7. Euclidean fallback is forbidden.
8. `k` cannot exceed `n_events - 1`.

The public constructor provides independent:

- `spatial_k` and `temporal_k`;
- multipliers;
- minimum spatial and temporal bandwidths.

## 7. `NetworkTimeSelectionCache`

The cache stores:

1. exact event-event `NetworkDistanceAsset`;
2. either event-lixel distance assets or maximum-bandwidth propagation traces;
3. signed event-event temporal offsets;
4. signed support-time by event offsets;
5. maximum spatial candidate;
6. junction policy and effective direction;
7. workspace identity;
8. a stable cache fingerprint.

For `simple` propagation:

- finite-support spatial kernels build or reuse an event-lixel asset with
  cutoff at least the largest candidate;
- infinite-support kernels require a full asset.

For `discontinuous` and `continuous` propagation:

- each event is traced once at the largest candidate bandwidth;
- every smaller candidate evaluates only the portion within that bandwidth;
- path policies still require finite-support spatial kernels;
- continuous propagation remains undirected.

The cache deliberately does not store a dense
`event × time × lixel` representation.

## 8. Network-time leave-one-out likelihood

For scalar candidate pair \((h_s,h_t)\), define the source-by-target event
matrix:

\[
M_{ri} =
K^G_{h_s}(x_r\rightarrow x_i)
K^T_{h_t}(t_i-t_r).
\]

The diagonal is set to zero by event index. Weighted LOO density is:

\[
\hat f_{-i}(x_i,t_i)
=
\frac{\sum_{r\ne i} w_r M_{ri}}
{\sum_r w_r-w_i}.
\]

The minimized weighted negative log-likelihood is:

\[
-\sum_i p_i\log\max(\hat f_{-i},\epsilon),
\qquad
p_i=\frac{w_i}{\sum_r w_r}.
\]

The density floor prevents logarithmic singularity; it does not turn an
unreachable event into a positive kernel contribution.

## 9. Network-time LSCV

For temporal cell \(q\), lixel \(j\), source event \(i\), the full density is:

\[
\hat f_{qj}
=
\sum_i p_i
K^T_{h_t}(t_q-t_i)
K^G_{h_s}(x_i\rightarrow l_j).
\]

The support measure is the actual arixel measure:

\[
\mu_{qj}=\Delta t_q\Delta l_j.
\]

The objective is:

\[
CV_{LS}(h_s,h_t)
=
\sum_{q,j}\hat f_{qj}^2\mu_{qj}
-2\sum_i p_i\hat f_{-i}(x_i,t_i).
\]

Remainder temporal cells and remainder lixels retain their actual widths and
lengths. Nominal resolutions are never substituted.

## 10. Joint and separate selection modes

`NetworkTimeBandwidthExperiment` accepts ordered, unique, positive spatial and
temporal candidate arrays.

`mode="joint"` evaluates every pair and chooses the first minimum in NumPy
row-major order. This makes ties deterministic.

`mode="separate"`:

1. evaluates the marginal spatial objective over lixels;
2. evaluates the marginal temporal objective over time cells;
3. chooses each marginal minimum independently;
4. reports the complete product objective at that pair.

Both modes retain the full joint score matrix. Objective names are:

- input `"likelihood"` → result `"loo_likelihood"`;
- input `"least_squares"` → result `"least_squares_cv"`.

`NetworkTimeBandwidthSelectionResult` owns read-only candidate arrays and the
score matrix, validates the selected pair, records the cache fingerprint, and
exports every pair through `to_frame()`.

## 11. Adaptive `TemporalNetworkKDE`

`TemporalNetworkKDE` now accepts:

```python
TemporalNetworkKDE(
    bandwidths=NetworkTimeBandwidths(...),
)
```

or:

```python
TemporalNetworkKDE(
    bandwidths=NetworkTimeKNNBandwidth(...),
)
```

For path policies, traces extend to the maximum source-event spatial
bandwidth, while evaluation uses the correct bandwidth and normalization for
each source. For simple kernels, the distance cutoff similarly uses the
maximum finite-support bandwidth.

The temporal evaluator accepts one bandwidth per final-axis source, including
normalized periodic image sums in cyclic time.

`NetworkTimeField` now retains scalar or event-specific spatial and temporal
bandwidths and exposes adaptive flags. xarray metadata stores adaptive flags
and min/max values instead of placing arrays in attributes.

## 12. Performance and cache principles

Candidate experiments reuse expensive structures:

- exact event-event network distances;
- event-lixel distances;
- maximum-bandwidth propagation traces;
- event-event signed time offsets;
- support-event signed time offsets.

Only kernel evaluations and factorized matrix products vary across candidate
pairs. The benchmark intentionally reports event count, arixel count,
candidate pair count, elapsed time, selected pair, and cache fingerprint.

No benchmark result is a formal performance guarantee. Regression should focus
on asymptotic allocation and asset reuse, not a fragile wall-clock threshold.

## 13. Public API added

- `NetworkTimeBandwidths`
- `NetworkTimeKNNBandwidth`
- `NetworkTimeSelectionCache`
- `NetworkTimeBandwidthExperiment`
- `NetworkTimeBandwidthSelectionResult`

Changed public behavior:

- `TemporalNetworkKDE` accepts fixed or adaptive bandwidth pairs;
- `NetworkTimeField` retains scalar or event-specific bandwidths;
- `evaluate_temporal_kernel` accepts one bandwidth per source in its final
  axis.

## 14. Main source and test files

Added:

- `src/pykdex/bandwidths/network_time.py`
- `src/pykdex/selection/network_time.py`
- `tests/test_network_time_bandwidths.py`
- `examples/15_network_time_bandwidths.py`
- `benchmarks/benchmark_network_time_bandwidths.py`

Changed:

- `src/pykdex/estimators/temporal_network_kde.py`
- `src/pykdex/spatiotemporal/evaluation.py`
- `src/pykdex/core/network_time_results.py`
- package and subpackage public exports
- network-time API and estimator documentation
- changelog, architecture, roadmap, citation, validation, and smoke metadata.

## 15. Observed local validation

- focused network-time and neighboring tests: `22 passed`;
- full regression: `226 passed`;
- branch coverage: `81.15%`, above required `80%`;
- public API/example map: `117 public symbols`, all mapped;
- new executable example: passed;
- benchmark: passed for `100` events, `6912` arixels, and `64` candidate pairs;
- Black: passed;
- isort: passed;
- Ruff: passed;
- mypy: passed for `82` source files;
- strict MkDocs build: passed;
- wheel and sdist build: passed;
- Twine metadata check: passed;
- distribution archive content verification: passed;
- isolated wheel installation and smoke test: passed.

The first complete GitHub CI matrix passed on Linux, Windows, macOS, and
Python 3.11-3.14. Final clean CI and merge fields remain pending until
observed.

## 16. Deliberate exclusions

This unit does not include:

- heat-equation diffusion in network-time;
- nonseparable or coupled per-event bandwidth matrices;
- causal, advection-aware, or time-dependent-network kernels;
- exposure-adjusted relative risk;
- bootstrap uncertainty or separability tests;
- persistent workspace formats;
- PostGIS or Zarr storage;
- distributed execution or compiled acceleration.

These are separate numerical or infrastructure contracts and must not be
smuggled into bandwidth selection.

## 17. Rejected shortcuts

The following designs were explicitly rejected:

1. User loops that rebuild a workspace for each candidate pair.
2. Dense event-by-arixel distance cubes.
3. Treating time as an extra network distance coordinate.
4. Excluding all zero-distance neighbors instead of only the self index.
5. Silently replacing zero kNN bandwidth with machine epsilon.
6. Falling back to Euclidean distance for directed-unreachable events.
7. Query-centred balloon semantics disguised as event-specific bandwidths.
8. Retacing path propagation separately for every candidate.
9. LSCV based on nominal cell size rather than actual arixel measure.
10. Nondeterministic candidate tie handling.

## 18. Next recommended unit: 0.0.14 persistence foundation

The next unit should make expensive prepared data and distance assets portable
between processes while preserving identity and validation.

Recommended order:

1. define a versioned `WorkspaceManifest`;
2. define explicit schemas for network geometry/topology, snapped events,
   lixels, arixels, distance assets, and provenance;
3. implement a safe local directory/archive backend before database backends;
4. add checksums and schema-version migration guards;
5. add `NetworkWorkspace.save/load`;
6. add `NetworkTimeWorkspace.save/load`;
7. retain sparse distance assets without densification;
8. reject mismatched fingerprints, units, CRS, domain, and directed mode;
9. test round-trips, corruption, partial writes, atomic replacement, and
   cross-process reuse;
10. add a size/reload benchmark;
11. create `HANDOFF_0.0.14_WORKSPACE_PERSISTENCE.md`.

Do not begin exposure risk, PostGIS, Zarr, distributed execution, or remote
object storage until the core portable schema and atomic local contract are
stable.

## 19. Recovery procedure for a new conversation

1. Read this document completely.
2. Read `HANDOFF_NEXT_CONVERSATION.md`.
3. Inspect `git status --short --branch`.
4. Fetch and inspect `origin/main`.
5. Confirm `src/pykdex/__init__.py` reports `0.0.13`.
6. Confirm PR, commit, and CI fields against GitHub; do not trust pending text.
7. Run the focused network-time bandwidth tests.
8. Run the full test and coverage suite.
9. Run Black, isort, Ruff, mypy, strict MkDocs, distribution, archive, and
   isolated wheel checks.
10. Start 0.0.14 from the final merged `main`, not from an obsolete feature
    worktree.

## 20. Temporary infrastructure

No temporary GitHub workflow is part of this unit. Local virtual environments,
coverage files, built archives, rendered site output, and transfer artifacts
must remain untracked.
