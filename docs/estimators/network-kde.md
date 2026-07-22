# Network KDE

`NetworkKDE` evaluates one-dimensional radial kernels on measured lixel support.
It accepts a prepared `NetworkWorkspace`, uses the accepted snapped event
weights, and returns an immutable `NetworkField`.

```python
from pykdex import NetworkKDE, NetworkWorkspace, load_t_junction

dataset = load_t_junction()
workspace = NetworkWorkspace.prepare(
    dataset.network,
    dataset.raw_events,
    lixel_length=0.05,
    max_snap_distance=0.25,
)
field = NetworkKDE(
    bandwidth=0.8,
    kernel="epanechnikov",
    junction_policy="continuous",
).fit_predict(workspace)
```

## Junction policies

### Simple

The `simple` policy evaluates the kernel at shortest-path distance. It does not
split amplitude at a junction, so one event can contribute the full radial value
to several branches. This is a useful biased geodesic baseline and is the only
current network policy that accepts infinite-support kernels such as Gaussian.

### Discontinuous equal split

The `discontinuous` policy enumerates non-backtracking walks. After a path enters
a vertex of degree \(d\), its coefficient is divided equally among the
\(d-1\) forward directions. The reverse direction receives zero. Branch values
can therefore jump at a vertex.

### Continuous equal split

The `continuous` policy uses the vertex scattering coefficients

\[
T = \frac{2}{d}, \qquad R = \frac{2}{d} - 1,
\]

where \(T\) is assigned to transmitted directions and \(R\) to the reflected
direction. The signed reflected path supplies the backward correction required
for the limiting values on all incident edges to agree. Terminal vertices act
as reflecting boundaries. This policy is currently restricted to undirected
networks.

## Kernel and bandwidth scope

`NetworkKDE` accepts a positive scalar bandwidth, a network cross-validation
strategy, or one source-centred bandwidth per event. Discontinuous and continuous
path tracing still require compact kernels because an infinite-support kernel would
require infinitely many cyclic walks. Gaussian equal-split network smoothing is
deliberately reserved for a later heat-equation estimator. See the
[network bandwidth guide](../guides/network-bandwidths.md).

## Density and intensity

For event weights \(w_i\), density normalizes coefficients by
\(\sum_i w_i\), while intensity uses the original weights. Thus intensity is
measured per network-length unit and its integral approximates the total event
weight when the selected policy and finite network boundaries conserve mass.

```python
field.integral()
field.to_frame()
field.to_geodataframe()
```

The integral uses the actual length of every lixel, including remainder lixels.
A finer lixel length improves the midpoint-rule approximation without changing
the estimator bandwidth.
