# Workspace persistence

Prepared network assets can be expensive: topology normalization, event
snapping, lixelization, network distances, arixel construction, and temporal
offsets should not be recomputed merely because a Python process ended.
pyKDEX therefore persists the prepared workspace, not an estimator or arbitrary
Python session.

## Save and reload

```python
workspace = (
    NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=25.0,
        max_snap_distance=50.0,
    )
    .with_event_lixel_distances(cutoff=1000.0)
    .with_event_event_distances()
)

workspace.save("city.pykdex")
restored = NetworkWorkspace.load("city.pykdex")
assert restored.fingerprint == workspace.fingerprint
```

The equivalent functional API is useful in generic pipelines:

```python
save_network_workspace(workspace, "city.pykdex")
restored = load_network_workspace("city.pykdex")
```

`NetworkTimeWorkspace` uses the same contract:

```python
network_time.save("city-network-time.pykdex")
restored = NetworkTimeWorkspace.load("city-network-time.pykdex")
```

## Archive and directory backends

The default `format="archive"` writes one deterministic ZIP file. ZIP is only
a container here: loading reads and validates entries directly and never
extracts paths to disk.

```python
workspace.save("city.pykdex")
```

The directory backend exposes the same logical payloads:

```python
workspace.save("city-workspace", format="directory")
```

Both backends contain:

- `manifest.json`;
- non-object arrays in independent `.npy` payloads;
- object identifiers in a closed typed JSON representation;
- geometry as concatenated WKB bytes plus integer offsets.

Existing targets are protected. Pass `overwrite=True` only when replacement is
intentional. The new bundle is fully prepared next to the destination before an
atomic rename. A failed write does not partially update the destination.

## Integrity and compatibility

`WorkspaceManifest` declares:

- format name and integer schema version;
- workspace kind (`network` or `network_time`);
- writer version and complete workspace fingerprint;
- exact payload inventory;
- SHA-256 digest and byte size for every payload;
- the component graph needed to reconstruct the workspace.

Loading rejects:

- unknown schema versions or workspace kinds;
- missing, unexpected, duplicated, or unsafe payload paths;
- size or SHA-256 mismatches;
- object arrays disguised as `.npy`;
- unsupported typed metadata;
- invalid WKB, array shapes, or dtypes;
- mismatched network, event, lixel, arixel, time-domain, CRS, unit, direction,
  or distance fingerprints;
- a reconstructed fingerprint that differs from the manifest.

The default aggregate payload safety limit is 1 GiB. For a trusted larger local
asset, set an explicit higher bound:

```python
workspace = NetworkWorkspace.load(
    "large-city.pykdex",
    max_payload_bytes=4 * 1024**3,
)
```

## Security boundary

Persistence deliberately does not use pickle, joblib, cloudpickle, or an
estimator snapshot. Loading data therefore does not import or execute a class
named inside the bundle. The typed metadata schema supports:

- `None`, booleans, strings, bytes, integers, and floats;
- NumPy scalar values with their dtype;
- tuples, lists, mappings, and NumPy arrays composed from supported values.

Other arbitrary Python objects fail at save time. This is an intentional
portability and security rule.

## What is and is not persisted

The network workspace stores:

- canonical `LinearNetwork` topology, attributes, costs, CRS, units, and WKB;
- accepted `NetworkEvents`;
- rejected snapping records, validation report, and snapping parameters;
- measured `LixelSupport`;
- optional event-lixel and event-event sparse distance assets;
- provenance and deterministic metadata.

The network-time workspace additionally stores:

- accepted temporal coordinates and their linear or cyclic domain;
- temporal unit, origin, and timezone;
- arixel temporal edges and measured lixel reference;
- optional factorized network and temporal distance assets.

Fitted estimators, PostGIS, Zarr, remote object stores, and distributed
execution are outside the 0.0.14 portable local format.
