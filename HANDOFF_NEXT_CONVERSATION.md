# pyKDEX current handoff

The latest stable merged version is **0.0.14**. Active development is **0.0.15
exposure-adjusted rates and relative risk**.

Read these records in order:

1. `HANDOFF_0.0.14_WORKSPACE_PERSISTENCE.md`;
2. `docs/development/design-0.0.15-exposure-relative-risk.md`;
3. `HANDOFF_0.0.15_PROGRESS_01_EXPOSURE_FIELD.md`.

## Current state

- repository: `hujinghaoabcd/pyKDEX`;
- branch: `agent/exposure-relative-risk`;
- draft PR: `#15 Add exposure-field foundation for pyKDEX 0.0.15`;
- base `main`: `1315619afba79a6ddf1fbfd7b91900bf0c0992f1`;
- clean implementation head before handoff updates:
  `85dc5fc1a5fb71e8ec54841c8a4d4ba7d8584d26`;
- corrected CI run `#146` (`30348884054`): success;
- final CI after handoff updates: pending observation;
- merge: not merged;
- package version remains `0.0.14` until the complete 0.0.15 unit is finished.

Do not merge PR #15 after only this first subunit.

## Implemented in progress subunit 01

- fixed the statistical distinction between exposure-adjusted event rates and
  case-control density-ratio relative risk;
- inspected `sparr`, `spatstat.explore`, `spatstat.linnet`, and `spNetwork` as
  methodological references without copying GPL source;
- added a closed measured-support contract for spatial grids, lixels, measured
  space-time points, space-time grids, and arixels;
- added immutable `SupportDescriptor` identity, measure, CRS, unit, temporal-domain,
  identifier, fingerprint, and shape contracts;
- added immutable `ExposureField` construction from density or per-element amounts;
- retained explicit exposure unit, provenance, metadata, total exposure, fingerprint,
  and supported table/grid/geospatial exports;
- added focused tests across spatial, network, space-time, and network-time supports.

The canonical exposure convention is:

```text
exposure_amount_j = exposure_density_j * support_measure_j
total_exposure = sum_j exposure_amount_j
```

Unmeasured point support is rejected. Equal array shape is not support compatibility.
A zero exposure field may be constructed for inspection, but later rate estimation
must apply an explicit denominator policy.

## Validation

The first CI run `#143` found only a Black formatting failure. A temporary branch-only
formatting workflow generated the exact correction and was removed immediately.

Corrected CI run `#146` passed:

- Black, isort, Ruff, mypy, API mapping, and strict MkDocs;
- branch coverage;
- distributions, Twine, archive verification, and isolated wheel smoke testing;
- Linux, Windows, and macOS on Python 3.11-3.14.

## Exact next subunit

1. Add denominator policies: `raise`, `nan`, and explicit positive `minimum`.
2. Add closed adapters for existing spatial, network, space-time, and network-time
   result objects.
3. Reject probability-density numerators; event rates require intensity.
4. Validate exact support, CRS, units, time domain, network direction, and estimator
   metadata.
5. Add immutable `EventRateField` and `estimate_event_rate(...)`.
6. Retain raw intensity, effective exposure, invalid mask, event mass, total exposure,
   and exposure-weighted mean rate.
7. Add analytical constant-exposure and zero-denominator tests on all four domains.
8. Create progress handoff 02 before case-control relative risk.

Do not add adaptive relative risk, bandwidth selection, shrinkage, uncertainty,
separability diagnostics, PostGIS/Zarr, or distributed execution in this subunit.

## Recovery checklist

1. Inspect PR #15 and verify its real head, draft state, and CI.
2. Confirm `.github/workflows/format-diagnostic.yml` is absent.
3. Read the three records listed at the top.
4. Inspect `src/pykdex/risk/support.py` and `src/pykdex/risk/exposure.py`.
5. Run `tests/test_exposure_field.py` and the complete repository validation matrix.
6. Continue on `agent/exposure-relative-risk`.

The final release must still create
`HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md` with actual final version, public API,
validation, PR, CI, and merge evidence.
