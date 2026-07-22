# Development handoff policy

Every completed pyKDEX development unit must leave a recoverable Markdown record before
its pull request is merged. This is a project requirement, not an optional release note.

## Required files

1. Create one immutable, versioned root document named
   `HANDOFF_<VERSION>_<UNIT>.md`.
2. Update `HANDOFF_NEXT_CONVERSATION.md` so a new conversation sees the latest state
   immediately.
3. Add a corresponding page under `docs/development/` when the development unit changes
   public architecture or numerical contracts.
4. Update `CHANGELOG.md`, `BASELINE_VALIDATION.md`, and version metadata.

## Required content

Each versioned handoff must state:

- project purpose and current version;
- design decisions and why alternatives were rejected;
- numerical definitions and normalization conventions;
- files and public symbols added or changed;
- data ownership, fitted-state, CRS, unit, and fingerprint rules;
- tests, coverage, formatting, typing, documentation, build, and CI results;
- deliberate exclusions and unresolved limitations;
- exact next development unit and recommended implementation order;
- recovery instructions for checking the repository, PR, branch, and CI;
- temporary diagnostic infrastructure that was removed before merge.

## Reliability rules

- Never claim a test or CI result that was not observed.
- Keep failed experiments out of `main`, but record important rejected designs.
- Do not expose empty placeholder APIs.
- Do not merge temporary workflows, captured logs, or auto-fix scripts.
- A handoff is updated after the final clean CI, so its validation counts match the merged
  commit.
- Public mathematical behavior must be described independently of implementation details.

This policy protects the project if a conversation, local workspace, or temporary artifact
is lost.
