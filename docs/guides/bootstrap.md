# Empirical bootstrap uncertainty

pyKDEX 0.0.16 introduces an empirical ordinary-bootstrap foundation for measured KDE
fields. The current implemented adapter is deliberately restricted to spatial KDE:

```text
SpatialEvents + GridSupport + SpatialKDE
```

Other domains and risk-derived fields are added in later development units.

## Spatial example

```python
from pykdex import GridSupport, SpatialEvents, SpatialKDE
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde

events = SpatialEvents.from_array(
    [[0.2, 0.2], [0.8, 0.7], [1.5, 0.4]],
    spatial_unit="km",
)
support = GridSupport.from_bounds(
    (0.0, 0.0, 2.0, 1.0),
    resolution=0.25,
    spatial_unit="km",
)

result = bootstrap_kde(
    SpatialKDE(
        bandwidth=0.5,
        kernel="epanechnikov",
        metric="euclidean",
        target="density",
    ),
    events,
    support,
    plan=BootstrapPlan(
        n_resamples=999,
        confidence_level=0.95,
        random_state=20260728,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=512 * 1024 * 1024,
            target_chunk_size=250,
            replicate_chunk_size=8,
            n_jobs=4,
            backend="thread",
        ),
    ),
)

lower = support.reshape(result.interval.lower)
estimate = support.reshape(result.interval.estimate)
upper = support.reshape(result.interval.upper)
```

The returned object contains:

```text
result.ensemble
result.interval
result.plan
result.seed_metadata
result.metadata
```

## Statistical interpretation

`bootstrap_kde` performs ordinary event-identity resampling with replacement while keeping
the observed event count fixed. For every replicate it refits the same estimator contract
on the same measured support.

The interpretation is therefore conditional on the observed event count for both density
and intensity fields. The current implementation does not model unconditional Poisson
count uncertainty.

Duplicate sampled events remain duplicate events at the same location. This is different
from perturbing event coordinates or performing a smoothed bootstrap.

## Fixed estimator contract

The initial spatial adapter requires:

- immutable `SpatialEvents`;
- exact `GridSupport`;
- unit event weights;
- a finite positive numeric scalar bandwidth;
- built-in kernel, metric, and boundary-correction string names;
- a fixed optional `SpatialBoundary`;
- fixed density or intensity target;
- no bandwidth selection inside replicates.

It rejects:

- raw arrays and DataFrames;
- non-unit weights;
- bandwidth selectors;
- adaptive bandwidth vectors;
- bandwidth matrices;
- balloon bandwidths;
- custom kernel, metric, or correction objects;
- changing support or estimator configuration;
- arbitrary resampling callbacks.

A fitted source estimator may be supplied, but bootstrap reads only its configuration. It
does not mutate the fitted object or reuse its fitted numerical state.

## Deterministic random streams

All child random streams are created from NumPy `SeedSequence` in logical replicate order
before work is scheduled. Each replicate has a stable spawn key and uses `PCG64`.

Consequently the replicate assigned to logical index `b` does not change when the user
changes:

- worker count;
- sequential versus thread execution;
- target chunk size;
- replicate chunk size; or
- worker completion order.

When `random_state=None`, generated root entropy is retained in `result.seed_metadata`, so
the run can be replayed from the recorded entropy.

## Replicate event identity

A bootstrap sample may select the same observed event multiple times. Every reconstructed
replicate receives new unique event IDs in replicate row order. The selected source-event
indices and original event fingerprint are retained in provenance.

This keeps event-container identity valid without losing the bootstrap sample audit trail.

## Pointwise percentile intervals

The default interval stores:

```text
lower
estimate
upper
standard_error
bias
confidence_level
method="percentile"
```

For confidence level `1 - alpha`, lower and upper are empirical pointwise quantiles at
`alpha / 2` and `1 - alpha / 2` for each grid cell.

These summaries are **pointwise percentile bootstrap intervals**. They are not simultaneous
confidence bands and do not provide family-wise coverage over the full field.

## Complete replicate storage

`FieldEnsemble` stores the full `(B, M)` replicate matrix in memory. Approximate streaming
quantiles and disk-backed ensembles are not implemented.

The Bootstrap memory resolver counts, before scheduling:

- the complete replicate matrix;
- observed field and validity mask;
- event and support arrays;
- one resampled event container per requested concurrent worker;
- one estimator target block per requested concurrent worker; and
- the active replicate-chunk result block.

If fixed overhead or one replicate cannot fit the requested budget, the operation raises
`MemoryError` before replicate scheduling.

## Fail-fast behaviour

A replicate failure is never silently removed. The first replicate-chunk exception aborts
the Bootstrap operation and no partial `BootstrapResult` is returned.

A future partial-ensemble policy would require a separate statistical and API design.

## Reproducibility metadata

Useful audit fields include:

```python
result.seed_metadata["root_entropy"]
result.seed_metadata["child_spawn_keys"]
result.ensemble.execution_metadata
result.ensemble.metadata["estimator_contract_fingerprint"]
result.ensemble.metadata["source_event_fingerprint"]
result.ensemble.metadata["support_fingerprint"]
result.ensemble.metadata["memory_model"]
```

The complete result, ensemble, interval, plan, support, estimator contract, and seed ledger
all have stable fingerprints.

## Current exclusions

The current adapter does not include:

- network, heat, space-time, or network-time bootstrap;
- event-rate or relative-risk bootstrap;
- weighted bootstrap;
- smoothed, parametric, Bayesian, block, or wild bootstrap;
- adaptive bandwidth uncertainty;
- replicate-wise bandwidth selection;
- basic, bootstrap-t, or BCa intervals;
- simultaneous bands;
- streaming or approximate quantiles;
- uncertain exposure;
- separability or permutation tests.
