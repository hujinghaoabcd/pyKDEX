# pyKDEX 0.0.15 progress handoff 02: exposure-adjusted event rates

This document is the durable engineering record for the second completed subunit of
pyKDEX 0.0.15. It follows `HANDOFF_0.0.15_PROGRESS_01_EXPOSURE_FIELD.md` and records
the explicit denominator policies, measured intensity adapters, event-rate field,
analytical validation, limitations, and exact continuation point. It does not claim
that the complete 0.0.15 release is finished.

## 1. Repository state

- Project: `hujinghaoabcd/pyKDEX`
- Latest stable merged version: `0.0.14`
- Active development version: `0.0.15`
- Branch: `agent/exposure-relative-risk`
- Draft pull request: `#15 Add exposure-adjusted rate and relative-risk foundations`
- Base commit on `main`: `1315619afba79a6ddf1fbfd7b91900bf0c0992f1`
- Exposure-field foundation head: `40fc66841fdde4fa90774ed79ca31bb1fd5b4f58`
- Event-rate implementation head before handoff documents:
  `c806f34a2ebba8eb3dd1ae72cadcb7d895ef6ad1`
- Event-rate handoff-update head validated by CI:
  `a32652619f3990c91c811ea6e8381adb1727ceaa`
- First event-rate CI run: `#156` (`30350961687`), Black formatting failure
- Corrected implementation CI run: `#162` (`30351398127`), successful quality,
  coverage, distributions, and observed platform jobs; superseded by later handoff
  commits before a final workflow conclusion was used as the authoritative record
- Complete handoff-update CI run: `#165` (`30351722623`), success
- PR state: open and draft
- Merge state: not merged
- Package version remains `0.0.14` until the complete 0.0.15 unit is finished.

Read these files before continuing:

1. `docs/development/design-0.0.15-exposure-relative-risk.md`;
2. `HANDOFF_0.0.15_PROGRESS_01_EXPOSURE_FIELD.md`;
3. this document.

Do not merge PR #15 after only the exposure and event-rate subunits. The planned
case-control relative-risk subunit, final public API, example mapping, version bump,
and final release handoff are still required.

## 2. Purpose of this subunit

The first subunit created an immutable exposure denominator tied to measured support.
The second subunit adds the statistically distinct operation

```text
exposure-adjusted event rate = event intensity / exposure density
```

while preserving all information required to interpret the result:

- total event mass;
- original exposure total;
- effective exposure used after an explicit denominator policy;
- invalid and adjusted support-element masks;
- event and exposure units;
- exact measured-support identity;
- source intensity fingerprint and estimator metadata.

This is not case-control relative risk. It does not compare two separately normalized
probability densities and it does not estimate case probability or case odds.

## 3. Statistical definition

For measured support elements indexed by `j`, let:

- `m_j > 0` be the actual support measure;
- `lambda_j >= 0` be event intensity per unit support measure;
- `e_j >= 0` be exposure density per unit support measure.

The event rate is

```text
q_j = lambda_j / e_j
```

with unit

```text
event_unit / exposure_unit
```

The numerator must be an intensity field. A `target="density"` result is rejected
because its normalization has removed the total event mass needed for a rate.

The integrated event mass and original exposure total are retained separately:

```text
event_mass = sum_j lambda_j * m_j
exposure_total = sum_j e_j * m_j
```

The geometric integral of `q_j` is deliberately not exposed as “total risk” because it
has no universal interpretation. Instead, `EventRateField` exposes two documented
summaries:

```text
original-exposure-weighted mean
    = sum_j q_j * e_j * m_j / sum_j e_j * m_j

effective-exposure-weighted mean
    = sum_j q_j * e_eff_j * m_j / sum_j e_eff_j * m_j
```

The first reflects the original data over finite-rate cells. The second reflects the
actual denominator used after `minimum` flooring. When no denominator is invalid or
adjusted, both recover `event_mass / exposure_total`.

## 4. Explicit denominator policies

No hidden epsilon is used. The immutable `DenominatorPolicy` supports exactly three
modes.

### 4.1 `raise`

- default mode;
- values less than or equal to `validity_threshold` are invalid;
- any invalid denominator aborts the calculation;
- no rate field is returned.

### 4.2 `nan`

- values less than or equal to `validity_threshold` are invalid;
- the effective denominator and rate are `NaN` at those support elements;
- the exact invalid mask is retained and exported;
- positive infinity is never stored.

### 4.3 `minimum`

- requires an explicit finite positive `minimum_denominator`;
- denominators below that value are replaced by it;
- true non-positive denominators remain marked in `invalid_mask`;
- every floored denominator is marked in `adjusted_mask`;
- the threshold and affected counts are stored in metadata;
- this is an explicit sensitivity assumption, not numerical housekeeping.

The following shortcuts are rejected:

- undocumented machine epsilon;
- `inf` at zero exposure;
- supplying `minimum_denominator` to another mode;
- combining an already constructed `DenominatorPolicy` with duplicate scalar policy
  arguments;
- negative validity thresholds;
- a non-positive minimum denominator.

## 5. Closed measured-intensity adapter

`src/pykdex/risk/intensity.py` introduces a private, closed adapter contract for the
four existing public result families:

```text
SpatialKDEResult
NetworkField
SpatiotemporalKDEResult
NetworkTimeField
```

Unsupported arbitrary objects fail with `TypeError`. All accepted inputs must have
`target="intensity"` and finite non-negative values.

### 5.1 Spatial result validation

A spatial event rate requires exposure on `GridSupport`. The adapter verifies:

- explicit result `support_fingerprint`;
- exact match with the exposure-grid fingerprint;
- exact support coordinates;
- exact stable support identifiers;
- exact per-cell measures, including boundary remainder cells;
- exact CRS;
- exact spatial unit;
- measured support presence;
- estimator kernel, metric, bandwidth, boundary metadata, and source metadata in the
  source fingerprint.

The result's array shape alone is never sufficient.

### 5.2 Network result validation

For `NetworkField`, the adapter verifies the exact `LixelSupport` fingerprint and
retains:

- kernel;
- junction policy;
- directed setting;
- network fingerprint;
- event fingerprint;
- bandwidth and source metadata.

Actual lixel lengths remain the integration measure.

### 5.3 Ordinary space-time result validation

For `SpatiotemporalKDEResult`, the adapter verifies the exact measured
`SpatiotemporalPointSupport` or `SpatiotemporalGridSupport` fingerprint and retains:

- spatial and temporal bandwidths;
- spatial and temporal kernels;
- spatial metric;
- CRS and units through support identity;
- temporal-domain fingerprint through support identity;
- source metadata.

### 5.4 Network-time result validation

For `NetworkTimeField`, the adapter verifies the exact `ArixelSupport` fingerprint and
retains:

- spatial and temporal bandwidths;
- spatial and temporal kernels;
- junction policy;
- directed setting;
- network and event fingerprints;
- temporal-domain identity;
- length-times-time measures;
- source metadata.

The adapter returns an immutable internal `IntensityFieldView`; it does not retain a
mutable estimator object or alter the existing result classes.

## 6. Public event-rate API in this development branch

The risk subpackage now exports:

```python
DenominatorPolicy
EventRateField
estimate_event_rate
```

alongside the exposure and support objects added in subunit 01.

The functional interface is:

```python
rate = estimate_event_rate(
    event_intensity,
    exposure,
    event_unit="events",
    zero_policy="raise",
    validity_threshold=0.0,
    minimum_denominator=None,
)
```

`event_unit` is mandatory. It is not inferred from an estimator or from the support.
The result unit is represented explicitly as `event_unit/exposure_unit`.

These names are currently exported from `pykdex.risk`, not from top-level `pykdex`.
Top-level exports, API-example mapping, and version metadata are deferred until the
complete 0.0.15 API is stable.

## 7. EventRateField contract

`EventRateField` is a frozen dataclass. Its owned arrays are read-only. It retains:

- rate values;
- exact measured support and descriptor;
- original event-intensity values;
- original `ExposureField`;
- effective exposure after policy application;
- invalid-denominator mask;
- adjusted-denominator mask;
- immutable denominator policy;
- explicit event unit;
- source intensity fingerprint;
- immutable metadata;
- deterministic result fingerprint.

Construction re-applies the denominator policy and independently verifies that:

- all arrays contain one value per support element;
- support and exposure fingerprints agree;
- intensity is finite and non-negative;
- rate values are non-negative and never infinite;
- effective exposure and masks match the policy exactly;
- stored rate values equal `event_intensity / effective_exposure`;
- `NaN` values occur exactly at invalid cells and only under `nan` mode.

Public properties and exports include:

```text
rate_unit
event_mass
total_exposure
effective_exposure_total
exposure_weighted_mean_rate
effective_exposure_weighted_mean_rate
fingerprint
to_frame
to_grid
to_geodataframe
```

`to_frame` and geospatial export preserve intensity, original exposure, effective
exposure, rate, invalid mask, and adjusted mask.

## 8. Files added or changed in this subunit

Added:

```text
src/pykdex/risk/policies.py
src/pykdex/risk/intensity.py
src/pykdex/risk/rate.py
tests/test_event_rate.py
HANDOFF_0.0.15_PROGRESS_02_EVENT_RATE.md
```

Changed:

```text
src/pykdex/risk/__init__.py
HANDOFF_NEXT_CONVERSATION.md
docs/development/handoff-0.0.15-progress-02-event-rate.md
```

A temporary branch-only workflow named
`.github/workflows/format-event-rate.yml` was created solely to obtain exact
Black/isort output in the restricted execution environment. It was deleted before the
corrected clean validation and is absent from the validated handoff head.

## 9. Analytical and contract tests

`tests/test_event_rate.py` covers:

1. denominator-policy constructors and invalid argument combinations;
2. constant intensity divided by constant exposure on an unequal-measure spatial grid;
3. event-mass and exposure-total identity;
4. recovery of `event_mass / exposure_total` by the exposure-weighted mean when no
   denominator is changed;
5. deterministic field fingerprints;
6. read-only values and masks;
7. linear scaling with event intensity;
8. inverse scaling with exposure;
9. `raise`, `nan`, and `minimum` denominator behavior;
10. validity thresholds above zero;
11. exact invalid and adjusted masks;
12. rejection of probability-density numerators;
13. rejection of spatial support-fingerprint mismatch;
14. network-lixel rate using actual lixel lengths and network semantics;
15. cyclic ordinary space-time grid rate;
16. cyclic network-time arixel rate;
17. native grid reshaping for spatial, space-time, and network-time results;
18. preservation of junction and temporal-domain metadata.

The constant-field fixtures are analytical references. For each domain, constant
`lambda` and constant positive `e` must produce constant `lambda/e` independently of
cell, lixel, or arixel measure. The measured support remains necessary for mass and
exposure totals.

## 10. Validation evidence

### 10.1 First event-rate CI

CI run `#156` (`30350961687`) was triggered at the first complete event-rate
implementation. Observed successful work before the quality job stopped included
source/wheel distribution construction and completed platform tests. The quality job
failed at Black formatting, so later quality steps were skipped.

No numerical failure was established by that run. The confirmed issue was formatting
of newly added event-rate files.

### 10.2 Formatting correction

A temporary branch-only formatter workflow ran Black and isort over the new risk files
and `tests/test_event_rate.py`, uploaded the exact formatted output as an Actions
artifact, and was then removed. Only the formatted source and test changes were
retained.

### 10.3 Corrected implementation CI

CI run `#162` (`30351398127`) validated the corrected implementation head
`c806f34a2ebba8eb3dd1ae72cadcb7d895ef6ad1`. Quality, coverage, distributions, and
observed platform jobs passed. Subsequent handoff commits superseded this run, so its
overall workflow conclusion is not used as the final authoritative subunit record.

### 10.4 Complete handoff-update CI

CI run `#165` (`30351722623`) completed successfully for head
`a32652619f3990c91c811ea6e8381adb1727ceaa`.

Observed successful jobs include:

- Black;
- isort;
- Ruff;
- mypy;
- public-API example-map validation;
- strict MkDocs build;
- branch-coverage suite;
- source and wheel distribution build;
- Twine metadata validation;
- distribution archive verification;
- isolated wheel installation and smoke test;
- Linux, Windows, and macOS tests across Python 3.11, 3.12, 3.13, and 3.14.

No unobserved local test result is claimed. GitHub Actions is the authoritative
validation environment for this subunit.

## 11. Deliberate exclusions

This subunit does not include:

- `RelativeRiskField`;
- `estimate_relative_risk`;
- case-control density-ratio risk;
- log relative risk;
- case probability or pooled-process odds;
- shared-bandwidth compatibility checking between two density results;
- relative-risk bandwidth selection;
- adaptive or independently selected case/control bandwidths;
- shrinkage estimators;
- bootstrap or asymptotic inference;
- tolerance contours;
- separability diagnostics;
- persistence-schema changes;
- PostGIS, Zarr, remote storage, or distributed execution;
- version bump from `0.0.14` to `0.0.15`;
- top-level `pykdex` exports;
- the final executable 0.0.15 public example.

## 12. Rejected shortcuts

The following designs were rejected:

1. accepting probability density as a rate numerator;
2. inferring event units from estimator metadata;
3. comparing numerator and exposure by shape only;
4. allowing arbitrary duck-typed intensity objects;
5. silently applying epsilon to zero exposure;
6. storing positive infinity at zero exposure;
7. collapsing invalid and adjusted denominator masks into one flag;
8. reporting a geometric rate integral as total risk;
9. dropping original exposure after minimum flooring;
10. discarding estimator-specific network, time-domain, kernel, or metric metadata;
11. exposing the incomplete API at top-level before relative risk is implemented;
12. retaining the temporary formatter workflow.

## 13. Exact next implementation subunit

Continue on `agent/exposure-relative-risk` and PR #15. The next subunit is
**shared-fixed-bandwidth case-control relative risk**.

Recommended order:

1. add a closed density-result adapter for the same four result families;
2. require `target="density"` for both case and control inputs;
3. require exact measured-support identity;
4. verify that each input approximately integrates to one on measured support, with an
   explicit documented tolerance;
5. require scalar fixed bandwidths and reject adaptive arrays;
6. require equal case/control bandwidths;
7. require equal kernel family, metric or junction policy, boundary-correction contract,
   directed setting, network identity, temporal domain, CRS, and units;
8. implement immutable `RelativeRiskField`;
9. implement raw density ratio `case_density / control_density`;
10. implement log relative risk `log(case_density) - log(control_density)` as a
    first-class output;
11. reuse the explicit `raise`, `nan`, and `minimum` denominator policies for control
    density;
12. retain case and control source fingerprints, raw densities, effective control
    density, masks, bandwidth contract, and estimator metadata;
13. test identical densities, swapped inputs, reciprocal/negation identities, control-
    weighted normalization, all denominator policies, and all four support families;
14. create progress handoff 03 before completing the final 0.0.15 public API and release
    documents.

Do not add relative-risk bandwidth selection, adaptive relative risk, inference, or
scalable execution in this next subunit.

## 14. Recovery procedure

1. Read the three records listed at the beginning of this document.
2. Inspect PR #15 and verify its actual head, draft state, and CI.
3. Confirm `.github/workflows/format-event-rate.yml` is absent.
4. Inspect `src/pykdex/risk/policies.py`.
5. Inspect `src/pykdex/risk/intensity.py`.
6. Inspect `src/pykdex/risk/rate.py`.
7. Run `tests/test_exposure_field.py` and `tests/test_event_rate.py`.
8. Run the full regression, branch coverage, formatting, lint, typing, strict docs,
   distribution, isolated-wheel, and complete platform matrix.
9. Continue with the relative-risk subunit only after the branch is clean.
10. Keep PR #15 draft until all 0.0.15 public APIs and release records are complete.

## 15. Permanent project rules

The existing handoff, numerical-reference, implementation-independence, public-example,
and CI-truthfulness rules remain in force. Every completed subunit must leave a
recoverable Markdown record. The final 0.0.15 release must still create
`HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md` containing the final version, complete public
API, tests, coverage, examples, documentation, PR, CI, and merge evidence.
