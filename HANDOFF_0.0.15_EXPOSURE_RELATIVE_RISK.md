# pyKDEX 0.0.15 final handoff: exposure-adjusted rates and relative risk

This is the durable engineering and release handoff for pyKDEX 0.0.15. It consolidates
the three implementation subunits, final public API, analytical validation, release
candidate, pull-request audit, and observed merge state. Future conversations must read
this file before designing 0.0.16.

## 1. Final repository state

- Project: `hujinghaoabcd/pyKDEX`
- Stable package version in `main`: `0.0.15`
- Previous stable version: `0.0.14`
- Development branch: `agent/exposure-relative-risk`
- Pull request: `#15 Release pyKDEX 0.0.15 exposure-adjusted rates and relative risk`
- Release-candidate head: `2652c8b81a662e358059eb809cbde645c05ebb8b`
- Release-candidate CI: `#229` (`30357305493`), success
- PR transition: Draft to Ready after successful CI and audit
- Merge method: squash
- Merge commit: `dcac85cd1399b9ad18257451601dcc47c4e73f20`
- Merged at: `2026-07-28T12:09:31Z`
- PR state: closed and merged
- Merge-state documentation commit: created by the update containing this file
- Post-merge `main` CI: must be inspected for the final merge-state documentation head;
  the available connector exposes PR-triggered workflow runs but not repository push-run
  enumeration, so no unobserved push result is claimed here.

The CI workflow is configured to run on pushes to `main` and `master`, pull requests, and
manual dispatch. A later conversation must inspect the live Actions state before relying
on a statement about the merge-state documentation commit.

Read these records in order:

1. `docs/development/design-0.0.15-exposure-relative-risk.md`;
2. `HANDOFF_0.0.15_PROGRESS_01_EXPOSURE_FIELD.md`;
3. `HANDOFF_0.0.15_PROGRESS_02_EVENT_RATE.md`;
4. `HANDOFF_0.0.15_PROGRESS_03_RELATIVE_RISK.md`;
5. this final handoff;
6. `HANDOFF_NEXT_CONVERSATION.md`.

## 2. Release purpose

Version 0.0.15 adds two statistically distinct layers on measured pyKDEX supports:

1. exposure-adjusted event rates; and
2. separately normalized case-control density-ratio relative risk.

They share support-validation and denominator-policy infrastructure but are not collapsed
into one ambiguous operation.

## 3. Final top-level public API

The five new stable top-level exports are:

```python
ExposureField
EventRateField
RelativeRiskField
estimate_event_rate
estimate_relative_risk
```

They are available from both:

```python
from pykdex import ...
from pykdex.risk import ...
```

`pykdex.risk` additionally exposes `DenominatorPolicy` and advanced measured-support
helpers. Those helper names are intentionally not added to top-level `pykdex`.

## 4. Measured-support contract

Every exposure, rate, and relative-risk field is bound to explicit measured support.
Supported domains are:

- `GridSupport`, measured by actual cell area;
- `LixelSupport`, measured by actual lixel length;
- measured ordinary space-time support, measured by spatial measure multiplied by
  temporal-cell width;
- `ArixelSupport`, measured by lixel length multiplied by temporal-cell width.

Compatibility is never inferred from shape alone. Validation includes the applicable:

```text
support fingerprint
stable identifiers
per-element measure
CRS
spatial unit
temporal unit
time-domain fingerprint
network fingerprint
```

Boundary remainder cells, unequal lixels, and unequal final time bins retain their real
measure.

## 5. ExposureField

`ExposureField` is immutable and stores canonical exposure density with respect to support
measure. It can be constructed from density or from per-element amounts.

For support element `j` with measure `m_j`, density `e_j`, and amount `E_j`:

```text
E_j = e_j * m_j
E_total = sum_j e_j * m_j
```

Public constructors:

```python
ExposureField.from_density(...)
ExposureField.from_amounts(...)
```

The field retains:

- read-only canonical density values;
- recoverable per-element amounts;
- original representation (`density` or `amount`);
- exposure unit;
- exact support and descriptor;
- provenance and immutable metadata;
- measured total exposure;
- deterministic fingerprint;
- DataFrame, grid, and GeoDataFrame exports where supported.

Negative or non-finite exposure is rejected. A complete zero field may be represented for
data inspection but is rejected by default rate calculation.

## 6. Explicit denominator policy

No hidden epsilon, pseudocount, or implicit denominator regularization is used.

The immutable policy supports:

- `raise`: reject denominators at or below the validity threshold;
- `nan`: produce `NaN` exactly at invalid elements and preserve the invalid mask;
- `minimum`: use an explicitly supplied positive floor and preserve both invalid and
  adjusted masks.

Positive-infinite rate or relative-risk values are never stored.

## 7. Exposure-adjusted event rates

The numerator must be event intensity. Probability density is rejected because it has
lost total event mass.

For intensity `lambda_j` and exposure density `e_j`:

```text
q_j = lambda_j / e_j
rate_unit = event_unit / exposure_unit
```

The closed adapter accepts exactly:

```text
SpatialKDEResult
NetworkField
SpatiotemporalKDEResult
NetworkTimeField
```

with `target="intensity"`.

`EventRateField` retains:

- rate values;
- original intensity;
- original and effective exposure;
- invalid and adjusted masks;
- event and rate units;
- measured event mass and exposure totals;
- original and effective exposure-weighted mean rates;
- source fingerprint and metadata;
- deterministic result fingerprint;
- tabular, grid, and geospatial exports.

When no cell is excluded or floored:

```text
exposure-weighted mean rate = total event mass / total exposure
```

The geometric integral of a rate field is not labelled total risk.

## 8. Case-control relative risk

Case and control inputs must be separately normalized probability densities on the exact
same measured support.

For case density `f_j` and control density `g_j`:

```text
r_j = f_j / g_j
rho_j = log(f_j) - log(g_j)
```

Both densities must satisfy:

```text
sum_j density_j * measure_j approximately equals 1
```

within explicit positive `normalization_tolerance`, default `1e-6`. Arbitrary or
truncated fields are not silently renormalized.

The closed density adapter accepts the same four result families with
`target="density"`.

### 8.1 Shared fixed-bandwidth restriction

Version 0.0.15 requires:

- positive scalar fixed bandwidths;
- exact equality of case and control bandwidth tuples;
- matching kernels;
- matching spatial metric or network junction policy;
- matching boundary-correction contract;
- matching direction, network, and time-domain contracts;
- exact measured-support identity.

Adaptive arrays, bandwidth matrices, and independently selected case/control bandwidths
are rejected.

Event fingerprints, sample sizes, weights, and sample provenance may differ. They are
retained separately and intentionally excluded from shared estimator-contract equality.

### 8.2 RelativeRiskField

The immutable field retains:

- raw and log relative risk;
- original case and control densities;
- effective control density;
- invalid and adjusted control masks;
- result family and shared bandwidth tuple;
- shared estimator contract;
- separate source fingerprints and metadata;
- measured case and control integrals;
- original and effective control-weighted means;
- deterministic fingerprint;
- DataFrame, grid, log-grid, and GeoDataFrame exports.

When original control density is strictly positive:

```text
sum_j r_j * g_j * m_j = 1
```

Zero case density with valid control produces raw risk `0` and exact log risk `-inf`.
Zero control density follows the explicit policy and never yields stored positive
infinity.

## 9. Executable example and public API coverage

The complete example is:

```text
examples/17_exposure_relative_risk.py
```

It uses an unequal-measure spatial grid and verifies:

- exact recovery of exposure amounts;
- measured total exposure;
- event rates and units;
- measured event mass;
- separately normalized case and control densities;
- raw relative risk `[0.5, 1.0, 2.0]`;
- corresponding log relative risk;
- control-weighted mean relative risk equal to one.

All five new top-level symbols are registered in `examples/API_COVERAGE.csv`. The
repository example runner executes every numbered example in an isolated subprocess and
the coverage validator rejects missing or stale mappings.

## 10. Documentation and release surface

Added:

```text
docs/guides/exposure-relative-risk.md
docs/api/risk.md
docs/development/handoff-0.0.15-exposure-relative-risk.md
HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md
```

Updated:

```text
src/pykdex/__init__.py
README.md
docs/index.md
docs/zh/index.md
docs/development/roadmap.md
CHANGELOG.md
mkdocs.yml
examples/API_COVERAGE.csv
tools/smoke_installed_distribution.py
HANDOFF_NEXT_CONVERSATION.md
```

The package reports version `0.0.15`. The installed-wheel smoke test validates both the
version and the new top-level risk field classes.

## 11. Analytical validation coverage

The combined tests validate:

- amount-density round trips on unequal support measures;
- measured exposure totals and fingerprints;
- exact support, unit, provenance, CRS, network, and time-domain contracts;
- constant event-rate references;
- event and exposure scaling laws;
- event-mass and exposure-weighted rate identities;
- all denominator policies;
- rejection of probability density as an intensity numerator;
- reciprocal relative risk after swapping case and control;
- sign-reversed log risk after swapping inputs;
- control-weighted normalization;
- density-normalization tolerance;
- zero-case and zero-control semantics;
- rejection of adaptive, matrix, or unequal bandwidths;
- rejection of support or estimator-contract mismatch;
- unequal-measure spatial grids;
- network lixels and junction metadata;
- cyclic ordinary space-time grids;
- cyclic network-time arixels.

## 12. Release-candidate validation evidence

Release-candidate head `2652c8b81a662e358059eb809cbde645c05ebb8b`
completed CI `#229` (`30357305493`) successfully.

Observed successful validation included:

```text
Black
isort
Ruff
mypy
complete top-level API example mapping
strict MkDocs
branch coverage
complete pytest suite
sdist and wheel build
Twine metadata validation
distribution archive verification
isolated installed-wheel smoke test
Linux / Windows / macOS
Python 3.11 / 3.12 / 3.13 / 3.14
```

The PR audit found 33 intended changed files, no review comments, and no temporary
formatter workflows. Both `.github/workflows/format-event-rate.yml` and
`.github/workflows/format-relative-risk.yml` returned not found on the release branch.

## 13. Pull-request and merge evidence

PR #15 was updated from its development description to the full 0.0.15 release scope.
After CI #229 and the audit, it was marked Ready. GitHub reported it open, non-Draft,
and mergeable on unchanged head `2652c8b81a662e358059eb809cbde645c05ebb8b`.

The PR was squash merged with:

```text
merge commit: dcac85cd1399b9ad18257451601dcc47c4e73f20
merged_at: 2026-07-28T12:09:31Z
```

GitHub subsequently reported the PR closed and merged.

## 14. Deliberate exclusions

Version 0.0.15 does not include:

- adaptive relative risk;
- spatial bandwidth matrices for relative risk;
- independent case and control bandwidth selection;
- relative-risk bandwidth selection;
- case probability or pooled-process case odds;
- automatic density renormalization;
- hidden pseudocounts;
- bootstrap, permutation, or asymptotic inference;
- tolerance or significance contours;
- uncertainty fields;
- separability diagnostics;
- persistence-schema changes;
- PostGIS or Zarr adapters;
- distributed execution.

These require separate statistical or engineering designs.

## 15. Post-merge validation boundary

The repository CI workflow runs on pushes to `main` and `master`, pull requests, and
manual dispatch. This merge-state record changes documentation after the squash merge and
therefore produces a new `main` head.

The available GitHub connector can inspect PR-triggered workflow runs but cannot list
repository push-triggered runs by commit. Consequently:

- CI #229 is fully observed and validates the complete release tree before merge;
- the actual merge and merge commit are fully observed;
- no claim is made here that the later merge-state documentation head passed its push CI;
- the live Actions page must be checked before treating that later documentation commit
  as independently validated.

This limitation affects only observation of the status-record commit. It does not erase
the full release-candidate validation on the exact code, tests, examples, package
metadata, and documentation merged by PR #15.

## 16. Next version boundary

The next roadmap unit is 0.0.16:

```text
uncertainty, separability diagnostics, and scalable execution
```

It requires a new detailed design before implementation. Do not silently extend the
point-estimate semantics fixed in 0.0.15.

## 17. Recovery procedure

1. Inspect the current `main` head and live Actions state before trusting status newer
   than this record.
2. Read the six handoff records listed in section 1.
3. Confirm `src/pykdex/__init__.py` reports `0.0.15` and exports the five risk names.
4. Confirm `examples/17_exposure_relative_risk.py` and its API mappings exist.
5. Confirm temporary formatter workflows are absent.
6. Run the three risk test modules, all examples, and the complete repository matrix.
7. Do not redesign the 0.0.15 numerical contracts while starting 0.0.16.
