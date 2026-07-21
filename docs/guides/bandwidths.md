# Bandwidths

pyKDEX separates bandwidth strategies from kernel shapes and estimators.

## Fixed bandwidth

```python
from pykdex import FixedBandwidth, SpatialKDE

model = SpatialKDE(bandwidth=FixedBandwidth(500.0))
```

## Cross-validated scalar bandwidths

`LikelihoodCVBandwidth` minimizes the weighted negative leave-one-out log
likelihood and works with every normalized radial kernel. `LeastSquaresCVBandwidth`
uses the exact Gaussian convolution identity and currently requires the Gaussian
kernel.

```python
from pykdex import LikelihoodCVBandwidth, SpatialKDE

model = SpatialKDE(
    bandwidth=LikelihoodCVBandwidth(bounds=(100.0, 3000.0))
).fit(events)

print(model.bandwidth_)
print(model.bandwidth_selection_.to_frame())
```

The optimizer works on log bandwidth, retains the complete objective trace, and
returns a `BandwidthSelectionResult`.

## k-nearest-neighbour bandwidth

`KNNBandwidth(k)` assigns each event its distance to the k-th other event. It is
a sample-point adaptive strategy: dense areas receive smaller bandwidths and
sparse areas receive larger bandwidths.

Duplicate event locations can produce zero neighbour distances. Supply a
meaningful `minimum_bandwidth` in coordinate units when duplicates are expected.

## Abramson bandwidth

`AbramsonBandwidth` applies the square-root law by default:

\[
h_i = h_0\left(\frac{\tilde f(x_i)}{g}\right)^{-1/2}.
\]

The pilot bandwidth may be numeric or a scalar selection strategy. Optional
multiplier clipping limits extremely small or large local bandwidths.
