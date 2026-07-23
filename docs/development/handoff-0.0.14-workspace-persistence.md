# 0.0.14 workspace persistence handoff

The complete durable engineering record is
`HANDOFF_0.0.14_WORKSPACE_PERSISTENCE.md` in the repository root.

Version 0.0.14 adds:

- a closed, versioned `WorkspaceManifest`;
- deterministic ZIP and inspectable directory bundles;
- atomic replacement and overwrite protection;
- payload inventory, byte-size, SHA-256, path, and schema validation;
- non-object NPY arrays with pickle disabled;
- typed JSON for object identifiers and metadata;
- WKB geometry data with integer offsets;
- full `NetworkWorkspace` and `NetworkTimeWorkspace` save/load;
- exact sparse and factorized distance-asset recovery;
- final reconstructed-fingerprint validation;
- corruption, OSMnx, cyclic-time, cross-process, and failure tests.

The portable persistence format is intentionally a prepared-data boundary.
It does not serialize estimators and does not include PostGIS, Zarr, remote
storage, distributed execution, exposure risk, or uncertainty.

Read the root handoff before continuing development. It contains the complete
schema, security rules, source map, test inventory, benchmark, exclusions,
recovery procedure, and next recommended 0.0.15 unit.
