# pyKDEX 0.0.16 design: uncertainty, separability diagnostics, and scalable execution

Status: design complete, implementation not started  
Branch: `agent/uncertainty-separability-scalable-design`  
Base: pyKDEX `0.0.15`, `main` commit
`8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`

This document fixes the statistical meaning, public boundaries, deterministic execution
contract, implementation order, and exclusions for pyKDEX 0.0.16 before numerical code is
added. The version must not expose placeholder APIs or claim inferential coverage that has
not been analytically or independently validated.

## 1. Purpose

Version 0.0.16 develops three related but distinct foundations:

1. **scalable deterministic execution** for existing exact NumPy/SciPy estimators;
2. **empirical pointwise uncertainty** through explicit resampling ensembles; and
3. **first-order separability diagnostics** for ordinary space-time and network-time
   point patterns.

The three themes share execution, support identity, fingerprints, and reproducible random
streams. They must not be collapsed into one generic `analysis` object.

The release remains a point-estimation and diagnostic package. It does not introduce a
universal confidence-band claim, a universal point-process null model, approximate
numerics, distributed storage, or hidden parallel backends.

## 2. External references inspected

The following projects and publications are methodological or engineering references only.
No source code is copied into pyKDEX.

### 2.1 `tilmandavies/sparr`

Reference revision inspected:
`67ad2c995683b5122d4edee16d2eaacbbfb868cb`.

Relevant files include:

- `R/tolerance.R`;
- `R/risk.R`;
- fixed and adaptive risk documentation.

Important lessons:

- asymptotic and Monte Carlo tolerance calculations are different methods and must be
  named separately;
- Monte Carlo mark permutation preserves the smoothing and edge-correction regimen of the
  observed estimate;
- inferential output depends on the case-control sampling design and cannot be attached to
  an arbitrary ratio field;
- parallel repetition is an execution concern, not a different statistical estimator.

### 2.2 `cran/GET`

Reference revision inspected:
`5e434dd5b18db9d82dccdd8473b0a2c32df2f8cd`.

Relevant material includes:

- `R/envelopes.r`;
- `R/curve-set.r`;
- `global_envelope_test` documentation;
- point-pattern vignettes.

Important lessons:

- pointwise envelopes and global envelope tests are not interchangeable;
- global rank envelopes solve a multiple-testing problem over a function or vector;
- a local map of pointwise tail frequencies must not be labelled a globally calibrated
  significance surface.

Version 0.0.16 does not implement a global envelope test. The package first establishes
scalar separability tests and pointwise bootstrap intervals with explicit labels.

### 2.3 First-order separability literature

Primary references inspected:

- Schoenberg (2004), *Testing Separability in Spatial-Temporal Marked Point
  Processes*, Biometrics 60, 471-481, DOI `10.1111/j.0006-341X.2004.00192.x`;
- Fuentes-Santos, Gonzalez-Manteiga and Mateu (2018), *A first-order, ratio-based
  nonparametric separability test for spatiotemporal point processes*, Environmetrics 29,
  e2482, DOI `10.1002/env.2482`;
- Ghorbani, Vafaei, Dvorak and Myllymaki (2021), *Testing the first-order separability
  hypothesis for spatio-temporal point patterns*, Computational Statistics & Data
  Analysis 161, 107245, DOI `10.1016/j.csda.2021.107245`;
- Ghorbani, Vafaei and Myllymaki (2025), *A kernel-based test for the first-order
  separability of spatio-temporal point processes*, TEST 34, 580-611, DOI
  `10.1007/s11749-025-00972-y`.

Important lessons:

- first-order separability concerns the intensity or induced normalized joint
  distribution, not covariance separability;
- simple event-time permutation is appropriate only under an exchangeable Poisson or
  independent-event interpretation;
- naive permutations can destroy clustering or inhibition in non-Poisson point processes;
- stochastic reconstruction and block-permutation methods address broader nulls but have
  additional assumptions and computational cost;
- diagnostic maps and a calibrated scalar test must remain distinct.

### 2.4 Kernel uncertainty and relative-risk inference

Primary references inspected:

- Kern et al. (2003), *Using the bootstrap and fast Fourier transform to estimate
  confidence intervals of 2D kernel densities*, Environmental and Ecological Statistics
  10, 405-418, DOI `10.1023/A:1026092103819`;
- Hazelton and Davies (2009), *Inference based on kernel estimates of the relative risk
  function in geographical epidemiology*, Biometrical Journal 51, 98-109, DOI
  `10.1002/bimj.200810495`;
- Davies and Hazelton (2010), *Adaptive kernel estimation of spatial relative risk*,
  Statistics in Medicine 29, 2423-2437, DOI `10.1002/sim.3995`;
- Davies, Marshall and Hazelton (2018), *Tutorial on kernel estimation of continuous
  spatial and spatiotemporal relative risk*, Statistics in Medicine 37, 1191-1221, DOI
  `10.1002/sim.7577`;
- Chen (2017), *Nonparametric inference via bootstrapping the debiased estimator*,
  arXiv `1702.07027`.

Important lessons:

- a conventional KDE bandwidth optimizes estimation, not automatically inferential
  coverage;
- percentile bootstrap intervals are pointwise empirical summaries unless stronger bias
  and simultaneous-coverage theory is implemented;
- debiasing, undersmoothing, asymptotic contours, and bootstrap intervals are distinct
  inferential regimes;
- event-rate uncertainty depends on whether exposure is fixed or itself uncertain;
- relative-risk uncertainty requires independent within-group resampling of cases and
  controls, not pooled resampling.

### 2.5 Monte Carlo p-values

Phipson and Smyth (2010), *Permutation p-values should never be zero*, Statistical
Applications in Genetics and Molecular Biology 9, DOI `10.2202/1544-6115.1585`, is the
reference for finite Monte Carlo p-value calculation.

Randomly sampled permutation p-values use the observed configuration in the reference
set. The default right-tail calculation is therefore:

```text
p = (1 + number of permuted statistics >= observed statistic)
    / (n_permutations + 1)
```

### 2.6 Reproducible and scalable execution projects

GitHub revisions and official documentation inspected:

- `numpy/numpy` revision `7b3e1002a179046444a626722faaa8cb78451064` and
  NumPy `SeedSequence` / parallel random generation documentation;
- `dask/dask` revision `a54329156cd17a68ef081c83fdc2409ddb423426` and
  official array chunking, task graph, scheduling, and oversubscription guidance;
- `joblib/joblib` revision `53cea7b177c3400154613372614a0f35274b036d`
  and official parallel random-state and backend guidance.

Important lessons:

- independent parallel random streams must be derived from one recorded root seed;
- task identity must not depend on worker scheduling order;
- chunk size is a memory and overhead trade-off, not a statistical parameter;
- nested BLAS/OpenMP thread pools can cause severe oversubscription;
- libraries should not silently hard-code an external parallel backend;
- task graphs and caching are useful architectural references, but pyKDEX should not add a
  Dask or Joblib runtime dependency in this version.

## 3. Licence and implementation boundary

`sparr`, `GET`, and related R packages are research references. Their source is not copied,
translated, or mechanically ported into the MIT-licensed pyKDEX project.

For 0.0.16:

1. public mathematical definitions and documented behaviour may guide an independent
   implementation;
2. external packages may generate one-time reference fixtures with provenance;
3. runtime code must not import or call the inspected R packages;
4. Dask and Joblib are not runtime dependencies;
5. all numerical behaviour requires analytical tests or independently generated static
   fixtures;
6. exact source revisions and reference-generation scripts must be recorded when external
   fixtures are added.

## 4. Current pyKDEX architecture and gaps

The 0.0.15 architecture already provides:

- immutable data objects with CRS, units, identifiers, provenance, and fingerprints;
- exact measured spatial, network, space-time, and network-time supports;
- reusable distance assets, propagation traces, heat plans, and selection caches;
- target-row chunking in `SpatialKDE` and `SpatiotemporalKDE`;
- time-row chunking and factorized network/time multiplication in
  `TemporalNetworkKDE`;
- atomic fitted-state replacement;
- one NumPy/SciPy numerical route;
- cross-platform CI with BLAS thread counts set to one.

The gaps are:

- chunk parameters are estimator-specific (`chunk_size` and `time_chunk_size`);
- no common memory-budget calculation exists;
- `random_state` is validated but not yet tied to a reproducible resampling contract;
- no immutable record describes resolved chunking and worker choices;
- no generic exact-support ensemble stores replicate fields;
- no public distinction exists between pointwise intervals and simultaneous bands;
- no first-order separability diagnostic exists for product measured supports;
- no calibrated permutation test records its null assumption and permutation unit.

## 5. Overall design decision

Version 0.0.16 is implemented in three ordered subunits:

1. **deterministic execution foundation**;
2. **empirical field uncertainty foundation**;
3. **first-order separability diagnostics and the explicitly Poisson permutation test**.

Execution is implemented first because bootstrap and permutation calculations must share
one seed, chunking, memory, and parallelism contract.

The version is not complete after only one subunit. Each subunit receives a detailed root
handoff, tests, and real CI evidence. Package version metadata remains `0.0.15` until the
full release surface is complete.

## 6. Deterministic execution foundation

### 6.1 Public `ExecutionPlan`

The proposed immutable public object is:

```python
ExecutionPlan(
    *,
    memory_budget_bytes=268_435_456,
    target_chunk_size=None,
    replicate_chunk_size=None,
    n_jobs=1,
    backend="sequential",
)
```

Initial backend values are:

```text
sequential
thread
```

A process backend and distributed scheduler are excluded from 0.0.16.

Validation rules:

- memory budget is a positive integer or `None`;
- explicit chunk sizes are positive integers or `None`;
- `n_jobs` is a positive integer;
- `backend="sequential"` requires `n_jobs=1`;
- `backend="thread"` allows `n_jobs>=1`;
- an explicit chunk may not exceed a non-null memory budget after conservative peak-memory
  estimation;
- zero, negative, boolean, NaN-like, and implicit string coercions are rejected.

### 6.2 Resolved private execution contract

Every estimator or experiment resolves the public plan into a private immutable record:

```text
operation_name
n_targets
n_sources
bytes_per_pair
fixed_overhead_bytes
resolved_target_chunk_size
resolved_replicate_chunk_size
n_jobs
backend
parallel_axis
execution_plan_fingerprint
```

The resolved plan is retained in result metadata for audit. It is not part of the
statistical estimator-compatibility contract because changing chunk size or worker count
must not change the mathematical estimate.

### 6.3 Memory budgeting

The first implementation uses conservative analytical peak-memory estimates for dense
pairwise blocks. A target chunk is bounded by:

```text
chunk_rows <= floor(
    (memory_budget_bytes - fixed_overhead_bytes)
    / (n_sources * bytes_per_pair * safety_factor)
)
```

The exact formula is operation-specific and tested. It must include simultaneously live
kernel, distance, temporal, coefficient, and output arrays where applicable.

Sparse distance assets retain their existing storage. The execution plan controls the
size of dense materialized blocks generated from those assets; it does not silently
convert sparse assets to dense global matrices.

### 6.4 Parallel axis and deterministic reduction

Version 0.0.16 parallelizes only independent units:

- target chunks for ordinary estimation; or
- bootstrap/permutation replicates for resampling experiments.

It does **not** parallelize the source-event reduction. Each target value sums event
contributions in the existing stable source order. This avoids changing floating-point
reduction order merely because `n_jobs` changes.

Completed chunks are written into preassigned slices by logical chunk index. Result order
never follows worker completion order.

The deterministic contract is:

- same environment, data, estimator contract, root seed, and logical task count -> same
  arrays regardless of scheduling order;
- different target chunk sizes and `n_jobs` -> equal results to repository numerical
  tolerance;
- cross-platform floating-point results -> numerical agreement to documented tolerance,
  not an unsupported bitwise guarantee across BLAS and operating systems.

### 6.5 Thread oversubscription

The library does not globally mutate user environment variables. Documentation and CI
continue to recommend one BLAS/OpenMP thread per Python worker. Result metadata records the
requested Python worker count, but pyKDEX does not claim control over external thread pools
without a future explicit dependency and design.

### 6.6 Compatibility with current constructors

Existing `chunk_size` and `time_chunk_size` parameters remain supported in 0.0.16.

Transition rules:

- an estimator may accept `execution_plan=None` in addition to its legacy chunk argument;
- supplying both an explicit legacy chunk and an explicit plan chunk is an error;
- a legacy chunk is normalized into an equivalent `ExecutionPlan`;
- no deprecation warning is added until every estimator family supports the plan;
- numerical defaults remain unchanged when no plan is supplied.

## 7. Reproducible random streams

Randomness belongs to a resampling plan, not to `ExecutionPlan`.

### 7.1 `BootstrapPlan`

The proposed immutable public object is:

```python
BootstrapPlan(
    n_resamples=999,
    *,
    confidence_level=0.95,
    random_state=None,
    method="ordinary",
    store_replicates=True,
    execution_plan=None,
)
```

Initial method values contain only:

```text
ordinary
```

Smoothed, parametric, Bayesian, block, wild, and weighted bootstraps are excluded until
separately designed.

### 7.2 Seed ledger

A private immutable seed ledger is created from NumPy `SeedSequence`:

```text
root_entropy
n_logical_tasks
child_index
child_spawn_key or generated state
bit_generator_name
seed_ledger_fingerprint
```

All child streams are created in logical replicate order before work is scheduled. Worker
completion order cannot affect a replicate's random stream.

`random_state=None` is allowed for exploratory use but records generated root entropy in
the result. Reproducible examples and tests always use an explicit non-negative integer.

Changing `n_jobs`, target chunk size, or replicate chunk size does not change the random
sample attached to replicate index `b`.

## 8. Empirical uncertainty objects

### 8.1 `FieldEnsemble`

The central immutable object stores replicate fields on one exact measured support:

```text
replicate_values shape (B, M)
support and SupportDescriptor
field_family
observed_values
observed_field_fingerprint
replicate source fingerprints
resampling method
root seed and seed-ledger fingerprint
execution metadata
ensemble fingerprint
```

`M` is the number of measured support elements and `B` is the number of replicates.

Rules:

- all replicate values use one field family and exact measured support;
- support identity uses fingerprints, identifiers, measures, CRS, units, network, and time
  domain where applicable;
- positive infinity is rejected;
- NaN is permitted only when the originating field has an explicit `nan` denominator
  policy, and every replicate must retain a matching validity contract;
- arrays are read-only and C-contiguous;
- full replicate storage is required in the first release so exact empirical quantiles can
  be reproduced;
- estimated ensemble memory is checked before execution and must fit the explicit plan.

Approximate streaming quantiles and Zarr-backed ensembles are excluded.

### 8.2 `PointwiseInterval`

The initial uncertainty summary is explicitly pointwise:

```text
lower
estimate
upper
standard_error
bias
confidence_level
method="percentile"
support identity
source ensemble fingerprint
```

For level `1-alpha`, percentile endpoints are empirical quantiles at `alpha/2` and
`1-alpha/2` for each support element.

These are named **pointwise percentile bootstrap intervals**. They are not named confidence
bands and do not claim simultaneous family-wise coverage.

The first version excludes:

- basic intervals;
- bootstrap-t intervals;
- BCa intervals;
- debiased KDE bands;
- asymptotic tolerance contours;
- global rank envelopes.

### 8.3 `BootstrapResult`

A bootstrap function returns one immutable result containing:

- the observed field;
- `BootstrapPlan`;
- `FieldEnsemble`;
- default `PointwiseInterval`;
- replicate failure count and explicit failure records;
- estimator and source-data fingerprints;
- execution and seed-ledger metadata.

A replicate failure is not silently dropped. The default is fail-fast. A future partial
ensemble policy requires a separate design.

## 9. Built-in bootstrap semantics

The proposed public functions are:

```python
bootstrap_kde(...)
bootstrap_event_rate(...)
bootstrap_relative_risk(...)
```

They share infrastructure but have different sampling units and interpretation.

### 9.1 Common restrictions

The built-in 0.0.16 bootstrap requires:

- immutable pyKDEX event objects or prepared workspaces;
- unit event weights;
- fixed estimator configuration;
- fixed scalar spatial/network bandwidths and fixed scalar temporal bandwidth where
  applicable;
- fixed support;
- fixed boundary correction, junction policy, directed setting, network, and time domain;
- fixed event count within each resampled group;
- no bandwidth reselection inside replicates.

Arbitrary event weights are statistically ambiguous because pyKDEX does not yet distinguish
frequency, probability, exposure, and analytic weights. Weighted users may construct a
validated `FieldEnsemble` from externally justified replicate fields, but built-in
resampling rejects non-unit weights.

Adaptive bandwidths, bandwidth matrices, balloon bandwidths, and replicate-wise bandwidth
selection are excluded.

### 9.2 KDE bootstrap

`bootstrap_kde` resamples event identities with replacement within one event sample and
refits the same fixed estimator contract.

Interpretation:

- density uncertainty is conditional on the observed event count;
- intensity uncertainty is also conditional on event count;
- unconditional Poisson count uncertainty is not included;
- duplicate selected events contribute as duplicate events at the same location and time.

Supported domains are implemented through closed adapters:

- `SpatialEvents` with `SpatialKDE`;
- `NetworkWorkspace` with radial or heat `NetworkKDE` family estimators;
- `SpatiotemporalEvents` with `SpatiotemporalKDE`;
- `NetworkTimeWorkspace` with `TemporalNetworkKDE`.

For network domains, resampling occurs after accepted-event snapping. The network,
lixels/arixels, rejected-event audit, and geometry remain fixed. Reusable distance assets
are column-reindexed by bootstrap event indices where mathematically valid instead of
recomputing network geometry.

### 9.3 Event-rate bootstrap

`bootstrap_event_rate` bootstraps only the event-intensity numerator and treats the supplied
`ExposureField` as fixed.

For replicate `b`:

```text
q_j^(b) = lambda_j^(b) / e_j
```

The original denominator policy is reused exactly.

The result is labelled **conditional on fixed exposure**. Exposure measurement error,
population-estimate uncertainty, and joint numerator-denominator resampling are excluded.

### 9.4 Relative-risk bootstrap

`bootstrap_relative_risk` independently resamples cases within the case sample and controls
within the control sample while preserving the observed group sizes.

For replicate `b`:

```text
r_j^(b) = f_j^(b) / g_j^(b)
log_r_j^(b) = log(f_j^(b)) - log(g_j^(b))
```

The same fixed shared bandwidth, support, kernels, boundary correction, metric or junction
policy, network, direction, time domain, normalization tolerance, and denominator policy
are used for every replicate.

Case and control marks are not pooled for bootstrap sampling. Mark permutation is a null
test and belongs to a different API.

Intervals are produced for log relative risk by default because reciprocal deviations are
symmetric on the log scale. Raw-risk intervals may be obtained by exponentiating finite
log endpoints. Cells with explicit `nan` denominator policy retain matching validity
masks.

## 10. First-order separability diagnostic

### 10.1 Scope

The diagnostic is defined only on a complete Cartesian measured support:

- `SpatiotemporalGridSupport`; or
- `ArixelSupport` as lixel support x temporal cells.

Arbitrary `SpatiotemporalPointSupport` is rejected because its points do not define the
complete product measure needed to obtain marginals.

The input may be density or intensity. Intensity is normalized by its measured integral to
an induced probability density. The original event mass is retained separately.

### 10.2 Measured marginalization

Let product support values be `p_ij` at spatial/network element `i` and time element `j`.
Let spatial measure be `a_i` and temporal width be `dt_j`. The product measure is:

```text
m_ij = a_i * dt_j
```

The spatial and temporal marginals are:

```text
p_space_i = sum_j p_ij * dt_j
p_time_j  = sum_i p_ij * a_i
```

The first-order separable reconstruction is:

```text
p_sep_ij = p_space_i * p_time_j
```

The implementation verifies:

```text
sum_ij p_ij * m_ij approximately equals 1
sum_i p_space_i * a_i approximately equals 1
sum_j p_time_j * dt_j approximately equals 1
sum_ij p_sep_ij * m_ij approximately equals 1
```

Actual remainder-cell areas, lixel lengths, and final temporal-bin widths are used.

### 10.3 `SeparabilityDiagnostic`

The proposed immutable result retains:

- normalized observed joint density;
- spatial/network marginal density;
- temporal marginal density;
- separable reconstructed density;
- signed difference `p - p_sep`;
- absolute difference;
- optional density ratio and log ratio under the existing explicit denominator policy;
- total variation distance;
- squared Hellinger distance;
- original field family, mass, bandwidth, support, estimator metadata, and fingerprints;
- table, grid, time-slice, and geospatial exports where supported.

The primary dimensionless scalar diagnostics are:

```text
TV = 0.5 * sum_ij |p_ij - p_sep_ij| * m_ij

H2 = 0.5 * sum_ij (sqrt(p_ij) - sqrt(p_sep_ij))^2 * m_ij
```

Both are zero for an exactly separable normalized field and lie in `[0, 1]` up to
floating-point tolerance.

These are descriptive diagnostics. A large value does not itself provide a p-value.

The proposed public function is:

```python
estimate_separability(field, *, zero_policy="nan", ...)
```

## 11. Explicit Poisson permutation test

### 11.1 Public contract

The proposed public function is:

```python
test_separability(
    estimator,
    events_or_workspace,
    support,
    *,
    n_permutations=999,
    statistic="hellinger",
    assumption="poisson",
    random_state=None,
    execution_plan=None,
)
```

The caller must explicitly set or accept `assumption="poisson"`. Documentation states that
the event-time permutation is a conditional first-order test for exchangeable independent
events and is not valid for a general clustered or inhibited process.

### 11.2 Permutation unit

For each permutation:

- spatial coordinates or network locations remain fixed;
- observed event times are permuted among events;
- spatial and temporal marginal samples are therefore preserved;
- joint space-time pairing is broken under the separable null;
- event count remains fixed;
- unit weights remain fixed;
- the observed fixed bandwidth and estimator contract are reused.

For `NetworkTimeWorkspace`, permutation changes only the accepted-event time assignment.
Network topology, snapped locations, lixels, arixels, and spatial distance assets remain
fixed.

Cyclic time values are permuted in their normalized domain representation; the time domain,
period, temporal origin, timezone, and support bins do not change.

### 11.3 Test statistic and p-value

Initial statistic values are:

```text
hellinger
total_variation
```

The default is squared Hellinger distance. For randomly sampled permutations, the
right-tailed p-value is:

```text
p = (1 + count(T_b >= T_observed)) / (B + 1)
```

Ties use `>=`. The result records the complete null statistic vector, observed statistic,
p-value, number of permutations, seed ledger, assumption, permutation unit, estimator
contract, and support identity.

### 11.4 `SeparabilityTestResult`

The immutable result contains:

- observed `SeparabilityDiagnostic`;
- null statistic values;
- scalar p-value;
- statistic name;
- explicit null assumption;
- permutation unit;
- number of permutations;
- root seed and seed-ledger fingerprint;
- execution metadata;
- source and result fingerprints.

The result does not contain pointwise p-value surfaces or significance contours.

### 11.5 Non-Poisson boundary

Version 0.0.16 does not implement:

- stochastic reconstruction;
- block permutation;
- HSIC-based separability tests;
- conditional-intensity residual tests;
- global envelope tests.

Those methods require a separate design that specifies interaction preservation, block
selection, edge handling, network generalization, cyclic-time boundaries, and calibrated
reference fixtures.

For non-Poisson patterns, `estimate_separability` remains a valid descriptive comparison,
but `test_separability` must not claim a valid p-value.

## 12. Provisional package architecture

Proposed modules are:

```text
src/pykdex/execution/__init__.py
src/pykdex/execution/plan.py
src/pykdex/execution/chunks.py

src/pykdex/inference/__init__.py
src/pykdex/inference/plans.py
src/pykdex/inference/seeds.py
src/pykdex/inference/ensemble.py
src/pykdex/inference/bootstrap.py
src/pykdex/inference/adapters.py

src/pykdex/diagnostics/__init__.py
src/pykdex/diagnostics/separability.py
src/pykdex/diagnostics/permutation.py
```

Existing estimator numerical kernels remain in their current modules. Execution helpers
wrap the current numerical route; they do not create duplicate estimator implementations.

## 13. Provisional public API

Names are provisional until implementation tests freeze signatures.

Execution:

```python
ExecutionPlan
```

Inference:

```python
BootstrapPlan
FieldEnsemble
PointwiseInterval
BootstrapResult
bootstrap_kde
bootstrap_event_rate
bootstrap_relative_risk
```

Diagnostics:

```python
SeparabilityDiagnostic
SeparabilityTestResult
estimate_separability
test_separability
```

Advanced adapter and seed-ledger objects remain private. No name is added to top-level
`pykdex` until its implementation, tests, executable example, API mapping, and docs are
complete.

## 14. Fingerprints and provenance

Every new public object has a deterministic fingerprint.

Statistical fingerprints include:

- source event/workspace identity;
- support identity;
- estimator and smoothing contract;
- resampling method and sampling unit;
- root seed and logical replicate count;
- denominator and normalization policies;
- observed and replicate values.

Execution metadata includes:

- resolved chunk sizes;
- memory budget;
- Python worker count;
- backend;
- parallel axis;
- execution plan fingerprint.

Execution choices are not included in case-control estimator compatibility or separability
null definitions. A cache key for a numerical asset is based on the data and numerical
contract, not worker count.

A bootstrap result retains the 0.0.15 field fingerprints rather than mutable estimator
objects.

## 15. Cache boundary

Version 0.0.16 reuses existing in-memory assets:

- event-to-support distance matrices;
- event-to-event matrices;
- propagation traces;
- heat operators and plans;
- factorized network-time assets;
- selection caches;
- immutable workspaces.

It may add private replicate-index views that reindex source columns without copying
geometry.

It does not add:

- a general disk cache;
- cloud object storage;
- Zarr-backed replicate arrays;
- PostGIS execution;
- task-graph serialization;
- estimator pickle support.

Portable workspace persistence remains the 0.0.14 data boundary.

## 16. Required tests

### 16.1 Execution

1. Legacy chunk parameters and equivalent `ExecutionPlan` produce identical results.
2. Multiple target chunk sizes produce numerically equal fields.
3. Sequential and threaded target-chunk execution preserve output ordering and values.
4. Parallel source-event reduction is absent.
5. Memory-budget resolution chooses a valid positive chunk.
6. Impossible budgets fail before allocating large arrays.
7. Explicit chunks exceeding the budget fail.
8. Result metadata records the resolved plan without entering statistical compatibility.
9. Existing estimator defaults and public signatures remain backward compatible.
10. No Dask or Joblib runtime import is introduced.

### 16.2 Seed and ensemble contracts

1. A fixed root seed produces the same replicate indices for `n_jobs=1` and `n_jobs>1`.
2. Replicate identity is independent of worker completion order and replicate chunk size.
3. Different root seeds produce different ledgers.
4. `random_state=None` records generated entropy.
5. `FieldEnsemble` rejects support, shape, family, and validity-policy mismatch.
6. Replicate arrays are read-only.
7. Manual means, standard errors, bias, and percentile quantiles are recovered exactly.
8. Estimated ensemble bytes are checked before execution.

### 16.3 KDE bootstrap

1. Unit-weight event sampling preserves the event count.
2. Duplicate selected events are retained as duplicates.
3. A deterministic toy sample matches manually enumerated bootstrap replicates.
4. Fixed bandwidth and boundary/junction/time contracts are unchanged.
5. Non-unit weights fail with a precise message.
6. Adaptive, matrix, balloon, or selected-per-replicate bandwidths fail.
7. Network resampling reindexes accepted events and reusable distance columns correctly.
8. Cyclic-time resampling preserves time-domain identity.
9. Spatial, network, ordinary space-time, and network-time smoke examples are covered.

### 16.4 Event-rate and relative-risk bootstrap

1. Event-rate replicates use one unchanged `ExposureField`.
2. The original denominator policy and masks are retained.
3. Relative-risk cases and controls are resampled independently within group.
4. Group sizes remain fixed.
5. Shared bandwidth and estimator compatibility remain exact.
6. Log-risk intervals equal manual replicate quantiles.
7. `nan` denominator cells remain explicitly masked.
8. Pooled mark resampling is rejected by the bootstrap API.

### 16.5 Separability diagnostic

1. An exact product field gives `TV=0` and `H2=0`.
2. A manually nonseparable field gives analytical marginals, reconstruction, TV, and H2.
3. Unequal spatial cells and unequal final time bins use actual measures.
4. Arixel marginals use actual lixel lengths and temporal widths.
5. Density and normalized intensity produce the same diagnostic shape.
6. Arbitrary point support is rejected.
7. Joint and reconstructed densities integrate to one.
8. Cyclic time preserves support order and domain identity.
9. Ratio/log-ratio zero handling reuses explicit denominator policy.

### 16.6 Separability permutation test

1. Fixed seeds give identical null statistics across worker counts.
2. Event times, not locations, are permuted.
3. Spatial and temporal marginal samples are preserved in every replicate.
4. The plus-one Monte Carlo p-value is exact for a manually enumerated toy case.
5. Ties use the right-tail `>=` convention.
6. Non-unit weights fail.
7. Non-Poisson or unsupported assumptions fail rather than silently returning a p-value.
8. Ordinary space-time and network-time tests use the same statistical contract.
9. Cyclic times are permuted without changing period, origin, timezone, or bins.
10. The result retains the complete null statistic vector and seed ledger.

## 17. Validation and benchmarks

Each implementation subunit must run:

```text
Black
isort
Ruff
mypy
public API example mapping
strict MkDocs
branch coverage
complete pytest suite
sdist and wheel build
Twine validation
archive verification
isolated wheel smoke
Linux / Windows / macOS
Python 3.11 / 3.12 / 3.13 / 3.14
```

Benchmarks must separately report:

- elapsed time;
- peak estimated and observed memory where available;
- target count;
- event count;
- replicate count;
- chunk size;
- `n_jobs`;
- backend;
- asset reuse;
- support domain.

Performance thresholds are not hard CI gates until stable runners and variance analysis are
available. Correctness, deterministic task identity, and memory rejection are CI gates.

## 18. Deliberate exclusions

Version 0.0.16 does not implement:

- simultaneous confidence bands;
- BCa, bootstrap-t, basic, smoothed, Bayesian, wild, or block bootstrap;
- debiased or undersmoothed KDE inference;
- arbitrary weighted-event bootstrap;
- uncertainty in exposure fields;
- unconditional Poisson event-count uncertainty;
- adaptive or independently selected relative-risk bandwidths;
- replicate-wise bandwidth reselection;
- asymptotic tolerance contours;
- global rank envelopes;
- pointwise significance maps;
- non-Poisson separability p-values;
- block permutation, stochastic reconstruction, or HSIC tests;
- process pools, Dask, Ray, or distributed execution;
- GPU execution;
- approximate nearest-neighbour or approximate kernel summation;
- Zarr/PostGIS storage;
- disk-backed replicate matrices;
- persistence-schema changes.

## 19. Implementation order

### Subunit 01: deterministic execution foundation

1. implement immutable `ExecutionPlan`;
2. implement conservative chunk-resolution helpers;
3. integrate the plan with `SpatialKDE` while preserving legacy `chunk_size`;
4. integrate ordinary space-time target chunking;
5. integrate network and network-time chunk contracts without changing numerical kernels;
6. add sequential/thread target-chunk execution with fixed output slices;
7. add equivalence, budget, ordering, and metadata tests;
8. add an execution guide, API page, benchmark, and progress handoff;
9. run complete CI.

### Subunit 02: field ensembles and bootstrap uncertainty

1. implement `BootstrapPlan` and seed ledger;
2. implement `FieldEnsemble`, `PointwiseInterval`, and `BootstrapResult`;
3. implement user-supplied ensemble validation first;
4. implement closed fixed-bandwidth bootstrap adapters;
5. add `bootstrap_kde` across the four domains;
6. add fixed-exposure event-rate bootstrap;
7. add stratified case-control relative-risk bootstrap;
8. add examples, docs, analytical tests, and progress handoff;
9. run complete CI.

### Subunit 03: separability diagnostics and Poisson permutation

1. implement product-support adapters;
2. implement measured marginalization and separable reconstruction;
3. implement TV and squared-Hellinger diagnostics;
4. implement `SeparabilityDiagnostic` exports;
5. implement deterministic event-time permutation;
6. implement plus-one Monte Carlo p-values;
7. implement `SeparabilityTestResult`;
8. add ordinary space-time and network-time examples and tests;
9. add docs and progress handoff;
10. run complete CI.

### Final release unit

1. freeze public names and signatures;
2. add top-level exports only for complete APIs;
3. map every new top-level symbol to executable examples;
4. update README, roadmap, changelog, docs, and installed-wheel smoke;
5. bump version from `0.0.15` to `0.0.16`;
6. create `HANDOFF_0.0.16_UNCERTAINTY_SEPARABILITY_SCALABLE.md`;
7. run the full repository matrix;
8. audit the PR, mark ready, merge, and record actual merge evidence.

## 20. Exact next development unit

The next unit is **Subunit 01: deterministic execution foundation** only.

Do not begin bootstrap or separability code until:

- `ExecutionPlan` is immutable and fingerprinted;
- memory-budget chunk resolution is analytically tested;
- existing estimator outputs are unchanged;
- sequential and threaded target-chunk execution have deterministic task identity;
- legacy chunk parameters remain compatible;
- complete CI succeeds;
- `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md` is created.
