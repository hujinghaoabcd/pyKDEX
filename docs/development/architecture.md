# Architecture

pyKDEX follows pyGWRx engineering conventions: `src` layout, explicit public
inventory, atomic fitted state, copied training data, structured results,
strict documentation, cross-platform CI, and independent numerical fixtures.

KDE-specific functionality uses composition instead of a deep estimator
inheritance tree. Future network junction corrections and temporal kernels
will remain separate from base kernel shapes.
