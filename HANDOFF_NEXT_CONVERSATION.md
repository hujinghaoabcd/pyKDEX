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
9. detailed 02H independent relative-risk Bootstrap design.
10. normalized 02H-1 shared density-contract metadata.

The exact next implementation subunit is 02H-2: the linked immutable
`RelativeRiskBootstrapResult` validation container. Do not compute raw/log ratio ensembles or
expose `bootstrap_relative_risk` before the container and its validation tests pass full CI.

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
13. `docs/development/design-0.0.16-relative-risk-bootstrap.md`.
14. `HANDOFF_0.0.16_DESIGN_RELATIVE_RISK_BOOTSTRAP.md`.
15. `HANDOFF_0.0.16_PROGRESS_02H_1_RELATIVE_RISK_CONTRACTS.md`.
16. `docs/development/handoff-0.0.16-progress-02h-1-relative-risk-contracts.md`.

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
- exact next unit: 02H-2 linked relative-risk result validation types.

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

## Completed design subunit 02H: independent relative-risk Bootstrap

Design records:

```text
docs/development/design-0.0.16-relative-risk-bootstrap.md
HANDOFF_0.0.16_DESIGN_RELATIVE_RISK_BOOTSTRAP.md
```

Fixed decisions:

- consume two completed ordinary density Bootstrap results;
- case and control are resampled independently within group before the ratio operation;
- require distinct source results, source-event provenance, and seed-ledger fingerprints;
- require equal replicate counts and equal confidence levels;
- pair rows by the same logical replicate index without a new RNG;
- reject truncation, recycling, random rematching, and Cartesian-product expansion;
- require exact measured support and one normalized shared fixed estimator contract;
- require all-true source density validity masks;
- verify observed and every replicate density integrate to one;
- never silently renormalize density rows;
- reuse explicit control-denominator `raise`, `nan`, and `minimum` policies;
- use conservative whole-column invalidity for `nan` because current `FieldEnsemble`
  validity is one-dimensional;
- retain full observed and replicate invalid/adjusted control masks in a linked result;
- preserve zero case density as raw risk zero and log risk `-inf`;
- return a dedicated immutable container linking raw and log `BootstrapResult` objects;
- preflight resident case/control ensembles plus complete raw/log outputs and masks;
- generate no new random numbers and expose no significance p-values.

Methodological boundary:

- this is empirical pointwise sampling uncertainty for a density-ratio surface;
- it is not a pooled-label randomization test, asymptotic tolerance contour, Monte Carlo
  null test, or simultaneous band;
- established relative-risk inference literature is cited in the primary design.

## Completed subunit 02H-1: normalized shared density contracts

Common metadata keys:

```text
relative_risk_contract
relative_risk_contract_fingerprint
```

Implemented families:

```text
spatial
network
heat_network
spatiotemporal
network_time
```

Rules:

- the contract is an immutable mapping proxy;
- a standard dictionary view is JSON serializable;
- common fields are schema version, family, support fingerprint, target, and bandwidth tuple;
- family fields record fixed kernels, metrics/policies, boundary/network/time identity, and
  heat solver policy where relevant;
- event fingerprints, sample size, values, seeds, workers, chunks, and budgets are excluded;
- the original estimator contract fingerprint remains unchanged;
- compatible estimators with different events/execution plans yield equal contracts;
- meaningful family-specific estimator changes yield different contracts;
- result and ensemble metadata share the same contract object.

Clean implementation head:

```text
2b867ef171618feb8d812c58a1acf2d29f8c8c2c
```

CI #434 (`30419359103`) passed quality, strict documentation, full tests, branch coverage,
distributions, installed-wheel smoke, Linux, Windows, macOS, and Python 3.11-3.14.

## Exact next implementation subunit: 02H-2 linked result validation types

Implement only the immutable linked container proposed by the design:

```text
RelativeRiskBootstrapResult
```

02H-2 inputs are already constructed raw and log `BootstrapResult` fixtures. It must not
calculate ratios or expose a public transformation function.

Required owned state:

- raw relative-risk `BootstrapResult`;
- log-relative-risk `BootstrapResult`;
- explicit `DenominatorPolicy`;
- normalization tolerance;
- deterministic pairing rule;
- case and control source-result fingerprints;
- case and control ensemble fingerprints;
- case and control event fingerprints;
- case and control seed-ledger fingerprints;
- combined derived seed fingerprint;
- observed control invalid/adjusted masks `(M,)`;
- replicate control invalid/adjusted masks `(B, M)`;
- immutable metadata and stable linked fingerprint.

Required validation:

1. raw field family is `relative_risk` and log field family is `log_relative_risk`;
2. both nested operations are `bootstrap_relative_risk`;
3. support, replicate count, confidence level, validity mask, estimator family, and pairing
   fingerprints agree;
4. case/control source and seed identities are non-empty and distinct;
5. pairing rule is exactly `same_logical_replicate_index`;
6. normalization tolerance is finite and positive;
7. observed masks have shape `(M,)` and replicate masks `(B, M)`;
8. adjusted masks are subsets of invalid masks;
9. masks are immutable and finite boolean arrays;
10. raw valid values are finite/non-negative;
11. log valid values allow finite numbers and `-inf`, but reject `+inf`;
12. metadata is immutable and the linked fingerprint changes when any statistical identity
    changes;
13. memory-budget or execution metadata changes do not change the linked statistical
    fingerprint.

Add focused fixtures that build nested results manually without calling a numerical ratio
implementation.

Generate:

```text
HANDOFF_0.0.16_PROGRESS_02H_2_RELATIVE_RISK_RESULT.md
docs/development/handoff-0.0.16-progress-02h-2-relative-risk-result.md
```

## Do not begin during 02H-2

- public `bootstrap_relative_risk`;
- numerical raw/log division;
- density normalization scans;
- denominator-policy application to source matrices;
- pooled case-control resampling or permutation;
- unequal replicate counts;
- simultaneous bands or p-values;
- package version bump, ready-for-review transition, or merge.

## Recovery checklist

1. Inspect PR #16, current head, latest CI, and changed files once.
2. Confirm temporary workflows are absent and package version remains `0.0.15`.
3. Read all sixteen required records.
4. Preserve existing Bootstrap results and contract metadata.
5. Implement only linked result ownership and validation.
6. Use manually constructed fixtures; do not write numerical transformation code.
7. Generate both 02H-2 recovery records after full CI.
8. Do not begin 02H-3 until 02H-2 closes.
