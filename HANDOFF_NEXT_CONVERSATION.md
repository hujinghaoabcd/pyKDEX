# pyKDEX current handoff

The active development unit is **0.0.9 heat-equation KDE on measured metric
graphs**. Read `HANDOFF_0.0.9_HEAT_NETWORK_KDE.md` first for the full design,
implementation, validation, limitation, recovery, and next-unit record.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- default branch: `main`;
- stable base version: `0.0.8`;
- active branch: `agent/heat-network-kde`;
- source version: `0.0.9`;
- 0.0.9 pull request and merge commit: pending publication;
- observed local validation: `161 passed`, branch coverage `81.76%`,
  80 public symbols mapped, all 11 examples, formatting, lint, typing, strict
  docs, distributions, and isolated wheel smoke passed;
- final GitHub CI and merge fields: pending publication;
- no temporary repository workflow has been added.

## Implemented in 0.0.9

- separate public `HeatNetworkKDE`;
- reusable read-only `NetworkHeatOperator`;
- measured piecewise-linear metric-graph finite elements;
- exact event and lixel-boundary mesh insertion;
- shared vertex continuity and Kirchhoff flux balance;
- natural Neumann terminal conditions;
- density/intensity and per-component mass conservation;
- exact lixel cell-average output;
- analytical interval and ring references plus T-junction/disconnected tests.

## Next recommended development unit

After 0.0.9 is merged, implement reusable heat solver plans, batched
diffusion-time evaluation, heat likelihood/LSCV selection, and large-grid
benchmarks. Then proceed to temporal data objects and separable STKDE.

## Permanent process rule

Every completed development unit must create a versioned root Markdown handoff, update the
corresponding `docs/development` page and this file, and record actual CI and merge state.
See `docs/development/handoff-policy.md`.
