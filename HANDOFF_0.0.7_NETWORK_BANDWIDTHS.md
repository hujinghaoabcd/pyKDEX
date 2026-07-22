# pyKDEX 0.0.7 handoff: network bandwidth selection and adaptive NetworkKDE

## 1. Purpose of this document

This file is the recoverable engineering record for the pyKDEX 0.0.7 development unit.
It is written so that a new conversation can continue the project without relying on prior
chat history, a local scratch directory, or undocumented assumptions.

Repository: `hujinghaoabcd/pyKDEX`  
Development branch: `agent/network-bandwidths`  
Pull request: `#6 Add network bandwidth selection and adaptive NetworkKDE`

The document must be finalized with the merged commit and final CI result before the unit is
considered complete.

## 2. Project design in force

pyKDEX is a composition-oriented Python framework for spatial, network, spatiotemporal, and
network-time kernel density estimation. It follows the engineering conventions of pyGWRx:

- `src/` package layout;
- one NumPy/SciPy numerical route with acceleration hidden internally;
- atomic fitted state: failed `fit()` calls leave estimators unfitted;
- copied, read-only fitted inputs and result arrays;
- structured dataclass results rather than untyped dictionaries;
- strict CRS, unit, identifier, support-measure, and fingerprint contracts;
- Google-style docstrings, English source comments, SPDX headers, and author Jinghao Hu;
- pytest with branch coverage, Black, isort, Ruff, mypy, strict MkDocs, distribution checks,
  installed-wheel smoke tests, and Linux/Windows/macOS CI on Python 3.11–3.14;
- independent implementation: external KDE software is used only for research comparison,
  not as a runtime dependency or source-code donor.

The network architecture remains:

`external graph/roads → adapter → LinearNetwork → NetworkEvents → LixelSupport →`
`NetworkWorkspace → bandwidth strategy + kernel + JunctionPolicy → NetworkKDE → NetworkField`.

OSMnx and NetworkX are input ecosystems, not the internal model.

## 3. Problem solved in 0.0.7

Version 0.0.6 supported only one user-supplied scalar bandwidth. Version 0.0.7 adds the
network-specific bandwidth layer required for research use:

1. exact event-to-event network-distance assets;
2. source-centred network k-nearest-neighbour bandwidths;
3. weighted network leave-one-out likelihood selection;
4. lixel-integrated network least-squares cross-validation;
5. scalar and event-specific bandwidth integration with `NetworkKDE`;
6. reuse of prepared distances and propagation traces during optimization.

The implementation deliberately uses a separate `BaseNetworkBandwidth`. The existing
`BaseBandwidth` is Euclidean-estimator oriented and requires an array/metric context; forcing
network workspaces into that interface would hide topology, direction, lixel measure, and
junction propagation requirements.

## 4. Public API added

### Distance and workspace

- `build_event_event_distances`
- `NetworkWorkspace.event_distance_asset`
- `NetworkWorkspace.with_event_event_distances()`

The event-distance asset is source-by-target. Self-pairs are explicit zero entries. A second
event at the same network position remains an off-diagonal zero-distance pair. Directed
assets may be asymmetric, and unreachable pairs are omitted rather than represented as a
large sentinel.

### Bandwidth strategies

- `BaseNetworkBandwidth`
- `FixedNetworkBandwidth`
- `NetworkKNNBandwidth`
- `NetworkLikelihoodCVBandwidth`
- `NetworkLeastSquaresCVBandwidth`

### Direct selectors and cache

- `NetworkLikelihoodCV`
- `NetworkLeastSquaresCV`
- `NetworkSelectionCache`

`NetworkKDE.bandwidth` now accepts either a positive number or a network bandwidth strategy.
After fitting, `bandwidth_` is either a float or a read-only one-dimensional array with one
value per accepted event. `bandwidth_selection_` stores the full optimization result for CV
wrappers.

`NetworkField.bandwidth` supports scalar and event-specific values, and `NetworkField.adaptive`
reports whether an adaptive sample-point bandwidth was used.

## 5. Numerical definitions

### 5.1 Network kNN sample-point bandwidth

For source event `i`:

\[
h_i = c\,d_G(x_i,x_{i,(k)}),
\]

where `x_{i,(k)}` is the k-th other event under the selected directed or undirected network
distance. The source event is excluded by event index, not by distance. Consequently,
coincident but distinct events are valid neighbours at distance zero. When zero distances
would produce a non-positive bandwidth, the user must supply a meaningful
`minimum_bandwidth`.

On directed networks, the rank is based on events reachable from the source. The strategy
raises an explicit error when fewer than `k` other events are reachable.

### 5.2 Weighted network LOO likelihood

For event weights `w_i`, total weight `W`, and normalized target weights `p_i=w_i/W`:

\[
\hat f_{-i,h}(x_i)=
\frac{\sum_{r\ne i}w_r K_{r\rightarrow i,h}}
{W-w_i},
\]

\[
CV_{LL}(h)=-\sum_i p_i\log\max(\hat f_{-i,h}(x_i),\epsilon).
\]

For the simple policy, `K_{r→i,h}` is evaluated from exact source-to-target network
distances. For discontinuous and continuous policies, the kernel coefficient includes the
signed or split propagation amplitude. Only the source event itself is removed; other
coincident events remain.

### 5.3 Lixel-integrated network LSCV

\[
CV_{LS}(h)=
\sum_j \hat f_h(l_j)^2\Delta l_j
-2\sum_i p_i\hat f_{-i,h}(x_i).
\]

`l_j` is a lixel centre and `Δl_j` is that lixel's actual length. The final residual lixel on
an edge may be shorter than the requested lixel length and is weighted accordingly. This is
a measured-support numerical LSCV, not the Euclidean Gaussian convolution identity. The
same lixel support must be retained when comparing bandwidths.

### 5.4 Sample-point evaluation

With event-specific bandwidths, each source event uses its own `h_i` in both standardization
and normalization:

\[
K\left(d/h_i\right)/h_i.
\]

This convention is used for simple, discontinuous, and continuous policies. It is not a
balloon estimator.

## 6. Cache and performance principles

`NetworkSelectionCache` records:

- complete event-to-event distances;
- event-to-lixel distances for simple-policy objectives;
- upper-bound propagation traces for path-based objectives;
- upper search bandwidth, policy, direction, and workspace fingerprint.

For path-based optimization, traces are prepared once at the upper bandwidth bound and then
re-evaluated at smaller trial bandwidths. For simple-policy LSCV, event-to-lixel distances
are prepared once. Cached assets are accepted only when fingerprints, direction, weight, and
cutoff coverage match.

The optimizer remains deterministic bounded minimization in log-bandwidth space and returns
all visited bandwidths and scores through `BandwidthSelectionResult`.

## 7. Important implementation files

- `src/pykdex/network/distance.py`
- `src/pykdex/network/workspace.py`
- `src/pykdex/network/evaluation.py`
- `src/pykdex/bandwidths/network.py`
- `src/pykdex/selection/network.py`
- `src/pykdex/estimators/network_kde.py`
- `src/pykdex/core/network_results.py`
- `tests/test_network_bandwidths.py`
- `examples/09_network_bandwidths.py`
- `docs/guides/network-bandwidths.md`
- `docs/api/network-bandwidths.md`

## 8. Validation contract

The final handoff must record exact observed counts after the clean GitHub Actions run.
The current local validation covers:

- explicit self and duplicate zero-distance pairs;
- event-distance workspace caching and fingerprint changes;
- manual kNN distance values;
- duplicate-location floor handling;
- adaptive simple and continuous NetworkKDE;
- deterministic likelihood selection;
- path-based lixel LSCV and cached traces;
- estimator wrapper integration and selection-result retention;
- directed unreachable-neighbour failure;
- disconnected automatic-bound failure;
- existing 0.0.1–0.0.6 regression suite.

Before merge, verify:

- full pytest and branch coverage ≥80%;
- Black, isort, Ruff, and mypy;
- public API/example coverage;
- strict MkDocs build;
- wheel, sdist, Twine, and installed-wheel smoke test;
- Linux, Windows, and macOS with Python 3.11–3.14;
- temporary source-export and diagnostic workflows removed.

## 9. Deliberate exclusions

The following are not part of 0.0.7:

- network Abramson pilot adaptation;
- balloon kNN bandwidths evaluated at target locations;
- heat-equation Gaussian NKDE;
- network boundary correction beyond current junction definitions;
- temporal, spatiotemporal, and network-time data objects;
- relative-risk KDE, bootstrap uncertainty, and significance envelopes;
- persistent Zarr/PostGIS workspace serialization;
- low-level compiled acceleration.

No empty public placeholders should be added for these features.

## 10. Next recommended development unit

The next unit should return to the unfinished ordinary spatial KDE family before temporal
expansion:

1. polygon boundary renormalization;
2. reflection boundary correction for supported boundary geometries;
3. full positive-definite bandwidth matrices and anisotropic distance transforms;
4. balloon kNN bandwidths;
5. boundary-aware mass and analytical tests;
6. detailed handoff document following the project handoff policy.

An alternative is heat-equation NKDE, but it should remain a separate numerical engine and
must not be represented as an ordinary radial-kernel name.

## 11. Recovery procedure for a new conversation

1. Open repository `hujinghaoabcd/pyKDEX`.
2. Read this file, `HANDOFF_NEXT_CONVERSATION.md`, `CHANGELOG.md`, and
   `BASELINE_VALIDATION.md`.
3. Confirm the default branch and latest merged version in `src/pykdex/__init__.py`.
4. Check the most recent PR and final Actions run rather than trusting old chat claims.
5. Run `pytest`, branch coverage, quality checks, strict docs, and build checks locally when a
   materialized source tree is available.
6. Start the next unit on a dedicated `agent/...` branch and draft PR.
7. Create a new versioned handoff Markdown file before merging.

## 12. Finalization fields

- Final version: `0.0.7`
- Final test count: `137 passed`
- Final branch coverage: `81.97%`
- Final CI run: GitHub Actions run `#74` (`29902449039`), conclusion `success`
- Merge commit: `eec1bbee65e6131c942f67adb8286e6a4a56af26`
- Temporary workflow removal: completed
