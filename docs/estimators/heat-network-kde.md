# Heat-equation network KDE

`HeatNetworkKDE` is a separate numerical estimator for Gaussian-like smoothing
on an undirected metric graph. It is not a radial kernel name passed to
`NetworkKDE`: its computation, boundary conditions, and junction semantics are
different.

```python
from pykdex import HeatNetworkKDE, NetworkWorkspace, load_t_junction

dataset = load_t_junction()
workspace = NetworkWorkspace.prepare(
    dataset.network,
    dataset.raw_events,
    lixel_length=0.05,
    max_snap_distance=0.25,
)
field = HeatNetworkKDE(
    diffusion_time=0.08,
    mesh_size=0.025,
).fit_predict(workspace)

print(field.integral())
```

## Numerical definition

The metric graph is divided into measured one-dimensional finite elements.
Original vertices are shared degrees of freedom. Every accepted event offset
and lixel boundary is inserted into the mesh exactly, and optional uniform
refinement limits element length.

With lumped mass matrix \(M\), stiffness matrix \(K\), and nodal density \(u\),
the semi-discrete heat equation is

\[
M\frac{du}{dt}+Ku=0.
\]

The symmetric generator

\[
A=M^{-1/2}KM^{-1/2}
\]

is evolved at the requested positive `diffusion_time`. Small and medium systems
use symmetric eigendecomposition; larger systems use sparse exponential
multiplication. The effective Gaussian bandwidth recorded in the result is
\(\sqrt{2t}\).

## Junction and terminal conditions

All incident edges reference one shared value at a network vertex. Continuity
therefore holds algebraically rather than through a post-processing correction.
The weak finite-element form imposes Kirchhoff flux balance. Degree-one
terminals use the natural zero-flux Neumann boundary condition.

Directed networks are rejected: a directed diffusion process requires a
different generator and stationary-measure contract. Self-loop edge records are
also rejected in this release; ordinary cycles made from two or more edges are
supported.

## Measured output and mass

Events inject mass at their exact along-edge offsets. Density divides weights by
their total; intensity retains original event weights. Empty disconnected
components remain zero, and mass is checked independently in every occupied
component.

`HeatNetworkKDE` returns exact piecewise-linear **lixel cell averages**, not
samples at lixel centres. Therefore:

```python
field.integral()
```

uses lixel lengths and reproduces the normalized density mass or total intensity
weight to numerical precision. The result metadata records
`lixel_evaluation="cell_average"`.

## Reusable operator

The measured operator can be inspected or prepared separately:

```python
from pykdex import build_network_heat_operator

operator = build_network_heat_operator(workspace, mesh_size=0.025)
print(operator.n_dofs, operator.n_segments, operator.fingerprint)
```

`NetworkHeatOperator` stores read-only nodal measures, the sparse stiffness
matrix, per-edge breakpoints and degree-of-freedom maps, exact event nodes, and
connected-component labels.
