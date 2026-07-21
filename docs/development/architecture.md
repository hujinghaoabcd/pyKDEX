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
fingerprints. Future OSMnx and NetworkX inputs will be converted to pyKDEX's own
`LinearNetwork`; core network estimators will not depend directly on either
external graph representation.
