# pyKDEX current handoff

The latest merged version is **0.0.15**. The next task is a new detailed design for
**0.0.16 uncertainty, separability diagnostics, and scalable execution**.

Read these records in order:

1. `HANDOFF_0.0.14_WORKSPACE_PERSISTENCE.md`;
2. `docs/development/design-0.0.15-exposure-relative-risk.md`;
3. `HANDOFF_0.0.15_PROGRESS_01_EXPOSURE_FIELD.md`;
4. `HANDOFF_0.0.15_PROGRESS_02_EVENT_RATE.md`;
5. `HANDOFF_0.0.15_PROGRESS_03_RELATIVE_RISK.md`;
6. `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`.

## Current stable state

- repository: `hujinghaoabcd/pyKDEX`;
- default branch: `main`;
- package version: `0.0.15`;
- release PR: `#15 Release pyKDEX 0.0.15 exposure-adjusted rates and relative risk`;
- release-candidate head: `2652c8b81a662e358059eb809cbde645c05ebb8b`;
- release-candidate CI: `#229` (`30357305493`), success;
- PR audit: 33 intended changed files, no comments, no temporary formatter workflows;
- merge method: squash;
- merge commit: `dcac85cd1399b9ad18257451601dcc47c4e73f20`;
- merged at: `2026-07-28T12:09:31Z`;
- PR state: closed and merged;
- root merge-state record commit: `a118ece967fc507baa4b2ea321ade2b2bca390e5`;
- development handoff update commit: `98b9545dc14c1f75bd474dfeba72e11dbb1fae74`;
- this current-handoff update creates the final recorded `main` head for the task.

The CI workflow is configured to run on pushes to `main`. The available connector can
fully inspect PR-triggered runs but cannot enumerate repository push-triggered runs by
commit. Therefore CI #229 and the merge are recorded as observed facts, while no later
push result is invented. Inspect the live Actions page before relying on a status newer
than this handoff.

## 0.0.15 public API

The five new top-level exports are:

```python
ExposureField
EventRateField
RelativeRiskField
estimate_event_rate
estimate_relative_risk
```

They are also available from `pykdex.risk`. Advanced `DenominatorPolicy` and support
helpers remain in the risk subpackage rather than top-level `pykdex`.

## Exposure fields

`ExposureField` stores immutable exposure density on exact measured support and can be
constructed from density or per-element amounts.

```text
exposure_amount_j = exposure_density_j * support_measure_j
total_exposure = sum_j exposure_amount_j
```

It retains units, provenance, actual support measures, totals, fingerprints, and table,
grid, or geospatial exports.

## Exposure-adjusted event rates

Event rates require an intensity numerator and independent exposure density:

```text
event_rate_j = event_intensity_j / exposure_density_j
rate_unit = event_unit / exposure_unit
```

Probability density is rejected because it has discarded total event mass.
`EventRateField` retains event mass, exposure totals, units, original and effective
denominators, masks, source fingerprints, and weighted summaries.

## Case-control relative risk

Relative risk compares separately normalized case and control densities:

```text
relative_risk_j = case_density_j / control_density_j
log_relative_risk_j = log(case_density_j) - log(control_density_j)
```

Version 0.0.15 requires exact measured-support and estimator-contract compatibility with
shared positive scalar fixed bandwidths. Event fingerprints, sample sizes, weights, and
sample provenance may differ.

No hidden epsilon or pseudocount is introduced. Zero case density gives raw risk `0` and
log risk `-inf` when control is valid. Zero control density follows explicit `raise`,
`nan`, or `minimum` policy and never produces stored positive infinity.

## Supported measured domains

- spatial grids with actual cell area;
- network lixels with actual length;
- ordinary space-time support with spatial measure × temporal width;
- network-time arixels with lixel length × temporal width.

Support compatibility uses fingerprints, stable identifiers, measures, CRS, units,
network identity, and temporal-domain identity rather than shape.

## Executable example and documentation

```text
examples/17_exposure_relative_risk.py
docs/guides/exposure-relative-risk.md
docs/api/risk.md
```

All five top-level names are mapped in `examples/API_COVERAGE.csv`, and the installed
wheel smoke test validates version `0.0.15` and the public risk field classes.

## Observed validation

Release-candidate CI #229 passed:

- Black, isort, Ruff, and mypy;
- complete public API example mapping;
- strict MkDocs;
- branch coverage and complete tests;
- source and wheel builds, Twine, archive verification, and installed-wheel smoke;
- Linux, Windows, and macOS on Python 3.11, 3.12, 3.13, and 3.14.

## 0.0.16 exact next task

Do not immediately code 0.0.16. First create a detailed design document and decide the
statistical and engineering boundaries of three separate themes:

1. uncertainty;
2. separability diagnostics;
3. scalable execution.

The design must answer at least:

- which uncertainty object is valid for density, intensity, event rate, and relative
  risk;
- bootstrap versus asymptotic versus permutation responsibilities;
- how resampling preserves event weights, measured support, network components, cyclic
  time, and case/control sample identity;
- whether uncertainty belongs to estimators, result objects, experiments, or a separate
  inference package;
- what separability means for ordinary space-time and network-time KDE;
- which diagnostic statistics have analytical or independent numerical references;
- how chunking, sparse assets, memory budgets, and optional parallel execution preserve
  deterministic results;
- which computations can be cached without weakening fingerprints and provenance;
- how scalable execution remains independent from future PostGIS/Zarr storage adapters.

## 0.0.16 exclusions until designed

Do not add any of the following before the detailed design is reviewed:

- adaptive or independently selected case/control relative-risk bandwidths;
- undocumented confidence intervals;
- significance contours without calibrated reference distributions;
- generic bootstrap wrappers that ignore network or cyclic-time structure;
- approximate execution that silently changes numerical semantics;
- PostGIS or Zarr persistence;
- distributed execution APIs.

## Recovery checklist

1. Inspect the current `main` head and live Actions status.
2. Read all six records listed at the top.
3. Confirm package version `0.0.15` and the five risk exports.
4. Run the three risk test modules and all numbered examples.
5. Run the complete quality, typing, docs, coverage, distribution, wheel, and platform
   matrix before changing numerical contracts.
6. Create the detailed 0.0.16 design and a new root handoff before implementation.
