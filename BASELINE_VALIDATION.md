# pyKDEX 0.0.13 validation

Validation date: 2026-07-23

## Implemented public functionality

- scalar, cross-validated, sample-point kNN, Abramson, matrix, and balloon
  spatial bandwidths;
- polygon boundary validation, renormalization, and rectangular reflection;
- explicit linear and cyclic time domains;
- ordinary space-time events, measured grids, product KDE, and bandwidth
  experiments;
- canonical networks, auditable snapping, measured lixels, exact distances,
  traversal, and three junction policies;
- fixed/adaptive traversal `NetworkKDE`;
- finite-element `HeatNetworkKDE`, reusable plans, batch experiments, and
  heat-time selection;
- network-time events, measured arixels, factorized assets, and reusable
  workspaces;
- fixed/adaptive `TemporalNetworkKDE`;
- network-time likelihood and measured LSCV candidate experiments;
- structured provenance, units, support measures, identifiers, and
  fingerprints.

## Network-time bandwidth validation

- scalar or event-specific bandwidth components are owned and read-only;
- event-specific arrays must match accepted event count;
- spatial and temporal kNN ranks are independent;
- only the event's own diagonal index is excluded;
- colocated other events and duplicate times remain valid zero-distance
  neighbours;
- zero selected distances require explicit positive floors;
- directed-unreachable spatial neighbour ranks fail explicitly;
- event-specific bandwidths evaluate under simple and path-based policies;
- path policies still reject infinite-support spatial kernels;
- cyclic temporal evaluation accepts one source bandwidth per event and
  preserves periodic image normalization;
- joint and separate likelihood experiments are deterministic;
- simple selection reuses a compatible workspace distance asset;
- continuous selection reuses maximum-candidate propagation traces;
- network-time LSCV integrates actual arixel measure;
- result candidate arrays and score matrices are immutable;
- cache fingerprints agree with selection results.

## Existing numerical validation retained

- ordinary spatial, boundary, anisotropic, and adaptive KDE references;
- ordinary space-time products, cyclic images, mass, and bandwidth experiments;
- exact event/lixel network distances and junction propagation;
- simple, discontinuous, and continuous `NetworkKDE` references;
- finite-interval, ring, Kirchhoff, and mass-conserving heat references;
- fixed temporal-network products, cyclic mass, direction, chunking, and
  structured exports.

## Observed local validation

- focused network-time and neighboring tests: `22 passed`;
- full regression: `226 passed`;
- branch coverage: `81.15%`, above required `80%`;
- public API/example map: `117 public symbols`;
- executable examples: all `15` passed;
- benchmark: `100` events, `6912` arixels, and `64` candidate pairs completed;
- Black, isort, Ruff, mypy, and strict MkDocs: passed;
- wheel/sdist build, Twine, archive verification, and isolated installation:
  passed.

## GitHub state

- development branch: `agent/network-time-bandwidths`;
- PR: pending;
- feature implementation commit: pending;
- clean PR CI: pending;
- squash merge commit: pending;
- post-merge handoff commit: pending;
- post-merge `main` CI: pending.

No GitHub success is claimed before observation.

## Deliberate exclusions

- heat-equation network-time diffusion;
- fully coupled or nonseparable per-event bandwidths;
- causal or time-dependent-network kernels;
- exposure-adjusted risk and uncertainty;
- persistent workspaces and distance assets;
- PostGIS/Zarr storage;
- distributed or compiled execution.
