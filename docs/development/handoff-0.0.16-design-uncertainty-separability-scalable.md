# 0.0.16 design handoff: uncertainty, separability, and scalable execution

The complete engineering design is:

```text
docs/development/design-0.0.16-uncertainty-separability-scalable.md
```

The durable recovery record is:

```text
HANDOFF_0.0.16_DESIGN_UNCERTAINTY_SEPARABILITY_SCALABLE.md
```

## Status

- latest merged version: `0.0.15`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- design complete;
- numerical implementation not started;
- package version remains `0.0.15`;
- no provisional 0.0.16 top-level exports exist.

## Ordered release units

```text
01 deterministic execution foundation
02 empirical bootstrap uncertainty
03 first-order separability diagnostic and Poisson permutation test
```

Execution comes first so later bootstrap and permutation replicates share one deterministic
seed, chunk, memory, worker, output-order, and audit contract.

## Execution foundation

The provisional immutable `ExecutionPlan` controls conservative memory budgets, target and
replicate chunks, worker count, and an explicit sequential or thread backend.

Only independent target chunks or independent resampling replicates may run concurrently.
Source-event reductions remain in stable order. Existing `chunk_size` and
`time_chunk_size` arguments remain compatible, and numerical defaults do not change when
no plan is supplied.

Dask, Joblib, Ray, process pools, distributed schedulers, GPU execution, and approximate
kernels remain excluded.

## Bootstrap boundary

The first uncertainty implementation uses full exact-support replicate ensembles and
explicit pointwise percentile intervals. It does not claim simultaneous confidence bands.

Built-in resampling is restricted to unit weights, fixed scalar bandwidths, fixed support,
and fixed estimator contracts. Event-rate exposure is fixed. Relative-risk cases and
controls are resampled independently within group.

## Separability boundary

First-order diagnostics require complete product support:

```text
SpatiotemporalGridSupport
ArixelSupport
```

The measured joint density is compared with the product of its measured spatial/network
and temporal marginals using total variation and squared Hellinger distance.

The initial permutation test is explicitly conditional on `assumption="poisson"`: event
locations remain fixed and observed event times are permuted. Its finite Monte Carlo
p-value uses the plus-one rule. No non-Poisson p-value, local significance map, or global
envelope is implemented.

## Exact next unit

Implement only the deterministic execution foundation and create:

```text
HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md
```

Bootstrap and separability implementation must wait until the execution unit passes the
complete repository CI matrix.
