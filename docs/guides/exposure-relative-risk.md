# Exposure-adjusted rates and relative risk

pyKDEX 0.0.15 adds two statistically distinct operations on measured supports:

1. exposure-adjusted event rates; and
2. case-control density-ratio relative risk.

They share support-validation infrastructure but they do not share the same numerator,
denominator, units, or interpretation.

## Measured support

Every operation in this guide uses a support with an explicit integration measure:

- grid-cell area for spatial grids;
- lixel length for network support;
- area multiplied by time for ordinary space-time grids;
- lixel length multiplied by time for arixel support.

Compatibility is checked through support fingerprints, stable identifiers, CRS, units,
time-domain identity, and network identity where applicable. Matching array shapes are
not sufficient.

## Exposure fields

`ExposureField` stores exposure density with respect to support measure. For support
element `j` with measure `m_j`, exposure density `e_j`, and represented amount `E_j`,

```text
E_j = e_j * m_j
```

Use `from_density` when values are already expressed per unit support measure:

```python
from pykdex import ExposureField

exposure = ExposureField.from_density(
    population_density,
    grid,
    exposure_unit="persons",
)
```

Use `from_amounts` when values represent the total exposure assigned to each element:

```python
exposure = ExposureField.from_amounts(
    population_by_cell,
    grid,
    exposure_unit="persons",
)
```

The object retains both canonical densities and recoverable per-element amounts. Its
`total_exposure` property uses the actual support measure.

## Exposure-adjusted event rate

Let `lambda_j` be event intensity per unit support measure and `e_j` be exposure density.
The event rate is

```text
q_j = lambda_j / e_j
```

Its unit is the event-weight unit divided by the exposure unit. A probability density is
not accepted as the numerator because it has discarded total event mass.

```python
from pykdex import estimate_event_rate

rate = estimate_event_rate(
    event_intensity_result,
    exposure,
    event_unit="events",
)

print(rate.rate_unit)
print(rate.event_mass)
print(rate.total_exposure)
print(rate.exposure_weighted_mean_rate)
```

The integral of the rate over geometric support is not labelled as total risk. When no
cells are excluded or floored, the exposure-weighted mean rate recovers total event mass
divided by total exposure.

## Case-control relative risk

Case-control relative risk compares separately normalized probability densities on the
same measured support:

```text
r_j = f_case,j / f_control,j
rho_j = log(f_case,j) - log(f_control,j)
```

The first implementation requires the same positive scalar fixed bandwidths and matching
estimator contracts. Sample sizes, event fingerprints, weights, and sample provenance
may differ.

```python
from pykdex import estimate_relative_risk

risk = estimate_relative_risk(
    case_density_result,
    control_density_result,
    support=grid,  # required for SpatialKDEResult
)

print(risk.values)
print(risk.log_values)
print(risk.control_weighted_mean)
```

Spatial results require an explicit `GridSupport` because `SpatialKDEResult` does not
retain the complete grid object. Network, ordinary space-time, and network-time result
objects retain their measured supports and can infer them.

Both densities must independently integrate to approximately one. The default absolute
normalization tolerance is `1e-6`; pyKDEX validates the result and does not silently
renormalize a truncated or arbitrary field.

## Denominator policies

No hidden epsilon or pseudocount is added. Both rate and relative-risk calculations use
an explicit policy:

- `raise` rejects zero or threshold-invalid denominators and is the default;
- `nan` returns `NaN` at invalid elements and preserves the invalid mask;
- `minimum` floors invalid denominators at an explicitly supplied positive value and
  preserves both invalid and adjusted masks.

```python
risk = estimate_relative_risk(
    case_density_result,
    control_density_result,
    support=grid,
    zero_policy="minimum",
    minimum_denominator=1e-8,
)
```

A zero case density with a valid control density produces raw risk `0` and exact log risk
`-inf`. A zero control density never produces stored positive infinity.

## Shared fixed-bandwidth boundary

Version 0.0.15 deliberately excludes:

- adaptive relative risk;
- spatial bandwidth matrices;
- independently selected case and control bandwidths;
- case probability or pooled-process odds;
- bootstrap, permutation, or asymptotic inference;
- tolerance contours.

These are separate statistical regimes and require independent validation before they
can be added safely.

## Complete executable example

Run:

```bash
python examples/17_exposure_relative_risk.py
```

The example uses an unequal-measure grid, recovers exposure amounts, computes event
rates, and verifies raw and log case-control relative risk.
