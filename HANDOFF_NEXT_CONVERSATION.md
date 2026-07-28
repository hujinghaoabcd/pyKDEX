# pyKDEX current handoff

The latest stable merged version is **0.0.14**. Active development is **0.0.15
exposure-adjusted rates and relative risk**.

Read these records in order:

1. `HANDOFF_0.0.14_WORKSPACE_PERSISTENCE.md`;
2. `docs/development/design-0.0.15-exposure-relative-risk.md`;
3. `HANDOFF_0.0.15_PROGRESS_01_EXPOSURE_FIELD.md`;
4. `HANDOFF_0.0.15_PROGRESS_02_EVENT_RATE.md`.

## Current state

- repository: `hujinghaoabcd/pyKDEX`;
- branch: `agent/exposure-relative-risk`;
- draft PR: `#15`;
- base `main`: `1315619afba79a6ddf1fbfd7b91900bf0c0992f1`;
- exposure-field subunit final state commit: `40fc66841fdde4fa90774ed79ca31bb1fd5b4f58`;
- event-rate implementation head before handoff updates:
  `c806f34a2ebba8eb3dd1ae72cadcb7d895ef6ad1`;
- first event-rate CI `#156` (`30350961687`): stopped at Black formatting;
- corrected event-rate CI `#162` (`30351398127`): quality, coverage,
  distributions, and completed platform jobs succeeded; final workflow conclusion
  pending observation when this file was updated;
- merge: not merged;
- package version remains `0.0.14` until the complete 0.0.15 unit is finished.

Do not merge PR #15 after only the exposure and event-rate subunits.

## Implemented in progress subunit 01

- closed measured-support identity for spatial grids, lixels, measured space-time
  points, space-time grids, and arixels;
- immutable `SupportDescriptor`;
- immutable `ExposureField` from density or per-element exposure amounts;
- explicit exposure units, provenance, measured totals, fingerprints, and exports;
- analytical support and exposure tests across all four domains.

The canonical exposure convention is:

```text
exposure_amount_j = exposure_density_j * support_measure_j
total_exposure = sum_j exposure_amount_j
```

## Implemented in progress subunit 02

- immutable `DenominatorPolicy` with explicit `raise`, `nan`, and `minimum` modes;
- no hidden epsilon and no stored positive infinity;
- closed intensity adapters for `SpatialKDEResult`, `NetworkField`,
  `SpatiotemporalKDEResult`, and `NetworkTimeField`;
- strict rejection of `target="density"` as an event-rate numerator;
- exact support, CRS, unit, temporal-domain, network, direction, kernel, metric,
  junction, and source-metadata retention;
- immutable `EventRateField`;
- `estimate_event_rate(...)` with mandatory event unit;
- original intensity, original/effective exposure, invalid/adjusted masks, event mass,
  exposure totals, and documented exposure-weighted summaries;
- analytical tests for constant rates, scaling laws, all denominator policies, unequal
  grid measures, lixels, cyclic space-time grids, and cyclic arixels.

The event-rate definition is:

```text
event_rate_j = event_intensity_j / exposure_density_j
rate_unit = event_unit / exposure_unit
```

A temporary `.github/workflows/format-event-rate.yml` workflow was used only to obtain
exact Black/isort output and was deleted before corrected validation. Confirm it remains
absent.

## Exact next subunit

Build shared-fixed-bandwidth case-control relative risk:

1. add closed density-result adapters for the same four result families;
2. require `target="density"` for case and control;
3. require exact measured-support identity and density-integral validation;
4. require scalar fixed bandwidths and equal case/control bandwidths;
5. require equal kernels, metric or junction policy, boundary correction, direction,
   network identity, temporal domain, CRS, and units;
6. add immutable `RelativeRiskField`;
7. implement raw density ratio and log relative risk;
8. reuse explicit `raise`, `nan`, and `minimum` policies for control density;
9. retain both densities, effective control, masks, source fingerprints, bandwidth
   contract, and estimator metadata;
10. test identical densities, swapped inputs, reciprocal and negation identities,
    control-weighted normalization, denominator policies, and all four domains;
11. create progress handoff 03 before finalizing the 0.0.15 public API.

Do not add adaptive relative risk, independent bandwidth selection, inference,
uncertainty, separability diagnostics, PostGIS/Zarr, or distributed execution.

## Recovery checklist

1. Inspect PR #15 and verify its actual head, draft state, and CI.
2. Confirm `.github/workflows/format-event-rate.yml` is absent.
3. Read the four records listed at the top.
4. Inspect `src/pykdex/risk/support.py`, `exposure.py`, `policies.py`, `intensity.py`,
   and `rate.py`.
5. Run `tests/test_exposure_field.py` and `tests/test_event_rate.py`.
6. Run the full regression, coverage, quality, docs, distribution, isolated-wheel, and
   platform matrix.
7. Continue on `agent/exposure-relative-risk` with relative risk only after the branch
   is clean.

The final release must still create
`HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md` with actual final version, complete public
API, examples, validation, PR, CI, and merge evidence.
