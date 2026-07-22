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
- finalized handoff commit: `994c59b9ed0cd13391e54bcfc6dd2f96ee947c62`;
- validation: `137 passed`, branch coverage `81.97%`, and 70 public symbols mapped to examples;
- clean full CI run #74 (`29902449039`): success;
- temporary patch fragments, patch-application, source-export, formatter, finalizer, and
  diagnostic workflows: removed;
- current unit status: implementation, formatting, validation records, and versioned handoff are
  complete. The final documentation-only CI triggered by this update must pass before PR #6 is
  marked ready and squash-merged.

## Permanent process rule

Every completed development unit must create a new versioned Markdown handoff and update this
file. See `docs/development/handoff-policy.md`.
