# Temporal network KDE

`TemporalNetworkKDE` estimates density or intensity jointly over a linear
network and time. It combines the existing network junction semantics with an
independent temporal kernel:

\[
\hat f(l,t)=
\sum_i a_i
K^{G}_{h_s}(x_i\rightarrow l)
\frac{1}{h_t}K_t\left(\frac{t-t_i}{h_t}\right),
\]

where \(a_i=w_i/\sum_r w_r\) for density and \(a_i=w_i\) for intensity.
The network factor \(K^G\) is determined by the selected `JunctionPolicy`;
time can be linear or cyclic. Scalar bandwidths use \(h_s,h_t\). Event-specific
sample-point bandwidths replace these with \(h_{s,i},h_{t,i}\), so both
normalizing factors belong to source event \(i\).

This is a separable product model. It does not replace the network distance
with a Euclidean distance, concatenate road coordinates with time, or solve a
heat equation in network-time.

## Prepare once

```python
from pykdex import (
    CyclicTimeDomain,
    NetworkTimeWorkspace,
    SpatialEvents,
    TemporalNetworkKDE,
)

events = SpatialEvents.from_array(
    coordinates,
    weights=weights,
    crs=network.crs,
    spatial_unit=network.spatial_unit,
)
workspace = NetworkTimeWorkspace.prepare(
    network,
    events,
    event_hours,
    temporal_unit="hours",
    lixel_length=20.0,
    temporal_resolution=1.0,
    time_domain=CyclicTimeDomain(period=24.0),
    max_snap_distance=50.0,
)
workspace = workspace.with_distances(cutoff=500.0)
```

Preparation performs four explicit operations:

1. snap raw spatial events to the canonical `LinearNetwork`;
2. retain the corresponding time for every accepted event by stable event ID;
3. build measured lixels;
4. form `ArixelSupport`, the Cartesian product of lixels and temporal cells.

Rejected snap records remain available through
`workspace.network_workspace.snap_result`. Their times are not silently
shifted onto another accepted event.

## Arixel measure and result order

For lixel \(j\) with actual length \(\Delta l_j\) and temporal cell \(q\) with
actual width \(\Delta t_q\),

\[
\mu_{qj}=\Delta l_j\Delta t_q.
\]

Remainder lixels and remainder temporal cells retain their actual measure.
Flat arrays are time-major. The structured shape is always
`(n_times, n_lixels)`:

```python
field = TemporalNetworkKDE(
    spatial_bandwidth=500.0,
    temporal_bandwidth=2.0,
    junction_policy="continuous",
).fit_predict(workspace)

grid = field.to_grid()
print(field.integral())
```

`NetworkTimeField.integral()` computes
\(\sum_{q,j}\hat f_{qj}\mu_{qj}\). `to_frame()` repeats the lixel attributes for
each temporal cell; `to_geodataframe()` repeats geometry; and `to_xarray()`
returns a `time × lixel` array when the optional array dependency is installed.

## Network junction policies

- `simple` uses shortest-path network distance. It supports finite and
  infinite-support spatial kernels and directed networks.
- `discontinuous` uses non-backtracking equal-split propagation and requires a
  finite-support spatial kernel.
- `continuous` uses the existing \(2/d\) transmission and \(2/d-1\)
  reflection coefficients. It requires a finite-support spatial kernel and an
  undirected network.

These constraints are identical to fixed-bandwidth `NetworkKDE`. The temporal
factor never changes a junction coefficient.

## Linear and cyclic time

Linear time evaluates the ordinary temporal kernel. On a cyclic domain of
period \(P\), pyKDEX evaluates the normalized periodic image sum:

\[
K_{\mathrm{cyclic},h_t}(\Delta t)
=
\sum_{k\in\mathbb Z}
\frac{1}{h_t}
K_t\left(\frac{|\Delta t+kP|}{h_t}\right).
\]

An `ArixelSupport` for cyclic time must cover exactly one complete period,
starting at the domain origin. This gives an unambiguous full-domain
network-time integral.

## Factorized distance asset

`NetworkTimeDistanceAsset` stores:

- a sparse event-to-lixel `NetworkDistanceAsset`;
- a `target_time × event` matrix of signed temporal offsets;
- the corresponding domain-aware temporal distances;
- network, event, support, time-domain, and workspace fingerprints.

It deliberately does not allocate an event-to-arixel distance matrix. Spatial
distances are reused across every time slice.

```python
from pykdex import build_network_time_distance_asset

asset = build_network_time_distance_asset(
    workspace.network_workspace,
    workspace.events,
    workspace.arixels,
    cutoff=500.0,
)
```

`TemporalNetworkKDE` reuses a compatible workspace asset for `simple`
propagation and rebuilds only when the cutoff or directed mode is insufficient.
`time_chunk_size` bounds the result multiplication by temporal slices without
changing numerical results.

## Candidate experiments

`NetworkTimeBandwidthExperiment` evaluates an ordered spatial-by-temporal
candidate grid. It prepares exact event-event network distances, signed
event-event and support-event temporal offsets, and either event-lixel
distances or maximum-bandwidth propagation traces once.

```python
from pykdex import NetworkTimeBandwidthExperiment, NetworkTimeBandwidths

experiment = NetworkTimeBandwidthExperiment(
    spatial_candidates=[200.0, 350.0, 500.0, 800.0],
    temporal_candidates=[0.5, 1.0, 2.0, 4.0],
    objective="least_squares",
    mode="joint",
    junction_policy="continuous",
)
selection = experiment.run(workspace)
bandwidths = NetworkTimeBandwidths(
    spatial=selection.spatial_bandwidth,
    temporal=selection.temporal_bandwidth,
)
```

Weighted product-kernel leave-one-out likelihood uses

\[
\hat f_{-i}(x_i,t_i)=
\frac{\sum_{r\ne i}w_r
K^G_{h_s}(x_r\rightarrow x_i)
K^T_{h_t}(t_i-t_r)}
{\sum_{r\ne i}w_r}.
\]

Only the event's own index is removed. A distinct event at the same network
location and time remains a valid zero-distance observation.

Network-time LSCV uses the actual arixel measure:

\[
CV(h_s,h_t)=
\sum_{q,j}\hat f(l_j,t_q)^2\Delta l_j\Delta t_q
-2\sum_i p_i\hat f_{-i}(x_i,t_i),
\qquad p_i=\frac{w_i}{\sum_r w_r}.
\]

`mode="joint"` chooses the first row-major minimum of this complete grid.
`mode="separate"` chooses spatial and temporal marginal minima independently,
then reports the joint score at that pair. Candidate order is retained and
ties are deterministic.

## Event-specific kNN bandwidths

`NetworkTimeKNNBandwidth` resolves independent source-event bandwidths:

\[
h_{s,i}=c_s d_G(x_i,x_{i,(k_s)}), \qquad
h_{t,i}=c_t d_T(t_i,t_{i,(k_t)}).
\]

```python
from pykdex import NetworkTimeKNNBandwidth

adaptive = NetworkTimeKNNBandwidth(
    spatial_k=5,
    temporal_k=3,
    minimum_spatial_bandwidth=20.0,
    minimum_temporal_bandwidth=0.25,
)
field = TemporalNetworkKDE(
    bandwidths=adaptive,
    junction_policy="continuous",
).fit_predict(workspace)
```

The diagonal is excluded by index, not by distance. Other colocated events and
duplicate times are legitimate neighbours, so a meaningful positive floor is
required if their selected distance is zero. Directed spatial kNN reports
events that cannot reach the requested neighbour rank instead of substituting
Euclidean distance.

## Current scope

Version 0.0.13 includes scalar candidate selection and independent
sample-point spatial/temporal kNN bandwidths. It does not estimate a fully
coupled per-event bandwidth matrix. Heat diffusion in network-time,
exposure-adjusted risk, persistence, and out-of-core execution remain separate
development units.
