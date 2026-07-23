# pyKDEX current handoff

The latest implemented development unit is **0.0.14 portable workspace
persistence**. Read `HANDOFF_0.0.14_WORKSPACE_PERSISTENCE.md` first. It is the
complete design, schema, security, implementation, validation, limitation,
recovery, and next-unit record.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- development branch: `agent/workspace-persistence`;
- development worktree:
  `/workspace/scratch/660de0f0af7d/pykdex-workspace-persistence`;
- version implemented in this branch: `0.0.14`;
- latest stable merged version when development began: `0.0.13`;
- pull request: pending;
- feature commit: pending;
- CI: pending;
- merge commit: pending;
- focused persistence validation: `10 passed`;
- full regression: `236 passed`;
- branch coverage: `80.86%`;
- public API/example map after update: `122 public symbols`, all mapped;
- executable examples: `16`;
- Black, isort, Ruff, mypy, strict docs, distributions, and isolated wheel:
  passed;
- final PR CI and merge: pending final observation;
- no temporary repository workflow has been added.

Update pending fields only after they are observed. Do not infer CI or merge
success from local state.

## Implemented in 0.0.14

- public immutable `WorkspaceManifest`;
- schema version 1 of format `pykdex-workspace`;
- workspace kinds `network` and `network_time`;
- deterministic local ZIP archive backend;
- inspectable local directory backend;
- atomic staged writes and explicit overwrite protection;
- exact payload inventory and aggregate safety limit;
- byte-size and SHA-256 validation for every payload;
- safe-path and duplicate-entry rejection;
- non-object NPY arrays loaded with `allow_pickle=False`;
- typed JSON for object IDs, NumPy scalars, tuples, mappings, and metadata;
- WKB geometry as `uint8` data and `int64` offsets;
- network, snapping audit, lixel, provenance, CRS, unit, and attribute schemas;
- exact event-lixel and event-event sparse distance schemas;
- temporal coordinates and linear/cyclic time-domain schemas;
- arixel and factorized network-time distance schemas;
- `NetworkWorkspace.save/load`;
- `NetworkTimeWorkspace.save/load`;
- public functional save/load APIs;
- reconstructed object validation and final workspace-fingerprint check;
- deterministic byte-for-byte archive test;
- corruption, future-schema, payload-limit, atomic-failure, OSMnx,
  cyclic-time, and cross-process contracts;
- executable example 16 and size/reload benchmark;
- detailed root and documentation handoffs.

## Persistence rules that must not change accidentally

1. Persistence stores prepared data, not fitted estimators.
2. Pickle, joblib, and cloudpickle are forbidden.
3. Object arrays must never enter NPY payloads.
4. Unknown metadata types fail; they are not converted to `repr`.
5. Every payload is declared, sized, and checksummed.
6. Unknown schema versions fail explicitly.
7. ZIP content is read directly and never extracted.
8. Existing destinations are protected unless overwrite is explicit.
9. Writes are staged beside the destination before replacement.
10. Sparse distance coordinates remain sparse and retain reachable zero.
11. Network-time distance assets remain factorized.
12. Normal pyKDEX constructors and validation run after decoding.
13. The reconstructed full fingerprint must equal the manifest fingerprint.
14. Identical workspaces should produce identical archive bytes.
15. PostGIS/Zarr adapters must remain separate from the portable schema.

## Observed benchmark

```text
n_nodes: 121
n_edges: 220
n_events: 250
n_arixels: 10,560
distance_pairs: 33,875
archive_bytes: 149,733
save_seconds: 0.101
load_seconds: 0.124
```

Timings are environment-specific. Fingerprint equality is the benchmark's
required correctness assertion.

## Next recommended development unit

Build **0.0.15 exposure-adjusted rate and relative-risk estimation**:

1. immutable exposure fields bound to measured supports;
2. explicit exposure units and provenance;
3. support, CRS, unit, domain, and fingerprint validation;
4. non-negative and zero-exposure policies;
5. event rate fields;
6. case-control relative risk and log-relative risk;
7. shared fixed bandwidth first;
8. analytical constant-exposure and proportional-risk references;
9. spatial, network, cyclic-time, and arixel tests;
10. `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`.

Do not fold bootstrap envelopes, separability tests, PostGIS/Zarr, distributed
execution, or remote storage into the exposure foundation.

## Recovery checklist

1. Read `HANDOFF_0.0.14_WORKSPACE_PERSISTENCE.md`.
2. Inspect `git status --short --branch`.
3. Verify real GitHub `main`, PR, CI, and merge state.
4. Confirm version `0.0.14`.
5. Read the five files under `src/pykdex/persistence`.
6. Run `tests/test_workspace_persistence.py`.
7. Run full coverage, API map, 16 examples, format, lint, types, strict docs,
   distributions, and isolated wheel checks.
8. Finish the 0.0.14 PR and merge if any pending fields remain.
9. Start 0.0.15 only from final merged `main`.

## Permanent process rule

Every completed development unit must create a detailed versioned root
Markdown handoff, add or update the corresponding `docs/development` page,
update this file, and record actual validation, CI, PR, and merge state. See
`docs/development/handoff-policy.md`.
