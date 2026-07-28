# pyKDEX 0.0.16 design handoff: uncertainty, separability, and scalable execution

This is the durable recovery record for the pyKDEX 0.0.16 design phase. Numerical
implementation has **not** started. The authoritative detailed design is:

```text
docs/development/design-0.0.16-uncertainty-separability-scalable.md
```

## 1. Repository state

- repository: `hujinghaoabcd/pyKDEX`;
- latest merged release: `0.0.15`;
- stable `main` base: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- design implementation commit: `fc6d62bef0abed166c8674dc58275657568eab62`;
- package version remains `0.0.15`;
- no 0.0.16 source package, public API, tests, examples, or version metadata have been
  added;
- no merge has occurred;
- this record describes a design branch, not a release candidate.

Read these records in order:

1. `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`;
2. `HANDOFF_NEXT_CONVERSATION.md` from the merged 0.0.15 state;
3. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
4. this handoff.

## 2. Why 0.0.16 is split into three subunits

The release contains three related but statistically distinct foundations:

1. deterministic and memory-bounded execution;
2. empirical pointwise uncertainty through resampling ensembles;
3. first-order separability diagnostics and an explicitly Poisson event-time permutation
   test.

They share support identity, fingerprints, reproducible random streams, chunking, and
parallel execution. They must not be represented by one generic analysis API.

The implementation order is fixed:

```text
execution foundation -> bootstrap uncertainty -> separability diagnostics/test
```

Execution comes first because every later bootstrap or permutation replicate must use one
common deterministic seed, worker, chunk, and memory contract.

## 3. Research boundary

The design was informed by independently inspected statistical and engineering references,
including:

- `tilmandavies/sparr` at
  `67ad2c995683b5122d4edee16d2eaacbbfb868cb`;
- `cran/GET` at `5e434dd5b18db9d82dccdd8473b0a2c32df2f8cd`;
- first-order separability work by Schoenberg, Fuentes-Santos et al., Ghorbani et al.;
- kernel uncertainty and relative-risk inference work by Kern et al., Hazelton and Davies,
  Davies and Hazelton, Davies et al., and Chen;
- Phipson and Smyth for finite Monte Carlo p-values;
- NumPy `SeedSequence`, Dask chunking/scheduling guidance, and Joblib parallel-randomness
  guidance.

These sources are methodological references only. GPL-licensed code is not copied,
translated, mechanically ported, imported, or called by pyKDEX. Dask and Joblib are not
runtime dependencies for 0.0.16.

## 4. Deterministic execution decision

The proposed immutable public execution object is:

```python
ExecutionPlan(
    memory_budget_bytes=268_435_456,
    target_chunk_size=None,
    replicate_chunk_size=None,
    n_jobs=1,
    backend="sequential",
)
```

Initial backends are restricted to:

```text
sequential
thread
```

Process pools, Dask, Ray, distributed schedulers, GPU execution, and approximate kernels
are excluded.

The plan resolves into an immutable private execution record containing operation name,
target/source counts, conservative bytes-per-pair estimates, resolved target and replicate
chunks, workers, backend, parallel axis, and an execution-plan fingerprint.

Execution metadata is retained for audit but is not part of the statistical estimator
compatibility contract. Changing chunk size or worker count must not change the
mathematical estimate.

Only independent target chunks or independent resampling replicates may run concurrently.
Source-event reductions remain in stable source order. Completed chunks write to
preassigned output slices by logical index rather than completion order.

The package promises numerical equivalence to documented tolerance across chunking and
worker choices. It does not make an unsupported bitwise-across-platform guarantee.

Existing `chunk_size` and `time_chunk_size` arguments remain supported. Supplying both a
legacy explicit chunk and a conflicting explicit plan chunk is an error. Defaults remain
unchanged when no plan is supplied.

## 5. Reproducible randomness decision

Randomness belongs to `BootstrapPlan`, not `ExecutionPlan`.

The proposed bootstrap plan contains replicate count, confidence level, root seed,
ordinary-bootstrap method, replicate-storage choice, and execution plan.

A private seed ledger uses NumPy `SeedSequence`. Child random streams are assigned in
logical replicate order before scheduling. Therefore replicate `b` receives the same
random stream regardless of worker completion order, `n_jobs`, target chunk size, or
replicate chunk size.

`random_state=None` is allowed for exploratory use only if generated root entropy is
recorded. Tests and executable examples use explicit non-negative integer seeds.

## 6. Uncertainty decision

The central immutable object is a full `FieldEnsemble` with shape `(B, M)`, where `B` is
the replicate count and `M` is the number of exact measured support elements.

Version 0.0.16 stores full replicates so empirical quantiles are exactly reproducible.
Streaming approximate quantiles and disk/Zarr-backed ensembles are excluded.

The initial summary is explicitly named `PointwiseInterval` and uses percentile bootstrap
quantiles. It is not a simultaneous confidence band and does not claim family-wise
coverage.

Proposed built-in functions are:

```python
bootstrap_kde(...)
bootstrap_event_rate(...)
bootstrap_relative_risk(...)
```

Built-in bootstrap restrictions are deliberate:

- unit event weights only;
- fixed scalar bandwidths;
- fixed support and estimator contract;
- no bandwidth reselection inside replicates;
- fixed event/group counts;
- no adaptive, matrix, or balloon bandwidths.

`bootstrap_kde` resamples event identities within one sample. Network resampling occurs
after accepted-event snapping, while network geometry, support, and rejection audit remain
fixed.

`bootstrap_event_rate` resamples only the numerator and treats the `ExposureField` as
fixed. Its intervals are explicitly conditional on fixed exposure.

`bootstrap_relative_risk` independently resamples cases within the case sample and
controls within the control sample. It does not pool marks. Log-risk intervals are the
default.

## 7. Separability decision

The first-order diagnostic is defined only for complete Cartesian measured support:

```text
SpatiotemporalGridSupport
ArixelSupport = lixel support x temporal cells
```

Arbitrary space-time point support is rejected because it does not provide the complete
product measure required for marginals.

For normalized joint density `p_ij`, spatial/network measure `a_i`, and temporal width
`dt_j`:

```text
p_space_i = sum_j p_ij * dt_j
p_time_j  = sum_i p_ij * a_i
p_sep_ij  = p_space_i * p_time_j
```

The proposed `SeparabilityDiagnostic` retains observed density, marginals, separable
reconstruction, signed/absolute difference, optional ratio/log ratio, exact support, and
fingerprints.

Primary dimensionless descriptive statistics are:

```text
TV = 0.5 * sum_ij |p_ij - p_sep_ij| * a_i * dt_j

H2 = 0.5 * sum_ij (sqrt(p_ij) - sqrt(p_sep_ij))^2 * a_i * dt_j
```

A descriptive statistic does not imply a p-value.

## 8. Poisson permutation-test decision

The initial calibrated test is explicitly conditional on:

```text
assumption="poisson"
```

Each permutation keeps locations fixed and permutes observed event times among events. It
preserves the spatial and temporal marginal samples, breaks their pairing, keeps event
count fixed, and reuses the observed fixed estimator contract.

The initial scalar test statistics are squared Hellinger distance and total variation.
The right-tailed Monte Carlo p-value is:

```text
p = (1 + count(T_b >= T_observed)) / (B + 1)
```

Ties use `>=`. The observed configuration is included through the plus-one calculation.

The test must state that simple time permutation is not generally valid for clustered or
inhibited non-Poisson point processes. Non-Poisson p-values, block permutation, stochastic
reconstruction, HSIC tests, local p-value surfaces, significance contours, and global
envelope tests are excluded.

## 9. Provisional module and API layout

Proposed packages:

```text
pykdex.execution
pykdex.inference
pykdex.diagnostics
```

Provisional public names:

```python
ExecutionPlan
BootstrapPlan
FieldEnsemble
PointwiseInterval
BootstrapResult
bootstrap_kde
bootstrap_event_rate
bootstrap_relative_risk
SeparabilityDiagnostic
SeparabilityTestResult
estimate_separability
test_separability
```

These names are not frozen. No provisional name is added to top-level `pykdex` until its
implementation, tests, example mapping, API documentation, and distribution smoke test are
complete.

## 10. Exact implementation sequence

### Progress subunit 01: execution foundation

1. implement immutable `ExecutionPlan` and fingerprint;
2. implement conservative operation-specific chunk resolution;
3. preserve existing `chunk_size` and `time_chunk_size` compatibility;
4. integrate exact target chunking without duplicating numerical kernels;
5. add sequential and thread execution over independent target chunks;
6. preserve stable source-event reduction and fixed output ordering;
7. add memory-budget rejection before large allocation;
8. add equivalence, ordering, budget, metadata, and cross-domain tests;
9. add execution guide, API page, benchmark, and root progress handoff;
10. run the complete repository CI matrix.

Required handoff:

```text
HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md
```

### Progress subunit 02: bootstrap uncertainty

Implement seed ledger, ensembles, pointwise intervals, fixed-contract KDE bootstrap,
fixed-exposure event-rate bootstrap, and stratified relative-risk bootstrap only after the
execution foundation is validated.

### Progress subunit 03: separability

Implement product-support marginalization, TV/Hellinger diagnostics, deterministic time
permutation, and the plus-one Poisson p-value only after the bootstrap execution
infrastructure is validated.

### Final release

Freeze API, add top-level exports and examples, bump to 0.0.16, create final handoff, run
full CI, audit the PR, merge, and record actual merge evidence.

## 11. Deliberate exclusions

Do not add during 0.0.16 without a new design:

- simultaneous confidence bands;
- BCa, bootstrap-t, basic, smoothed, Bayesian, wild, or block bootstrap;
- debiased or undersmoothed KDE inference;
- arbitrary weighted-event bootstrap;
- uncertain exposure fields;
- unconditional Poisson event-count uncertainty;
- adaptive or independently selected relative-risk bandwidths;
- replicate-wise bandwidth selection;
- asymptotic tolerance contours;
- local significance maps or global rank envelopes;
- non-Poisson separability p-values;
- process pools, Dask, Ray, distributed or GPU execution;
- approximate nearest-neighbour or approximate kernel summation;
- Zarr/PostGIS storage or persistence-schema changes.

## 12. Recovery checklist

1. Inspect the branch and its actual head before trusting this record.
2. Confirm `src/pykdex/__init__.py` still reports `0.0.15`.
3. Confirm no provisional 0.0.16 top-level public symbols exist.
4. Read the detailed design in full.
5. Inspect existing spatial, network, ordinary space-time, and network-time chunking and
   reusable assets before editing.
6. Begin only Progress subunit 01.
7. Preserve the existing single NumPy/SciPy numerical route.
8. Never claim exact CI results that have not been observed for the current branch head.
9. Create the required root progress handoff after the execution unit is complete.
10. Do not start bootstrap or separability code until Progress subunit 01 passes full CI.
