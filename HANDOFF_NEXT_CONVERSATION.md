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
- initial reviewed source commit: `c55188f1a80bb53f68ed081d7dd7e4a0f21991f4`;
- formatted source and installed-wheel smoke-test commit: `91733f5519472401c54b01fee074562e50897d46`;
- Ruff-safe-fix commit: `412fad6cf4133ae7412b9db1430c400d45e2faff`;
- local validation: `145 passed`, branch coverage `81.41%`, 77 public symbols mapped, and all
  10 executable examples completed;
- online coverage and cross-platform tests confirmed the numerical regression suite; Black, isort,
  Ruff, and the installed-wheel version contract have now been corrected and independently checked;
- new public functionality: polygon renormalization, rectangular reflection, positive-definite
  bandwidth matrices, and query-centred balloon kNN;
- temporary transfer, formatting, Ruff-fix, apply, and export infrastructure: removed;
- permanent CI workflow: restored to the `main` version;
- current status: the final clean maintainer-triggered GitHub Actions quality, distribution, coverage,
  and platform matrix is pending;
- do not merge until final CI results are written into the versioned handoff.

## Next recommended unit after 0.0.8

Implement `HeatNetworkKDE` as a separate metric-graph heat-equation engine. Do not expose it as an
ordinary Gaussian radial-kernel name. The detailed implementation order is in the versioned handoff.

## Permanent process rule

Every completed development unit must create a new versioned root Markdown handoff, add/update the
corresponding `docs/development` page, update this file, and record actual final CI and merge state.
See `docs/development/handoff-policy.md`.
