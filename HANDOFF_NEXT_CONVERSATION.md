# pyKDEX current handoff

The active development unit is **0.0.8 spatial boundary correction, anisotropy, and balloon
bandwidths**. Read `HANDOFF_0.0.8_SPATIAL_BOUNDARY_ANISOTROPY.md` first. It records the
architecture, formulas, supported combinations, rejected combinations, implementation files,
validation results, limitations, recovery procedure, and next recommended unit.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- default branch: `main`;
- active development branch: `agent/spatial-boundary-anisotropy`;
- active pull request: `#7 Add spatial boundary correction and anisotropic KDE`;
- last stable completed version: `0.0.7`;
- development version: `0.0.8`;
- initial reviewed source commit: `c55188f1a80bb53f68ed081d7dd7e4a0f21991f4`;
- formatted source and installed-wheel smoke-test commit: `91733f5519472401c54b01fee074562e50897d46`;
- Ruff-safe-fix commit: `412fad6cf4133ae7412b9db1430c400d45e2faff`;
- finalized validation and versioned handoff commit: `cef3b28526d1337eba83f493febd9c291e75bf8e`;
- validation: `145 passed`, branch coverage `81.41%`, 77 public symbols mapped, and all
  10 executable examples completed;
- final clean pull-request CI run #101 (`29974418301`): success;
- Black, isort, Ruff, mypy, strict MkDocs, distributions, installed-wheel smoke tests, and the
  Linux/Windows/macOS Python 3.11-3.14 matrix passed;
- temporary transfer, apply, export, formatting, Ruff-fix, finalizer, and diagnostic
  infrastructure: removed;
- permanent CI workflow: restored;
- current status: implementation, validation, and recovery records are complete; the final
  documentation-complete CI and PR #7 squash merge remain pending.

## Next recommended unit after 0.0.8

Implement `HeatNetworkKDE` as a separate metric-graph heat-equation engine. Do not expose it as an
ordinary Gaussian radial-kernel name. The detailed implementation order is in the versioned handoff.

## Permanent process rule

Every completed development unit must create a new versioned root Markdown handoff, add/update the
corresponding `docs/development` page, update this file, and record actual final CI and merge state.
See `docs/development/handoff-policy.md`.
