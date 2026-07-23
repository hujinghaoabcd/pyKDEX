# Spatiotemporal KDE

`SpatiotemporalKDE` estimates an ordinary Euclidean space-time density or
intensity with independent spatial and temporal kernels:

\[
\hat f(x,t)=
\sum_i a_i
\frac{1}{h_s^d}K_s\left(\frac{d_s(x,x_i)}{h_s}\right)
\frac{1}{h_t}K_t\left(\frac{t-t_i}{h_t}\right).
\]

For density, \(a_i=w_i/\sum_r w_r\). For intensity, \(a_i=w_i\).
Spatial and temporal coordinates are never concatenated: their units, domains,
metrics, kernels, and bandwidths remain explicit.

## Linear time

```python
from pykdex import (
    LinearTimeDomain,
    SpatiotemporalEvents,
    SpatiotemporalKDE,
    SpatiotemporalPointSupport,
)

domain = LinearTimeDomain()
events = SpatiotemporalEvents.from_arrays(
    spatial_coordinates,
    times,
    weights=weights,
    spatial_unit="km",
    temporal_unit="hours",
    time_domain=domain,
)
support = SpatiotemporalPointSupport.from_arrays(
    query_coordinates,
    query_times,
    spatial_unit="km",
    temporal_unit="hours",
    time_domain=domain,
)
result = SpatiotemporalKDE(
    spatial_bandwidth=0.5,
    temporal_bandwidth=2.0,
).fit_predict(events, support)
```

## Cyclic time

`CyclicTimeDomain(period=24)` represents time of day. A cyclic kernel is not
computed from minimum circular distance alone. pyKDEX sums periodic kernel
images:

\[
K_{\mathrm{cyclic},h}(\Delta t)
=
\sum_{k\in\mathbb Z}
\frac{1}{h}K\left(\frac{|\Delta t+kP|}{h}\right).
\]

This distinction matters for Gaussian or exponential kernels and preserves
unit mass over one complete period.

```python
from pykdex import CyclicTimeDomain

domain = CyclicTimeDomain(period=24.0)
```

Finite-support kernels are summed over every intersecting image. Gaussian and
exponential tails are truncated by `cyclic_tail_tolerance`.

## Measured grids and xarray

`SpatiotemporalGridSupport` is the Cartesian product of a measured
`GridSupport` and temporal cells. Its measure is spatial cell area multiplied
by actual temporal cell width, including remainder cells.

```python
from pykdex import GridSupport, SpatiotemporalGridSupport

spatial = GridSupport.from_bounds(
    (0.0, 0.0, 10.0, 10.0),
    resolution=0.25,
    spatial_unit="km",
)
grid = SpatiotemporalGridSupport.from_spatial_grid(
    spatial,
    temporal_bounds=(0.0, 24.0),
    temporal_resolution=1.0,
    temporal_unit="hours",
)
result = model.predict_result(grid)
print(result.integral())
array = result.to_xarray()
```

`to_xarray()` requires the optional `array` dependencies:

```bash
python -m pip install "pyKDEX[array]"
```

The core estimator has no xarray runtime dependency.

## Reusable distances and bandwidth experiments

```python
from pykdex import (
    SpatiotemporalBandwidthExperiment,
    build_spatiotemporal_distance_asset,
)

asset = build_spatiotemporal_distance_asset(events, events)
selection = SpatiotemporalBandwidthExperiment(
    spatial_candidates=[0.25, 0.5, 1.0],
    temporal_candidates=[0.5, 1.0, 2.0],
    mode="joint",
).run(events, distance_asset=asset)
```

`joint` evaluates the full product grid by weighted leave-one-out likelihood.
`separate` selects the two marginal bandwidths independently and then reports
the product-kernel score at that pair. Both modes reuse one distance asset and
retain deterministic candidate order.

This estimator is ordinary Euclidean space-time KDE. It does not define
network-time distance, arixels, or temporal propagation on roads.
