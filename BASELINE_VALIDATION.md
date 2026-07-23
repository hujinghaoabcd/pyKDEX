# pyKDEX 0.0.14 validation

Validation date: 2026-07-23

## Implemented public functionality

- ordinary spatial, space-time, network, heat-network, and temporal-network
  KDE;
- scalar, matrix, balloon, sample-point, and cross-validated bandwidths;
- polygon boundary correction and measured result objects;
- canonical networks, auditable snapping, lixels, arixels, and exact sparse
  distances;
- linear and cyclic time domains;
- reusable network, heat, space-time, and network-time compute assets;
- portable, safe persistence for network and network-time workspaces;
- structured provenance, units, identifiers, measures, and fingerprints.

## Workspace persistence validation

- identical workspaces produce byte-identical archives;
- archive and directory backends recover identical fingerprints;
- object tuple IDs and NumPy scalar marks preserve their types;
- WKB restores exact network and lixel fingerprints;
- OSMnx-style direction, parallel-edge keys, IDs, and attributes survive;
- rejected snapping records, reports, and parameters survive;
- event-lixel and event-event sparse assets remain sparse and exact;
- linear and cyclic temporal domains survive;
- signed temporal offsets and factorized distances survive;
- future schema versions and wrong workspace kinds fail;
- corrupted sizes, checksums, and inventories fail;
- aggregate payload limits fail before object construction;
- unsupported arbitrary metadata fails before writing;
- existing destinations are protected;
- simulated atomic replacement failure preserves old bytes;
- independent-process loading returns the same fingerprint;
- final reconstructed fingerprints and normal object validation are required.

## Observed local validation

- focused persistence tests: `10 passed`;
- full regression: `236 passed`;
- branch coverage: `80.86%`;
- public API/example map after update: `122 public symbols`;
- all executable examples: `16 passed`;
- benchmark: `250` events, `10,560` arixels, and `33,875` sparse distance
  pairs saved to `149,733` bytes and reloaded with equal fingerprint;
- Black, isort, Ruff, and mypy: passed;
- strict MkDocs: passed;
- wheel, sdist, Twine, archive-content verification, and isolated wheel smoke:
  passed;
- corrected complete GitHub PR CI: passed;
- final clean PR CI: passed;
- PR merge: successful;
- post-merge `main` CI: pending.

## GitHub state

- development branch: `agent/workspace-persistence`;
- PR: `#14 Add portable workspace persistence`;
- initial feature commit:
  `35f333812e0e938c2ef11ced9c907b042b2fb346`;
- Windows fsync fix commit:
  `6a851e167d796eea02b28414a7d289aab8953888`;
- first PR CI run `#138` (`30017443733`): failed on Windows Python 3.14
  because a read-only descriptor cannot be fsynced on Windows;
- corrected PR CI run `#139` (`30017717273`): success across quality,
  coverage, distributions, Linux/Windows/macOS, and Python 3.11-3.14;
- final clean PR CI run `#140` (`30018184507`): success;
- final PR head:
  `17f73ff44f447d31470250545c8265060dc0f9b6`;
- squash merge commit:
  `979a2f3ada7e68e8f850d33b0722bb993c369e66`;
- post-merge `main` CI: pending.

PR #14 was merged and closed successfully. The post-merge field must be
replaced only with an observed GitHub result.

## Deliberate exclusions

- estimator serialization;
- pickle-compatible formats;
- PostGIS and Zarr;
- remote and distributed storage;
- out-of-core compute;
- exposure-adjusted risk;
- bootstrap uncertainty and separability tests;
- heat-equation network-time diffusion.
