# Empirical bootstrap uncertainty

pyKDEX 0.0.16 is developing a closed ordinary-bootstrap framework for measured KDE fields.
The currently implemented estimator adapters are:

```text
SpatialEvents + GridSupport + SpatialKDE
NetworkWorkspace + NetworkKDE
NetworkWorkspace + HeatNetworkKDE
SpatiotemporalEvents + SpatiotemporalGridSupport + SpatiotemporalKDE
NetworkTimeWorkspace + TemporalNetworkKDE
```

All adapters keep the observed event count fixed, resample complete event identities with
replacement, refit the same fixed estimator contract, store the complete replicate ensemble, and
report pointwise percentile intervals. They do not model unconditional Poisson count uncertainty.

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
`continuous` junction policies.

## Heat-equation network example

The heat adapter uses the same accepted snapped-event resampling boundary, but each replicate
builds a fresh finite-element operator and performs a fresh global heat solve.

```python
from pykdex import HeatNetworkKDE, NetworkWorkspace, SpatialEvents, load_t_junction
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde

network = load_t_junction().network
events = SpatialEvents.from_array(
    [[-0.75, 0.0], [0.5, 0.0], [0.0, 0.5]],
    crs=network.crs,
    spatial_unit=network.spatial_unit,
)
workspace = NetworkWorkspace.prepare(
    network,
    events,
    lixel_length=0.25,
    max_snap_distance=0.05,
)

result = bootstrap_kde(
    HeatNetworkKDE(
        diffusion_time=0.08,
        mesh_size=0.25,
        target="density",
    ),
    workspace,
    plan=BootstrapPlan(
        n_resamples=999,
        confidence_level=0.95,
        random_state=20260729,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=512 * 1024 * 1024,
            replicate_chunk_size=2,
            n_jobs=2,
            backend="thread",
        ),
    ),
)
```

Heat solves are global. `target_chunk_size` is therefore rejected rather than silently ignored.
Outer replicate ranges may use the thread backend, while every inner heat solve remains
sequential and unchunked.

## Spatiotemporal example

Ordinary space-time Bootstrap samples each observed location and time together as one event row.
It does not permute time independently of space.

```python
from pykdex import (
    CyclicTimeDomain,
    GridSupport,
    SpatiotemporalEvents,
    SpatiotemporalGridSupport,
    SpatiotemporalKDE,
)
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde

time_domain = CyclicTimeDomain(24.0)
events = SpatiotemporalEvents.from_arrays(
    [[0.25, 0.25], [1.0, 0.75], [1.75, 0.25]],
    [23.5, 0.5, 8.0],
    spatial_unit="km",
    temporal_unit="hours",
    time_domain=time_domain,
    temporal_origin="study-hour-zero",
    timezone="UTC",
)
spatial = GridSupport.from_bounds(
    (0.0, 0.0, 2.0, 1.0),
    resolution=0.5,
    spatial_unit="km",
)
support = SpatiotemporalGridSupport.from_spatial_grid(
    spatial,
    temporal_resolution=6.0,
    temporal_unit="hours",
    time_domain=time_domain,
    temporal_origin="study-hour-zero",
    timezone="UTC",
)

result = bootstrap_kde(
    SpatiotemporalKDE(
        spatial_bandwidth=0.7,
        temporal_bandwidth=2.0,
        spatial_kernel="epanechnikov",
        temporal_kernel="gaussian",
        target="density",
    ),
    events,
    support,
    plan=BootstrapPlan(
        n_resamples=999,
        confidence_level=0.95,
        random_state=20260729,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=512 * 1024 * 1024,
            target_chunk_size=64,
            replicate_chunk_size=2,
            n_jobs=2,
            backend="thread",
        ),
    ),
)
```

The built-in adapter requires the complete measured product-grid support
`SpatiotemporalGridSupport`. Arbitrary `SpatiotemporalPointSupport` is not accepted in the first
built-in release.

## Temporal-network example

Temporal-network Bootstrap begins from a prepared `NetworkTimeWorkspace`. It samples each
accepted snapped network location and its event time as one paired identity.

```python
from pykdex import (
    CyclicTimeDomain,
    NetworkTimeWorkspace,
    SpatialEvents,
    TemporalNetworkKDE,
    load_t_junction,
)
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde

network = load_t_junction().network
events = SpatialEvents.from_array(
    [[-0.75, 0.0], [0.5, 0.0], [0.0, 0.5]],
    crs=network.crs,
    spatial_unit=network.spatial_unit,
)
workspace = NetworkTimeWorkspace.prepare(
    network,
    events,
    [23.5, 0.5, 8.0],
    temporal_unit="hours",
    lixel_length=0.25,
    temporal_resolution=6.0,
    time_domain=CyclicTimeDomain(period=24.0),
    temporal_origin="study-hour-zero",
    timezone="UTC",
    max_snap_distance=0.05,
).with_distances(cutoff=0.8)

result = bootstrap_kde(
    TemporalNetworkKDE(
        spatial_bandwidth=0.8,
        temporal_bandwidth=2.0,
        junction_policy="simple",
        target="density",
    ),
    workspace,
    plan=BootstrapPlan(
        n_resamples=999,
        confidence_level=0.95,
        random_state=20260729,
        execution_plan=ExecutionPlan(
            memory_budget_bytes=512 * 1024 * 1024,
            target_chunk_size=2,
            replicate_chunk_size=2,
            n_jobs=2,
            backend="thread",
        ),
    ),
)
```

The exact measured support is `workspace.arixels`; a separate support argument is rejected.
Linear and cyclic time are supported. Ordinary Bootstrap never permutes event time
independently of snapped network location.

## Network resampling semantics

For every radial or heat-network replicate, pyKDEX:

1. draws accepted snapped-event indices with replacement;
2. creates a new immutable `NetworkEvents` object with unique replicate-local IDs;
3. preserves edge indices, offsets, snapped and original coordinates, snap distances,
   statuses, marks, CRS, units, and the network fingerprint;
4. preserves the original rejected-event table and snapping parameters;
5. retains sampled accepted-event indices and source fingerprints in provenance;
6. reuses the exact network and lixel support;
7. builds a fresh estimator with the same fixed contract.

The source workspace and supplied estimator are never mutated.

### Radial prepared distance assets

Where mathematically valid, radial prepared assets are reindexed rather than recomputed:

- event-to-lixel assets are reindexed along the event/source axis;
- event-to-event assets are reindexed along both source and target event axes;
- duplicate bootstrap selections create duplicate logical rows and columns with the same
  underlying distances;
- network, weight, direction, cutoff, target identity, and support identity remain fixed.

Path-based junction policies rebuild propagation traces from the resampled accepted events.

### Heat finite-element assets

Heat replicate workspaces do not propagate radial distance assets because the heat estimator does
not consume them. Each replicate instead:

- rebuilds the metric-graph finite-element operator from the sampled snapped offsets;
- preserves the exact network, lixel boundaries, mesh-size contract, and support fingerprint;
- preserves a fixed solver route across observed and replicate fields;
- performs a new global heat evolution and lixel cell-average evaluation.

A replicate can omit source-event offsets but cannot introduce a new offset. The source heat mesh
therefore provides a conservative upper bound on replicate degrees of freedom.

### Temporal-network factorized assets

A prepared temporal-network distance asset is factorized into event-to-lixel network
distances and time-to-event temporal offsets. For every replicate, pyKDEX:

- reindexes network-distance rows by sampled accepted-event identity;
- reindexes temporal-offset and temporal-distance columns by the same sampled identity;
- preserves target time rows, lixel columns, network, cutoff, directedness, and arixel
  support;
- rebuilds replicate event and base-workspace fingerprints;
- rebuilds propagation traces instead of reusing a distance asset for path-based policies.

Duplicate Bootstrap selections therefore create matching duplicate spatial rows and
temporal columns. Network location and time cannot become mispaired.

## Paired space-time resampling semantics

For every ordinary spatiotemporal replicate, pyKDEX:

1. draws complete source event-row indices with replacement;
2. selects spatial coordinates and time with the same sampled-index sequence;
3. selects optional marks with the same event identity;
4. preserves the observed event count;
5. creates new unique replicate-local IDs;
6. preserves coordinate names, CRS, spatial and temporal units, temporal origin, timezone, and
   exact `TimeDomain` fingerprint;
7. retains sampled source indices and the source event fingerprint in spatial, temporal, and joint
   provenance;
8. fits a fresh fixed-contract `SpatiotemporalKDE`;
9. evaluates the exact original measured spatial-grid-by-time-bin support.

Linear and cyclic time domains are supported. A cyclic replicate preserves the same period,
origin, timezone, and cyclic tail tolerance. No independent time permutation, cyclic phase shift,
or space-time reassignment occurs.

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

The built-in heat-network adapter requires:

- an undirected valid `NetworkWorkspace` with accepted snapped events;
- unit accepted-event weights;
- a finite positive numeric scalar diffusion time;
- fixed optional mesh size, target, and negative-roundoff tolerance;
- fixed network and lixel support;
- no heat-time selection inside replicates;
- global, sequential, unchunked inner solves.

The built-in spatiotemporal adapter requires:

- immutable `SpatiotemporalEvents`;
- exact `SpatiotemporalGridSupport`;
- unit event weights;
- finite positive numeric scalar spatial and temporal bandwidths;
- built-in spatial-kernel, temporal-kernel, and spatial-metric string names;
- fixed density/intensity target and cyclic tail tolerance;
- exact spatial dimension, CRS, spatial unit, temporal unit, temporal origin, timezone, and
  time-domain compatibility;
- paired spatial-time event-row resampling;
- no bandwidth selection inside replicates.

The built-in temporal-network adapter requires:

- a valid `NetworkTimeWorkspace` with accepted snapped events;
- exact measured `ArixelSupport` from the workspace;
- unit accepted-event weights;
- finite positive numeric scalar spatial and temporal bandwidths;
- built-in spatial-kernel, temporal-kernel, and junction-policy string names;
- fixed target, direction, cyclic-tail tolerance, coefficient tolerance, and record limit;
- paired snapped-location-time event-identity resampling;
- no bandwidth strategy or selection inside replicates.

Custom estimator components, selectors, adaptive bandwidths, arbitrary callbacks, changing
support, and weighted built-in resampling are rejected.

## Deterministic random streams

All child random streams are created from NumPy `SeedSequence` in logical replicate order before
work is scheduled. Each replicate has a stable spawn key and uses `PCG64`.

Consequently replicate `b` does not change when the user changes:

- worker count;
- sequential versus thread replicate execution;
- replicate chunk size;
- worker completion order;
- target chunk size for adapters that support target chunking.

When `random_state=None`, generated root entropy is retained in `result.seed_metadata` and can be
used to replay the run.

Target and replicate chunks are execution controls, not statistical parameters. Observed
space-time field fingerprints deliberately exclude execution metadata.

## Fixed-exposure event-rate Bootstrap

`bootstrap_event_rate` transforms a completed intensity Bootstrap on an exact measured
support using one fixed `ExposureField`:

```python
from pykdex.risk import ExposureField
from pykdex.uncertainty import bootstrap_event_rate

exposure = ExposureField.from_density(
    exposure_density,
    intensity_bootstrap.ensemble.support,
    exposure_unit="person",
)
rate_bootstrap = bootstrap_event_rate(
    intensity_bootstrap,
    exposure,
    event_unit="event",
    zero_policy="raise",
)
```

The source must be a completed `bootstrap_kde` result with
`field_family="intensity"`. Probability-density ensembles are rejected because density has
discarded total event mass.

For every replicate and valid support element, the transformation is:

```text
event_rate = event_intensity / effective_exposure_density
```

Exposure is applied identically to the observed intensity and every replicate. It is not
resampled. The returned intervals therefore describe event-resampling uncertainty
**conditional on fixed exposure** and do not include uncertainty in population,
person-time, traffic volume, monitoring effort, or another exposure measurement.

### Exact support and supported families

The exposure and source ensemble must share the exact measured-support fingerprint. The
transformation supports completed intensity ensembles on:

```text
GridSupport
LixelSupport
measured SpatiotemporalPointSupport
SpatiotemporalGridSupport
ArixelSupport
```

Built-in Bootstrap estimator adapters currently generate the spatial-grid, network-lixel,
spatiotemporal-grid, and network-time-arixel families.

### Explicit denominator policy

The same denominator policy used by deterministic event-rate fields is retained:

- `raise` rejects exposure at or below `validity_threshold`;
- `nan` marks those support columns invalid in observed, replicate, and interval arrays;
- `minimum` applies only the user-supplied positive `minimum_denominator` and keeps adjusted
  cells valid.

No hidden epsilon, pseudocount, or undocumented clipping rule is introduced. The output
validity mask combines the source intensity validity mask with finite effective exposure.

### Seed, identity, and memory

No KDE is refitted and no new random stream is created. The source Bootstrap plan, seed
ledger, logical replicate order, confidence level, and estimator-family label are retained.

Derived observed and replicate fingerprints combine source intensity identity, fixed
exposure, denominator policy, event unit, and exact support. The optional transformation
memory budget is operational and does not change statistical identity.

`memory_budget_bytes` is explicit and separate from the earlier KDE execution budget. The
preflight peak includes the resident source intensity ensemble, exposure and denominator
state, and the complete event-rate output ensemble. Insufficient budgets fail before the
complete output matrix is allocated.

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
observed estimate, replicate standard error with `ddof=1`, empirical bias, confidence level, and
`method="percentile"`.

These are pointwise intervals, not simultaneous confidence bands. They do not provide family-wise
coverage over the entire grid, network, or space-time product field.

## Complete replicate storage and memory

`FieldEnsemble` stores the complete `(B, M)` replicate matrix. Streaming quantiles and disk-backed
ensembles are not implemented.

Before scheduling, the adapters account for the full ensemble and conservative per-worker working
storage. Radial network Bootstrap includes accepted-event arrays, lixels, prepared assets,
reconstructed workspaces, output fields, kernel arrays, and a hard propagation-record upper bound.
Heat Bootstrap includes reconstructed snapped events, the global finite-element operator,
generator, stored spectral state where applicable, numerical work arrays, output fields, and an
additional conservative solver-temporary allowance for every requested concurrent replicate.
Spatiotemporal Bootstrap includes source coordinates and times, the complete product support,
reconstructed paired events, full replicate outputs, and target-chunk spatial and temporal
kernel-distance working blocks for every requested concurrent worker. Temporal-network Bootstrap additionally includes reconstructed paired snapped events, factorized network and time assets, propagation bounds, spatial matrices, and temporal-kernel blocks.

If fixed overhead or one replicate cannot fit, the operation raises `MemoryError` before replicate
scheduling. Each inner estimator uses one worker, so outer replicate and inner estimator thread
pools are not nested.

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

Network results record source and replicate workspace fingerprints. Heat results additionally
record the fixed solver route, dense threshold, source and replicate heat-compute-plan
fingerprints, and the source-mesh DOF upper bound. Spatiotemporal results record the exact time
domain, temporal origin, timezone, and paired-event resampling unit. Temporal-network results additionally record the exact arixel support, paired snapped-location-time resampling unit, and replicate workspace fingerprints.

## Relative-risk compatibility metadata

Every completed KDE Bootstrap result and ensemble now records an immutable normalized
compatibility mapping:

```text
relative_risk_contract
relative_risk_contract_fingerprint
```

The mapping is not a relative-risk estimate. It is an auditable prerequisite used to decide
whether independently generated case and control density ensembles share the same fixed
estimator and exact measured support.

All families use the common keys:

```text
schema_version
result_family
support_fingerprint
target
bandwidths
```

Family-specific fields describe kernels, metric or junction policy, boundary identity,
direction, network identity, heat policy, time domain, and cyclic-tail choices where
relevant.

The contract deliberately excludes event data, sample size, numerical fields, seed
metadata, workers, chunks, memory budgets, and completion order. Consequently case and
control groups with different observations can remain compatible, while a meaningful
smoothing or support difference changes the contract fingerprint.

The mapping is read-only. A standard dictionary view can be serialized for audit:

```python
contract = result.metadata["relative_risk_contract"]
serializable = dict(contract)
```

The pre-existing estimator contract fingerprint remains available and unchanged. The
normalized relative-risk contract exists specifically for cross-group compatibility and
human-readable mismatch diagnostics.

## Current exclusions

The current built-in Bootstrap does not include:

- relative-risk Bootstrap;
- weighted, smoothed, parametric, Bayesian, block, or wild Bootstrap;
- adaptive bandwidth uncertainty or replicate-wise bandwidth/time selection;
- basic, bootstrap-t, BCa, or simultaneous intervals;
- streaming or approximate quantiles;
- uncertain exposure;
- separability diagnostics or permutation tests.
