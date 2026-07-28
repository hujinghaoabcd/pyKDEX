# pyKDEX 0.0.15 final handoff: exposure-adjusted rates and relative risk

This is the durable release handoff for pyKDEX 0.0.15. It consolidates the three
validated development subunits into the final public API and records the release-candidate
state, statistical contracts, implementation boundaries, examples, documentation,
validation requirements, PR workflow, and recovery procedure.

The file must be updated after the final release-candidate CI, PR readiness transition,
merge, and post-merge `main` CI. Until those events are observed and recorded, this
handoff describes a release candidate rather than a completed merge.

## 1. Repository and release-candidate state

- Project: `hujinghaoabcd/pyKDEX`
- Release version in the branch: `0.0.15`
- Previous stable merged version: `0.0.14`
- Branch: `agent/exposure-relative-risk`
- Pull request: `#15 Add exposure-adjusted rate and relative-risk foundations`
- PR state at handoff creation: open, Draft, mergeable, not merged
- Base `main`: `1315619afba79a6ddf1fbfd7b91900bf0c0992f1`
- Last fully observed pre-release implementation/status CI:
  `#214` (`30355794150`), success on head
  `1aba2852db070d47aada69946d946d32489621f1`
- Final release-candidate CI after version, API, example, and documentation changes:
  pending observation
- Merge commit: not yet created
- Post-merge `main` CI: not yet observed

Read these records in order when recovering the project:

1. `docs/development/design-0.0.15-exposure-relative-risk.md`;
2. `HANDOFF_0.0.15_PROGRESS_01_EXPOSURE_FIELD.md`;
3. `HANDOFF_0.0.15_PROGRESS_02_EVENT_RATE.md`;
4. `HANDOFF_0.0.15_PROGRESS_03_RELATIVE_RISK.md`;
5. this final handoff;
6. `HANDOFF_NEXT_CONVERSATION.md`.

## 2. Release purpose

Version 0.0.15 adds two deliberately distinct statistical layers on measured pyKDEX
supports:

1. exposure-adjusted event rates; and
2. separately normalized case-control density-ratio relative risk.

They share measured-support and denominator-policy infrastructure but are not represented
by one ambiguous `risk` operation.

## 3. Final top-level public API

The new stable top-level exports are:

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

The risk subpackage additionally exposes `DenominatorPolicy` and measured-support helper
contracts for advanced validation. Those helper names are not added to the top-level
package API.

## 4. Measured-support contract

Every exposure, rate, and relative-risk field is bound to an explicit measured support.
Supported measured domains are:

- `GridSupport`, measured by actual cell area;
- `LixelSupport`, measured by actual lixel length;
- `SpatiotemporalGridSupport` and measured space-time support, measured by spatial
  measure multiplied by time-bin width;
- `ArixelSupport`, measured by lixel length multiplied by time-bin width.

Compatibility is not inferred from shape. Required identity includes the applicable:

```text
support fingerprint
stable support identifiers
support measure
CRS
spatial unit
temporal unit
time-domain fingerprint
network fingerprint
```

Boundary remainder cells, unequal lixels, and unequal final time bins retain their actual
measure.

## 5. ExposureField

`ExposureField` is an immutable, fingerprinted exposure-density field. Its canonical
stored values are exposure density with respect to support measure.

For element `j` with measure `m_j`, density `e_j`, and amount `E_j`:

```text
E_j = e_j * m_j
E_total = sum_j e_j * m_j
```

Public constructors are:

```python
ExposureField.from_density(...)
ExposureField.from_amounts(...)
```

The object retains:

- canonical read-only exposure densities;
- recoverable per-element exposure amounts;
- original representation (`density` or `amount`);
- exposure unit;
- exact measured support and descriptor;
- provenance and immutable metadata;
- total exposure;
- deterministic fingerprint;
- DataFrame, grid, and GeoDataFrame exports where supported.

Negative or non-finite exposure values are rejected. A completely zero field may be
constructed for data inspection but is invalid for default rate estimation.

## 6. Explicit denominator policy

No hidden epsilon, pseudocount, or implicit denominator regularization is allowed.

The immutable denominator policy supports:

- `raise`: reject denominators at or below the validity threshold;
- `nan`: return `NaN` exactly at invalid cells and preserve the invalid mask;
- `minimum`: replace invalid denominators with an explicit positive floor and preserve
  both invalid and adjusted masks.

Positive-infinite rate or relative-risk values are not stored. A user must choose an
explicit policy for zero denominators.

## 7. Exposure-adjusted event rates

The event-rate numerator must be an intensity result. Probability density is rejected
because it has discarded total event mass.

For event intensity `lambda_j` and exposure density `e_j`:

```text
q_j = lambda_j / e_j
```

The rate unit is:

```text
event_unit / exposure_unit
```

The closed intensity adapter accepts exactly:

```text
SpatialKDEResult
NetworkField
SpatiotemporalKDEResult
NetworkTimeField
```

and requires `target="intensity"`.

`EventRateField` retains:

- rate values;
- original event intensity;
- original `ExposureField`;
- effective exposure after explicit policy handling;
- invalid and adjusted masks;
- event and rate units;
- event mass and exposure totals;
- original and effective exposure-weighted mean rates;
- source-result fingerprint and metadata;
- deterministic result fingerprint;
- tabular, grid, and geospatial exports.

When no cells are excluded or floored:

```text
exposure-weighted mean rate = total event mass / total exposure
```

The geometric integral of a rate field has no universal statistical interpretation and
is not labelled total risk.

## 8. Case-control relative risk

The case and control inputs must be separately normalized probability-density results on
exactly the same measured support.

For case density `f_j` and control density `g_j`:

```text
r_j = f_j / g_j
rho_j = log(f_j) - log(g_j)
```

Both inputs must independently satisfy:

```text
sum_j density_j * measure_j approximately equals 1
```

within an explicit positive `normalization_tolerance`, default `1e-6`. No automatic
renormalization of truncated or arbitrary fields is performed.

The closed density adapter accepts exactly the same four result families and requires
`target="density"`.

### 8.1 Shared fixed-bandwidth restriction

The first public implementation requires:

- positive scalar fixed bandwidths;
- exact equality of case and control bandwidth tuples;
- matching kernel families;
- matching metric or network junction policy;
- matching boundary-correction contract;
- matching directed-network setting;
- matching network and time domains;
- exact measured-support identity.

Adaptive arrays, bandwidth matrices, and independently selected case/control bandwidths
are rejected.

Event fingerprints, sample sizes, weights, and sample provenance may differ. They are
retained separately and intentionally excluded from shared estimator-contract equality.

### 8.2 RelativeRiskField

The immutable field retains:

- raw relative risk;
- log relative risk;
- original case and control density;
- effective control density;
- invalid and adjusted control masks;
- result family and shared bandwidth tuple;
- shared estimator contract;
- separate case and control source fingerprints and metadata;
- case and control measured integrals;
- original and effective control-weighted means;
- deterministic fingerprint;
- DataFrame, grid, log-grid, and GeoDataFrame exports.

When the original control density is strictly positive:

```text
sum_j r_j * g_j * m_j = 1
```

A zero case density with valid control gives raw risk `0` and exact log risk `-inf`.
A zero control density follows the explicit denominator policy and never yields stored
positive infinity.

## 9. Deliberate exclusions

Version 0.0.15 does not implement:

- adaptive relative risk;
- spatial bandwidth matrices for relative risk;
- independent case and control bandwidth selection;
- relative-risk bandwidth selection;
- case probability;
- pooled-process case odds;
- automatic density renormalization;
- hidden pseudocounts;
- bootstrap, permutation, or asymptotic inference;
- tolerance or significance contours;
- uncertainty fields;
- separability diagnostics;
- persistence-schema changes;
- PostGIS or Zarr adapters;
- distributed execution.

These are separate statistical or engineering units and must not be folded into this
release without new design and analytical evidence.

## 10. Executable example and API coverage

The complete public example is:

```text
examples/17_exposure_relative_risk.py
```

It uses an unequal-measure spatial grid and verifies:

- exact recovery of exposure amounts;
- measured total exposure;
- exposure-adjusted event rates and units;
- measured event mass;
- separately normalized case/control densities;
- raw relative risk `[0.5, 1.0, 2.0]`;
- corresponding log relative risk;
- control-weighted mean relative risk equal to one.

All five new top-level symbols are registered in:

```text
examples/API_COVERAGE.csv
```

The repository example runner executes every numbered example in an isolated subprocess,
and the API coverage validator rejects missing or stale top-level mappings.

## 11. User and API documentation

Added:

```text
docs/guides/exposure-relative-risk.md
docs/api/risk.md
docs/development/handoff-0.0.15-exposure-relative-risk.md
```

Updated:

```text
README.md
docs/index.md
docs/zh/index.md
docs/development/roadmap.md
CHANGELOG.md
mkdocs.yml
```

The guide distinguishes event rate from density-ratio relative risk, documents measured
support, denominator policies, shared fixed-bandwidth restrictions, and deliberate
exclusions. The API page documents the five public objects/functions plus the explicit
denominator policy.

## 12. Source files added in 0.0.15

Core risk implementation:

```text
src/pykdex/risk/__init__.py
src/pykdex/risk/support.py
src/pykdex/risk/exposure.py
src/pykdex/risk/policies.py
src/pykdex/risk/intensity.py
src/pykdex/risk/rate.py
src/pykdex/risk/density.py
src/pykdex/risk/relative_risk.py
```

Tests:

```text
tests/test_exposure_field.py
tests/test_event_rate.py
tests/test_relative_risk.py
```

Release-surface changes:

```text
src/pykdex/__init__.py
examples/17_exposure_relative_risk.py
examples/API_COVERAGE.csv
tools/smoke_installed_distribution.py
```

## 13. Analytical validation coverage

The combined tests validate:

- amount-density round trips on unequal support measures;
- exposure total invariance;
- support identity, unit, provenance, and fingerprint contracts;
- constant event-rate fields;
- event and exposure scaling laws;
- event-mass and exposure-weighted rate identities;
- all denominator policies;
- rejection of density as an intensity numerator;
- reciprocal relative risk after swapping case/control;
- sign-reversed log risk after swapping inputs;
- control-weighted normalization;
- density-normalization tolerance;
- zero-case and zero-control semantics;
- rejection of adaptive/matrix/unequal bandwidths;
- rejection of support and estimator-contract mismatch;
- spatial unequal-measure grids;
- network lixels and junction metadata;
- cyclic ordinary space-time grids;
- cyclic network-time arixels.

## 14. Required release validation

The final release-candidate head must pass:

```text
Black
isort
Ruff
mypy
public API example mapping
strict MkDocs
branch coverage >= repository threshold
complete pytest suite
sdist and wheel build
Twine metadata validation
distribution archive verification
isolated installed-wheel smoke test
Linux / Windows / macOS
Python 3.11 / 3.12 / 3.13 / 3.14
```

Only GitHub Actions results actually observed for the relevant head may be recorded.
A previous successful CI does not validate later release-surface commits.

## 15. PR completion and merge procedure

After the final release-candidate CI succeeds:

1. inspect PR #15 metadata and changed files;
2. verify temporary formatter workflows are absent;
3. inspect review comments and unresolved threads;
4. update the PR title/body to describe the complete 0.0.15 release;
5. mark the PR ready for review;
6. confirm mergeability and required checks;
7. merge using the repository's established method;
8. observe the actual merge commit on `main`;
9. observe post-merge `main` CI;
10. update this handoff and `HANDOFF_NEXT_CONVERSATION.md` with real merge and CI
    evidence before declaring 0.0.15 stable.

Do not claim merge or post-merge success before those events are visible.

## 16. Next planned version

After 0.0.15 is merged and stable, the roadmap continues with 0.0.16:

```text
uncertainty, separability diagnostics, and scalable execution
```

That unit requires a new detailed design before implementation. It should not silently
extend the point-estimate semantics fixed in 0.0.15.

## 17. Recovery procedure

1. Inspect PR #15 and the current `main` branch before trusting recorded status.
2. Read the six records listed in section 1.
3. Confirm `src/pykdex/__init__.py` reports `0.0.15` and exports exactly the five new
   top-level risk names.
4. Confirm `examples/17_exposure_relative_risk.py` and its five API mappings exist.
5. Confirm `.github/workflows/format-event-rate.yml` and
   `.github/workflows/format-relative-risk.yml` are absent.
6. Run the three risk test modules and all numbered examples.
7. Run the complete repository validation matrix.
8. If the PR is still Draft, continue the release procedure from section 15.
9. If merged, inspect the real merge commit and post-merge CI before updating stable
   status.
