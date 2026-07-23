# Spatial KDE

`SpatialKDE` estimates a normalized density or event intensity in Euclidean
space. Bandwidth is expressed in the same units as the input coordinates.

The estimator supports:

- scalar fixed and cross-validated bandwidths;
- event-specific kNN and Abramson sample-point bandwidths;
- support-specific balloon kNN bandwidths;
- global positive-definite bandwidth matrices;
- polygon boundary validation and per-event renormalization;
- rectangular one-generation reflection correction.

For projected geographic analysis, coordinates should use a suitable projected
CRS rather than longitude and latitude degrees. Boundary metadata, event
metadata, and support metadata are checked when explicitly supplied.

Matrix bandwidths use the covariance/shape convention
\(|H|^{-1/2}K(\|H^{-1/2}(x-x_i)\|)\). A scalar `h` is equivalent to
`H = h**2 * I`.

Boundary and anisotropy details are described in
[Spatial boundary correction and anisotropy](../guides/spatial-boundary-anisotropy.md).
