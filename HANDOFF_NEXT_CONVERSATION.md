# pyKDEX current handoff

The latest implemented development unit is **0.0.12 network-time
foundation**. Read `HANDOFF_0.0.12_NETWORK_TIME_FOUNDATION.md` first for the
complete design, mathematics, implementation, validation, limitations,
recovery procedure, and next-unit record.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- default branch: `main`;
- development branch: `agent/network-time-foundation`;
- version under final validation: `0.0.12`;
- latest stable merged version before publication: `0.0.11`;
- pull request: `#12 Add network-time KDE foundation`;
- feature implementation commit:
  `3f3a752202b4a2ff91939a01513d67713074c5e9`;
- first complete PR CI run `#128` (`30011519807`): success;
- final clean PR CI: pending;
- squash merge commit: pending;
- post-merge handoff commit: pending;
- focused network-time validation: `17 passed`;
- final full local regression: `217 passed`;
- branch coverage: `81.14%`;
- public API/example map after update: `112 public symbols`, all mapped;
- executable examples: all `14` passed;
- Black, isort, Ruff, mypy, strict documentation build, wheel/sdist, Twine,
  archive verification, and isolated wheel smoke: passed;
- no temporary repository workflow has been added.

Replace remaining GitHub pending fields only with observed publication
results.

## Implemented in 0.0.12

- immutable `NetworkTimeEvents`;
- stable event-ID alignment of times after network snap rejection;
- measured `ArixelSupport` with actual lixel length × temporal width;
- reusable `NetworkTimeWorkspace`;
- factorized sparse network distance and signed temporal offset assets;
- fixed-bandwidth separable `TemporalNetworkKDE`;
- simple, discontinuous, and continuous junction semantics;
- linear and normalized cyclic temporal kernels;
- time-major chunked evaluation;
- directed simple propagation;
- density and intensity;
- measured `NetworkTimeField` with frame, GeoDataFrame, grid, and xarray
  exports;
- analytical, mass, cyclic, direction, weight, chunk, and state tests;
- executable example, API, estimator, guide, architecture, and recovery docs.

## Next recommended development unit

After 0.0.12 is merged, build network-time bandwidth selection and adaptive
temporal-network KDE:

1. `NetworkTimeSelectionCache`;
2. reusable exact event-event network distances and signed time offsets;
3. maximum-bandwidth propagation trace reuse;
4. weighted network-time leave-one-out likelihood;
5. arixel-measured network-time LSCV;
6. deterministic joint and separate candidate experiments;
7. explicit sample-point spatial/temporal bandwidth semantics;
8. cyclic, direction, duplicate-location, tie, weight, and cache tests;
9. factorization/reuse benchmark;
10. `HANDOFF_0.0.13_NETWORK_TIME_BANDWIDTHS.md`.

Do not fold exposure risk, persistence, heat network-time diffusion, or
distributed execution into the bandwidth-selection unit.

## Permanent process rule

Every completed development unit must create a detailed versioned root
Markdown handoff, add or update the corresponding `docs/development` page,
update this file, and record actual validation, CI, PR, and merge state. See
`docs/development/handoff-policy.md`.
