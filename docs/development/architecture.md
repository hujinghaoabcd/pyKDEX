# Architecture

pyKDEX follows pyGWRx engineering conventions: `src` layout, explicit public
inventory, atomic fitted state, copied training data, structured results,
strict documentation, cross-platform CI, and independent numerical fixtures.

The architecture is data-first and composition-oriented. Raw arrays and external
geospatial objects are normalized into validated pyKDEX data objects before
estimation. Estimators combine domains, metrics, kernels, bandwidths,
corrections, measured supports, and compute plans rather than creating a class
for every possible combination.

Structured data objects carry CRS, units, identifiers, provenance, and stable
fingerprints. OSMnx and NetworkX inputs are converted to pyKDEX's own
`LinearNetwork`; core network estimators do not depend directly on either
external graph representation.


## Network preparation

External GeoDataFrame, NetworkX, and OSMnx inputs are converted to an immutable
`LinearNetwork`. Event snapping and lixelization produce separately validated
objects, while `NetworkWorkspace` bundles reusable prepared assets without
binding them to a particular estimator.

## Space-time and network-time

Ordinary space-time and network-time are separate estimator families. Both
reuse explicit linear/cyclic time domains, but ordinary space-time uses a
spatial metric over coordinates whereas network-time uses along-edge
locations, junction policies, and measured lixels.

`NetworkTimeWorkspace` composes a `NetworkWorkspace`, accepted
`NetworkTimeEvents`, `ArixelSupport`, and an optional factorized distance
asset. It never expands network distances over every temporal cell.

`NetworkTimeSelectionCache` extends that factorization to bandwidth
experiments: source-event network matrices and target-time offset matrices are
evaluated separately and combined only for an objective. Path-based policies
trace each source once at the largest candidate spatial bandwidth. Adaptive
spatial and temporal bandwidths are sample-point values owned by source
events, never query-centred balloon bandwidths.

## Portable workspace persistence

Persistence is a data boundary, not estimator serialization. A versioned
manifest describes a closed component graph and an exact payload inventory.
Numeric arrays remain independent NPY payloads with pickle disabled; object
identifiers use a typed JSON codec; line geometry uses WKB data and offsets.
Every payload is checked by byte size and SHA-256 before object construction.

Archive and directory backends share this logical schema. Writes are staged
beside the destination and atomically renamed, while reads validate schema,
paths, checksums, dtype/shape contracts, component fingerprints, and finally
the complete reconstructed workspace fingerprint. Storage-provider adapters
such as PostGIS or Zarr must remain separate from this portable foundation.
