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
8. fixed-exposure event-rate Bootstrap on exact measured support.

The exact next unit is a detailed design for independent case-control relative-risk
Bootstrap. Do not begin numerical implementation until replicate pairing, independent seed
ledgers, shared fixed-bandwidth compatibility, normalization, raw/log linked outputs, and
memory accounting are fixed in the design.

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
12. `HANDOFF_0.0.16_PROGRESS_02G_FIXED_EXPOSURE_EVENT_RATE_BOOTSTRAP.md`.

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
- exact next unit: 02H independent case-control relative-risk Bootstrap design.

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

## Completed subunit 02G: fixed-exposure event-rate Bootstrap

Public operation:

```text
intensity BootstrapResult + fixed ExposureField -> bootstrap_event_rate
```

Statistical rules:

- accept only completed `bootstrap_kde` intensity ensembles;
- preserve the source Bootstrap plan, seed ledger, replicate identities, and confidence level;
- require exact measured-support identity between source ensemble and exposure;
- treat exposure as fixed and never resample it;
- return event uncertainty conditional on fixed exposure;
- reject probability-density source ensembles;
- reuse explicit `raise`, `nan`, and `minimum` denominator policies;
- introduce no hidden epsilon or pseudocount;
- combine source validity with finite effective exposure;
- retain distinct source-intensity, exposure, and event-rate fingerprints.

Execution and memory:

- no KDE is refitted and no random stream is generated;
- observed and replicate rates are deterministic transforms of stored intensity fields;
- an explicit derived-operation memory budget is separate from the earlier KDE budget;
- preflight includes the resident source ensemble, exposure/denominator state, and complete
  output ensemble;
- source result and exposure remain immutable.

Supported measured support families:

```text
spatial_grid
network_lixel
measured spatiotemporal_points when a valid intensity ensemble exists
spatiotemporal_grid
network_time_arixel
```

Clean implementation head:

```text
50686d4a05195c41d40c9acd0ec010d3a67c17f4
```

CI #416 (`30416870784`) passed quality, strict documentation, full tests, branch coverage,
distributions, installed-wheel smoke, Linux, Windows, macOS, and Python 3.11-3.14.

## Exact next unit: 02H independent case-control relative-risk Bootstrap design

Inspect:

```text
src/pykdex/risk/density.py
src/pykdex/risk/relative_risk.py
src/pykdex/uncertainty/
existing relative-risk tests and 0.0.15 handoffs
```

Produce a detailed design before numerical code. It must decide:

1. whether initial case and control ensembles must have equal replicate counts;
2. how replicate rows are paired while preserving independent within-group resampling;
3. whether distinct seed-ledger fingerprints are mandatory and how accidental shared streams
   are rejected;
4. how exact support, result family, shared scalar bandwidths, kernels, metrics, policies, and
   correction contracts are compared;
5. how observed and every replicate density are verified to integrate to one;
6. how denominator `raise`, `nan`, and `minimum` policies define raw-risk validity;
7. how zero case density yields raw risk zero and log risk `-inf` without becoming an invalid
   denominator;
8. how `FieldEnsemble` validation represents valid `-inf` log-risk values;
9. whether the public return is two linked `BootstrapResult` objects or one dedicated linked
   result container;
10. how complete case, control, raw-risk, and log-risk ensembles are budgeted without hidden
    streaming;
11. how pooled case-control resampling and mark permutation are kept outside this operation;
12. which analytical and independent numerical fixtures validate the first release.

Required design records:

```text
docs/development/design-0.0.16-relative-risk-bootstrap.md
HANDOFF_0.0.16_DESIGN_RELATIVE_RISK_BOOTSTRAP.md
```

Do not write numerical relative-risk Bootstrap code until the design answers all twelve
questions.

## Do not begin during the 02H design unit

- pooled case-control resampling;
- case/control mark permutation;
- uncertain exposure;
- separability diagnostics;
- permutation p-values;
- adaptive or independently selected case/control bandwidths;
- BCa, bootstrap-t, basic, or simultaneous intervals;
- streaming or disk-backed ensembles;
- persistence changes;
- package version bump;
- ready-for-review transition or merge.

## Recovery checklist

1. Inspect PR #16, current head, changed files, and latest CI once.
2. Confirm PR is open, Draft, unmerged, and version remains `0.0.15`.
3. Confirm temporary workflows, formatting artifacts, placeholders, and diagnostic logs are absent.
4. Read all twelve required records.
5. Preserve exact support, independent group identities, seed provenance, and explicit denominator rules.
6. Write only the 02H relative-risk Bootstrap design and tests/fixtures plan.
7. Open no new public API and write no numerical ratio ensemble code during the design unit.
8. Update the current handoff after the design passes strict documentation and full CI.
