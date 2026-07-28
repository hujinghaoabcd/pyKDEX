# pyKDEX 0.0.16 design: uncertainty, separability diagnostics, and scalable execution

Status: design complete; implementation in progress through heat-network ordinary Bootstrap  
Branch: `agent/uncertainty-separability-scalable-design`  
Base: pyKDEX `0.0.15`, `main` commit
`8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`

This document fixes the statistical meaning, public boundaries, deterministic execution
contract, implementation order, and exclusions for pyKDEX 0.0.16. Detailed completed behaviour is
recorded in the progress handoffs. The remaining implementation must continue to follow the
original design below.

## Implementation progress note

Completed and validated on Draft PR #16:

1. deterministic memory-bounded execution;
2. ordinary-Bootstrap plan, seed ledger, ensemble, interval, and replicate execution;
3. spatial ordinary Bootstrap;
4. radial network ordinary Bootstrap;
5. heat-equation network ordinary Bootstrap.

Exact next unit:

```text
SpatiotemporalEvents + SpatiotemporalKDE ordinary Bootstrap
```

Read the following for exact implemented contracts and CI evidence:

- `development/handoff-0.0.16-progress-01-execution-plan.md`;
- `development/handoff-0.0.16-progress-02a-bootstrap-foundation.md`;
- `development/handoff-0.0.16-progress-02b-spatial-bootstrap.md`;
- `development/handoff-0.0.16-progress-02c-network-bootstrap.md`;
- `development/handoff-0.0.16-progress-02d-heat-bootstrap.md`.

## Original detailed design

The complete original design remains preserved in the root recovery record:

```text
HANDOFF_0.0.16_DESIGN_UNCERTAINTY_SEPARABILITY_SCALABLE.md
```

That record remains the normative source for:

- external methodological references and licence boundaries;
- deterministic execution and memory semantics;
- ordinary KDE Bootstrap across spatial, network, space-time, and network-time domains;
- fixed-exposure event-rate Bootstrap;
- independent within-group relative-risk Bootstrap;
- first-order separability diagnostics;
- explicitly Poisson event-time permutation tests;
- fingerprints, provenance, caching, tests, documentation, release staging, and exclusions.

The implementation must not weaken these rules:

- pointwise intervals are not simultaneous bands;
- ordinary Bootstrap keeps complete event identities paired;
- network resampling occurs after snapping;
- time permutation is a null test, not Bootstrap;
- arbitrary weights and adaptive/reselected bandwidths remain excluded from built-in Bootstrap;
- case and control samples are resampled independently for relative risk;
- exposure is fixed for the first event-rate Bootstrap;
- non-Poisson separability p-values are not claimed;
- execution choices do not alter the statistical contract;
- package version remains `0.0.15` until the complete release surface is validated.
