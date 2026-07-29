# pyKDEX 0.0.16 progress 02D: heat-network Bootstrap

Status: implementation complete; release remains incomplete.

The detailed durable record is:

```text
HANDOFF_0.0.16_PROGRESS_02D_HEAT_BOOTSTRAP.md
```

## Completed domain

```text
NetworkWorkspace + HeatNetworkKDE -> bootstrap_kde
```

The adapter performs ordinary accepted snapped-event resampling after snapping, keeps the
accepted-event count and snapping/rejection outcome fixed, and constructs a fresh global
finite-element heat solve for every logical replicate.

## Fixed contract

The built-in adapter requires:

- unit accepted-event weights;
- finite positive numeric scalar diffusion time;
- fixed optional mesh size;
- fixed target and negative-roundoff tolerance;
- exact undirected network and lixel support;
- no heat-time selector or replicate-wise reselection;
- no explicit support argument;
- no target chunks.

The public call retains the compatibility keyword:

```python
bootstrap_kde(
    estimator=HeatNetworkKDE(...),
    events=workspace,
    plan=BootstrapPlan(...),
)
```

## Replicate reconstruction

Every replicate:

1. samples accepted snapped-event indices with replacement;
2. creates new unique replicate-local event IDs;
3. preserves selected edge indices, offsets, coordinates, snap metadata, marks, CRS, and units;
4. preserves the original rejected-event table and snapping parameters;
5. reuses the exact network and lixel support;
6. omits radial distance assets because the heat estimator does not consume them;
7. rebuilds the heat operator, generator, compute plan, source mass, global solution, and lixel
   cell averages.

The source event mesh is an upper bound because a replicate can remove observed event offsets but
cannot introduce a new offset. The implementation checks:

```text
replicate n_dofs <= source n_dofs
```

## Fixed solver route

- source DOFs at most 1024: observed and replicates use dense symmetric eigendecomposition;
- source DOFs above 1024: the adapter fixes threshold one so observed and replicates use sparse
  `expm_multiply`.

This prevents replicate event multiplicity from silently changing the numerical route.

## Execution and memory

Outer logical replicate ranges may be threaded. Every inner heat solve is sequential and
unchunked. Logical seed/result identity is invariant to worker count, replicate chunks, and worker
completion order.

The memory model includes the complete ensemble, supplied inputs, reconstructed accepted events,
rejection audit, finite-element operator, generator, stored spectral state, nodal and output
arrays, and conservative solver temporary storage for every requested concurrent replicate.
Too-small budgets fail before replicate scheduling.

## Validation

Clean implementation head:

```text
c8f6760d7115c8f725c0e734e04f5c749cf74fbf
```

CI #360 (`30382166566`) passed quality, strict documentation, complete tests, branch coverage,
distributions, installed-wheel smoke, Linux, Windows, macOS, and Python 3.11-3.14.

The later guide/example/handoff state requires its own final CI before it is called validated.

## Exact next unit

```text
02E: SpatiotemporalEvents + SpatiotemporalKDE ordinary Bootstrap
```

Space and time must be resampled together as one event identity. Fixed scalar spatial and temporal
bandwidths, fixed kernels, boundary/time domain, cyclic semantics, exact product support, unit
weights, deterministic replicate identity, and complete memory preflight are mandatory.

Time permutation is reserved for the later explicitly Poisson separability test and must not be
mixed with ordinary Bootstrap.
