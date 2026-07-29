# pyKDEX 0.0.16 progress 02H-1: shared density contracts

## Status

This implementation prerequisite for independent relative-risk Bootstrap is
complete on Draft PR #16.

Validated clean implementation head:

```text
2b867ef171618feb8d812c58a1acf2d29f8c8c2c
```

Validation:

```text
CI #434
run id 30419359103
conclusion: success
```

The package version remains `0.0.15`. PR #16 remains open, Draft, unmerged, and
mergeable.

## Scope

02H-1 adds normalized, auditable, execution-independent compatibility metadata
to every completed KDE Bootstrap adapter.

No relative-risk ratio is computed. No public `bootstrap_relative_risk` function
or linked result container exists yet.

## Common metadata keys

Every completed Bootstrap density result now exposes in both
`BootstrapResult.metadata` and `FieldEnsemble.metadata`:

```text
relative_risk_contract
relative_risk_contract_fingerprint
```

The contract is an immutable mapping proxy. A standard dictionary view is JSON
serializable:

```python
json.dumps(dict(result.metadata["relative_risk_contract"]))
```

Attempted mutation raises `TypeError`.

## Common schema

Every mapping begins with:

```text
schema_version = 1
result_family
support_fingerprint
target
bandwidths
```

The contract helper validates non-empty family/support identity, accepted target,
and finite positive bandwidth values before computing the stable fingerprint.

Internal helper:

```text
src/pykdex/uncertainty/contracts.py
```

## Supported result families

```text
spatial
network
heat_network
spatiotemporal
network_time
```

### Spatial

Contract components:

```text
kernel
metric
boundary_correction
boundary_fingerprint
```

### Radial network

Contract components:

```text
kernel
junction_policy
directed
network_fingerprint
path_based
coefficient_tolerance
max_records_per_event
```

### Heat network

Contract components:

```text
estimator_kind = heat_equation
diffusion_time
mesh_size
negative_tolerance
network_fingerprint
solver_policy = source_dof_threshold_auto
dense_threshold_policy = 1024
```

The contract records the deterministic solver policy, not event-derived mesh DOF
counts or the observed dense/sparse route. This preserves event independence
while keeping the numerical policy auditable.

### Ordinary space-time

Contract components:

```text
spatial_kernel
temporal_kernel
spatial_metric
cyclic_tail_tolerance
time_domain_fingerprint
```

### Temporal network

Contract components:

```text
spatial_kernel
temporal_kernel
junction_policy
directed
network_fingerprint
path_based
cyclic_tail_tolerance
coefficient_tolerance
max_records_per_event
time_domain_fingerprint
```

## Deliberate exclusions

The normalized compatibility contract excludes:

- source event fingerprints;
- event IDs and sample size;
- observed and replicate numerical values;
- seed entropy and seed-ledger identity;
- worker count and execution backend;
- target or replicate chunk size;
- memory budgets and memory models;
- workspace reconstruction fingerprints;
- completion order;
- stored propagation traces;
- event-derived heat mesh DOF counts.

These quantities remain available elsewhere in result provenance but do not
define whether two density estimators are compatible for relative-risk ratios.

## Existing identity preservation

The pre-existing private `estimator_contract_fingerprint` remains unchanged.
02H-1 adds a second normalized contract specifically for cross-group
relative-risk compatibility and human-readable mismatch diagnostics.

KDE observed fields and replicate numerical arrays are unchanged. The expanded
result and ensemble metadata intentionally changes their encompassing metadata
fingerprints, but not numerical field identity or seed ordering.

## Tests

Added:

```text
tests/test_bootstrap_relative_risk_contracts.py
```

The tests execute all five real Bootstrap families and verify:

1. both result and ensemble metadata expose the same immutable contract object;
2. standard dictionary views are JSON serializable;
3. contract mutation is rejected;
4. different source events on one fixed support do not change the contract;
5. sequential versus threaded replicate execution does not change the contract;
6. meaningful family-specific estimator changes change mapping and fingerprint;
7. all five family labels are normalized consistently;
8. observed and replicate numerical values remain valid and unchanged by the
   metadata addition.

Family-specific changed parameters in the focused fixtures include:

```text
spatial bandwidth
network kernel
heat diffusion time
space-time temporal bandwidth
network-time temporal bandwidth
```

## Files added or changed

```text
src/pykdex/uncertainty/contracts.py
src/pykdex/uncertainty/spatial.py
src/pykdex/uncertainty/network.py
src/pykdex/uncertainty/heat.py
src/pykdex/uncertainty/spatiotemporal.py
src/pykdex/uncertainty/network_time.py
tests/test_bootstrap_relative_risk_contracts.py
HANDOFF_0.0.16_PROGRESS_02H_1_RELATIVE_RISK_CONTRACTS.md
docs/development/handoff-0.0.16-progress-02h-1-relative-risk-contracts.md
```

## CI evidence

Clean implementation head `2b867ef171618feb8d812c58a1acf2d29f8c8c2c`
passed CI #434 (`30419359103`), including:

- Black;
- isort;
- Ruff;
- mypy;
- public API example coverage;
- strict MkDocs;
- full tests and branch coverage;
- source and wheel builds;
- Twine and archive verification;
- installed-wheel smoke;
- Linux, Windows, and macOS;
- Python 3.11, 3.12, 3.13, and 3.14.

## Exact next subunit

02H-2 implements only the linked immutable result and validation types needed by
the design:

```text
RelativeRiskBootstrapResult
```

02H-2 must not compute ratios. It should validate two already constructed raw/log
`BootstrapResult` fixtures plus:

- shared support;
- shared replicate count;
- shared confidence level;
- shared validity mask;
- linked case/control source identities;
- distinct case/control seed-ledger identities;
- deterministic pairing rule;
- observed and `(B, M)` invalid/adjusted control masks;
- policy and normalization tolerance;
- combined seed fingerprint;
- immutable metadata and stable linked fingerprint.

Do not add `bootstrap_relative_risk` or allocate numerical raw/log ratio matrices
until 02H-2 closes and passes full CI.
