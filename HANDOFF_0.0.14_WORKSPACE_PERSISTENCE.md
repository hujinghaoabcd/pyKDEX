# pyKDEX 0.0.14 handoff: portable workspace persistence

This is the durable engineering record for pyKDEX 0.0.14. It is intended to
let a new conversation recover the complete design, implementation state,
security boundary, validation evidence, and next-unit plan without relying on
chat history.

## 1. Release identity

- Project: `hujinghaoabcd/pyKDEX`
- Version developed: `0.0.14`
- Development branch: `agent/workspace-persistence`
- Development worktree:
  `/workspace/scratch/660de0f0af7d/pykdex-workspace-persistence`
- Base stable version: `0.0.13`
- Pull request: `#14 Add portable workspace persistence`
- Initial feature commit:
  `35f333812e0e938c2ef11ced9c907b042b2fb346`
- Windows fsync fix commit:
  `6a851e167d796eea02b28414a7d289aab8953888`
- First PR CI run `#138` (`30017443733`): failed on Windows Python
  3.14 because Windows rejects `fsync` on a read-only descriptor
- Corrected complete PR CI run `#139` (`30017717273`): success
- Final clean PR CI after handoff update: pending
- Squash merge commit: pending

Do not replace the remaining pending fields with guesses. After GitHub observes
the final clean checks and merge, update this file and
`HANDOFF_NEXT_CONVERSATION.md` with the actual identifiers.

## 2. Why this development unit exists

Network analysis preparation can be much more expensive than fitting a single
estimator. The following assets are intentionally estimator-independent:

1. normalized network geometry and topology;
2. stable public node, edge, and event identifiers;
3. event snapping decisions and rejected-event audit records;
4. lixel partitions and actual integration lengths;
5. event-lixel and event-event sparse network distances;
6. temporal coordinates and linear/cyclic time domains;
7. arixel partitions and length-times-time measure;
8. factorized network-time distances and signed temporal offsets.

Before 0.0.14 these objects were reusable only inside one live Python process.
Changing a bandwidth did not require rebuilding them, but restarting a process
did. This unit makes those prepared assets portable between processes while
preserving identity and validation.

The persisted object is a prepared data workspace. It is not:

- a pickled estimator;
- a Python session snapshot;
- an arbitrary object graph;
- a remote storage protocol;
- a database schema;
- a distributed compute checkpoint.

## 3. Core public API

New top-level public symbols:

```python
WorkspaceManifest
save_network_workspace
load_network_workspace
save_network_time_workspace
load_network_time_workspace
```

Object-oriented entry points:

```python
workspace.save(
    "city.pykdex",
    format="archive",
    overwrite=False,
)
restored = NetworkWorkspace.load(
    "city.pykdex",
    max_payload_bytes=1_073_741_824,
)
```

The same methods exist on `NetworkTimeWorkspace`.

The functional form is equivalent:

```python
save_network_workspace(workspace, path)
workspace = load_network_workspace(path)

save_network_time_workspace(workspace, path)
workspace = load_network_time_workspace(path)
```

## 4. Portable bundle contract

The format name is:

```text
pykdex-workspace
```

The current schema version is:

```text
1
```

Two physical backends share one logical schema:

1. `format="archive"`: one deterministic ZIP file;
2. `format="directory"`: an inspectable directory tree.

Both contain `manifest.json` plus independent payload files.

The default remains archive because it is easy to move as one file. The
directory backend exists for inspection, debugging, and environments that
manage directory assets natively.

## 5. Manifest schema

`WorkspaceManifest` validates and exposes:

```text
format
schema_version
workspace_kind
workspace_fingerprint
writer_version
payloads
components
```

`workspace_kind` is closed to:

```text
network
network_time
```

Each payload record contains:

```text
sha256
size
```

The manifest lists every payload. Loading rejects both missing payloads and
unexpected payloads. This prevents silent partial bundles and undeclared data.

The `components` tree is declarative. It says which validated payload contains
each array and which inline metadata belongs to each pyKDEX object. It never
names a Python callable to import or execute.

## 6. Physical encoding rules

### 6.1 Numeric and string arrays

Non-object NumPy arrays use independent `.npy` payloads. Loading always calls:

```python
np.load(..., allow_pickle=False)
```

The manifest also records the expected dtype and shape. A checksum-valid NPY
file with a different dtype or shape is still rejected.

### 6.2 Object identifiers and object arrays

Object dtype cannot safely use NPY without pickle. Object arrays therefore use
a closed typed JSON representation that preserves:

- `None`;
- booleans;
- strings;
- bytes;
- arbitrary-size Python integers;
- finite and non-finite Python floats;
- NumPy scalars and their dtype;
- tuples;
- lists;
- mappings;
- NumPy arrays composed from supported values.

Unsupported arbitrary Python objects fail at save time with `TypeError`.
They are never converted to `repr`, and no import hook is used on load.

Tuple preservation matters because NetworkX/OSMnx identifiers commonly use
tuples such as `(u, v, key)`. NumPy scalar preservation matters because
fingerprints include the scalar type.

### 6.3 Geometry

Line geometry is stored as:

```text
concatenated WKB bytes
integer offset array
geometry count
```

The WKB bytes are represented by a `uint8` NPY array and offsets by an `int64`
NPY array. This avoids pickle, GeoPackage side effects, and dependency on a
single table format while retaining exact line geometry.

### 6.4 JSON

Manifest and typed-value JSON are:

- UTF-8;
- key-sorted;
- compact;
- non-NaN JSON at the outer serialization layer;
- deterministic for identical workspaces.

Special floating values appear only inside explicit typed-value records.

## 7. Deterministic archive rule

ZIP entries are written in sorted order with a fixed timestamp and fixed file
mode. The manifest has no generated timestamp. Two saves of an identical
workspace produce identical archive bytes.

This rule makes:

- content-addressed storage practical;
- archive diffs meaningful;
- reproducibility testable;
- unnecessary cache invalidation less likely.

The workspace's logical fingerprint remains the authoritative identity. Archive
byte determinism is an additional engineering property.

## 8. Atomic write and overwrite rules

Archive writes:

1. serialize all components in memory;
2. create a temporary file beside the destination;
3. write and close the complete ZIP;
4. fsync the temporary file;
5. atomically rename it to the destination.

Directory writes:

1. create a temporary sibling directory;
2. write and fsync every payload;
3. when overwriting, rename the old destination to a sibling backup;
4. rename the complete temporary directory into place;
5. restore the backup if replacement fails;
6. remove the backup after success.

Existing destinations are protected by default. Replacement requires:

```python
overwrite=True
```

A simulated archive replacement failure is tested to leave the original bytes
unchanged and remove its temporary file.

## 9. Read safety rules

The reader:

1. distinguishes a directory from an archive by the local filesystem object;
2. never extracts ZIP content;
3. rejects duplicate ZIP paths;
4. rejects absolute paths, parent traversal, and backslash paths;
5. rejects directory symbolic links;
6. enforces an aggregate uncompressed payload limit;
7. parses and validates the manifest;
8. checks exact payload inventory;
9. checks declared byte size;
10. checks SHA-256;
11. decodes arrays with pickle disabled;
12. validates component dtype, shape, and closed-schema keys;
13. constructs normal pyKDEX immutable objects;
14. runs normal workspace validation;
15. compares the reconstructed full workspace fingerprint with the manifest.

The default payload limit is 1 GiB. A trusted larger local bundle can use an
explicit higher value. The default is a safety bound, not a claim that pyKDEX
workspaces must be smaller than 1 GiB.

## 10. Persisted `NetworkWorkspace` graph

The following are stored:

### `LinearNetwork`

- node IDs and coordinates;
- edge IDs, endpoints, and keys;
- edge WKB geometry;
- edge lengths and costs;
- directed mode;
- CRS and spatial unit;
- every edge attribute array;
- network metadata;
- provenance.

### `SnapResult`

- optional accepted `NetworkEvents`;
- rejected-event DataFrame;
- complete `DataValidationReport`;
- snapping parameters.

### `NetworkEvents`

- event IDs;
- edge indices and public edge IDs;
- along-edge offsets;
- snapped and original coordinates;
- weights;
- snapping distances and statuses;
- optional marks;
- network fingerprint;
- CRS, unit, and provenance.

### `LixelSupport`

- lixel IDs and parent edges;
- start, end, and center offsets;
- actual lixel lengths;
- center coordinates;
- lixel WKB;
- target length;
- network fingerprint;
- CRS, unit, and provenance.

### Sparse distance assets

Both optional assets are stored independently:

- `distance_asset`: event to lixel;
- `event_distance_asset`: event to event.

For each `NetworkDistanceAsset` the format retains:

- source and target IDs;
- row and column coordinate arrays;
- finite distance values, including reachable zero;
- network/source/target fingerprints;
- length/cost weight;
- directed mode;
- optional cutoff;
- metadata.

No sparse asset is densified.

## 11. Persisted `NetworkTimeWorkspace` graph

A network-time bundle contains one complete base `NetworkWorkspace`, plus:

### `NetworkTimeEvents`

- accepted base network events by reference to the reconstructed base object;
- temporal coordinate values;
- linear or cyclic time domain;
- temporal unit;
- origin;
- timezone;
- temporal and event provenance.

### `ArixelSupport`

- base lixels by reference;
- exact temporal edge array;
- linear or cyclic time domain;
- temporal unit, origin, and timezone;
- provenance.

Derived time centers, widths, repeated lixel indices, arixel IDs, and measure
are reconstructed by the validated `ArixelSupport` constructor. They are not
duplicated in the format.

### `NetworkTimeDistanceAsset`

- sparse event-lixel `NetworkDistanceAsset`;
- signed temporal offset matrix;
- non-negative temporal distance matrix;
- event fingerprint;
- support fingerprint;
- time-domain fingerprint;
- base workspace fingerprint.

The network-time asset remains factorized. The persistence layer does not
create an event-by-arixel cube.

## 12. Identity and compatibility validation

Normal object constructors and workspace validation enforce:

- network fingerprint ownership;
- edge index and along-edge offset validity;
- lixel coverage and length;
- CRS compatibility;
- spatial-unit compatibility;
- event identity and ordering;
- distance source/target identity;
- directed mode;
- distance weight and cutoff;
- lixel identity inside arixels;
- temporal unit;
- temporal origin and timezone;
- linear/cyclic time-domain identity;
- event-time alignment;
- temporal distance shapes;
- complete workspace fingerprint.

Checksums detect physical payload changes. Fingerprints detect logically
incompatible reconstructed components. Both layers are required.

## 13. Main source files

```text
src/pykdex/persistence/__init__.py
src/pykdex/persistence/manifest.py
src/pykdex/persistence/_archive.py
src/pykdex/persistence/_codec.py
src/pykdex/persistence/workspace.py
src/pykdex/network/workspace.py
src/pykdex/network_time/workspace.py
src/pykdex/__init__.py
```

Responsibilities:

- `manifest.py`: public versioned manifest contract;
- `_archive.py`: deterministic bundle IO, checksums, path safety, limits, and
  atomic replacement;
- `_codec.py`: typed values, safe arrays, WKB, DataFrame, provenance,
  validation-report, and time-domain codecs;
- `workspace.py`: explicit component schemas and public save/load functions;
- network workspace modules: local-import object methods that avoid circular
  module initialization.

## 14. Tests and contracts

Primary new test file:

```text
tests/test_workspace_persistence.py
```

It covers:

1. exact network archive round trip;
2. byte-identical deterministic saves;
3. object tuple IDs;
4. NumPy scalar marks;
5. rejected snapping records and reports;
6. event-lixel and event-event sparse assets;
7. linear network-time round trip;
8. cyclic network-time round trip;
9. signed temporal offsets;
10. directory backend;
11. explicit overwrite;
12. OSMnx-style multigraph IDs, keys, attributes, and direction;
13. payload size/checksum corruption;
14. unexpected payload inventory;
15. future schema rejection;
16. workspace-kind mismatch;
17. payload safety limit;
18. simulated atomic replacement failure;
19. cross-process reload under a different `PYTHONHASHSEED`;
20. unsupported metadata rejection;
21. existing-destination protection;
22. direct manifest contract validation.

The full existing KDE, network, heat, space-time, and network-time regression
suite remains required.

## 15. Example and benchmark

Executable example:

```text
examples/16_workspace_persistence.py
```

It exercises both object-oriented and functional APIs, archive and directory
backends, network and network-time workspaces, and fingerprint equality.

Benchmark:

```text
benchmarks/benchmark_workspace_persistence.py
```

Observed local benchmark:

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

These timings are descriptive for the current environment, not performance
guarantees. The important benchmark assertion is exact fingerprint recovery.

## 16. Documentation

New documentation:

```text
docs/guides/workspace-persistence.md
docs/api/persistence.md
docs/development/handoff-0.0.14-workspace-persistence.md
```

Updated:

```text
README.md
docs/index.md
docs/zh/index.md
docs/development/architecture.md
docs/development/roadmap.md
mkdocs.yml
CHANGELOG.md
CITATION.cff
BASELINE_VALIDATION.md
HANDOFF_NEXT_CONVERSATION.md
```

## 17. Current local validation

Final local evidence before GitHub publication:

- focused persistence tests: `10 passed`;
- full regression: `236 passed`;
- branch coverage: `80.86%`, above the required `80%`;
- public API/example map: `122 public symbols`, all mapped;
- all `16` executable examples: passed;
- persistence benchmark: passed;
- Black: passed;
- isort: passed;
- Ruff: passed;
- mypy: passed for `87` source files;
- strict MkDocs: passed;
- wheel and sdist: built;
- Twine metadata: passed;
- distribution archive content: passed;
- isolated wheel installation and smoke test: passed.

Corrected PR CI run `#139` (`30017717273`) passed quality, coverage,
distributions, Linux, Windows, macOS, and Python 3.11-3.14. The first run
identified a real Windows portability defect: `os.fsync` requires a writable
file handle on Windows. Opening the complete temporary archive as `r+b`
preserves the durability step and passes all platforms. Final clean CI after
this handoff update and merge evidence remain pending until observed.

## 18. Deliberate exclusions

0.0.14 does not include:

- estimator serialization;
- pickle/joblib/cloudpickle;
- schema migrations from a prior workspace schema;
- PostGIS;
- Zarr;
- remote object storage;
- distributed or out-of-core execution;
- concurrent multi-writer locking;
- exposure-adjusted relative risk;
- bootstrap uncertainty;
- separability tests;
- heat-equation network-time diffusion.

Schema migration code should be added only when schema version 2 actually
exists. A speculative migration layer would create untested compatibility.

## 19. Rejected shortcuts

The following designs were explicitly rejected:

1. Pickling the workspace object.
2. Saving object-dtype NPY arrays with `allow_pickle=True`.
3. Converting unknown metadata to `repr`.
4. Storing geometry only as lossy coordinate summaries.
5. Densifying sparse network distances.
6. Expanding network-time distances over every arixel.
7. Trusting a checksum without reconstructing and validating fingerprints.
8. Trusting fingerprints without physical payload checksums.
9. Loading unknown schema versions optimistically.
10. Extracting ZIP paths before validation.
11. Silently overwriting an existing target.
12. Writing directly into the final destination.
13. Coupling the portable schema to PostGIS or Zarr.
14. Persisting fitted estimator state in this data format.

## 20. Next recommended unit: 0.0.15 exposure and relative risk

The next unit should build exposure-adjusted estimation as an independent
statistical layer. Recommended order:

1. define immutable `ExposureField` contracts on measured spatial, network,
   space-time, and network-time supports;
2. distinguish population/time-at-risk exposure from a comparison-event
   density;
3. validate support identity, CRS, units, domain, measure, and non-negativity;
4. define explicit zero-exposure and minimum-exposure policies;
5. add rate fields with interpretable units;
6. add case-control relative-risk or log-relative-risk estimators using
   separately normalized numerator and denominator;
7. support fixed shared bandwidth first;
8. specify whether independently selected bandwidths are statistically valid
   before exposing them;
9. retain measured integration and provenance;
10. add analytical constant-exposure and proportional-risk references;
11. add boundary, network-junction, cyclic-time, and zero-denominator tests;
12. create `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`.

Do not combine bootstrap envelopes, separability tests, PostGIS/Zarr, or
distributed execution into the exposure foundation.

## 21. Recovery procedure for a new conversation

1. Read this document completely.
2. Read `HANDOFF_NEXT_CONVERSATION.md`.
3. Inspect `git status --short --branch`.
4. Confirm the real GitHub `main`, PR, CI, and merge state.
5. Confirm `src/pykdex/__init__.py` reports `0.0.14`.
6. Inspect `src/pykdex/persistence/manifest.py`.
7. Inspect `src/pykdex/persistence/_archive.py`.
8. Inspect `src/pykdex/persistence/_codec.py`.
9. Inspect `src/pykdex/persistence/workspace.py`.
10. Run `tests/test_workspace_persistence.py`.
11. Run the full test and branch-coverage suite.
12. Run API coverage and all examples.
13. Run formatting, lint, type checking, strict docs, distributions, and
    isolated installation.
14. If 0.0.14 is not merged, finish its PR and clean CI first.
15. Start 0.0.15 only from the final merged `main`.

## 22. Permanent project rules

The following rules survive this development unit:

1. Every completed unit creates a detailed root handoff Markdown file.
2. Every unit adds or updates its `docs/development` handoff page.
3. Every unit updates `HANDOFF_NEXT_CONVERSATION.md`.
4. Handoffs record design, mathematics, code, tests, exclusions, next steps,
   recovery, real CI, and real merge state.
5. Public symbols must map to executable examples.
6. New numerical behavior requires analytical or independent references.
7. Temporary transfer, formatting, or diagnostic infrastructure must not be
   merged.
8. No pending CI or merge claim may be presented as completed.

## 23. Temporary local artifacts

The local `.venv`, coverage files, build directories, site output, caches, and
transfer artifacts are not project source. `uv.lock` is not retained because
this project does not currently track it. Verify `git status` before commit.
