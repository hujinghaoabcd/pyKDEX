# pyKDEX current handoff

The latest completed development unit is **0.0.10 reusable heat plans, batch
diffusion times, and heat-time selection**. Read
`HANDOFF_0.0.10_HEAT_SELECTION_BATCH.md` first for the complete design,
mathematics, implementation, validation, limitations, recovery procedure, and
next-unit record.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- default branch: `main`;
- latest stable version: `0.0.10`;
- merged feature branch: `agent/heat-selection-batch`;
- pull request: `#10 Add reusable heat plans and time selection`;
- feature commit: `9342a414f99947137a6cf45051687f15c065c8f2`;
- first complete CI run `#118` (`29996503549`): success;
- final clean CI run `#119` (`29996740029`): success;
- PR #10 squash merge commit:
  `49bb6ba36f9ac1dc82a655ee23a06397dba0a529`;
- post-merge handoff commit:
  `7459ce3666955caded92b2b7eecb82afb321f439`;
- observed local validation: `178 passed`, branch coverage `81.67%`;
- public API/example map: `91 public symbols`, all `12` examples executable;
- Black, isort, Ruff, mypy, strict docs, distributions, and isolated wheel
  smoke: passed;
- unit status: implementation, documentation, validation, final CI, and feature
  merge are complete;
- no temporary repository workflow was added.

## Implemented in 0.0.10

- reusable read-only `HeatComputePlan`;
- dense spectral decomposition reuse and sparse generator reuse;
- multi-source, ordered multi-time heat evolution;
- `HeatNetworkExperiment` and `HeatNetworkBatchResult`;
- exact piecewise-linear squared-field integration;
- weighted heat leave-one-out likelihood;
- exact finite-element heat LSCV;
- fixed and selected heat-time strategies for `HeatNetworkKDE`;
- strict network/event/support/mesh compatibility fingerprints;
- deterministic grid performance and memory benchmark.

## Next recommended development unit

Build the ordinary temporal and spatiotemporal data foundation before
temporal-network KDE:

1. explicit linear and cyclic time domains;
2. immutable space-time events with independent spatial and temporal units;
3. measured space-time support and xarray-compatible structured results;
4. separable product STKDE with explicit spatial and temporal kernels/metrics;
5. shared spatial/temporal distance assets and deterministic bandwidth experiments;
6. moving-hotspot, cyclic-boundary, mass, weighting, and chunk-invariance tests;
7. `HANDOFF_0.0.11_SPATIOTEMPORAL_FOUNDATION.md`.

## Permanent process rule

Every completed development unit must create a detailed versioned root Markdown
handoff, add/update the corresponding `docs/development` page, update this file,
and record actual validation, CI, PR, and merge state. See
`docs/development/handoff-policy.md`.
