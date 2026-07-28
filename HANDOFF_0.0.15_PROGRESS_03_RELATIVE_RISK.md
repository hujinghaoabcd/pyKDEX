# pyKDEX 0.0.15 progress handoff 03: shared-bandwidth relative risk

This document is the durable engineering record for the third completed subunit of
pyKDEX 0.0.15. It follows the exposure-field and event-rate handoffs and records the
closed probability-density adapters, shared-fixed-bandwidth case-control relative-risk
field, analytical validation, deliberate exclusions, CI evidence, and exact continuation
point. It does not claim that the complete 0.0.15 release is finished.

## 1. Repository state

- Project: `hujinghaoabcd/pyKDEX`
- Latest stable merged version: `0.0.14`
- Active development version: `0.0.15`
- Branch: `agent/exposure-relative-risk`
- Draft pull request: `#15 Add exposure-adjusted rate and relative-risk foundations`
- Base commit on `main`: `1315619afba79a6ddf1fbfd7b91900bf0c0992f1`
- Relative-risk implementation and formatter-removal head:
  `5a42a59815cda5321ee89b52d0f86704b5f7f31f`
- Relative-risk progress handoff root commit:
  `9eb2686cd0e85b4fafad670ed7ab0de01662ed35`
- First relative-risk CI run: `#172` (`30353108398`), stopped at Black formatting
- Corrected implementation CI run: `#177` (`30353630091`), success
- Documentation-update CI: pending observation after progress records and MkDocs
  navigation updates
- PR state: open and draft
- Merge state: not merged
- Package version remains `0.0.14` until the final 0.0.15 public API, example,
  documentation, metadata, and release handoff are complete.

Read these records in order before continuing:

1. `docs/development/design-0.0.15-exposure-relative-risk.md`;
2. `HANDOFF_0.0.15_PROGRESS_01_EXPOSURE_FIELD.md`;
3. `HANDOFF_0.0.15_PROGRESS_02_EVENT_RATE.md`;
4. this document.

Do not merge PR #15 after only the three numerical subunits. The final public API,
executable example mapping, user documentation, version bump, release handoff, and
post-merge validation are still required.

## 2. Statistical object implemented

This subunit implements case-control density-ratio relative risk on a common measured
support. It is statistically distinct from the exposure-adjusted event rate implemented
in subunit 02.

For measured support elements indexed by `j`, let:

- `m_j > 0` be the actual cell, lixel, space-time, or arixel measure;
- `f_case,j >= 0` be a case probability density;
- `f_control,j >= 0` be a control probability density.

Each input must independently satisfy the measured normalization contract

```text
sum_j f_case,j * m_j approximately equals 1
sum_j f_control,j * m_j approximately equals 1
```

within an explicit positive `normalization_tolerance`, whose default is `1e-6`.
The implementation validates these integrals; it does not silently renormalize arbitrary
arrays or compensate for a truncated evaluation domain.

The raw relative-risk field is

```text
relative_risk_j = f_case,j / f_control,j
```

and the log-relative-risk field is

```text
log_relative_risk_j = log(f_case,j) - log(f_control,j)
```

where the control denominator is valid under the selected explicit denominator policy.
These fields are dimensionless density ratios. They are not case probabilities, odds,
incidence rates, or exposure-adjusted rates.

When both densities integrate to one and the original control density is strictly
positive, the control-weighted mean identity is

```text
sum_j relative_risk_j * f_control,j * m_j = 1
```

This identity is exposed through `control_weighted_mean` and tested analytically.

## 3. Shared fixed bandwidth contract

The first supported estimator is deliberately conservative: case and control results
must use the same scalar fixed bandwidth configuration.

Accepted bandwidth forms are:

- one positive scalar for `SpatialKDEResult`;
- one positive scalar for `NetworkField`;
- one positive spatial scalar and one positive temporal scalar for
  `SpatiotemporalKDEResult`;
- one positive network-distance scalar and one positive temporal scalar for
  `NetworkTimeField`.

Rejected forms include:

- adaptive one-value-per-event bandwidth arrays;
- support-specific adaptive arrays;
- spatial bandwidth matrices;
- separately selected case and control bandwidths;
- equal-looking arrays that do not represent the same measured support.

Exact tuple equality is required for the resolved scalar bandwidths. Bandwidth selection
itself remains outside this subunit.

## 4. Closed density-result adapter

`src/pykdex/risk/density.py` adds a private, closed adapter layer for exactly four
existing public result families:

```text
SpatialKDEResult
NetworkField
SpatiotemporalKDEResult
NetworkTimeField
```

Unsupported arbitrary or duck-typed result objects fail with `TypeError`. Both case and
control inputs must have `target="density"`; intensity results are rejected.

The internal immutable `DensityFieldView` retains:

- read-only density values;
- exact measured support and `SupportDescriptor`;
- result family;
- resolved scalar bandwidth tuple;
- shared estimator contract;
- source-result fingerprint;
- measured density integral;
- explicit normalization tolerance;
- immutable source metadata.

### 4.1 Event-specific versus shared metadata

Case and control samples are expected to differ in event fingerprint, event count,
weights, and other sample-specific provenance. Those fields are retained in each source
fingerprint and metadata but are not required to be equal.

The compatibility contract instead requires equality of the configuration that makes
the two densities scientifically comparable.

### 4.2 Spatial result contract

Spatial relative risk requires an explicit `support=GridSupport`. This is necessary
because `SpatialKDEResult` stores coordinates, identifiers, measures, CRS, unit, and a
support fingerprint but does not retain the complete grid object with bounds,
resolution, shape semantics, and provenance.

The adapter validates:

- exact grid support fingerprint;
- coordinates;
- stable identifiers;
- actual per-cell measures, including boundary remainder cells;
- CRS and spatial unit;
- scalar fixed bandwidth;
- kernel;
- metric;
- dimension;
- boundary-correction name and boundary fingerprint where retained.

A new `GridSupport` is never reconstructed or guessed from coordinates.

### 4.3 Network result contract

For `NetworkField`, the embedded `LixelSupport` is used when no support is supplied.
Compatibility requires:

- exact lixel-support fingerprint and measured lengths;
- scalar fixed bandwidth;
- kernel;
- junction policy;
- directed setting;
- network fingerprint;
- path-based versus simple evaluation contract where retained.

Case and control event fingerprints may differ and remain in their respective source
fingerprints.

### 4.4 Ordinary space-time contract

For `SpatiotemporalKDEResult`, the embedded measured support is used. Compatibility
requires:

- exact support and temporal-domain fingerprint;
- scalar spatial and temporal bandwidths;
- spatial and temporal kernels;
- spatial metric;
- CRS, spatial unit, temporal unit, identifiers, and measured support through exact
  support identity.

### 4.5 Network-time contract

For `NetworkTimeField`, the embedded `ArixelSupport` is used. Compatibility requires:

- exact arixel support, lixel lengths, time-bin measures, and temporal domain;
- scalar spatial and temporal bandwidths;
- spatial and temporal kernels;
- junction policy;
- directed setting;
- network fingerprint.

## 5. Public API in the development branch

The risk subpackage now exports:

```python
RelativeRiskField
estimate_relative_risk
```

alongside the exposure and event-rate APIs from the prior subunits.

The functional interface is:

```python
risk = estimate_relative_risk(
    case_density,
    control_density,
    support=grid_support,          # required only for SpatialKDEResult
    zero_policy="raise",
    validity_threshold=0.0,
    minimum_denominator=None,
    normalization_tolerance=1e-6,
)
```

For network, ordinary space-time, and network-time results, `support` may be omitted
because both result objects retain complete support objects. When an explicit support is
provided, it is still validated against both inputs.

These names are currently exported from `pykdex.risk`, not top-level `pykdex`. Top-level
exports and API-example mapping are deferred until the complete 0.0.15 surface is stable.

## 6. RelativeRiskField contract

`RelativeRiskField` is a frozen dataclass. Owned arrays are read-only. It retains:

- raw relative-risk values;
- log-relative-risk values;
- exact measured support and descriptor;
- original case density;
- original control density;
- effective control density after explicit denominator handling;
- invalid-control and adjusted-control masks;
- denominator policy;
- result family;
- shared scalar bandwidth tuple;
- immutable shared estimator contract;
- case and control source fingerprints;
- explicit normalization tolerance;
- immutable metadata;
- deterministic result fingerprint.

Construction independently revalidates:

- one value per measured support element;
- finite non-negative case and control densities;
- both measured integrals within tolerance of one;
- exact effective denominator and masks produced by the policy;
- raw ratio equality;
- log-ratio equality;
- absence of positive infinity;
- `NaN` occurrence exactly at invalid control cells under `nan` mode;
- positive finite scalar bandwidths and non-empty fingerprints.

Public summaries and exports include:

```text
case_integral
control_integral
effective_control_integral
control_weighted_mean
effective_control_weighted_mean
fingerprint
to_frame
to_grid
log_to_grid
to_geodataframe
```

## 7. Zero-density semantics

No pseudocount or hidden epsilon is introduced.

### 7.1 Zero case density

When the control denominator is valid and `f_case,j == 0`:

```text
relative_risk_j = 0
log_relative_risk_j = -infinity
```

Negative infinity is retained because it is the exact logarithm of zero relative risk.
Positive infinity is never retained.

### 7.2 Invalid control density

The existing immutable `DenominatorPolicy` is reused:

- `raise`: abort if control density is at or below `validity_threshold`;
- `nan`: return `NaN` at invalid control cells and retain the exact mask;
- `minimum`: floor control density at an explicit positive
  `minimum_denominator`, retaining original invalid and adjusted masks.

If division overflows even with a positive denominator, calculation raises and asks the
caller to inspect the density scale or choose an explicit larger minimum.

### 7.3 Weighting after a policy

`control_weighted_mean` uses the original control density over finite-risk cells.
`effective_control_weighted_mean` uses the actual denominator after flooring. These
quantities intentionally differ when `minimum` changes the denominator.

## 8. Files added or changed

Added:

```text
src/pykdex/risk/density.py
src/pykdex/risk/relative_risk.py
tests/test_relative_risk.py
HANDOFF_0.0.15_PROGRESS_03_RELATIVE_RISK.md
```

Changed:

```text
src/pykdex/risk/__init__.py
HANDOFF_NEXT_CONVERSATION.md
docs/development/handoff-0.0.15-progress-03-relative-risk.md
mkdocs.yml
```

A temporary branch-only workflow
`.github/workflows/format-relative-risk.yml` was created solely to run Black and isort
and upload the exact formatted files in the restricted execution environment. It was
deleted before corrected CI and must not exist in the branch or final PR.

## 9. Analytical and contract tests

`tests/test_relative_risk.py` covers:

1. nonuniform spatial density ratios on an unequal-measure grid;
2. raw reciprocal identity after swapping case and control;
3. log-risk sign reversal after swapping inputs;
4. case and control integral validation;
5. original and effective control-weighted normalization;
6. deterministic fingerprints and read-only arrays;
7. native raw and log grid reshaping;
8. default `raise` behavior at zero control density;
9. `nan` control handling and exact invalid masks;
10. explicit `minimum` flooring and adjusted masks;
11. exact zero-case raw risk and negative-infinite log risk;
12. rejection of intensity results;
13. rejection of non-normalized density results;
14. rejection of adaptive bandwidth arrays;
15. required explicit `GridSupport` for spatial results;
16. rejection of unequal case/control bandwidths;
17. rejection of kernel-contract mismatch;
18. rejection of support-fingerprint mismatch;
19. explicit normalization-tolerance sensitivity;
20. network-lixel relative risk with different case/control event provenance;
21. cyclic ordinary space-time grid relative risk;
22. cyclic network-time arixel relative risk;
23. preservation of network, junction, temporal-domain, and source metadata.

The constant network and time-domain fixtures are analytical references: identical
separately normalized densities on the same measured support must produce raw relative
risk one and log relative risk zero, independent of lixel or arixel measure.

## 10. Validation evidence

### 10.1 First implementation CI

CI run `#172` (`30353108398`) was triggered for the initial complete implementation.
Distribution construction and observed platform tests passed, while the quality job
stopped at Black formatting. Later quality steps were skipped, so this run is not used
as final validation evidence. No numerical failure was established by that run.

### 10.2 Exact formatting correction

Temporary formatter run `30353243769` executed Black and isort, uploaded the exact
formatted risk sources and tests, and completed successfully. Only the three newly added
files were written back. The temporary workflow itself was then deleted.

### 10.3 Corrected implementation CI

CI run `#177` (`30353630091`) completed successfully for implementation head
`5a42a59815cda5321ee89b52d0f86704b5f7f31f`.

Successful jobs include:

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

GitHub Actions is the authoritative validation environment. No unobserved local test
result is claimed.

### 10.4 Progress-documentation CI

The progress root handoff, development page, MkDocs navigation, current handoff entry,
and PR description were added after CI `#177`. Their complete CI result must be copied
from GitHub only after the documentation-update head has completed validation.

## 11. Deliberate exclusions

This subunit does not include:

- relative-risk bandwidth selection;
- independently selected case and control bandwidths;
- adaptive relative risk;
- spatial bandwidth matrices;
- automatic density renormalization on a truncated support;
- case probability or pooled-process odds;
- pseudocounts or shrinkage estimators;
- bootstrap, permutation, or asymptotic inference;
- tolerance contours or significance surfaces;
- separability diagnostics;
- persistence-schema changes;
- PostGIS, Zarr, remote storage, or distributed execution;
- top-level `pykdex` exports;
- final executable 0.0.15 example mapping;
- user-facing risk guide and API page;
- package version bump;
- final release handoff;
- merge of PR #15.

## 12. Rejected shortcuts

The following designs were explicitly rejected:

1. dividing intensity results and calling the result case-control relative risk;
2. accepting density arrays based only on matching shape;
3. accepting unmeasured point support;
4. reconstructing a `GridSupport` from spatial result coordinates;
5. comparing complete metadata dictionaries and thereby rejecting legitimate different
   case/control samples;
6. ignoring kernel, metric, boundary, junction, direction, network, or temporal-domain
   differences;
7. accepting adaptive or matrix bandwidths in the first implementation;
8. allowing unequal fixed case/control bandwidths;
9. silently renormalizing densities that do not integrate to one on measured support;
10. silently adding epsilon or a pseudocount to zero control density;
11. storing positive-infinite relative risk;
12. replacing exact negative-infinite log risk at zero case density by a finite number;
13. collapsing invalid and adjusted control masks;
14. exposing the incomplete API at top-level before final release validation;
15. retaining the temporary formatter workflow.

## 13. Exact next implementation subunit

Continue on `agent/exposure-relative-risk` and PR #15. The next subunit is the final
**0.0.15 public API and release-completion unit**.

Recommended order:

1. review the complete risk API names and signatures across all three subunits;
2. decide and add stable top-level exports for the final public objects and functions;
3. add a user-facing risk guide that clearly distinguishes exposure-adjusted event rate
   from case-control density-ratio relative risk;
4. add an API reference page for the public risk objects;
5. add one executable public example covering exposure, event rate, raw relative risk,
   log relative risk, explicit denominator policy, and measured-support validation;
6. register every new public symbol in the executable API-example map;
7. update README, changelog/release notes, roadmap, and relevant result documentation;
8. bump all authoritative package/version metadata from `0.0.14` to `0.0.15`;
9. create final root handoff `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md` and matching
   development documentation page;
10. run the complete regression, branch coverage, quality, typing, strict docs,
    distributions, isolated-wheel smoke, and three-system Python 3.11-3.14 matrix;
11. verify PR #15 diff, temporary-workflow absence, review threads, and mergeability;
12. mark the PR ready only when the complete release unit is clean;
13. merge with the repository's established method;
14. observe and record post-merge `main` CI before declaring 0.0.15 stable.

Do not add bandwidth selection, adaptive risk, inference, uncertainty, scalable storage,
or distributed execution to the finalization unit. Those require separate design units.

## 14. Recovery procedure

1. Read the four records listed at the beginning of this document.
2. Inspect PR #15 and verify its actual head, Draft state, merge state, and CI.
3. Confirm `.github/workflows/format-event-rate.yml` and
   `.github/workflows/format-relative-risk.yml` are absent.
4. Inspect `src/pykdex/risk/support.py`, `exposure.py`, `policies.py`, `intensity.py`,
   `rate.py`, `density.py`, and `relative_risk.py`.
5. Run `tests/test_exposure_field.py`, `tests/test_event_rate.py`, and
   `tests/test_relative_risk.py`.
6. Run the complete repository validation matrix.
7. Continue only with final API and release completion; do not redesign the validated
   numerical contracts inside the finalization unit without new analytical evidence.
