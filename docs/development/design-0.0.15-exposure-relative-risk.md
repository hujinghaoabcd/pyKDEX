# pyKDEX 0.0.15 design: exposure-adjusted rates and relative risk

Status: pre-implementation design record  
Branch: `agent/exposure-relative-risk`  
Base: pyKDEX `0.0.14` on `main`

This document fixes the statistical meaning, public boundaries, validation rules,
and implementation order for pyKDEX 0.0.15 before public code is added. It is not
the final versioned handoff. The completed unit must still create
`HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md` and satisfy the normal release and CI
requirements.

## 1. Purpose

The existing estimators produce density or intensity fields on measured spatial,
network, space-time, and network-time supports. Version 0.0.15 adds two distinct
statistical layers:

1. **exposure-adjusted event rates**, where an event intensity is divided by an
   independently supplied exposure density; and
2. **case-control relative risk**, where separately normalized case and control
   probability densities are compared on the same support.

These quantities must not be represented by one ambiguous `risk` operation.
Their denominators, units, normalization, and interpretation are different.

## 2. External references inspected

The following projects and publications are methodological references only.
No source code is copied into pyKDEX.

### 2.1 `tilmandavies/sparr`

Reference revision inspected: `67ad2c995683b5122d4edee16d2eaacbbfb868cb`.

Relevant files:

- `R/risk.R`;
- `R/LSCV.risk.R`;
- `R/tolerance.R`;
- spatial and spatiotemporal risk documentation.

Important lessons:

- spatial relative risk is treated as a ratio of separately estimated case and
  control densities;
- log relative risk is preferred for symmetric interpretation;
- fixed and adaptive estimators are different statistical regimes;
- denominator regularization must be explicit;
- tolerance contours and inferential procedures are separate from the point
  estimate.

### 2.2 `spatstat/spatstat.explore` and `spatstat/spatstat.linnet`

Network reference revision inspected:
`2632475d0dd76915442546eb52be833a98141071`.

Relevant files:

- `spatstat.linnet/R/relrisk.lpp.R`;
- planar `relrisk.ppp` documentation;
- network bandwidth-selection documentation.

Important lessons:

- a multitype point pattern can be represented through smoothed type-specific
  intensities and a pooled intensity;
- case probability, case odds, and a separately normalized density ratio are
  related but are not identical API meanings;
- network relative-risk estimation must preserve network support and path-based
  smoothing semantics;
- leave-one-out evaluation belongs to bandwidth selection, not to the final
  field object.

### 2.3 `JeremyGelb/spNetwork`

Reference revision inspected: `53127c019770784db8d8a1bf0f284bbaa9523ab9`.

Relevant material:

- `vignettes/NKDE.Rmd`;
- `vignettes/TNKDE.Rmd`;
- adaptive-bandwidth documentation.

Important lessons:

- network and temporal-network fields must remain bound to lixel/arixel support;
- actual lixel length and temporal-cell width are part of the integration
  measure;
- risk calculations must not silently fall back to planar cells or discard
  network topology.

### 2.4 Primary statistical references

- Kelsall, J. E. and Diggle, P. J. (1995), *Kernel estimation of relative
  risk*, Bernoulli 1, 3-16.
- Kelsall, J. E. and Diggle, P. J. (1995), *Non-parametric estimation of
  spatial variation in relative risk*, Statistics in Medicine 14, 2335-2342.
- Hazelton, M. L. and Davies, T. M. (2009), *Inference based on kernel estimates
  of the relative risk function in geographical epidemiology*, Biometrical
  Journal 51, 98-109, DOI `10.1002/bimj.200810495`.
- Davies, T. M. and Hazelton, M. L. (2010), *Adaptive kernel estimation of
  spatial relative risk*, Statistics in Medicine 29, 2423-2437, DOI
  `10.1002/sim.3995`.
- Davies, T. M., Marshall, J. C. and Hazelton, M. L. (2018), *Tutorial on kernel
  estimation of continuous spatial and spatiotemporal relative risk*,
  Statistics in Medicine 37, 1191-1221, DOI `10.1002/sim.7577`.

## 3. Licence and implementation boundary

`sparr`, `spatstat`, and `spNetwork` are GPL-licensed research references. pyKDEX
is MIT-licensed. Therefore:

1. their source code is not copied, translated, or mechanically ported;
2. public mathematics and documented behaviour may guide an independent design;
3. one-time numerical reference fixtures may be generated externally and stored
   as static expected values with provenance;
4. pyKDEX runtime code must not import or call those packages;
5. all new numerical behaviour requires analytical or independently generated
   references.

This is consistent with `THIRD_PARTY_NOTICES.md`.

## 4. Statistical definitions

### 4.1 Measured support

Every field in this unit is defined on a measured support with locations or
support elements indexed by `j` and positive integration measures `m_j`.
Examples are:

- grid-cell area for spatial grids;
- lixel length for network support;
- area-times-time for ordinary space-time grids;
- lixel-length-times-time for arixel support.

Support identity is not inferred from shape alone. Compatible objects must agree
on the relevant support fingerprint, stable support identifiers, CRS, spatial
unit, temporal unit and time-domain identity.

### 4.2 Exposure field

The canonical stored value `e_j` is **exposure density with respect to support
measure**. Its unit is:

```text
exposure_unit / support_measure_unit
```

The exposure amount represented by support element `j` is:

```text
E_j = e_j * m_j
```

and total exposure is:

```text
E_total = sum_j e_j * m_j
```

This convention allows population, person-time, vehicle-time, observation-time,
or another at-risk quantity to be compared consistently across supports with
unequal cell, lixel, or arixel measures.

Two constructors are required:

1. `ExposureField.from_density(...)`, accepting canonical exposure densities;
2. `ExposureField.from_amounts(...)`, accepting exposure amounts per support
   element and dividing by the measured support.

The public object must retain:

- canonical non-negative exposure-density values;
- the original representation (`density` or `amount`);
- exposure unit;
- support object or immutable support identity;
- support kind;
- CRS and spatial/temporal units when applicable;
- provenance;
- support fingerprint;
- an exposure-field fingerprint.

Exposure values must be finite and non-negative. A completely zero exposure
field is invalid for rate estimation, although it may be constructed for data
validation and inspection.

### 4.3 Exposure-adjusted event rate

Let `lambda_j` be an event **intensity** with units of event weight per support
measure. The exposure-adjusted rate is

```text
q_j = lambda_j / e_j
```

with units:

```text
event_weight_unit / exposure_unit
```

The numerator must be an intensity field. A probability density that integrates
to one is not accepted as an event-rate numerator because it has discarded total
event mass.

For a measured result, the following totals are retained separately:

```text
event_mass ~= sum_j lambda_j * m_j
exposure_total = sum_j e_j * m_j
```

The integral of `q_j` over geometric support has no universal interpretation and
must not be labelled as total risk. A useful exposure-weighted average rate is

```text
sum_j q_j * e_j * m_j / sum_j e_j * m_j
```

which should recover total event mass divided by total exposure when no cells are
excluded or floored.

### 4.4 Case-control relative risk

For the first implementation, case and control KDEs must both be probability
densities evaluated on exactly the same measured support. Let

```text
f_j = case density
g_j = control density
```

The raw density-ratio relative risk is

```text
r_j = f_j / g_j
```

and log relative risk is

```text
rho_j = log(f_j) - log(g_j)
```

The case and control samples are normalized separately. Sample-size prevalence
or prior odds are not folded into this field. Therefore this object is not named
`case_probability` and is not interpreted as an absolute disease probability.

The first version requires a **shared fixed bandwidth** and matching numerical
contracts:

- same support and measure;
- same kernel family;
- same metric or network junction policy;
- same boundary-correction contract;
- same directed-network setting;
- same spatial and temporal domains;
- scalar, equal bandwidths.

Independent or adaptive bandwidths remain excluded until their statistical
meaning and validation rules are implemented explicitly.

### 4.5 Distinct quantities that must remain distinct

The following must not share one public name:

1. exposure-adjusted event rate `lambda / e`;
2. separately normalized case-control density ratio `f / g`;
3. case probability `lambda_case / (lambda_case + lambda_control)`;
4. case odds `lambda_case / lambda_control` based on type-specific intensities.

Version 0.0.15 implements items 1 and 2. Case probability and pooled-process odds
are deliberate exclusions.

## 5. Denominator policy

No hidden epsilon is allowed. Every division uses one explicit policy:

### `raise`

Reject the calculation when the denominator is zero or below an explicitly
specified validity threshold. This is the default.

### `nan`

Return `NaN` at invalid support elements and expose a read-only validity mask.
Exports must preserve the mask. Summary methods must state how invalid elements
are handled.

### `minimum`

Replace denominators below `minimum_denominator` by that positive value. The
threshold and number of affected elements must be recorded in metadata. This is
an explicit sensitivity choice, not numerical housekeeping.

Positive infinity is not a valid stored field value. A user requesting an
unregularized zero denominator must choose `nan` or receive an error.

## 6. Proposed public objects and functions

The initial public API should be small and compositional:

```python
ExposureField
EventRateField
RelativeRiskField
estimate_event_rate(...)
estimate_relative_risk(...)
```

Recommended construction pattern:

```python
exposure = ExposureField.from_amounts(
    population_by_cell,
    support=grid,
    exposure_unit="persons",
    provenance={"source": "census"},
)

rate = estimate_event_rate(
    event_intensity,
    exposure,
    zero_policy="raise",
)

risk = estimate_relative_risk(
    case_density,
    control_density,
    log=True,
    zero_policy="raise",
)
```

`EventRateField` and `RelativeRiskField` should retain their numerator and
 denominator identities through fingerprints and metadata, but should not retain
 mutable estimator objects.

## 7. Support architecture

Avoid four copied implementations. A private support-adapter layer should
extract a closed contract from existing result/support types:

```text
support_kind
values
support_measure
support_ids
support_fingerprint
crs
spatial_unit
temporal_unit
time_domain_fingerprint
network_fingerprint
```

The adapter must support the existing public result families:

- `SpatialKDEResult`;
- network KDE/heat-network measured fields;
- ordinary spatiotemporal fields;
- `NetworkTimeField`.

Compatibility is checked by explicit identity fields, not by duck-typing only.
Unsupported arbitrary objects fail with `TypeError`.

## 8. Required invariants and reference tests

### 8.1 Exposure

1. `from_amounts` followed by multiplication by support measure recovers the
   original amounts exactly within floating-point tolerance.
2. Total exposure is invariant between amount and density constructors.
3. Negative, infinite, incompatible-unit, and mismatched-support inputs fail.

### 8.2 Event rate

1. Constant intensity `lambda` and constant exposure density `e` produce the
   constant rate `lambda / e`.
2. Exposure-weighted mean rate recovers total event mass divided by total
   exposure when no denominator adjustment occurs.
3. Scaling event weights by `a` scales the rate by `a`.
4. Scaling exposure by `b` divides the rate by `b`.
5. Zero-policy behaviour is tested separately for `raise`, `nan`, and `minimum`.

### 8.3 Relative risk

1. Identical case and control densities produce raw risk 1 and log risk 0.
2. Swapping case and control produces the reciprocal raw risk and negated log
   risk.
3. For positive control density and complete measured support,
   `sum(r * g * measure)` approximates 1 because both densities integrate to 1.
4. Multiplying either input density by a constant is rejected or independently
   normalized by an explicit preprocessing step; it is never silently accepted
   as a valid density.
5. Mismatched support, kernel, metric, correction, direction, time domain, or
   bandwidth fails.
6. Spatial, network, cyclic-time, and arixel fixtures are all required.

## 9. Implementation order

1. Add private support-field adapters and compatibility validation.
2. Add immutable `ExposureField` with density/amount constructors and
   fingerprints.
3. Add the explicit denominator-policy utility.
4. Add `EventRateField` and `estimate_event_rate`.
5. Add `RelativeRiskField` and shared-fixed-bandwidth
   `estimate_relative_risk`.
6. Add analytical spatial tests first.
7. Add network, ordinary space-time, cyclic-time, and network-time tests.
8. Add one executable public example covering exposure rate and density-ratio
   risk.
9. Add API documentation, mathematical guide, changelog, citation and roadmap
   updates.
10. Create the root and documentation handoffs.
11. Run focused tests, full regression, branch coverage, API/example mapping,
    formatting, lint, typing, strict docs, distribution checks, isolated wheel
    install, and the complete GitHub CI matrix.
12. Merge only after a final clean CI run and update the handoff with observed
    identifiers.

## 10. Deliberate exclusions from the foundation

The following are not part of the first 0.0.15 implementation:

- adaptive or independently selected case/control bandwidths;
- asymptotic tolerance contours;
- bootstrap confidence bands or permutation inference;
- shrinkage relative-risk estimators;
- case probabilities or prevalence-calibrated absolute risks;
- separability diagnostics;
- heat-equation network-time relative risk unless existing compatible measured
  fields make it a direct field operation without a new solver;
- PostGIS, Zarr, remote storage, distributed execution, or out-of-core arrays;
- persistence of fitted fields inside the prepared-workspace schema.

These exclusions keep the first unit mathematically testable and prevent the
risk layer from becoming coupled to later uncertainty and scalability work.

## 11. Decision summary

The implementation will proceed with these fixed decisions:

1. exposure rates and case-control relative risk are separate APIs;
2. exposure is stored canonically as density with respect to measured support;
3. event-rate numerators must be intensity fields;
4. relative-risk inputs must be separately normalized density fields;
5. shared fixed bandwidth is required for the first relative-risk estimator;
6. log relative risk is supported as a first-class output;
7. denominator handling is explicit and never hidden behind an undocumented
   epsilon;
8. all four pyKDEX support families are covered through one closed adapter
   contract;
9. GPL projects are research references only;
10. inference, adaptive risk, and scalable storage remain later units.
