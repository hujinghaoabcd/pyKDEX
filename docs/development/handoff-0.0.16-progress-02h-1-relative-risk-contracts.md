# pyKDEX 0.0.16 progress 02H-1: shared density contracts

## Completion record

Normalized relative-risk compatibility metadata is complete for all five density
Bootstrap families on Draft PR #16.

Validated clean implementation head:

```text
2b867ef171618feb8d812c58a1acf2d29f8c8c2c
```

Full validation:

```text
CI #434
run id 30419359103
conclusion: success
```

The package version remains `0.0.15`; the PR remains Draft and unmerged.

## Metadata contract

Every completed density Bootstrap result and ensemble exposes:

```text
relative_risk_contract
relative_risk_contract_fingerprint
```

The immutable contract includes exact support and fixed estimator choices needed
for case/control compatibility while excluding event, seed, value, and execution
identity.

Families:

```text
spatial
network
heat_network
spatiotemporal
network_time
```

The original estimator contract fingerprint remains unchanged. This normalized
mapping exists for cross-group relative-risk validation and useful mismatch
messages.

## Validation

Focused tests create real results from all five adapters and prove event-data and
execution-plan independence, family-specific parameter sensitivity, metadata
immutability/serialization, and numerical preservation.

## Next subunit

02H-2 defines the linked immutable `RelativeRiskBootstrapResult` container and
validation-only tests. It must not expose `bootstrap_relative_risk` or compute any
raw/log ratio matrices.
