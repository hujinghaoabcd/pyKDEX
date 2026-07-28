# pyKDEX current handoff

The latest stable merged version is **0.0.14**. Active development is **0.0.15
exposure-adjusted rates and relative risk**.

Read these records in order:

1. `HANDOFF_0.0.14_WORKSPACE_PERSISTENCE.md`;
2. `docs/development/design-0.0.15-exposure-relative-risk.md`;
3. `HANDOFF_0.0.15_PROGRESS_01_EXPOSURE_FIELD.md`;
4. `HANDOFF_0.0.15_PROGRESS_02_EVENT_RATE.md`;
5. `HANDOFF_0.0.15_PROGRESS_03_RELATIVE_RISK.md`.

## Current state

- repository: `hujinghaoabcd/pyKDEX`;
- branch: `agent/exposure-relative-risk`;
- draft PR: `#15 Add exposure-adjusted rate and relative-risk foundations`;
- base `main`: `1315619afba79a6ddf1fbfd7b91900bf0c0992f1`;
- exposure-field subunit final state commit: `40fc66841fdde4fa90774ed79ca31bb1fd5b4f58`;
- event-rate implementation and handoff state documented in progress handoff 02;
- relative-risk implementation and formatter-removal head:
  `5a42a59815cda5321ee89b52d0f86704b5f7f31f`;
- relative-risk progress handoff root commit:
  `9eb2686cd0e85b4fafad670ed7ab0de01662ed35`;
- first relative-risk CI `#172` (`30353108398`): stopped at Black formatting;
- corrected relative-risk implementation CI `#177` (`30353630091`): success;
- documentation-update CI: pending observation after this state update;
- merge: not merged;
- PR remains Draft;
- package version remains `0.0.14` until the complete 0.0.15 release unit is finished.

Do not merge PR #15 after only the three numerical subunits.

## Implemented in progress subunit 01

- closed measured-support identity for spatial grids, lixels, measured space-time
  points, space-time grids, and arixels;
- immutable `SupportDescriptor`;
- immutable `ExposureField` from density or per-element exposure amounts;
- explicit exposure units, provenance, measured totals, fingerprints, and exports;
- analytical support and exposure tests across all four domains.

```text
exposure_amount_j = exposure_density_j * support_measure_j
total_exposure = sum_j exposure_amount_j
```

## Implemented in progress subunit 02

- immutable `DenominatorPolicy` with explicit `raise`, `nan`, and `minimum` modes;
- no hidden epsilon and no stored positive infinity;
- closed intensity adapters for `SpatialKDEResult`, `NetworkField`,
  `SpatiotemporalKDEResult`, and `NetworkTimeField`;
- strict rejection of probability density as an event-rate numerator;
- immutable `EventRateField` and `estimate_event_rate(...)`;
- original intensity, original/effective exposure, masks, units, event mass, exposure
  totals, source fingerprints, and documented exposure-weighted summaries;
- analytical tests on spatial, network, space-time, and network-time supports.

```text
event_rate_j = event_intensity_j / exposure_density_j
rate_unit = event_unit / exposure_unit
```

## Implemented in progress subunit 03

- closed density adapters for the same four result families;
- mandatory `target="density"` for case and control;
- measured density-integral validation with explicit positive
  `normalization_tolerance`;
- explicit `GridSupport` requirement for spatial results because the complete grid is
  not retained by `SpatialKDEResult`;
- embedded support inference for network, ordinary space-time, and network-time results;
- shared positive scalar fixed-bandwidth contract;
- rejection of adaptive arrays, spatial matrices, and unequal case/control bandwidths;
- exact support, kernel, metric, boundary, junction, direction, network, CRS, units, and
  temporal-domain compatibility where applicable;
- legitimate different event fingerprint, event count, weights, and provenance retained
  but excluded from shared-configuration equality;
- immutable `RelativeRiskField` and `estimate_relative_risk(...)`;
- raw and log relative-risk outputs;
- original/effective control densities and invalid/adjusted masks;
- zero case density represented exactly as raw risk `0` and log risk `-inf`;
- zero control density handled only by explicit `raise`, `nan`, or `minimum` policy;
- reciprocal, sign-reversal, control-weighted normalization, denominator-policy,
  unequal-measure grid, lixel, cyclic space-time, and cyclic arixel tests.

```text
relative_risk_j = case_density_j / control_density_j
log_relative_risk_j = log(case_density_j) - log(control_density_j)
```

A temporary `.github/workflows/format-relative-risk.yml` workflow was used only to
obtain exact Black/isort output and was deleted before corrected validation. It must be
absent from the branch and final PR.

## Validation

Corrected implementation CI `#177` passed:

- Black, isort, Ruff, mypy, API mapping, and strict MkDocs;
- branch coverage;
- source/wheel distributions, Twine, archive verification, and isolated wheel smoke;
- Linux, Windows, and macOS on Python 3.11, 3.12, 3.13, and 3.14.

GitHub Actions is the authoritative validation environment.

## Exact next subunit

Complete the **0.0.15 public API and release unit**:

1. review and freeze public names and signatures across exposure, rate, and relative
   risk;
2. add stable top-level exports;
3. add a user guide distinguishing exposure-adjusted event rate from case-control
   density-ratio relative risk;
4. add a risk API reference page;
5. add one executable end-to-end public example;
6. register every new public symbol in the API-example map;
7. update README, roadmap, result documentation, changelog/release notes, and all
   authoritative version metadata;
8. bump the package from `0.0.14` to `0.0.15`;
9. create `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md` and matching development page;
10. run the full repository validation matrix;
11. verify PR diff, temporary-workflow absence, review threads, and mergeability;
12. mark PR ready, merge using the established method, and observe post-merge `main` CI;
13. record real merge and CI evidence before declaring 0.0.15 stable.

Do not add relative-risk bandwidth selection, independent or adaptive bandwidths,
inference, uncertainty, separability diagnostics, PostGIS/Zarr, or distributed execution
inside the finalization unit.

## Recovery checklist

1. Inspect PR #15 and verify its actual head, Draft state, merge state, and CI.
2. Confirm `.github/workflows/format-event-rate.yml` and
   `.github/workflows/format-relative-risk.yml` are absent.
3. Read the five records listed at the top.
4. Inspect all files under `src/pykdex/risk/`.
5. Run `tests/test_exposure_field.py`, `tests/test_event_rate.py`, and
   `tests/test_relative_risk.py`.
6. Run the full regression, coverage, quality, docs, distribution, isolated-wheel, and
   platform matrix.
7. Continue only with final public API and release completion.

The final release must create `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md` with actual
version, complete public API, examples, validation, PR, merge, and post-merge CI evidence.
