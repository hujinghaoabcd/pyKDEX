# Bandwidths

pyKDEX separates bandwidth strategies from kernel shapes and estimators.

## Fixed bandwidth

```python
from pykdex import FixedBandwidth, SpatialKDE

model = SpatialKDE(bandwidth=FixedBandwidth(500.0))
```

## Cross-validated scalar bandwidths

`LikelihoodCVBandwidth` minimizes weighted negative leave-one-out log
likelihood and works with every normalized radial kernel.
`LeastSquaresCVBandwidth` uses the exact Gaussian convolution identity and
currently requires the Gaussian kernel.

```python
from pykdex import LikelihoodCVBandwidth, SpatialKDE

model = SpatialKDE(
    bandwidth=LikelihoodCVBandwidth(bounds=(100.0, 3000.0))
).fit(events)
print(model.bandwidth_selection_.to_frame())
```

## Sample-point k-nearest-neighbour bandwidth

`KNNBandwidth(k)` assigns each source event its distance to the k-th other
event. Dense areas receive smaller bandwidths and sparse areas receive larger
bandwidths. Duplicate locations may require a positive `minimum_bandwidth`.

## Abramson bandwidth

`AbramsonBandwidth` applies the square-root law by default:

\[
h_i = h_0\left(\frac{\tilde f(x_i)}{g}\right)^{-1/2}.
\]

The pilot bandwidth may be numeric or a scalar selection strategy. Optional
multiplier clipping limits extreme local bandwidths.

## Global matrix bandwidth

`BandwidthMatrix(H)` supplies one symmetric positive-definite covariance/shape
matrix. Matrix orientation is defined in coordinate space and therefore
requires the Euclidean metric.

## Query-centred balloon bandwidth

`BalloonKNNBandwidth(k)` computes one bandwidth per support point from the k-th
fitted-event distance. It is not interchangeable with sample-point kNN:
normalization uses the query-specific `h(x)` for all source kernels at that
query.
