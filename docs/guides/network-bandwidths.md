# Network bandwidth selection

`NetworkKDE` accepts one fixed bandwidth, a scalar bandwidth selected by cross-validation,
or one source-centred bandwidth per event.

## Event-to-event distance assets

```python
workspace = workspace.with_event_event_distances(directed=False)
```

The resulting `NetworkDistanceAsset` stores finite source–target pairs explicitly. The
diagonal remains zero, and duplicate events at the same network position remain distinct
off-diagonal zero-distance pairs. For directed networks, the matrix may be asymmetric and
unreachable pairs are omitted.

## k-nearest-neighbour bandwidths

```python
model = NetworkKDE(
    bandwidth=NetworkKNNBandwidth(k=20, minimum_bandwidth=5.0),
    junction_policy="continuous",
)
```

For event \(i\), the sample-point bandwidth is

\[
h_i = c\,d_G(x_i, x_{i,(k)}),
\]

where the self-pair is excluded by event index. A different event at exactly the same
position is not excluded. Set `minimum_bandwidth` when duplicate locations are possible.
On a directed network, the neighbour rank is based on locations reachable from the source
event; fitting fails explicitly when the requested rank is unavailable.

## Network likelihood cross-validation

`NetworkLikelihoodCV` minimizes weighted negative leave-one-out log likelihood:

\[
-\sum_i p_i\log\hat f_{-i,h}(x_i).
\]

The source event itself is excluded, while other coincident events remain in the estimate.
For `simple`, exact event-to-event shortest-path distances are reused. For path-based
policies, propagation traces are prepared once at the upper search bound and reused during
optimization.

```python
model = NetworkKDE(
    bandwidth=NetworkLikelihoodCVBandwidth(bounds=(100.0, 3000.0)),
    junction_policy="simple",
)
```

## Lixel-integrated network LSCV

`NetworkLeastSquaresCV` minimizes

\[
\sum_j \hat f_h(l_j)^2\,\Delta l_j
-2\sum_i p_i\hat f_{-i,h}(x_i),
\]

where each lixel contributes its actual length. This is a measured-support numerical LSCV,
not the Euclidean Gaussian convolution shortcut. Its accuracy therefore depends on lixel
resolution; bandwidth comparisons should use a fixed support.

```python
model = NetworkKDE(
    bandwidth=NetworkLeastSquaresCVBandwidth(bounds=(100.0, 3000.0)),
    junction_policy="continuous",
)
```

## Scope and restrictions

- Scalar selection uses density semantics even when the final estimator target is intensity.
- Path-based selection requires finite-support kernels.
- Continuous propagation remains restricted to undirected networks.
- Network kNN returns sample-point bandwidths, not balloon bandwidths.
- Heat-equation Gaussian NKDE and network Abramson bandwidths are later development units.
