# pyKDEX current handoff

The latest merged release is **0.0.15**. Active development is pyKDEX **0.0.16** on Draft
PR #16.

Completed development subunits:

1. deterministic memory-bounded execution;
2. common ordinary-Bootstrap plan, seed ledger, ensemble, interval, and replicate execution;
3. spatial ordinary Bootstrap;
4. radial network ordinary Bootstrap;
5. heat-equation network ordinary Bootstrap;
6. ordinary spatiotemporal Bootstrap on measured product grids.

The exact next implementation unit is ordinary Bootstrap for the existing temporal-network KDE
family. Do not begin risk-derived Bootstrap, separability diagnostics, or permutation testing
before the temporal-network unit is designed, implemented, documented, and validated.

## Read these records in order

1. `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`;
2. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
3. `HANDOFF_0.0.16_DESIGN_UNCERTAINTY_SEPARABILITY_SCALABLE.md`;
4. `HANDOFF_0.0.16_DESIGN_VALIDATION.md`;
5. `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md`;
6. `HANDOFF_0.0.16_PROGRESS_02A_BOOTSTRAP_FOUNDATION.md`;
7. `HANDOFF_0.0.16_PROGRESS_02B_SPATIAL_BOOTSTRAP.md`;
8. `HANDOFF_0.0.16_PROGRESS_02C_NETWORK_BOOTSTRAP.md`;
9. `HANDOFF_0.0.16_PROGRESS_02D_HEAT_BOOTSTRAP.md`;
10. `HANDOFF_0.0.16_PROGRESS_02E_SPATIOTEMPORAL_BOOTSTRAP.md`.

## Current repository state

- repository: `hujinghaoabcd/pyKDEX`;
- stable base: pyKDEX `0.0.15` on `main`;
- base commit: `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- active branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: `#16 Develop pyKDEX 0.0.16 uncertainty, separability, and scalable execution`;
- package version remains `0.0.15`;
- PR remains open, Draft, and unmerged;
- no provisional 0.0.16 top-level exports;
- public execution namespace: `pykdex.execution`;
- public uncertainty namespace: `pykdex.uncertainty`;
- exact next unit: temporal-network ordinary Bootstrap.

Inspect the current PR head, latest CI, and changed-file list once before continuing. Documentation
and handoff commits may follow a separately validated numerical implementation head.

## Completed subunit 01: deterministic execution

Public object:

```text
ExecutionPlan
```

Integrated estimator families:

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
- logical output slices are fixed before scheduling;
- memory budgets fail before large work allocations;
- heat evolution does not expose fake target threading;
- statistical fingerprints exclude operational execution choices.

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

- ordinary event-identity Bootstrap only;
- complete replicate storage;
- NumPy `SeedSequence`/`PCG64` streams assigned by logical replicate;
- replicate identity independent of workers and chunks;
- exact measured support and validity mask;
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
- unique replicate-local IDs and source-index provenance;
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
- preserve network, lixels, CRS, units, direction, and audit;
- unit weights and fixed numeric scalar bandwidth;
- built-in kernel and junction-policy names;
- event-to-lixel assets reindexed on the event axis;
- event-to-event assets reindexed on both event axes;
- path traces rebuilt from sampled snapped events;
- outer replicate threading and inner sequential estimator execution;
- hard propagation-record memory upper bound;
- source estimator and workspace unchanged.

Final 02C handoff state passed CI #354 (`30380511733`).

## Completed subunit 02D: heat-network Bootstrap

Closed domain:

```text
NetworkWorkspace + HeatNetworkKDE -> bootstrap_kde
```

Rules:

- resample accepted snapped-event identities after snapping;
- condition on accepted-event count and rejection audit;
- preserve exact network and lixel support;
- unit accepted-event weights;
- fixed numeric scalar diffusion time, mesh size, target, and negative tolerance;
- no heat-time selector or replicate-wise selection;
- fresh global finite-element operator and heat solve per replicate;
- replicate heat DOFs cannot exceed source heat DOFs;
- observed and replicate fields use one fixed dense or sparse solver route;
- radial distance assets are not copied because heat estimation does not consume them;
- outer replicate ranges may be threaded;
- inner heat solves are sequential and globally unchunked;
- `target_chunk_size` is rejected;
- full solver state and conservative temporary storage are budgeted per worker;
- source estimator and workspace remain unchanged.

Clean implementation head `c8f6760d7115c8f725c0e734e04f5c749cf74fbf` passed
CI #360 (`30382166566`). Final 02D documentation and restored design state
`9dbce9f5ee53ca95e261cbe960f9d541e27647b6` passed CI #370 (`30382721663`).

## Completed subunit 02E: ordinary spatiotemporal Bootstrap

Closed domain:

```text
SpatiotemporalEvents + SpatiotemporalKDE + SpatiotemporalGridSupport
    -> bootstrap_kde
```

Statistical rules:

- sample complete space-time event rows with replacement;
- use one sampled-index sequence for spatial coordinates, time, and optional marks;
- preserve observed event count;
- create unique replicate-local IDs;
- retain sampled source indices and source fingerprints in spatial, temporal, and joint
  provenance;
- require exact unit weights;
- require fixed numeric scalar spatial and temporal bandwidths;
- require built-in spatial-kernel, temporal-kernel, and spatial-metric string names;
- preserve fixed target and cyclic tail tolerance;
- preserve exact spatial dimension, CRS, spatial unit, temporal unit, temporal origin, timezone,
  and time-domain fingerprint;
- accept only exact measured `SpatiotemporalGridSupport`;
- reject `SpatiotemporalPointSupport` in the first built-in adapter;
- support linear and cyclic time without independently permuting time;
- time permutation remains reserved for the later separability null test.

Execution and memory:

- outer logical replicate ranges may be threaded;
- every inner `SpatiotemporalKDE` is sequential;
- caller target chunks remain operational memory controls;
- target and replicate chunks do not change observed statistical fingerprints or replicate rows;
- memory preflight includes the complete ensemble, source events, complete product support,
  reconstructed paired events, outputs, and spatial/temporal kernel working blocks;
- too-small budgets fail before replicate scheduling;
- source estimator remains unchanged.

Clean numerical implementation head:

```text
eb650cd371f1da7838103aad3e114d7d9d884949
```

CI #390 (`30386883100`) passed quality, strict documentation, full tests, branch coverage,
distributions, installed-wheel smoke, Linux, Windows, macOS, and Python 3.11-3.14.

The later example, guide, API, handoff, navigation, and PR-description commits require their own
final CI inspection.

## Exact next unit: 02F temporal-network Bootstrap

Before writing code, inspect:

```text
src/pykdex/network_time/
src/pykdex/estimators/temporal_network_kde.py
existing temporal-network tests and handoffs
```

Determine the exact current event and workspace types rather than guessing from names.

The next built-in adapter must:

1. resample complete accepted snapped-network-location-plus-time event identities after snapping;
2. use one sampled-index sequence for edge/offset/location fields and time;
3. preserve accepted-event count, rejection audit, network, lixels, arixel support, CRS, units,
   direction, time domain, origin, and timezone;
4. create unique replicate-local IDs and retain sampled source indices;
5. require unit weights;
6. require fixed numeric scalar network and temporal bandwidths;
7. preserve built-in network kernel, temporal kernel, junction policy, target, direction, and cyclic
   tail semantics;
8. reindex reusable event-axis network distance assets where mathematically valid;
9. preserve cyclic time without independent time permutation;
10. separate outer replicate scheduling from inner sequential network-time evaluation;
11. preserve logical identity across workers, spatial/time chunks, and replicate chunks;
12. preflight complete ensemble, network-time workspace, reusable assets, temporal kernel blocks,
    reconstructed events, and concurrent outputs;
13. test manual replay, linear/cyclic time, asset reindexing, scheduling, support identity,
    immutability, memory failure, and closed-component rejection;
14. generate `HANDOFF_0.0.16_PROGRESS_02F_TEMPORAL_NETWORK_BOOTSTRAP.md` and pass full CI.

## Do not begin during 02F

- fixed-exposure event-rate Bootstrap;
- independent case-control relative-risk Bootstrap;
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
3. Confirm temporary workflows, formatting artifacts, placeholders, and diagnostic logs are absent.
4. Read all ten required records.
5. Preserve execution, seed ordering, exact support, paired-event identity, and fail-fast contracts.
6. Inspect exact temporal-network types and numerical routes before coding.
7. Implement only temporal-network ordinary Bootstrap.
8. Generate root and docs 02F handoffs after the numerical unit passes full CI.
9. Do not move to risk-derived Bootstrap or separability before 02F closes.
