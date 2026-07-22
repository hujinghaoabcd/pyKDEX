# pyKDEX current handoff

The latest development unit is **0.0.7 network bandwidth selection and adaptive NetworkKDE**.
Read `HANDOFF_0.0.7_NETWORK_BANDWIDTHS.md` first; it contains the full architecture,
mathematical definitions, changed files, validation contract, exclusions, recovery steps,
and recommended next unit.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- default branch: `main`;
- active development branch: `agent/network-bandwidths`;
- active pull request: `#6`;
- last stable merged version before this unit: `0.0.6`;
- development version on the branch: `0.0.7`;
- reviewed source commit: `9685687764f66a86c19dcd3cde3f1587da9ec236`;
- formatted source commit: `3fbb6fac3477ea389398347b9194214d434839c4`;
- local validation: `137 passed`, branch coverage `81.97%`, and 70 public symbols mapped to examples;
- temporary patch fragments, patch-application workflow, source-export workflow, and formatter
  workflow: removed;
- current unit status: implementation and formatting are complete and the clean
  maintainer-triggered GitHub Actions matrix is pending; do not merge until its final result is
  recorded in the versioned handoff.

## Permanent process rule

Every completed development unit must create a new versioned Markdown handoff and update this
file. See `docs/development/handoff-policy.md`.
