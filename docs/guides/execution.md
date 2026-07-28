# Deterministic and memory-bounded execution

pyKDEX 0.0.16 introduces a shared execution contract for the existing KDE families. The
contract controls conservative memory budgeting, target chunking, and deterministic thread
execution without changing the statistical estimator.

The public object is available from the dedicated execution namespace:

```python
from pykdex.execution import ExecutionPlan
```

## Basic use

Provide a plan when constructing an estimator:

```python
from pykdex import GridSupport, SpatialKDE
from pykdex.execution import ExecutionPlan

support = GridSupport.from_bounds(
    (0.0, 0.0, 1000.0, 1000.0),
    resolution=20.0,
    spatial_unit="m",
)

plan = ExecutionPlan(
    memory_budget_bytes=256 * 1024 * 1024,
    target_chunk_size=500,
    n_jobs=4,
    backend="thread",
)

result = SpatialKDE(
    bandwidth=75.0,
    execution_plan=plan,
).fit_predict(events, support)
```

The initial backends are deliberately restricted to:

- `sequential`, which requires `n_jobs=1`; and
- `thread`, which may run independent target chunks concurrently.

Process pools, Dask, Joblib, Ray, GPU execution, approximate kernels, and distributed
schedulers are not part of this contract.

## Default behaviour

There is an important distinction between omitting a plan and constructing the default
plan explicitly:

```python
SpatialKDE(bandwidth=75.0)
```

preserves the pre-0.0.16 estimator default and does not impose a new memory budget. In
contrast,

```python
SpatialKDE(
    bandwidth=75.0,
    execution_plan=ExecutionPlan(),
)
```

uses the explicit default budget of 256 MiB and lets pyKDEX resolve a target chunk that
fits the conservative estimate.

Set `memory_budget_bytes=None` when an explicit plan is needed but budget-based chunk
resolution should be disabled.

## Memory contract

Before allocating the main pairwise block, each estimator resolves an operation-specific
plan. The estimate includes:

- fixed live arrays and reusable numerical assets;
- the requested or resolved target block;
- source-event or source-location count;
- operation-specific temporary bytes per source-target pair;
- concurrent worker count; and
- a conservative safety factor.

A plan fails before the main block allocation when the fixed overhead, one target row, or
an explicitly requested chunk cannot fit the budget. The estimate is an auditable upper
bound for pyKDEX-managed arrays, not a promise about total process resident memory. Python,
NumPy, SciPy, BLAS, operating-system, and allocator overhead may consume additional memory.

## Deterministic execution

Thread execution is restricted to independent target blocks. Within each block, source
events are reduced in their existing stable order. Completed blocks are written into fixed
output slices identified by logical block index, so task completion order cannot reorder
the result.

Changing target chunk size or worker count must leave the statistical estimate numerically
equivalent. Exact bitwise equality across operating systems, BLAS implementations, or
floating-point hardware is not promised; repository tests use explicit numerical
tolerances.

## Supported estimators

| Estimator | Resolved target axis | Threaded target blocks | Important fixed assets |
| --- | --- | --- | --- |
| `SpatialKDE` | support points or grid cells | yes | supplied full distance asset, when present |
| `SpatiotemporalKDE` | space-time support rows | yes | supplied space-time distance asset |
| `NetworkKDE` | lixels | yes | sparse network distances or propagation traces |
| `TemporalNetworkKDE` | temporal cells | yes | spatial event-by-lixel kernel matrix and network-time asset |
| `HeatNetworkKDE` | none | no | finite-element operator, solver plan, and global state arrays |

`HeatNetworkKDE` is a global finite-element solve. Its execution plan performs budget
auditing, but partial target chunks and a multi-worker thread backend are rejected rather
than silently ignored.

## Legacy chunk parameters

Existing chunk controls remain valid:

```text
SpatialKDE.chunk_size
SpatiotemporalKDE.chunk_size
TemporalNetworkKDE.time_chunk_size
```

They are recorded as a legacy execution source. A legacy chunk and
`execution_plan.target_chunk_size` cannot both be supplied because two independent chunk
requests would make the effective contract ambiguous.

## Execution metadata

Every integrated estimator stores the resolved audit record in its result metadata:

```python
execution = result.metadata["execution"]

print(execution["operation_name"])
print(execution["source"])
print(execution["resolved_target_chunk_size"])
print(execution["resolved_n_jobs"])
print(execution["estimated_peak_bytes"])
```

The record includes requested and resolved chunk sizes, requested and resolved workers,
backend, parallel axis, fixed overhead, bytes per pair, estimated peak bytes, number of
logical chunks, and stable plan fingerprints.

Execution metadata is operational provenance. It is intentionally excluded from
statistical estimator compatibility and reusable distance-asset identity: two runs with
different safe chunk sizes remain the same estimator.

## Reserved replicate chunking

`ExecutionPlan.replicate_chunk_size` is validated and fingerprinted now so future bootstrap
and permutation operations can share the same execution contract. Current KDE estimators
do not execute replicate blocks and do not interpret this value numerically.

## Failure examples

A plan raises instead of silently changing semantics when:

- a non-positive budget, chunk size, or worker count is supplied;
- `backend="sequential"` is combined with `n_jobs != 1`;
- the fixed overhead exceeds the budget;
- one target row cannot fit the budget;
- an explicit chunk exceeds the budget;
- both a legacy chunk and a plan chunk are supplied; or
- a non-chunkable global solver is asked to use target threads or partial target chunks.

Estimator state is reset on failure, following the same atomic fit behaviour as the rest
of pyKDEX.

## Benchmark

A deterministic spatial benchmark compares sequential and threaded plans while verifying
numerical equivalence:

```bash
python benchmarks/benchmark_execution_plan.py
```

Benchmark timings are descriptive for the current machine and numerical stack. They are
not a cross-platform speed guarantee.
