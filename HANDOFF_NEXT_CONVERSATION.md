# pyKDEX current handoff

The latest merged release is **0.0.15**. Active development is pyKDEX **0.0.16** on Draft
PR #16. The following development subunits are complete on the branch:

1. deterministic memory-bounded execution;
2. common ordinary-Bootstrap plan, seed, ensemble, interval, and replicate execution;
3. spatial ordinary Bootstrap;
4. radial network ordinary Bootstrap;
5. heat-equation network ordinary Bootstrap.

The exact next implementation unit is ordinary Bootstrap for `SpatiotemporalKDE` only.

## Read these records in order

1. `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`;
2. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
3. `HANDOFF_0.0.16_DESIGN_UNCERTAINTY_SEPARABILITY_SCALABLE.md`;
4. `HANDOFF_0.0.16_DESIGN_VALIDATION.md`;
5. `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md`;
6. `HANDOFF_0.0.16_PROGRESS_02A_BOOTSTRAP_FOUNDATION.md`;
7. `HANDOFF_0.0.16_PROGRESS_02B_SPATIAL_BOOTSTRAP.md`;
8. `HANDOFF_0.0.16_PROGRESS_02C_NETWORK_BOOTSTRAP.md`;
9. `HANDOFF_0.0.16_PROGRESS_02D_HEAT_BOOTSTRAP.md`.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- stable base: pyKDEX `0.0.15` on `main`;
- base commit: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: `#16 Develop pyKDEX 0.0.16 uncertainty, separability, and scalable execution`;
- package version remains `0.0.15`;
- PR remains open, Draft, and unmerged;
- no 0.0.16 top-level provisional exports;
- public execution namespace: `pykdex.execution`;
- public uncertainty namespace: `pykdex.uncertainty`;
- exact next unit: `SpatiotemporalEvents + SpatiotemporalKDE` ordinary Bootstrap.

Always inspect the current PR head and latest CI once before continuing. Documentation and handoff
commits may follow the validated numerical implementation head.

## Completed subunit 01: deterministic execution

Public object:

```text
ExecutionPlan
```

Integrated estimators:

```text
SpatialKDE
SpatiotemporalKDE
NetworkKDE: simple, discontinuous, continuous
TemporalNetworkKDE
HeatNetworkKDE: global-solver budget audit
```

Rules that must not change:

- execution chunks and workers are operational, not statistical;
- source-event reduction order remains stable;
- output slices are fixed before scheduling;
- explicit memory budgets fail before large work allocations;
- heat evolution must not expose fake target threading.

Clean execution implementation head `cef94f9b26c3faab6aaeab85dadf0740bcc34078` passed
CI #281 (`30369196085`).

## Completed subunit 02A: Bootstrap foundation

Dedicated-namespace objects:

```text
BootstrapPlan
BootstrapResult
FieldEnsemble
PointwiseInterval
pointwise_percentile_interval
bootstrap_kde
```

Core rules:

- ordinary event Bootstrap only;
- complete replicate storage;
- NumPy `SeedSequence`/`PCG64` streams assigned by logical replicate;
- replicate identity independent of workers and chunks;
- one exact measured support and validity mask;
- pointwise percentile intervals only;
- fail-fast, no partial ensemble;
- no process pool, distributed scheduler, streaming quantiles, or disk-backed ensemble.

Clean foundation head `b9d5110f7ea1879311b4edcdbd588a18c5662ca3` passed
CI #314 (`30374221919`).

## Completed subunit 02B: spatial Bootstrap

Closed domain:

```text
SpatialEvents + GridSupport + SpatialKDE -> bootstrap_kde
```

Rules:

- unit weights;
- fixed positive numeric scalar bandwidth;
- built-in kernel, metric, and correction string names;
- fixed optional boundary and exact `GridSupport`;
- observed event count fixed;
- new unique replicate IDs and source-index provenance;
- fresh estimator per observed and replicate fit;
- complete ensemble and kernel working memory audited;
- outer replicate threading and inner sequential target evaluation;
- public `events=` keyword retained.

Clean spatial implementation head `957c8551744f52a642103e83c91f1fdb2159f305` passed
CI #332 (`30376591895`). Guide/API/example head
`b18dea683cd4de29ad80bf705fcb6261f06d2fef` passed CI #335 (`30377065654`). Final
02B handoff state passed CI #339 (`30378427092`).

## Completed subunit 02C: radial network Bootstrap

Closed domain:

```text
NetworkWorkspace + NetworkKDE -> bootstrap_kde
```

Supported policies:

```text
simple
discontinuous
continuous
```

Rules:

- resample accepted snapped-event identities after snapping;
- condition on accepted-event count and snapping/rejection outcome;
- preserve exact network, lixels, CRS, units, direction, and audit;
- unit weights and fixed positive numeric scalar bandwidth;
- built-in kernel and junction-policy names;
- event-to-lixel assets reindexed on the event axis;
- event-to-event assets reindexed on both event axes;
- path traces rebuilt from sampled snapped events;
- outer replicate threading, inner sequential estimator execution;
- hard propagation-record memory upper bound;
- source estimator and workspace unchanged.

Final 02C handoff state passed CI #354 (`30380511733`).

## Completed subunit 02D: heat-network Bootstrap

Closed domain:

```text
NetworkWorkspace + HeatNetworkKDE -> bootstrap_kde
```

Statistical boundary:

- ordinary accepted snapped-event resampling after snapping;
- accepted-event count and rejection audit fixed;
- exact network and lixel support fixed;
- unit accepted-event weights;
- fixed numeric scalar diffusion time;
- fixed mesh size, target, and negative tolerance;
- no heat-time selector or replicate-wise selection;
- fresh global finite-element operator and heat solve per replicate;
- pointwise percentile intervals conditional on observed accepted-event count.

Finite-element and solver rules:

- a replicate samples only observed offsets, so replicate DOFs cannot exceed source DOFs;
- source DOFs at most 1024 use fixed dense symmetric eigendecomposition;
- source DOFs above 1024 force a fixed sparse `expm_multiply` route;
- the solver route may not change across replicates;
- radial distance assets are not copied because heat estimation does not consume them;
- source and replicate compute-plan fingerprints are retained.

Execution and memory:

- outer replicate ranges may be threaded;
- each inner heat estimator is sequential and globally unchunked;
- `target_chunk_size` is explicitly rejected;
- complete ensemble, reconstructed events, finite-element operator, generator, spectral state,
  numerical arrays, and conservative solver temporary storage are budgeted per concurrent worker;
- too-small budgets fail before replicate scheduling;
- source estimator and source workspace remain unchanged.

Clean implementation head:

```text
c8f6760d7115c8f725c0e734e04f5c749cf74fbf
```

CI #360 (`30382166566`) passed quality, strict documentation, full tests, branch coverage,
distributions, installed-wheel smoke, Linux, Windows, macOS, and Python 3.11-3.14.

The later guide, example, handoff, and navigation head requires its own final CI inspection.

## Exact next unit: 02E ordinary space-time Bootstrap

Implement only:

```text
SpatiotemporalEvents + SpatiotemporalKDE + exact measured product support
```

Required contract:

1. sample complete event identities with replacement;
2. keep each event's spatial coordinates and time paired as one sampled record;
3. preserve observed event count;
4. create new unique replicate-local IDs;
5. retain sampled source indices and source fingerprint in provenance;
6. require unit weights;
7. require fixed positive numeric scalar spatial and temporal bandwidths;
8. preserve fixed spatial and temporal kernels, metric, optional boundary correction, target,
   time domain, cyclic period/origin, and exact product support;
9. reject selectors, adaptive arrays, matrices, balloon bandwidths, arbitrary support, and
   weighted built-in resampling;
10. keep outer replicate scheduling separate from inner sequential target-chunk execution;
11. preserve logical seed/result identity across workers, target chunks, and replicate chunks;
12. preflight the complete ensemble, reconstructed events, support, spatial/temporal kernel
    blocks, and concurrent outputs;
13. test linear and cyclic time, paired identity, manual reconstruction, support identity,
    scheduling, memory failure, and source immutability;
14. generate `HANDOFF_0.0.16_PROGRESS_02E_SPATIOTEMPORAL_BOOTSTRAP.md` and pass full CI.

Time permutation is not ordinary Bootstrap. It belongs to the later explicitly Poisson
first-order separability test.

## Do not begin during 02E

- temporal-network Bootstrap;
- fixed-exposure event-rate Bootstrap;
- case-control relative-risk Bootstrap;
- separability diagnostics;
- permutation p-values;
- weighted or adaptive built-in Bootstrap;
- bandwidth selection inside replicates;
- BCa, bootstrap-t, basic, or simultaneous intervals;
- uncertain exposure;
- streaming or disk-backed ensembles;
- persistence changes;
- package version bump;
- ready-for-review transition or merge.

## Recovery checklist

1. Inspect PR #16, current head, changed files, and latest CI once.
2. Confirm PR is open, Draft, unmerged, and version remains `0.0.15`.
3. Confirm temporary workflows and diagnostic logs are absent.
4. Read all nine required records.
5. Preserve execution, seed ordering, exact support, and fail-fast contracts.
6. Implement only ordinary `SpatiotemporalKDE` Bootstrap.
7. Generate the 02E root and docs handoff after full CI.
8. Do not move to temporal-network or risk-derived Bootstrap before 02E closes.
