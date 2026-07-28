# Empirical bootstrap uncertainty

pyKDEX 0.0.16 is developing a closed ordinary-bootstrap framework for measured KDE fields.
The currently implemented estimator adapters are:

```text
SpatialEvents + GridSupport + SpatialKDE
NetworkWorkspace + NetworkKDE
```

Both adapters keep the observed event count fixed, resample event identities with replacement,
refit the same fixed estimator contract, store the complete replicate ensemble, and report
pointwise percentile intervals. They do not model unconditional Poisson count uncertainty.

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

The public spatial keyword name `events=` remains supported.

## Radial network example

Network bootstrap starts from a prepared `NetworkWorkspace`. Resampling happens **after
snapping** and therefore does not repeat geometry matching or change the accepted/rejected
snap audit.

```python
from pykdex import NetworkKDE, NetworkWorkspace, SpatialEvents, load_t_junction
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde

network = load_t_junction().network
events = SpatialEvents.from_array(
    [[-0.75, 0.0], [0.5, 0.0], [0.0, 0.75]],
    crs=network.crs,
    spatial_unit=network.spatial_unit,
)
workspace = NetworkWorkspace.prepare(
    network,
    events,
    lixel_length=0.1,
    max_snap_distance=0.05,
).with_event_lixel_distances(cutoff=0.8)

result = bootstrap_kde(
    NetworkKDE(
        bandwidth=0.8,
        kernel="epanechnikov",
        junction_policy="simple",
        target="density",
    ),
    workspace,
    plan=BootstrapPlan(
        n_resamples=999,
        confidence_level=0.95,
        random_state=20260728,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=512 * 1024 * 1024,
            target_chunk_size=100,
            replicate_chunk_size=4,
            n_jobs=4,
            backend="thread",
        ),
    ),
)
```

The radial network adapter supports the built-in `simple`, `discontinuous`, and
`continuous` junction policies. `HeatNetworkKDE` is not part of this adapter.

## Network resampling semantics

For every network replicate, pyKDEX:

1. draws accepted snapped-event indices with replacement;
2. creates a new immutable `NetworkEvents` object with unique replicate-local IDs;
3. preserves edge indices, offsets, snapped and original coordinates, snap distances,
   statuses, marks, CRS, units, and the network fingerprint;
4. preserves the original rejected-event table and snapping parameters;
5. retains sampled accepted-event indices and source fingerprints in provenance;
6. reuses the exact network and lixel support;
7. builds a fresh `NetworkKDE` with the same fixed contract.

The source workspace and supplied estimator are never mutated.

### Prepared distance assets

Where mathematically valid, prepared assets are reindexed rather than recomputed:

- event-to-lixel assets are reindexed along the event/source axis;
- event-to-event assets are reindexed along both source and target event axes;
- duplicate bootstrap selections create duplicate logical rows and columns with the same
  underlying distances;
- network, weight, direction, cutoff, target identity, and support identity remain fixed.

Path-based junction policies do not use shortest-path distance assets for evaluation. Their
propagation traces are rebuilt from the resampled accepted events while the network and support
remain fixed.

## Fixed estimator contracts

The built-in spatial adapter requires:

- immutable `SpatialEvents`;
- exact `GridSupport`;
- unit event weights;
- a finite positive numeric scalar bandwidth;
- built-in kernel, metric, and boundary-correction string names;
- fixed optional boundary and fixed density/intensity target.

The built-in radial network adapter requires:

- a valid `NetworkWorkspace` with accepted snapped events;
- unit accepted-event weights;
- a finite positive numeric scalar network bandwidth;
- built-in kernel and junction-policy string names;
- fixed target, directedness, coefficient tolerance, record limit, network, and lixels;
- no bandwidth selection inside replicates.

Custom estimator components, bandwidth selectors, adaptive bandwidths, arbitrary callbacks,
changing support, and weighted built-in resampling are rejected.

## Deterministic random streams

All child random streams are created from NumPy `SeedSequence` in logical replicate order
before work is scheduled. Each replicate has a stable spawn key and uses `PCG64`.

Consequently replicate `b` does not change when the user changes:

- worker count;
- sequential versus thread execution;
- target chunk size;
- replicate chunk size; or
- worker completion order.

When `random_state=None`, generated root entropy is retained in `result.seed_metadata` and can
be used to replay the run.

## Pointwise percentile intervals

The returned `BootstrapResult` contains:

```text
result.ensemble
result.interval
result.plan
result.seed_metadata
result.metadata
```

The default `PointwiseInterval` stores lower and upper empirical pointwise percentiles, the
observed estimate, replicate standard error with `ddof=1`, empirical bias, confidence level,
and `method="percentile"`.

These are pointwise intervals, not simultaneous confidence bands. They do not provide
family-wise coverage over the entire grid or network.

## Complete replicate storage and memory

`FieldEnsemble` stores the complete `(B, M)` replicate matrix. Streaming quantiles and
disk-backed ensembles are not implemented.

Before scheduling, the adapters account for the full ensemble and conservative per-worker
working storage. Network bootstrap additionally accounts for accepted-event arrays, lixel
arrays, prepared distance assets, reconstructed workspace assets, output fields, and a hard
propagation-record upper bound for path-based policies. If fixed overhead or one replicate
cannot fit, the operation raises `MemoryError` before replicate scheduling.

The outer layer may parallelize independent replicate ranges. Each inner estimator runs with
one worker so replicate-level and target-level thread pools are not nested.

## Fail-fast behaviour

A failed replicate is never silently removed. The first replicate-chunk exception aborts the
operation and no partial `BootstrapResult` is returned.

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

Network results also record the source workspace fingerprint, network fingerprint, junction
policy, directedness, and replicate workspace fingerprints.

## Current exclusions

The current built-in bootstrap does not include:

- heat-equation, space-time, or network-time adapters;
- event-rate or relative-risk bootstrap;
- weighted, smoothed, parametric, Bayesian, block, or wild bootstrap;
- adaptive bandwidth uncertainty or replicate-wise bandwidth selection;
- basic, bootstrap-t, BCa, or simultaneous intervals;
- streaming or approximate quantiles;
- uncertain exposure;
- separability diagnostics or permutation tests.
