# pyKDEX current handoff

The latest completed development unit is **0.0.7 network bandwidth selection and adaptive
NetworkKDE**. Read `HANDOFF_0.0.7_NETWORK_BANDWIDTHS.md` first; it contains the full
architecture, mathematical definitions, changed files, validation contract, exclusions,
recovery steps, and recommended next unit.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- default branch: `main`;
- latest stable development version: `0.0.7`;
- completed pull request: `#6 Add network bandwidth selection and adaptive NetworkKDE`;
- PR #6 squash merge commit: `eec1bbee65e6131c942f67adb8286e6a4a56af26`;
- post-merge handoff-record commit: `0a5adc6ae21052f6dcd1bd0eb7c53595ed766ae0`;
- validation: `137 passed`, branch coverage `81.97%`, and 70 public symbols mapped to examples;
- final documentation-complete PR CI run #77 (`29902827180`): success;
- Black, isort, Ruff, mypy, strict MkDocs, distributions, installed-wheel smoke tests, and the
  Linux/Windows/macOS Python 3.11-3.14 matrix passed;
- temporary patch fragments and all patch, source-export, formatter, finalizer, merge-recorder,
  and diagnostic workflows were removed;
- unit status: complete and merged into `main`.

## Next recommended development unit

Return to the unfinished ordinary spatial KDE family in a new dedicated branch:

1. polygon boundary renormalization;
2. reflection correction for explicitly supported boundary geometries;
3. positive-definite bandwidth matrices and anisotropic transformations;
4. balloon kNN bandwidths;
5. boundary-aware analytical and mass-conservation tests;
6. a new detailed versioned Markdown handoff before merge.

Heat-equation Gaussian NKDE remains a separate later numerical engine and must not be exposed as
an ordinary radial-kernel name.

## Permanent process rule

Every completed development unit must create a new versioned Markdown handoff and update this
file. See `docs/development/handoff-policy.md`.
