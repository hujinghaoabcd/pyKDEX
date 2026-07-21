# pyKDEX handoff

The current directory is the first reliable pyKDEX engineering baseline.
Do not rebuild it from isolated snippets.

## Current status

- version: `0.0.1`;
- public estimator: `SpatialKDE`;
- tests: 42 passed;
- branch coverage: 87.3%;
- formatting, linting, typing, documentation, build, and installation gates pass;
- no runtime dependency on external KDE implementations.

## Next recommended development unit

Implement bandwidth selection and adaptive spatial KDE before beginning network
algorithms. The recommended sequence is:

1. leave-one-out likelihood objective;
2. least-squares cross-validation objective;
3. bounded scalar optimization with deterministic result objects;
4. k-nearest-neighbour bandwidth strategy;
5. Abramson sample-point adaptive bandwidth;
6. independent fixtures and mass-conservation tests;
7. examples and documentation for every new public symbol.

Do not add network and temporal placeholders to the public API until they are
implemented and tested.
