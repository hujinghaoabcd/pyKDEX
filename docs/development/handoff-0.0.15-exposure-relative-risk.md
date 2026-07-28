# 0.0.15 handoff: exposure-adjusted rates and relative risk

The complete recoverable engineering record is
`HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md` in the repository root. This page summarizes
the final public release surface.

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

`ExposureField` stores exposure density with respect to measured support. It can be
constructed from density or per-element amounts. Event rates divide a measured intensity
result by exposure density:

```text
event_rate_j = event_intensity_j / exposure_density_j
```

Probability density is rejected as the numerator because it has discarded total event
mass. Units, event mass, exposure totals, original and effective denominators, and masks
are retained in `EventRateField`.

## Case-control relative risk

Relative risk compares separately normalized case and control probability densities:

```text
relative_risk_j = case_density_j / control_density_j
log_relative_risk_j = log(case_density_j) - log(control_density_j)
```

Version 0.0.15 requires exact measured-support identity and shared positive scalar fixed
bandwidths. Kernel, metric or junction policy, boundary correction, direction, network,
CRS, units, and temporal-domain contracts must match. Event fingerprints and sample
provenance may differ.

## Denominator semantics

No hidden epsilon or pseudocount is introduced. Invalid denominators require one explicit
policy:

- `raise`;
- `nan`;
- `minimum` with an explicit positive floor.

Zero case density produces raw risk `0` and log risk `-inf` when the control denominator
is valid. Positive-infinite fields are never stored.

## Measured domains

The implementation supports:

- spatial grids measured by actual cell area;
- network lixels measured by actual length;
- ordinary space-time grids measured by area × time;
- network-time arixels measured by lixel length × time.

Compatibility is based on fingerprints, identifiers, measures, CRS, units, network, and
time-domain identity rather than array shape.

## Example and documentation

The executable public example is:

```text
examples/17_exposure_relative_risk.py
```

User documentation is in:

```text
docs/guides/exposure-relative-risk.md
docs/api/risk.md
```

All five new top-level symbols are registered in `examples/API_COVERAGE.csv`.

## Validation boundary

The release must pass quality, typing, strict documentation, branch coverage, all
examples, complete tests, distributions, isolated-wheel smoke testing, and the
Linux/Windows/macOS Python 3.11-3.14 matrix.

Adaptive or independent case/control bandwidths, inference, uncertainty, tolerance
contours, separability diagnostics, scalable execution, and storage adapters remain
outside 0.0.15.

## Release status

At creation of this page, the branch reports version `0.0.15`, while PR #15 remains
Draft and unmerged. The root handoff must be updated with the actual final candidate CI,
merge commit, and post-merge `main` CI before the release is declared stable.
