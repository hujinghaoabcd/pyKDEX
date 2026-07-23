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

## Reusable compute plan and batch times

Repeated fits should reuse a `HeatComputePlan`, which owns the assembled
symmetric generator and, for small and medium systems, one read-only
eigendecomposition:

```python
from pykdex import HeatNetworkExperiment, build_heat_compute_plan

plan = build_heat_compute_plan(workspace, mesh_size=0.025)
batch = HeatNetworkExperiment(
    diffusion_times=[0.02, 0.08, 0.2],
    mesh_size=0.025,
).run(workspace, compute_plan=plan)

for time, result in zip(batch.diffusion_times, batch.fields, strict=True):
    print(time, result.integral())
```

Requested order and duplicate times are retained. Dense plans reuse one
spectral decomposition across all times and sources. Sparse plans reuse the
same generator and apply deterministic Krylov exponential products. A plan
validates the network, accepted-event, lixel-support, and mesh fingerprints
before use.

## Selecting diffusion time

The authoritative heat smoothing parameter is `diffusion_time`, not the
equivalent Gaussian distance \(\sqrt{2t}\). pyKDEX provides two heat-specific
selectors:

```python
from pykdex import HeatLeastSquaresCV, HeatLikelihoodCVTime

model = HeatNetworkKDE(
    diffusion_time=HeatLikelihoodCVTime(bounds=(0.005, 0.5)),
    mesh_size=0.025,
).fit(workspace, compute_plan=plan)

lscv = HeatLeastSquaresCV(bounds=(0.005, 0.5))
selection = lscv.select(workspace, compute_plan=plan)
print(selection.bandwidth)  # selected diffusion time
```

`HeatLikelihoodCV` evaluates the heat transition density at event locations,
deletes only each event's own diagonal contribution, and computes weighted
leave-one-out log likelihood. Distinct events at the same network position
remain valid contributors.

`HeatLeastSquaresCV` computes

\[
\int_G \hat f_t(x)^2\,d\ell(x)
-2\sum_i p_i\hat f_{-i,t}(x_i).
\]

The squared-field term is integrated exactly on every piecewise-linear finite
element using

\[
\int_0^\ell u(x)^2\,dx
=\frac{\ell}{3}(a^2+ab+b^2),
\]

then summed over the metric graph. Both selectors return the project's generic
`BandwidthSelectionResult`; its `bandwidth` field contains the selected
diffusion time for compatibility with existing optimization tooling.
