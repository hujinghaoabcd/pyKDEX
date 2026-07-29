# 0.0.16 progress 02A: bootstrap foundation

The empirical uncertainty foundation is complete, but estimator bootstrap functions have
not started. The package remains `0.0.15` and PR #16 remains Draft and unmerged.

Full recovery record:

```text
HANDOFF_0.0.16_PROGRESS_02A_BOOTSTRAP_FOUNDATION.md
```

## Completed contracts

```python
from pykdex.uncertainty import (
    BootstrapPlan,
    FieldEnsemble,
    PointwiseInterval,
    pointwise_percentile_interval,
)
```

The foundation provides:

- ordinary-bootstrap requests only;
- deterministic NumPy `SeedSequence` child streams by logical replicate index;
- replicate chunk resolution through `ExecutionPlan`;
- deterministic sequential/thread replicate scheduling;
- complete in-memory exact-support replicate ensembles;
- pointwise percentile intervals, standard errors, and bias;
- shared support validity masks;
- explicit log-risk handling for `-inf`.

`FieldEnsemble` uses the existing closed measured-support descriptor. Complete ensemble
storage must be included in fixed overhead before future bootstrap operations schedule
replicates.

## Validation

Clean foundation head:

```text
b9d5110f7ea1879311b4edcdbd588a18c5662ca3
```

CI #314 (`30374221919`) passed quality, strict documentation, full regression tests,
coverage, source/wheel distribution checks, Linux, Windows, macOS, and Python 3.11-3.14.

## Exact next unit

Implement `BootstrapResult` and spatial `bootstrap_kde` only, restricted to:

```text
SpatialEvents + GridSupport + SpatialKDE
unit weights
fixed finite positive scalar numeric bandwidth
fixed kernel, metric, target, boundary, and boundary correction
ordinary event-index resampling with replacement
complete replicate storage
```

Replicate event IDs must be unique even when source events are sampled repeatedly. Sampled
source indices must be retained in provenance. The result must be invariant to thread
completion, worker count, and replicate chunking.

Do not add other estimator domains, event-rate bootstrap, relative-risk bootstrap,
separability, permutation tests, adaptive bandwidths, bandwidth reselection, simultaneous
bands, or persistence changes in the next unit.
