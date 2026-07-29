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
7. ordinary temporal-network Bootstrap on measured arixel support.

The exact next implementation unit is fixed-exposure event-rate Bootstrap. Do not begin
independent case-control relative-risk Bootstrap, uncertain-exposure Bootstrap, separability
diagnostics, or permutation testing before the fixed-exposure event-rate unit is designed,
implemented, documented, and validated.

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
11. `HANDOFF_0.0.16_PROGRESS_02F_TEMPORAL_NETWORK_BOOTSTRAP.md`.

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
- exact next unit: fixed-exposure event-rate Bootstrap.

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

Final 02E documentation and handoff head `f4d9ca0652904e8c546e20ee2d34301ba2a94e72`
passed CI #397 (`30387640653`) across the complete repository matrix.

## Completed subunit 02F: ordinary temporal-network Bootstrap

Closed domain:

```text
NetworkTimeWorkspace + TemporalNetworkKDE -> bootstrap_kde
```

Statistical rules:

- resample accepted snapped-network-location-plus-time identities after snapping;
- use one sampled-index sequence for network location, time, and optional marks;
- preserve accepted-event count, rejection audit, network, lixels, and exact arixels;
- preserve CRS, spatial/temporal units, time domain, temporal origin, and timezone;
- create unique replicate-local IDs and retain sampled source indices;
- require unit weights and fixed numeric scalar spatial/temporal bandwidths;
- require built-in kernel and junction-policy string names;
- support simple, discontinuous, and continuous policies;
- support linear and cyclic time without independent time permutation;
- reindex event-to-lixel rows and temporal-offset/distance columns by the same event axis;
- rebuild path propagation traces for path-based policies.

Execution and identity:

- outer replicate ranges may be threaded;
- every inner `TemporalNetworkKDE` is sequential and chunks only target time rows;
- explicit Bootstrap target chunks override legacy estimator `time_chunk_size`;
- seed and replicate identity are independent of workers and chunks;
- observed-field identity uses the fixed estimator contract, events, network, and arixel
  support rather than raw floating-point output bytes;
- memory preflight includes complete ensemble, reconstructed workspaces, factorized assets,
  propagation bounds, spatial matrices, temporal blocks, and concurrent outputs;
- source estimator and workspace remain unchanged.

Clean implementation head:

```text
2636e6c542359ef89decb6896cfadb267460bd03
```

CI #404 (`30415551843`) passed quality, strict documentation, full tests, branch coverage,
distributions, installed-wheel smoke, Linux, Windows, macOS, and Python 3.11-3.14.

## Exact next unit: 02G fixed-exposure event-rate Bootstrap

Inspect the exact current contracts in:

```text
src/pykdex/risk/
src/pykdex/uncertainty/
existing exposure and event-rate tests and handoffs
```

Design and implement only the fixed-exposure event-rate uncertainty path. Required decisions:

1. identify which completed intensity Bootstrap families can feed event-rate uncertainty;
2. require exact measured support compatibility between every intensity field and exposure;
3. treat exposure as fixed and record that conditioning explicitly;
4. preserve the existing explicit zero-denominator policy without hidden epsilon;
5. decide whether to transform a completed intensity ensemble or wrap each intensity replicate;
6. retain separate intensity, exposure, and event-rate fingerprints;
7. budget the complete transformed event-rate ensemble before allocation;
8. return pointwise percentile intervals labelled as event uncertainty conditional on fixed
   exposure;
9. test spatial, network, ordinary space-time, and network-time measured supports where the
   current risk contracts permit them;
10. generate `HANDOFF_0.0.16_PROGRESS_02G_FIXED_EXPOSURE_EVENT_RATE_BOOTSTRAP.md` and pass full CI.

## Do not begin during 02G

- uncertain-exposure Bootstrap;
- independent case-control relative-risk Bootstrap;
- pooled case-control resampling;
- separability diagnostics;
- permutation p-values;
- weighted or adaptive built-in Bootstrap;
- bandwidth selection inside replicates;
- BCa, bootstrap-t, basic, or simultaneous intervals;
- streaming or disk-backed ensembles;
- persistence changes;
- package version bump;
- ready-for-review transition or merge.

## Recovery checklist

1. Inspect PR #16, current head, changed files, and latest CI once.
2. Confirm PR is open, Draft, unmerged, and version remains `0.0.15`.
3. Confirm temporary workflows, formatting artifacts, placeholders, and diagnostic logs are absent.
4. Read all eleven required records.
5. Preserve execution, seed ordering, exact support, paired-event identity, and fail-fast contracts.
6. Inspect exact risk, exposure, event-rate, and uncertainty types before coding.
7. Implement only fixed-exposure event-rate Bootstrap.
8. Generate root and docs 02G handoffs after the numerical unit passes full CI.
9. Do not move to relative-risk or separability before 02G closes.
