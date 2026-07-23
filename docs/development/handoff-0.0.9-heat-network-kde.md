# 0.0.9 heat-equation network KDE handoff

The complete recoverable engineering record is maintained in
`HANDOFF_0.0.9_HEAT_NETWORK_KDE.md` at the repository root. This documentation
page summarizes the permanent numerical contract.

## Implemented architecture

`HeatNetworkKDE` is a separate metric-graph heat-equation estimator, not a
Gaussian alias for radial `NetworkKDE`. `NetworkHeatOperator` assembles measured
piecewise-linear finite elements with:

- exact event-offset insertion;
- exact lixel-boundary insertion;
- shared vertex degrees of freedom;
- lumped nodal measures;
- sparse symmetric stiffness;
- connected-component labels and deterministic fingerprints.

The evolution equation is

\[
M\frac{du}{dt}+Ku=0,
\qquad
A=M^{-1/2}KM^{-1/2}.
\]

Shared vertex degrees of freedom enforce continuity. The weak form enforces
Kirchhoff flux balance and natural zero-flux conditions at terminal vertices.
Directed networks and self-loop edge records are rejected in 0.0.9.

Events inject density-normalized or raw intensity mass at their exact mesh
nodes. Output values are exact piecewise-linear lixel cell averages, so
`NetworkField.integral()` reproduces component mass to numerical precision.

## Validation

The new tests compare against analytical Neumann interval and periodic ring
heat kernels, verify T-junction continuity, disconnected-component isolation,
weighted density/intensity mass, exact event placement, sparse/read-only assets,
deterministic fingerprints, validation errors, and atomic failed-fit state.

The final test, coverage, CI, PR, and merge identifiers are recorded in the root
handoff after publication.

## Next unit

0.0.10 should add reusable heat solver plans, batched diffusion-time
evaluation, heat likelihood/LSCV selection, and grid-network performance
benchmarks. It must retain the independent heat-estimator identity.
