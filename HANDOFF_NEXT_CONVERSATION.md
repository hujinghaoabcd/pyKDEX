# pyKDEX current handoff

The latest merged release is **0.0.15**. Active development is pyKDEX **0.0.16** on Draft
PR #16. The deterministic execution foundation, common Bootstrap foundation, spatial
Bootstrap adapter, and radial network Bootstrap adapter are complete in the development branch.

The exact next implementation unit is ordinary Bootstrap for `HeatNetworkKDE` only.

## Read these records in order

1. `HANDOFF_0.0.15_EXPOSURE_RELATIVE_RISK.md`;
2. `docs/development/design-0.0.16-uncertainty-separability-scalable.md`;
3. `HANDOFF_0.0.16_DESIGN_UNCERTAINTY_SEPARABILITY_SCALABLE.md`;
4. `HANDOFF_0.0.16_DESIGN_VALIDATION.md`;
5. `HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md`;
6. `HANDOFF_0.0.16_PROGRESS_02A_BOOTSTRAP_FOUNDATION.md`;
7. `HANDOFF_0.0.16_PROGRESS_02B_SPATIAL_BOOTSTRAP.md`;
8. `HANDOFF_0.0.16_PROGRESS_02C_NETWORK_BOOTSTRAP.md`.

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
- exact next unit: `NetworkWorkspace + HeatNetworkKDE` ordinary Bootstrap.

Always inspect the current PR head and latest CI before continuing. Do not infer the live head
from a recorded implementation commit because documentation/status commits may follow it.

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
HeatNetworkKDE: global-solver budget audit only
```

Rules that must not change:

- execution chunks and workers are operational, not statistical;
- only independent target chunks are threaded;
- source-event reduction order remains stable;
- output slices are fixed before scheduling;
- explicit memory budgets fail before large work allocations;
- `HeatNetworkKDE` must not expose fake target threading.

Clean execution implementation head `cef94f9b26c3faab6aaeab85dadf0740bcc34078`
passed CI #281 (`30369196085`).

## Completed subunit 02A: Bootstrap foundation

Public dedicated-namespace objects:

```text
BootstrapPlan
BootstrapResult
FieldEnsemble
PointwiseInterval
pointwise_percentile_interval
```

Private foundations:

```text
SeedLedger
ResolvedReplicateExecution
resolve_replicate_execution
replicate_chunk_ranges
execute_replicate_chunks
```

Core rules:

- only ordinary event Bootstrap;
- complete replicate storage is mandatory;
- NumPy `SeedSequence`/`PCG64` streams are assigned in logical replicate order;
- replicate identity is independent of workers and chunks;
- one shared exact measured support and validity mask;
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
- fixed optional boundary and exact GridSupport;
- observed event count fixed;
- new unique replicate event IDs;
- sampled source indices retained in provenance;
- fresh estimator per observed/replicate fit;
- complete ensemble and kernel working memory audited before scheduling;
- outer replicate threading, inner target execution sequential;
- existing `events=` keyword remains part of the public call.

Clean spatial implementation head `957c8551744f52a642103e83c91f1fdb2159f305`
passed CI #332 (`30376591895`). Guide/API/example head
`b18dea683cd4de29ad80bf705fcb6261f06d2fef` passed CI #335
(`30377065654`). Final 02B handoff state passed CI #339 (`30378427092`).

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

Statistical boundary:

- resample accepted snapped-event identities after snapping;
- condition on observed accepted-event count and snapping/rejection outcome;
- preserve exact network, lixels, CRS, units, direction, and snap audit;
- do not repeat raw-geometry snapping;
- unit weights and fixed positive numeric scalar bandwidth only;
- built-in kernel and junction-policy string names only;
- no bandwidth selection in replicates;
- source estimator/workspace remain unchanged.

Prepared assets:

- event-to-lixel asset is reindexed along the event/source axis;
- event-to-event asset is reindexed along both event axes;
- duplicate selections create duplicate logical rows/columns;
- stored distances, network, target support, weight mode, direction, and cutoff remain fixed;
- reconstructed assets are validated before estimation.

Execution and memory:

- logical seed/result identity is invariant to workers and chunks;
- outer replicate ranges may be threaded;
- inner `NetworkKDE` runs sequentially with one worker;
- complete ensemble, events, lixels, assets, reconstructed workspaces, output, and kernel working
  arrays are audited before scheduling;
- path policies reserve `n_events * max_records_per_event * 96` bytes per concurrent worker as a
  conservative propagation-record upper bound;
- first replicate failure aborts the operation.

Implementation commit `d6fcfefa55e1095d280735e3c056f92ab4008c98` passed all
network tests, coverage, distributions, and completed platform jobs in CI #343
(`30379267533`); the only failure was Black formatting. Exact format commit
`78ac248d193fec62c858074dc65c8b5daf53dfac` changed layout only. Temporary workflow was deleted
at `d23e8e28f04b65dd9de57e8a14141b9366fa1f1e`, where the full quality chain passed in CI #346.
The latest documentation/handoff head requires its own complete CI inspection.

## Exact next unit: heat-equation Bootstrap

Implement only:

```text
NetworkWorkspace + HeatNetworkKDE
```

Required contract:

1. ordinary accepted snapped-event resampling after snapping;
2. unit accepted-event weights;
3. fixed exact network, lixels, snapping audit, CRS, units, and topology;
4. fixed numeric heat time/bandwidth configuration, no selector or replicate-wise reselection;
5. fresh `HeatNetworkKDE` and fresh global finite-element solve per replicate;
6. deterministic logical `SeedSequence` identity;
7. outer replicate scheduling only;
8. inner heat solve sequential and non-chunked;
9. full global solver state included in conservative per-worker memory accounting;
10. explicit rejection of unsupported target threading or partial target chunks;
11. source estimator/workspace immutability;
12. degenerate/manual, scheduling, memory, and contract tests;
13. `HANDOFF_0.0.16_PROGRESS_02D_HEAT_BOOTSTRAP.md` before any further domain.

## Do not begin during 02D

- spatiotemporal Bootstrap;
- temporal-network Bootstrap;
- event-rate Bootstrap;
- relative-risk Bootstrap;
- separability diagnostics;
- permutation p-values;
- weighted or adaptive built-in Bootstrap;
- heat-time/bandwidth selection inside replicates;
- BCa, bootstrap-t, basic, or simultaneous intervals;
- uncertain exposure;
- streaming or disk-backed ensembles;
- persistence changes;
- package version bump;
- ready-for-review transition or merge.

## Recovery checklist

1. Inspect PR #16, current branch head, changed files, and latest CI once.
2. Confirm PR is open, Draft, unmerged, and version remains `0.0.15`.
3. Confirm all temporary workflows and diagnostic logs are absent from the PR diff.
4. Read all eight required records.
5. Preserve execution, seed ordering, fixed support, and fail-fast contracts.
6. Implement only heat-equation Bootstrap.
7. Generate the 02D root and docs handoff after full CI.
8. Do not move to space-time or risk-derived Bootstrap before 02D closes.
