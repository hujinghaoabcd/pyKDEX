# pyKDEX current handoff

The latest merged release is **0.0.15**. Active development is the **0.0.16 design and
execution-foundation phase**.

Read these records in order:

1. `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`;
2. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
3. `HANDOFF_0.0.16_DESIGN_UNCERTAINTY_SEPARABILITY_SCALABLE.md`.

## Current state

- repository: `hujinghaoabcd/pyKDEX`;
- stable base: pyKDEX `0.0.15` on `main`;
- base commit: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- detailed design commit: `fc6d62bef0abed166c8674dc58275657568eab62`;
- root design-handoff commit: `fd00faac75362bb0710ab146ad8ccb0c77b15c22`;
- numerical implementation: not started;
- package version: still `0.0.15`;
- provisional 0.0.16 top-level exports: none;
- merge: not merged;
- exact next unit: deterministic execution foundation.

Do not bump the package version or expose provisional API names during the design or first
progress subunit.

## 0.0.16 fixed architecture

The version is split into three ordered subunits:

```text
01 deterministic execution foundation
02 empirical bootstrap uncertainty
03 first-order separability diagnostic and Poisson permutation test
```

The order is mandatory. Bootstrap and permutation must share the execution foundation's
seed, chunk, memory, worker, ordering, and audit contracts.

## Subunit 01 contract

Implement immutable `ExecutionPlan` with conservative memory-budget chunk resolution.
Initial execution backends are restricted to:

```text
sequential
thread
```

Only independent target chunks may execute concurrently in this subunit. Source-event
reductions remain in stable source order. Completed work is written into fixed output
slices by logical chunk index.

Changing target chunk size or `n_jobs` must not change the statistical estimate. Exact
bitwise equality across operating systems and BLAS implementations is not promised;
numerical equivalence uses explicit repository tolerances.

Existing estimator parameters remain compatible:

```text
SpatialKDE.chunk_size
SpatiotemporalKDE.chunk_size
TemporalNetworkKDE.time_chunk_size
```

A legacy explicit chunk and a conflicting explicit `ExecutionPlan` chunk must raise an
error. Existing defaults remain unchanged when no plan is supplied.

Execution metadata is retained for audit but is excluded from statistical estimator
compatibility and asset-cache identity.

## Future bootstrap boundary

After Subunit 01 is fully validated, Subunit 02 may add:

```python
BootstrapPlan
FieldEnsemble
PointwiseInterval
BootstrapResult
bootstrap_kde
bootstrap_event_rate
bootstrap_relative_risk
```

The initial built-in bootstrap is deliberately restricted to unit weights, fixed scalar
bandwidths, fixed support, and fixed estimator contracts. Bandwidth reselection, adaptive
bandwidths, matrices, balloon bandwidths, and arbitrary weighted-event bootstrap are
excluded.

`bootstrap_event_rate` treats exposure as fixed. `bootstrap_relative_risk` independently
resamples cases and controls within their groups and defaults to log-risk pointwise
percentile intervals.

Pointwise intervals are not simultaneous confidence bands.

## Future separability boundary

After the bootstrap execution infrastructure is validated, Subunit 03 may add descriptive
first-order separability diagnostics on complete product supports only:

```text
SpatiotemporalGridSupport
ArixelSupport
```

The measured reconstruction is:

```text
p_space_i = sum_j p_ij * dt_j
p_time_j  = sum_i p_ij * a_i
p_sep_ij  = p_space_i * p_time_j
```

Primary scalar diagnostics are total variation and squared Hellinger distance.

The initial test is explicitly `assumption="poisson"`: keep locations fixed and permute
observed event times. Its right-tail Monte Carlo p-value is:

```text
p = (1 + count(T_b >= T_observed)) / (B + 1)
```

This test must not claim validity for a general clustered or inhibited non-Poisson process.
Block permutation, stochastic reconstruction, HSIC, local significance maps, and global
envelope tests are excluded.

## 0.0.16 execution exclusions

Do not add in Subunit 01:

- bootstrap or permutation code;
- process pools;
- Dask, Joblib, Ray, or distributed runtime dependencies;
- GPU or approximate kernels;
- parallel source-event reductions;
- disk or Zarr-backed arrays;
- PostGIS execution;
- persistence-schema changes;
- placeholder public exports.

## Exact next tasks

1. inspect every current chunking route and its peak live arrays;
2. design operation-specific conservative byte estimators;
3. implement immutable `ExecutionPlan` and fingerprint;
4. implement resolved private execution records;
5. integrate legacy chunk normalization;
6. integrate `SpatialKDE` first with exact sequential equivalence;
7. add thread execution over target chunks with fixed output order;
8. extend the same contract across ordinary space-time, network, and network-time families;
9. add budget, equivalence, ordering, metadata, and failure tests;
10. add an execution guide, API page, benchmark, and progress handoff;
11. create `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md`;
12. run the complete quality, typing, docs, coverage, distribution, wheel, and platform CI
    matrix.

## Recovery checklist

1. Inspect the branch, Draft PR if present, current head, and live CI.
2. Confirm package version remains `0.0.15`.
3. Confirm no provisional 0.0.16 top-level exports exist.
4. Read the detailed design and root design handoff in full.
5. Preserve the single NumPy/SciPy numerical route and current estimator defaults.
6. Begin only the deterministic execution foundation.
7. Do not start bootstrap or separability implementation before Subunit 01 passes complete
   CI and receives its root progress handoff.
