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
