# 0.0.15 handoff: exposure-adjusted rates and relative risk

The complete recoverable engineering record is
`HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md` in the repository root.

## Release state

pyKDEX 0.0.15 was released to `main` through PR #15:

```text
release candidate: 2652c8b81a662e358059eb809cbde645c05ebb8b
candidate CI: #229 (30357305493), success
merge method: squash
merge commit: dcac85cd1399b9ad18257451601dcc47c4e73f20
merged_at: 2026-07-28T12:09:31Z
```

The PR was audited before merge: it had no review comments, all 33 changed files belonged
to the intended release, and both temporary formatter workflows were absent.

The repository CI workflow is configured for pushes to `main`, but the available
connector does not enumerate push-triggered workflow runs by commit. The final root
handoff therefore records the fully observed release-candidate CI and merge while leaving
any later merge-state documentation push result unclaimed.

## New public API

```python
from pykdex import (
    EventRateField,
    ExposureField,
    RelativeRiskField,
    estimate_event_rate,
    estimate_relative_risk,
)
```

## Exposure-adjusted event rates

`ExposureField` stores exposure density with respect to measured support and can be
constructed from density or per-element amounts.

```text
event_rate_j = event_intensity_j / exposure_density_j
rate_unit = event_unit / exposure_unit
```

Probability density is rejected as the numerator because it has discarded total event
mass. `EventRateField` retains units, event mass, exposure totals, original and effective
denominators, masks, fingerprints, and weighted summaries.

## Case-control relative risk

Relative risk compares separately normalized case and control probability densities:

```text
relative_risk_j = case_density_j / control_density_j
log_relative_risk_j = log(case_density_j) - log(control_density_j)
```

Version 0.0.15 requires exact measured-support identity and shared positive scalar fixed
bandwidths. Kernel, metric or junction policy, boundary correction, direction, network,
CRS, units, and temporal-domain contracts must match. Event fingerprints, sample sizes,
weights, and provenance may differ.

## Denominator semantics

No hidden epsilon or pseudocount is introduced. Invalid denominators require one explicit
policy:

- `raise`;
- `nan`;
- `minimum` with an explicit positive floor.

Zero case density produces raw risk `0` and log risk `-inf` when control is valid.
Positive-infinite fields are never stored.

## Measured domains

The implementation supports:

- spatial grids measured by actual cell area;
- network lixels measured by actual length;
- ordinary space-time grids measured by area × time;
- network-time arixels measured by lixel length × time.

Compatibility uses fingerprints, identifiers, actual measures, CRS, units, network, and
time-domain identity rather than array shape.

## Example and documentation

The executable example is:

```text
examples/17_exposure_relative_risk.py
```

User documentation is in:

```text
docs/guides/exposure-relative-risk.md
docs/api/risk.md
```

All five new top-level symbols are registered in `examples/API_COVERAGE.csv`.

## Validation

CI #229 passed:

- Black, isort, Ruff, and mypy;
- complete public API example mapping;
- strict MkDocs;
- branch coverage and complete tests;
- sdist, wheel, Twine, archive verification, and installed-wheel smoke;
- Linux, Windows, and macOS on Python 3.11-3.14.

## Next boundary

Adaptive or independent case/control bandwidths, inference, uncertainty, tolerance
contours, separability diagnostics, scalable execution, and storage adapters remain
outside 0.0.15.

The next roadmap unit is 0.0.16: uncertainty, separability diagnostics, and scalable
execution. It requires a new detailed design before implementation.
