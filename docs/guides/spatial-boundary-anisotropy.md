# Spatial boundary correction and anisotropy

## Study boundaries

Pass a `SpatialBoundary` to make the fitted study domain explicit. Events and
support locations must lie inside or on the polygon, and CRS/unit metadata must
match whenever both sides provide it.

```python
from pykdex import SpatialBoundary, SpatialKDE

boundary = SpatialBoundary.from_bounds((0.0, 0.0, 1000.0, 1000.0))
model = SpatialKDE(
    bandwidth=100.0,
    boundary=boundary,
    boundary_correction="renormalization",
).fit(events)
```

## Renormalization

For source event \(x_i\), pyKDEX divides the kernel by its in-domain mass:

\[
c_i = \int_W K_{H_i}(u-x_i)\,du,
\qquad
K^{\mathrm{renorm}}_{H_i}(x-x_i)=\frac{K_{H_i}(x-x_i)}{c_i}.
\]

Every corrected source kernel therefore integrates to one over the study
polygon, up to the selected numerical integration accuracy. Rectangular
Gaussian domains use analytical probabilities. General Polygon/MultiPolygon
domains use deterministic measured-cell quadrature: each cell is weighted by
its exact intersection area with the polygon. Holes and disconnected polygon
parts are retained.

`RenormalizationCorrection(cells_per_axis=...)` exposes the quadrature
resolution. It should be increased when the polygon has narrow features or a
compact kernel is small relative to the study extent.

## Reflection

`ReflectionCorrection` implements a one-generation rectangular reflection
estimator. Every two-dimensional source event contributes its original kernel,
four side mirrors, and four corner mirrors.

Reflection currently requires an axis-aligned rectangular boundary. It accepts
scalar, event-specific scalar, and diagonal matrix bandwidths. A full matrix
with cross-axis covariance is rejected because a correct reflection must also
transform covariance orientation.

Renormalization is the preferred method when per-event in-domain mass
preservation is required. Reflection is useful when a mirror interpretation is
scientifically appropriate and the rectangular-domain assumption is explicit.

## Bandwidth matrices

`BandwidthMatrix(H)` uses one global symmetric positive-definite matrix:

\[
K_H(x-x_i)=|H|^{-1/2}
K\left(\left\|H^{-1/2}(x-x_i)\right\|\right).
\]

A scalar bandwidth \(h\) is equivalent to \(H=h^2I\). Matrix bandwidths require
the Euclidean metric because their orientation is defined in coordinate space.

```python
import numpy as np
from pykdex import BandwidthMatrix, SpatialKDE

model = SpatialKDE(
    bandwidth=BandwidthMatrix(
        np.array([[40000.0, 12000.0], [12000.0, 16000.0]])
    )
).fit(events)
```

## Balloon kNN

`BalloonKNNBandwidth` chooses one bandwidth for each query/support point:

\[
h(x)=c\,d\left(x,x_{(k)}\right).
\]

No source event is excluded because the ranked distances are from a support
location to fitted events. This differs from `KNNBandwidth`, which assigns one
sample-point bandwidth to each source event.

```python
from pykdex import BalloonKNNBandwidth, SpatialKDE

model = SpatialKDE(
    bandwidth=BalloonKNNBandwidth(k=20, minimum_bandwidth=10.0)
).fit(events)
result = model.predict_result(support)
print(result.bandwidth)  # one value per support row
```

Boundary correction and balloon bandwidths are deliberately not combined in
0.0.8. The boundary mass would depend on every support-specific bandwidth and
must be defined as a separate query-centred correction algorithm rather than by
reusing sample-point normalization.
