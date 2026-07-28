# pyKDEX current handoff

The latest stable merged version is **0.0.14**. Branch
`agent/exposure-relative-risk` is now the **0.0.15 release candidate**.

Read these records in order:

1. `HANDOFF_0.0.14_WORKSPACE_PERSISTENCE.md`;
2. `docs/development/design-0.0.15-exposure-relative-risk.md`;
3. `HANDOFF_0.0.15_PROGRESS_01_EXPOSURE_FIELD.md`;
4. `HANDOFF_0.0.15_PROGRESS_02_EVENT_RATE.md`;
5. `HANDOFF_0.0.15_PROGRESS_03_RELATIVE_RISK.md`;
6. `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`.

## Current state

- repository: `hujinghaoabcd/pyKDEX`;
- branch: `agent/exposure-relative-risk`;
- release-candidate head before this handoff update:
  `9e54215fa7a057bf8fe3ca5ba87a0d3433b3d1db`;
- PR: `#15 Add exposure-adjusted rate and relative-risk foundations`;
- PR state: open, Draft, mergeable, not merged;
- base `main`: `1315619afba79a6ddf1fbfd7b91900bf0c0992f1`;
- package version in the branch: `0.0.15`;
- last fully observed pre-release status CI:
  `#214` (`30355794150`), success;
- final release-candidate CI after API, version, example, and documentation changes:
  pending observation;
- merge commit: not created;
- post-merge `main` CI: not observed.

Do not claim 0.0.15 is stable until the final candidate CI, merge, and post-merge `main`
CI have been observed and recorded.

## Completed numerical subunits

### 01. Exposure fields

- exact measured-support identity for spatial grids, lixels, measured space-time, and
  arixels;
- immutable `SupportDescriptor` and `ExposureField`;
- construction from density or per-element amounts;
- exposure units, provenance, totals, fingerprints, and exports.

```text
exposure_amount_j = exposure_density_j * support_measure_j
total_exposure = sum_j exposure_amount_j
```

### 02. Exposure-adjusted event rates

- explicit immutable `raise`, `nan`, and `minimum` denominator policies;
- closed intensity adapters for spatial, network, space-time, and network-time results;
- rejection of probability density as the numerator;
- immutable `EventRateField` and `estimate_event_rate`;
- event mass, exposure totals, units, masks, source fingerprints, and weighted summaries.

```text
event_rate_j = event_intensity_j / exposure_density_j
rate_unit = event_unit / exposure_unit
```

### 03. Shared-fixed-bandwidth relative risk

- closed density adapters for the same four result families;
- separately normalized case and control densities;
- exact support and estimator-contract compatibility;
- shared positive scalar fixed bandwidths;
- immutable `RelativeRiskField` and `estimate_relative_risk`;
- raw and log risk, original/effective control density, masks, fingerprints, and
  control-weighted summaries.

```text
relative_risk_j = case_density_j / control_density_j
log_relative_risk_j = log(case_density_j) - log(control_density_j)
```

Zero case density gives raw risk `0` and log risk `-inf` when control is valid. Zero
control density follows an explicit policy and never produces stored positive infinity.

## Final public release surface

The five new top-level exports are:

```python
ExposureField
EventRateField
RelativeRiskField
estimate_event_rate
estimate_relative_risk
```

Release completion changes already added to the branch:

- `src/pykdex/__init__.py` reports `0.0.15` and exports the five names;
- `examples/17_exposure_relative_risk.py` is the executable end-to-end example;
- `examples/API_COVERAGE.csv` maps all five symbols;
- `tools/smoke_installed_distribution.py` validates the 0.0.15 wheel and risk exports;
- `docs/guides/exposure-relative-risk.md` documents the statistical distinction;
- `docs/api/risk.md` documents the risk API;
- README, English and Chinese site homes, roadmap, changelog, and MkDocs navigation are
  updated;
- `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md` and its development page are present.

## Validation history

Observed successful runs before the final release surface:

- implementation CI `#177` (`30353630091`);
- progress-documentation CI `#201` (`30354857130`);
- final progress-state CI `#214` (`30355794150`).

Each passed quality, typing, strict docs, branch coverage, distributions, isolated wheel
smoke, and Linux/Windows/macOS Python 3.11-3.14 testing for its own head.

The new release-candidate head must receive its own complete CI before PR readiness or
merge.

## Exact continuation procedure

1. Run and observe the complete CI for the current release-candidate head.
2. Fix only failures established by logs and rerun the complete matrix.
3. Inspect all PR changed files and verify both temporary formatter workflows are absent.
4. Inspect PR comments and unresolved review threads.
5. Update the PR title and body to describe the complete 0.0.15 release.
6. Mark PR #15 ready for review only after all checks pass.
7. Confirm the ready PR remains mergeable and required checks are successful.
8. Merge using the repository's established method.
9. Observe the actual merge commit and post-merge `main` CI.
10. Update `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md` and this file with real merge and
    post-merge evidence.
11. Only then declare 0.0.15 stable and begin a new detailed 0.0.16 design.

## 0.0.16 boundary

The next roadmap unit is uncertainty, separability diagnostics, and scalable execution.
Do not add adaptive relative risk, independent case/control bandwidths, inference,
PostGIS/Zarr, or distributed execution to the 0.0.15 release candidate.
