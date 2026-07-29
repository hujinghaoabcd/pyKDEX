# Design: pyKDEX 0.0.16 independent relative-risk Bootstrap

## 1. Status and design boundary

This document defines subunit **02H**. It is a design-only unit. No numerical
relative-risk Bootstrap API should be added until this document, its recovery
handoff, strict documentation build, and full repository CI have passed.

The proposed operation consumes two already completed ordinary KDE Bootstrap
results:

```text
case density BootstrapResult
control density BootstrapResult
```

and derives linked empirical uncertainty for:

```text
relative_risk = case_density / control_density
log_relative_risk = log(case_density) - log(control_density)
```

The operation estimates sampling variability from **independent within-group
ordinary resampling**. It is not:

- a pooled case-control mark permutation;
- a Monte Carlo null test of homogeneous risk;
- an asymptotic tolerance-contour calculation;
- a simultaneous confidence-band procedure;
- a bandwidth-selection procedure;
- a model for uncertain exposure.

## 2. Methodological basis

The design follows these methodological distinctions.

1. Efron's ordinary Bootstrap treats each observed sample as its own empirical
   distribution and resamples observations with replacement. For two independent
   samples, the natural product Bootstrap resamples each sample independently.
2. Kernel relative risk is a density-ratio object. The case and control density
   estimators must use compatible smoothing and support contracts so that
   differences are not artifacts of unrelated smoothing choices.
3. The established spatial relative-risk literature distinguishes estimation of
   a density-ratio surface from significance procedures such as asymptotic or
   Monte Carlo tolerance contours.
4. pyKDEX 0.0.16 already implements empirical pointwise ordinary-Bootstrap
   ensembles for measured KDE fields. The new operation therefore transforms
   completed density ensembles rather than refitting estimators or inventing a
   second resampling engine.

Primary methodological references:

- Efron, B. (1979). *Bootstrap Methods: Another Look at the Jackknife*.
  The Annals of Statistics 7(1), 1-26. DOI: 10.1214/aos/1176344552.
- Kelsall, J. E. and Diggle, P. J. (1995). *Kernel estimation of relative
  risk*. Bernoulli 1, 3-16.
- Kelsall, J. E. and Diggle, P. J. (1995). *Non-parametric estimation of
  spatial variation in relative risk*. Statistics in Medicine 14, 2335-2342.
  DOI: 10.1002/sim.4780142106.
- Hazelton, M. L. and Davies, T. M. (2009). *Inference based on kernel estimates
  of the relative risk function in geographical epidemiology*. Biometrical
  Journal 51, 98-109. DOI: 10.1002/bimj.200810495.
- Davies, T. M. and Hazelton, M. L. (2010). *Adaptive kernel estimation of
  spatial relative risk*. Statistics in Medicine 29, 2423-2437.
  DOI: 10.1002/sim.3995.
- Davies, T. M., Marshall, J. C., and Hazelton, M. L. (2018). *Tutorial on
  kernel estimation of continuous spatial and spatiotemporal relative risk*.
  Statistics in Medicine 37, 1191-1221. DOI: 10.1002/sim.7577.
- Kern, J. W. et al. (2003). *Using the bootstrap and fast Fourier transform to
  estimate confidence intervals of 2D kernel densities*. Environmental and
  Ecological Statistics 10, 405-420. DOI: 10.1023/A:1026092103819.

The literature supports the density-ratio interpretation, the importance of
smoothing compatibility, and the separation between surface uncertainty and
formal null testing. The exact linked-ensemble API below is a pyKDEX engineering
contract, not a claim that pointwise percentile intervals replace established
relative-risk significance procedures.

## 3. Source objects

### 3.1 Required source type

Both inputs must be immutable `BootstrapResult` objects with:

```text
operation == "bootstrap_kde"
ensemble.field_family == "density"
resampling_method == "ordinary"
```

The sources may come from completed pyKDEX density Bootstrap adapters for:

```text
SpatialKDE on GridSupport
NetworkKDE on LixelSupport
HeatNetworkKDE on LixelSupport
SpatiotemporalKDE on SpatiotemporalGridSupport
TemporalNetworkKDE on ArixelSupport
```

A generic measured `SpatiotemporalPointSupport` density ensemble may be accepted
if it already satisfies every contract, although no current built-in ordinary
Bootstrap estimator adapter produces that family.

### 3.2 Complete density validity

Deterministic `estimate_relative_risk` requires finite non-negative probability
densities over the complete measured support. The Bootstrap operation must retain
that boundary.

Therefore the first release requires:

```text
case.ensemble.valid_mask is all True
control.ensemble.valid_mask is all True
```

Partially masked density ensembles are rejected rather than renormalized over a
reduced support. Silent support-dependent renormalization would change the
statistical object.

### 3.3 Exact support identity

Case and control must share the exact `SupportDescriptor` contract:

- support kind;
- support fingerprint;
- stable IDs;
- measured integration weights;
- shape;
- CRS and spatial unit;
- temporal unit and time-domain fingerprint where present.

Matching array shape alone is insufficient.

### 3.4 Distinct group identity

The operation must reject accidental reuse of one source as both case and
control.

Required evidence:

- different completed source-result fingerprints;
- different source ensemble fingerprints;
- different source-event fingerprints where present;
- different seed-ledger fingerprints.

The source-event fingerprint requirement is deliberately strict. Two groups with
identical coordinates must carry distinct event provenance if they are genuinely
separate samples.

## 4. Independent Bootstrap and replicate pairing

### 4.1 Within-group resampling

Case and control source ensembles must already have been generated independently
within each group. The relative-risk operation performs no new resampling.

It must not:

- pool case and control observations;
- resample labels;
- shuffle case/control marks;
- copy one group's sampled indices to the other group;
- generate a new shared random stream.

### 4.2 Equal replicate counts

The first implementation requires:

```text
B_case == B_control
```

Unequal counts are rejected.

Reasons:

- truncating to `min(B_case, B_control)` silently discards valid draws;
- recycling rows creates unequal replicate weights;
- random rematching introduces an additional unrecorded RNG;
- the full Cartesian product has `B_case * B_control` fields, changes the
  empirical distribution, and can multiply memory by orders of magnitude.

### 4.3 Pairing rule

Replicate rows are paired deterministically by logical index:

```text
pair b = (case replicate b, control replicate b)
```

This gives `B` draws from the product empirical Bootstrap distribution when the
two source ensembles were independently generated.

Pairing metadata must record:

```text
pairing_rule = "same_logical_replicate_index"
case_replicate_source_fingerprint[b]
control_replicate_source_fingerprint[b]
```

No row permutation is performed.

### 4.4 Seed-ledger independence

Case and control seed-ledger fingerprints must differ. Equal fingerprints are
rejected as evidence that the same logical streams were reused.

The derived operation creates no random numbers. It constructs a combined seed
identity only for provenance:

```text
combined_seed_fingerprint = fingerprint(
    case_seed_ledger_fingerprint,
    control_seed_ledger_fingerprint,
    pairing_rule,
)
```

The combined identity does not imply a third random generator.

## 5. Shared estimator contract

### 5.1 Result family

Case and control must have the same estimator family:

```text
spatial
network
heat_network
spatiotemporal
network_time
```

Cross-family ratios are rejected even on numerically matching support arrays.

### 5.2 Existing contract fingerprint

Both source ensembles and results must expose a non-empty
`estimator_contract_fingerprint`. The fingerprints must match exactly.

Current Bootstrap contract fingerprints include fixed estimator choices and the
support identity. Event-specific data are excluded.

### 5.3 Auditable normalized contract metadata

Fingerprint equality is necessary but not sufficient for useful diagnostics.
Before numerical implementation, every completed density Bootstrap adapter
should expose a normalized serializable contract mapping in result and ensemble
metadata, for example:

```text
relative_risk_contract = {
    result_family,
    support_fingerprint,
    bandwidths,
    kernel names,
    metric or junction policy,
    directedness,
    boundary correction/fingerprint,
    heat diffusion-time/mesh/solver route where applicable,
    cyclic-tail tolerance where applicable,
}
```

The mapping must exclude:

- source event fingerprints;
- sample size;
- seed information;
- execution chunks/workers;
- observed or replicate values.

Implementation must compare both the normalized mapping and its fingerprint.
This provides precise errors such as `temporal_bandwidth differs` instead of only
`contract fingerprint differs`.

### 5.4 Shared bandwidth restriction

The first release supports only equal fixed scalar bandwidths or equal fixed heat
parameters already accepted by deterministic relative risk.

Excluded:

- adaptive bandwidth arrays;
- bandwidth matrices;
- independently selected case/control bandwidths;
- replicate-wise bandwidth reselection;
- balloon estimators;
- unequal spatial or temporal bandwidths.

## 6. Density normalization

### 6.1 Observed and replicate checks

For support measure vector `m`, every observed and replicate density must satisfy:

```text
abs(sum_j density[j] * m[j] - 1) <= normalization_tolerance
```

Checks are required for:

- observed case density;
- every case replicate;
- observed control density;
- every control replicate.

The tolerance must be an explicit finite positive scalar. The initial default
should remain consistent with deterministic relative risk:

```text
normalization_tolerance = 1e-6
```

### 6.2 No automatic renormalization

The operation must not silently divide each row by its measured integral.
Automatic renormalization could conceal insufficient support coverage or a
mismatched estimator contract.

A normalization failure reports:

- group;
- observed or replicate index;
- measured integral;
- requested tolerance.

## 7. Denominator policy and validity

### 7.1 Control density is the denominator

The existing explicit `DenominatorPolicy` applies to observed and replicate
control densities. No epsilon or pseudocount is introduced.

### 7.2 `raise` mode

`raise` rejects the operation if any observed or replicate control value is at or
below `validity_threshold`.

The error should report:

- observed invalid count;
- total replicate invalid count;
- number of affected support columns;
- first affected replicate and support ID.

Failure occurs before complete raw-risk and log-risk output allocation.

### 7.3 `minimum` mode

`minimum` applies the explicit positive `minimum_denominator` independently to
observed and replicate control fields.

All output cells remain valid. The result retains:

- observed invalid-control mask;
- observed adjusted-control mask;
- replicate invalid-control mask `(B, M)`;
- replicate adjusted-control mask `(B, M)`.

### 7.4 `nan` mode and the 1D ensemble mask

Current `FieldEnsemble.valid_mask` is one-dimensional. It cannot represent a cell
that is valid in some replicates and invalid in others.

The first implementation therefore uses a conservative support-column rule:

```text
column valid only if observed control and every control replicate
are above the validity threshold
```

If any paired control field invalidates a support element:

- the entire raw-risk column is set to NaN;
- the entire log-risk column is set to NaN;
- the shared 1D output validity mask marks the column false.

The dedicated linked result still stores the complete observed and `(B, M)`
control invalid masks so users can distinguish one-replicate failure from
systematic denominator failure.

This rule avoids:

- varying effective replicate counts by support element;
- hidden omission of invalid replicate ratios;
- a major 2D-validity redesign of `FieldEnsemble` during 0.0.16.

Future work may add replicate-specific validity, but 02H must not silently emulate
it.

## 8. Raw and log relative risk

### 8.1 Raw field

For valid cells:

```text
R[b, j] = case[b, j] / effective_control[b, j]
```

Raw relative risk must be finite and non-negative. Overflow raises
`FloatingPointError`.

### 8.2 Log field

For valid cells with positive case density:

```text
L[b, j] = log(case[b, j]) - log(effective_control[b, j])
```

For valid cells with zero case density:

```text
R[b, j] = 0
L[b, j] = -inf
```

Zero case density is not denominator invalidity.

Positive infinity is never permitted. NaN is allowed only in support columns
invalidated by `nan` control-denominator policy.

### 8.3 Pointwise log summaries

`FieldEnsemble(field_family="log_relative_risk")` already permits valid `-inf`
values. `pointwise_percentile_interval` uses discrete empirical quantiles for
non-finite log columns.

When a valid log-risk column contains `-inf` in any replicate:

- percentile bounds may be finite or `-inf` according to empirical order;
- standard error is NaN;
- bias is NaN.

This is explicit and preferable to replacing zero case density with a
pseudocount.

## 9. Proposed public result structure

### 9.1 Function

Provisional API:

```python
bootstrap_relative_risk(
    case_bootstrap: BootstrapResult,
    control_bootstrap: BootstrapResult,
    *,
    zero_policy: DenominatorPolicyInput = "raise",
    validity_threshold: float = 0.0,
    minimum_denominator: float | None = None,
    normalization_tolerance: float = 1e-6,
    memory_budget_bytes: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> RelativeRiskBootstrapResult
```

This API is not public until implementation and validation are complete.

### 9.2 Dedicated linked container

Return a dedicated immutable `RelativeRiskBootstrapResult` containing:

```text
relative_risk: BootstrapResult
log_relative_risk: BootstrapResult
policy: DenominatorPolicy
normalization_tolerance: float
pairing_rule: str
case_source_fingerprint: str
control_source_fingerprint: str
case_seed_ledger_fingerprint: str
control_seed_ledger_fingerprint: str
combined_seed_ledger_fingerprint: str
observed_control_invalid_mask: (M,)
observed_control_adjusted_mask: (M,)
replicate_control_invalid_mask: (B, M)
replicate_control_adjusted_mask: (B, M)
metadata
```

The container validates that raw and log results share:

- support;
- replicate count;
- paired source fingerprints;
- confidence level;
- combined seed identity;
- validity mask;
- estimator family;
- source case/control identities.

Returning a plain tuple is rejected because linkage and masks would be
unvalidated.

### 9.3 Linked BootstrapResult objects

Both nested results use:

```text
operation = "bootstrap_relative_risk"
```

One has `field_family="relative_risk"`; the other has
`field_family="log_relative_risk"`.

Because the operation generates no new randomness, create a derived summary
`BootstrapPlan` with:

- equal source replicate count;
- equal source confidence level;
- `random_state=None`;
- no derived execution plan.

Metadata must state:

```text
derived_plan = true
no_new_randomness = true
case_plan_fingerprint
control_plan_fingerprint
```

Combined seed metadata embeds both complete source seed metadata records and the
pairing rule.

## 10. Fingerprints and provenance

### 10.1 Observed identities

Raw observed-field fingerprint includes:

- observed case density fingerprint;
- observed control density fingerprint;
- exact support;
- shared estimator contract;
- denominator policy;
- normalization tolerance;
- `field_family="relative_risk"`.

Log observed-field identity adds `field_family="log_relative_risk"` and links to
the raw observed identity.

### 10.2 Replicate identities

Paired replicate `b` fingerprint includes:

- case replicate source fingerprint `b`;
- control replicate source fingerprint `b`;
- pairing rule;
- shared contract;
- denominator policy;
- output field family.

### 10.3 Operational exclusions

Statistical fingerprints exclude:

- memory budget;
- worker count;
- source execution chunks;
- derived transform chunk size;
- completion order.

## 11. Memory and execution

### 11.1 No new stochastic execution

The operation is deterministic over stored source ensembles. It does not require
thread workers. A sequential replicate-row transform is sufficient and avoids
nested scheduling semantics.

### 11.2 Complete owned state

Preflight must include the estimated simultaneous peak of:

- resident case ensemble;
- resident control ensemble;
- case/control support and masks;
- observed effective control;
- replicate control invalid mask `(B, M)`;
- replicate control adjusted mask `(B, M)`;
- complete raw-risk replicate matrix `(B, M)`;
- complete log-risk replicate matrix `(B, M)`;
- observed raw and log fields;
- two output validity masks;
- raw and log interval arrays;
- one replicate-row denominator and log working buffer;
- linked-result mask ownership.

No source ensemble is copied unnecessarily.

### 11.3 Explicit derived-operation budget

Use an optional dedicated `memory_budget_bytes`, not either source KDE execution
budget. The earlier budgets described separate estimator runs and cannot be
silently interpreted as a combined case-control derived-field peak.

If fixed overhead plus complete outputs do not fit, fail before output matrix
allocation.

## 12. Algorithm sketch

1. Validate both source objects and density field families.
2. Require exact support and all-true source validity masks.
3. Require equal replicate counts and confidence levels.
4. Require distinct source results, event fingerprints, and seed ledgers.
5. Require same estimator family and normalized shared contract.
6. Validate observed and every replicate density integral.
7. Resolve denominator policy.
8. Scan observed and replicate controls to build invalid/adjusted masks and
   perform `raise` fail-fast checks.
9. Resolve conservative 1D output validity for `nan` mode.
10. Preflight complete memory.
11. Allocate raw and log output matrices.
12. Transform observed fields.
13. Transform paired replicate rows in logical order.
14. Build paired replicate fingerprints and combined seed metadata.
15. Build raw and log `FieldEnsemble` objects.
16. Build pointwise percentile intervals.
17. Build linked nested `BootstrapResult` objects.
18. Build and validate `RelativeRiskBootstrapResult`.

## 13. Test and validation plan

### 13.1 Algebraic fixtures

- equal case/control densities produce raw risk one and log risk zero;
- swapping case/control produces reciprocal raw risk and negated log risk when
  denominators remain valid;
- manual small matrices match exact paired-row division;
- zero case density produces raw zero and log `-inf`;
- raw risk is never infinite.

### 13.2 Bootstrap independence

- equal seed-ledger fingerprints rejected;
- same source object supplied twice rejected;
- distinct source-event provenance required;
- paired replicate fingerprints contain both source identities;
- no new RNG or row shuffle occurs.

### 13.3 Contract tests

- unequal replicate counts rejected;
- unequal confidence levels rejected;
- support mismatch rejected;
- estimator-family mismatch rejected;
- bandwidth mismatch rejected;
- kernel/metric/policy/direction/boundary mismatch rejected;
- adaptive or selected bandwidth sources rejected by upstream adapters and
  normalized contract checks.

### 13.4 Normalization tests

- observed case failure;
- observed control failure;
- single case replicate failure with index reported;
- single control replicate failure with index reported;
- explicit tolerance boundary acceptance/rejection;
- no automatic renormalization.

### 13.5 Denominator tests

- `raise` fails on observed invalid control;
- `raise` fails on one replicate invalid control before allocation;
- `nan` conservatively invalidates a whole support column;
- `minimum` records observed and replicate adjustment masks;
- validity threshold and minimum denominator remain explicit;
- no epsilon or pseudocount.

### 13.6 Log-field tests

- all-positive finite log ensemble;
- mixed zero/positive case replicates;
- all-zero case column;
- empirical quantiles with `-inf`;
- NaN standard error and bias for non-finite valid log columns;
- positive infinity rejected.

### 13.7 Support families

At minimum:

- spatial grid;
- network lixel;
- heat-network lixel if contract metadata is available;
- cyclic spatiotemporal grid;
- cyclic network-time arixel.

### 13.8 Memory and immutability

- insufficient budget fails before complete output allocation;
- memory metadata matches expected shapes;
- source case/control results remain unchanged;
- changing only memory budget does not change statistical field fingerprints.

### 13.9 Independent numerical reference

Create a small NumPy-only reference fixture outside the implementation module:

```text
case matrix
control matrix
support measure
policy
expected raw matrix
expected log matrix
expected masks
expected pointwise empirical quantiles
```

The fixture must not call `bootstrap_relative_risk` or deterministic
`estimate_relative_risk` to generate expected values.

## 14. Required implementation prerequisites

Before implementing the numerical transform:

1. add normalized auditable relative-risk contract metadata to all completed
   density Bootstrap adapters;
2. add tests proving that event data and execution choices do not enter that
   contract;
3. confirm `FieldEnsemble` log-risk `-inf` and percentile behavior with focused
   tests;
4. define and validate the dedicated linked result container;
5. create a conservative memory model before output allocation.

## 15. Explicit exclusions

02H numerical implementation must not include:

- unequal case/control replicate counts;
- Cartesian-product replicate expansion;
- random rematching of rows;
- pooled case-control Bootstrap;
- mark permutation;
- significance p-values or tolerance contours;
- simultaneous confidence bands;
- adaptive case/control bandwidths;
- independently selected bandwidths;
- replicate-wise bandwidth reselection;
- uncertain exposure;
- streaming quantiles;
- disk-backed ensembles;
- distributed execution;
- persistence changes;
- package version bump or PR merge.

## 16. Implementation sequencing after design approval

Recommended subunits:

```text
02H-1 normalized shared density-contract metadata
02H-2 linked relative-risk result and validation types
02H-3 paired raw/log numerical transform and memory preflight
02H-4 analytical/reference tests across support families
02H-5 user guide, example, API documentation, and recovery handoff
```

Each subunit must have its own recoverable Markdown record and validated clean
head. The Draft PR remains unmerged until the complete 0.0.16 release surface is
finished.
