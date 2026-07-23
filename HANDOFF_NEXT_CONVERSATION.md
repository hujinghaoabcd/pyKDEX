# pyKDEX current handoff

The latest completed development unit is **0.0.8 spatial boundary correction, anisotropy,
and balloon bandwidths**. Read `HANDOFF_0.0.8_SPATIAL_BOUNDARY_ANISOTROPY.md` first. It
contains the complete architecture, formulas, supported and rejected combinations,
implementation files, validation results, limitations, recovery procedure, and next unit.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- default branch: `main`;
- latest stable development version: `0.0.8`;
- completed pull request: `#7 Add spatial boundary correction and anisotropic KDE`;
- PR #7 squash merge commit: `9f0aef9e8be57cc9e1c6beb210225b421501a623`;
- post-merge handoff-record commit: `a7b1ae9461ab90c3ba7c89b6043693ffcb26e412`;
- post-merge main verification source commit: `4e73ea1fc2812305f47c702444860e8c90ac9fd4`;
- validation: `145 passed`, branch coverage `81.41%`, 77 public symbols mapped, and all
  10 executable examples completed;
- final documentation-complete pull-request CI run #104 (`29974693141`): success;
- Black, isort, Ruff, mypy, strict MkDocs, distributions, installed-wheel smoke tests, and
  Linux/Windows/macOS on Python 3.11-3.14 passed;
- temporary transfer, patch, apply, export, formatting, Ruff-fix, finalizer, merge-recorder,
  and diagnostic infrastructure: removed;
- permanent CI workflow: restored on `main`;
- post-merge verification PR: pending full permanent-CI result;
- unit status: complete and merged into `main`; this verification PR records the final exact
  repository-state check without adding a temporary workflow.

## Implemented in 0.0.8

- polygon boundary renormalization with exact rectangular Gaussian mass and deterministic
  measured-cell Polygon/MultiPolygon quadrature;
- one-generation reflection correction for explicitly supported axis-aligned rectangles;
- global symmetric positive-definite bandwidth matrices with Cholesky anisotropic transforms;
- query-centred balloon kNN bandwidths with support-bandwidth result metadata;
- strict boundary CRS, unit, containment, compatibility, and atomic failed-fit contracts.

## Next recommended development unit

Implement `HeatNetworkKDE` as a separate metric-graph heat-equation engine:

1. define the metric-graph Laplacian and vertex conditions;
2. build a measured sparse edge discretization;
3. map event mass without losing along-edge offsets;
4. solve diffusion using a validated stable sparse method;
5. return `NetworkField` mass and continuity diagnostics;
6. validate line, terminal interval, T-junction, ring, and disconnected references;
7. create `HANDOFF_0.0.9_HEAT_NETWORK_KDE.md` before merge.

Heat KDE must not be exposed as an ordinary Gaussian radial-kernel alias.

## Permanent process rule

Every completed development unit must create a versioned root Markdown handoff, update the
corresponding `docs/development` page and this file, and record actual CI and merge state.
See `docs/development/handoff-policy.md`.
