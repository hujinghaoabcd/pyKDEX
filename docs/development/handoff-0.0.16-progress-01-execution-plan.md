# 0.0.16 progress 01: deterministic execution foundation

The first pyKDEX 0.0.16 implementation subunit is complete. The package version remains
`0.0.15`, PR #16 remains Draft, and bootstrap and separability implementation have not
started.

The complete recovery record is:

```text
HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md
```

## Public contract

```python
from pykdex.execution import ExecutionPlan

plan = ExecutionPlan(
    memory_budget_bytes=256 * 1024 * 1024,
    target_chunk_size=None,
    replicate_chunk_size=None,
    n_jobs=1,
    backend="sequential",
)
```

Supported backends are only `sequential` and `thread`. An omitted plan preserves legacy
unbounded defaults; an explicit `ExecutionPlan()` requests the default 256 MiB budget.

The operation-specific private resolution record includes requested and resolved target
chunks, workers, backend, parallel axis, fixed overhead, bytes per pair, safety factor,
estimated peak bytes, logical chunk count, and stable fingerprints.

## Deterministic rule

Only independent target chunks run concurrently. Source-event reductions retain their
stable order, and completed work is written into preassigned logical output slices. Worker
completion order therefore cannot reorder results.

Changing chunk size or worker count must preserve the statistical estimate to repository
numerical tolerance. Cross-platform bitwise equality is not claimed.

## Integrated estimators

| Estimator | Execution axis | Thread support |
| --- | --- | --- |
| `SpatialKDE` | support points or cells | yes |
| `SpatiotemporalKDE` | space-time support rows | yes |
| `NetworkKDE` | lixels | yes |
| `TemporalNetworkKDE` | temporal cells | yes |
| `HeatNetworkKDE` | global solve, audit only | no target threads |

`NetworkKDE` supports simple, discontinuous, and continuous policies. Propagation traces
are still generated in event order. `TemporalNetworkKDE` now creates temporal offsets and
kernels per time block instead of retaining a complete time-by-event temporal kernel
matrix. `HeatNetworkKDE` counts the finite-element operator and compute plan but rejects
partial target chunks and threaded target execution.

Legacy `SpatialKDE.chunk_size`, `SpatiotemporalKDE.chunk_size`, and
`TemporalNetworkKDE.time_chunk_size` remain supported. A legacy chunk and an explicit plan
target chunk cannot both be supplied.

## Validation

Clean implementation head:

```text
cef94f9b26c3faab6aaeab85dadf0740bcc34078
```

CI #281 (`30369196085`) passed quality, strict docs, full regression tests, branch
coverage, source/wheel distribution checks, isolated-wheel smoke tests, Linux, Windows,
macOS, and Python 3.11-3.14.

The focused execution suite contains 39 tests across plan resolution, spatial, ordinary
space-time, network, network-time, and heat integration.

## Documentation

```text
docs/guides/execution.md
docs/api/execution.md
benchmarks/benchmark_execution_plan.py
```

## Exact next subunit

Implement the empirical bootstrap uncertainty foundation only:

- immutable `BootstrapPlan` with ordinary bootstrap only;
- deterministic NumPy `SeedSequence` ledger in logical replicate order;
- exact-support `FieldEnsemble` with complete in-memory replicate storage;
- pointwise percentile `PointwiseInterval`;
- immutable fail-fast `BootstrapResult`;
- `bootstrap_kde`;
- fixed-exposure `bootstrap_event_rate`;
- independent within-group `bootstrap_relative_risk` with default log-risk intervals;
- unit weights and fixed scalar bandwidths only;
- fixed support and fixed estimator contracts;
- replicate chunking through the completed `ExecutionPlan` contract.

Do not add separability, permutation tests, adaptive bandwidth bootstrap, bandwidth
reselection, uncertain exposure, non-unit weights, BCa/bootstrap-t/basic intervals,
simultaneous bands, streaming quantiles, or disk-backed ensembles in the next subunit.
