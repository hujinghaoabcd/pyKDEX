# pyKDEX 0.0.15 progress handoff 01: exposure-field foundation

This document is the durable engineering record for the first completed subunit of
pyKDEX 0.0.15. It records the design, implementation, validation evidence,
limitations, and exact continuation point without claiming that the complete 0.0.15
release is finished.

## 1. Repository state

- Project: `hujinghaoabcd/pyKDEX`
- Latest stable merged version: `0.0.14`
- Active development version: `0.0.15`
- Branch: `agent/exposure-relative-risk`
- Draft pull request: `#15 Add exposure-field foundation for pyKDEX 0.0.15`
- Base commit on `main`: `1315619afba79a6ddf1fbfd7b91900bf0c0992f1`
- Design commit: `092cb2b77dcb90d4e6c444c8659a5fffe5e54a34`
- First implementation head: `92decf03737f43c13802db0e270867cfd0eccc47`
- Corrected clean implementation head before this handoff:
  `85dc5fc1a5fb71e8ec54841c8a4d4ba7d8584d26`
- Corrected complete CI run: `#146` (`30348884054`), success
- PR state: open and draft
- Merge state: not merged

Read `docs/development/design-0.0.15-exposure-relative-risk.md` before continuing.
That document fixes the complete 0.0.15 statistical definitions and implementation
order. This handoff covers only the measured-support and exposure-field foundation.

## 2. Why this subunit exists

The existing estimators return densities or intensities on several support types. An
exposure-adjusted event rate requires an independent denominator with explicit units,
measure, provenance, and support identity. An array of denominator values is not
sufficient because two arrays can have the same shape while referring to different
cells, lixels, time domains, networks, coordinate systems, or units.

The first subunit therefore establishes:

1. a closed measured-support adapter;
2. an immutable support identity descriptor;
3. an immutable exposure field stored canonically as exposure density;
4. exact conversion between per-element exposure amount and exposure density;
5. integration, identity, export, and validation contracts required by later rate and
   relative-risk objects.

No event-rate division or case-control relative-risk calculation is exposed yet.

## 3. External references and implementation independence

The 0.0.15 design inspected the public mathematical behaviour and documentation of:

- `tilmandavies/sparr`;
- `spatstat/spatstat.explore`;
- `spatstat/spatstat.linnet`;
- `JeremyGelb/spNetwork`.

These GPL-licensed projects are methodological references only. Their source code was
not copied, translated, or mechanically ported. Runtime pyKDEX code does not import or
call them. This follows `THIRD_PARTY_NOTICES.md`: external packages may inform public
mathematical definitions and one-time independent numerical fixtures, but they are not
source-code donors to this MIT-licensed project.

## 4. Statistical convention

For support elements indexed by `j`, let `m_j > 0` be the actual measured support:

- spatial grid-cell area;
- lixel length;
- measured space-time support;
- spatial-cell-area times temporal-cell width;
- lixel length times temporal-cell width.

`ExposureField.values` always stores the canonical exposure density `e_j` with respect
to `m_j`. The represented exposure amount is

```text
E_j = e_j * m_j
```

and total exposure is

```text
E_total = sum_j e_j * m_j
```

`ExposureField.from_density(...)` accepts `e_j` directly.
`ExposureField.from_amounts(...)` accepts `E_j` and computes `e_j = E_j / m_j`.

This distinction is necessary because pyKDEX supports retain remainder grid cells,
remainder lixels, and remainder time cells whose measures may differ from nominal
resolution.

A completely zero field is valid as a data object for inspection and validation. It
will be rejected later by event-rate estimation unless an explicit denominator policy
permits otherwise.

## 5. Closed measured-support contract

The new `MeasuredSupport` type is deliberately closed to validated pyKDEX classes:

```text
GridSupport
LixelSupport
SpatiotemporalPointSupport with support_measure
SpatiotemporalGridSupport
ArixelSupport
```

Ordinary `PointSupport` is not measured and is rejected. A
`SpatiotemporalPointSupport` without `support_measure` is also rejected.

`SupportDescriptor` retains:

- canonical support kind;
- number of support elements;
- positive measured integration weights;
- stable support identifiers;
- support fingerprint;
- CRS;
- spatial unit;
- temporal unit;
- time-domain fingerprint;
- native result shape.

Compatibility is based on support kind and fingerprint, not shape alone.
`require_same_measured_support(...)` enforces exact measured-support identity for later
numerator/denominator operations.

## 6. ExposureField contract

`ExposureField` is a frozen dataclass with owned read-only NumPy values and immutable
metadata. It retains:

- canonical exposure-density values;
- measured support;
- explicit exposure unit;
- original public representation (`density` or `amount`);
- provenance;
- support descriptor;
- deterministic field fingerprint;
- immutable metadata.

Validation requires:

- one value per support element;
- finite non-negative values;
- an explicit non-empty exposure unit;
- a supported measured support;
- valid provenance and support metadata.

Public operations currently include:

```text
ExposureField.from_density
ExposureField.from_amounts
ExposureField.density
ExposureField.amounts
ExposureField.total_exposure
ExposureField.is_zero
ExposureField.fingerprint
ExposureField.to_frame
ExposureField.to_grid
ExposureField.to_geodataframe
```

The package-level symbols are currently exposed from `pykdex.risk`, not yet from the
top-level `pykdex` namespace. Top-level exposure, rate, and risk exports will be added
together with executable examples when the complete 0.0.15 public API is stable.

## 7. Files added

```text
docs/development/design-0.0.15-exposure-relative-risk.md
src/pykdex/risk/__init__.py
src/pykdex/risk/support.py
src/pykdex/risk/exposure.py
tests/test_exposure_field.py
HANDOFF_0.0.15_PROGRESS_01_EXPOSURE_FIELD.md
```

A corresponding development handoff page is also added under `docs/development/`.

## 8. Tests and numerical contracts

`tests/test_exposure_field.py` covers:

1. density construction on unequal spatial cell measures;
2. amount-to-density conversion;
3. exact integrated total exposure;
4. read-only values and derived amounts;
5. deterministic content fingerprints;
6. zero-field construction for inspection;
7. invalid shape, negative values, and non-finite values;
8. explicit exposure-unit validation;
9. rejection of unmeasured point support;
10. rejection of unmeasured space-time point support;
11. measured space-time point support;
12. network exposure using actual lixel lengths;
13. space-time grid domain identity;
14. arixel domain identity and length-times-time measure;
15. exact support-fingerprint compatibility.

The unequal-cell and unequal-lixel tests are analytical references: conversion must
recover the original amounts exactly within floating-point tolerance, and integrated
exposure must equal the sum of the supplied per-element amounts.

## 9. Validation evidence

### 9.1 First PR CI

CI run `#143` (`30348395422`) established that:

- the full regression and platform tests passed in completed jobs;
- branch coverage passed;
- distributions, Twine checks, archive verification, and isolated wheel smoke passed;
- the quality job stopped at Black formatting.

No numerical or functional failure was observed. The only confirmed defect was source
formatting in `src/pykdex/risk/exposure.py`.

### 9.2 Formatting correction

A temporary branch-only GitHub Actions workflow generated the exact Black/isort output
as an artifact because the current execution container could not resolve `github.com`
and therefore could not clone the repository locally. The formatted artifact showed
that only `exposure.py` required a Black change.

The exact formatting change was applied. The temporary workflow was then deleted before
the corrected clean validation. It is not present in the current branch.

### 9.3 Corrected clean CI

CI run `#146` (`30348884054`) completed successfully. Observed successful jobs include:

- Black;
- isort;
- Ruff;
- mypy;
- public-API example-map validation;
- strict MkDocs build;
- branch-coverage suite;
- wheel and source distribution build;
- Twine metadata validation;
- distribution archive verification;
- isolated wheel installation and smoke test;
- Linux, Windows, and macOS tests across Python 3.11, 3.12, 3.13, and 3.14.

The exact CI result is success; no unobserved local test claim is made.

## 10. Deliberate exclusions

This completed subunit does not include:

- event-rate calculation;
- `EventRateField`;
- zero-denominator or minimum-exposure policies;
- case-control density-ratio relative risk;
- log relative risk;
- case probability or odds;
- adaptive relative risk;
- relative-risk bandwidth selection;
- shrinkage estimators;
- bootstrap uncertainty or tolerance contours;
- separability diagnostics;
- persistence-schema changes;
- PostGIS, Zarr, remote storage, or distributed execution;
- version bump from `0.0.14` to `0.0.15`;
- top-level `pykdex` exports or final examples.

These exclusions keep the denominator data model independently testable before adding
statistical division and estimator compatibility logic.

## 11. Rejected shortcuts

The following designs were rejected:

1. Accepting arbitrary objects with `measure` and `fingerprint` attributes.
2. Treating equal array shape as support compatibility.
3. Allowing exposure fields on unmeasured point support.
4. Storing per-element amounts without a canonical density representation.
5. Assuming all grid cells, lixels, or temporal cells have nominal resolution.
6. Inferring exposure units from support units.
7. Silently replacing zero values with epsilon at construction time.
8. Combining exposure rate and case-control relative risk into one `risk` function.
9. Exposing incomplete placeholder estimators at the top-level package API.
10. Retaining the temporary formatting workflow in the repository.

## 12. Next implementation subunit

Continue on `agent/exposure-relative-risk` and PR #15. The next subunit is explicit
denominator handling and exposure-adjusted event rates:

1. define an immutable denominator policy with `raise`, `nan`, and `minimum` modes;
2. require a finite positive minimum only for `minimum` mode;
3. define `EventRateField` on the exact same measured support;
4. adapt existing spatial, network, space-time, and network-time intensity result
   objects through a closed result adapter;
5. reject probability-density numerators because total event mass has been removed;
6. validate support fingerprint, CRS, units, time domain, network direction, and
   estimator-specific metadata;
7. implement `estimate_event_rate(...)`;
8. retain the original event intensity, effective exposure, invalid-cell mask, event
   mass, total exposure, and exposure-weighted mean rate;
9. add constant-exposure and zero-exposure analytical tests on all four domains;
10. update this progress handoff or create progress handoff 02 before proceeding to
    case-control relative risk.

Do not start relative-risk bandwidth selection, uncertainty, or scalable execution in
the event-rate subunit.

## 13. Recovery procedure

1. Read `HANDOFF_0.0.14_WORKSPACE_PERSISTENCE.md` for the stable base.
2. Read `docs/development/design-0.0.15-exposure-relative-risk.md` completely.
3. Read this progress handoff.
4. Inspect PR #15 and confirm its actual head, draft state, and CI.
5. Confirm the temporary formatting workflow is absent.
6. Inspect `src/pykdex/risk/support.py`.
7. Inspect `src/pykdex/risk/exposure.py`.
8. Run `tests/test_exposure_field.py`.
9. Run the full regression, coverage, quality, docs, distribution, and platform matrix.
10. Continue with the denominator-policy and event-rate subunit only after the current
    branch is clean.

## 14. Permanent project rules

The existing handoff, mathematical validation, public-example, CI-truthfulness, and
implementation-independence rules remain in force. In particular, every completed
subunit must leave a recoverable Markdown record, and the final 0.0.15 release must
still create `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md` with final version, API,
validation, PR, and merge evidence.
