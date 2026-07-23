# pyKDEX current handoff

The active development unit is **0.0.8 spatial boundary correction, anisotropy, and balloon
bandwidths**. Read `HANDOFF_0.0.8_SPATIAL_BOUNDARY_ANISOTROPY.md` first. It records the
architecture, formulas, supported combinations, rejected combinations, implementation files,
validation contract, limitations, recovery procedure, and next recommended unit.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- default branch: `main`;
- active development branch: `agent/spatial-boundary-anisotropy`;
- active pull request: `#7 Add spatial boundary correction and anisotropic KDE`;
- last stable completed version: `0.0.7`;
- development version: `0.0.8`;
- local validation: `145 passed`, branch coverage `81.41%`;
- new public functionality: polygon renormalization, rectangular reflection, positive-definite
  bandwidth matrices, and query-centred balloon kNN;
- current status: implementation, tests, examples, and recovery documentation are prepared;
  formal quality checks and clean cross-platform GitHub Actions remain pending;
- do not merge until temporary source-export infrastructure is removed and final CI results are
  written into the versioned handoff.

## Next recommended unit after 0.0.8

Implement `HeatNetworkKDE` as a separate metric-graph heat-equation engine. Do not expose it as an
ordinary Gaussian radial-kernel name. The detailed implementation order is in the versioned handoff.

## Permanent process rule

Every completed development unit must create a new versioned root Markdown handoff, add/update the
corresponding `docs/development` page, update this file, and record actual final CI and merge state.
See `docs/development/handoff-policy.md`.
