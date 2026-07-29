# pyKDEX 0.0.16 design validation

This record captures the observed GitHub state after the complete 0.0.16 design and
handoff documents were added. It supplements, rather than replaces:

```text
docs/development/design-0.0.16-uncertainty-separability-scalable.md
HANDOFF_0.0.16_DESIGN_UNCERTAINTY_SEPARABILITY_SCALABLE.md
```

## Repository state

- repository: `hujinghaoabcd/pyKDEX`;
- branch: `agent/uncertainty-separability-scalable-design`;
- Draft PR: `#16 Design pyKDEX 0.0.16 uncertainty, separability, and scalable execution`;
- PR base: `main` at `8b3b2d8626a2e3e5bfd6dae497f71ea344d2ac0e`;
- validated design head: `744bf7fce1de2621a023c7b0c9d1e771cd445318`;
- design CI: `#234` (`30361402955`), success;
- package version: `0.0.15`;
- numerical implementation: not started;
- provisional 0.0.16 top-level public exports: none;
- merge: not merged;
- PR remains Draft.

The accidental empty `docs/development/.keep` file created while preparing the PR was
removed before PR creation. It is absent from the final branch diff and validated head.

## Observed validation

CI #234 completed successfully for the validated design head. The run covered:

- Black;
- isort;
- Ruff;
- mypy;
- complete top-level public API example mapping;
- strict MkDocs;
- branch coverage and the complete pytest regression suite;
- source distribution and wheel construction;
- Twine metadata validation;
- distribution archive verification;
- isolated installed-wheel smoke testing;
- Linux, Windows, and macOS;
- Python 3.11, 3.12, 3.13, and 3.14.

No 0.0.16 code or version metadata was required to make this design state pass. The
successful matrix confirms that the documentation and handoff changes preserve the merged
0.0.15 baseline.

## Design decisions validated as documentation contracts

The branch records these boundaries before implementation:

1. execution, bootstrap uncertainty, and separability remain distinct ordered subunits;
2. `ExecutionPlan` is implemented before any resampling or permutation code;
3. only sequential and thread execution are initially permitted;
4. source-event reductions retain stable order;
5. pointwise percentile intervals are not simultaneous confidence bands;
6. built-in bootstrap initially accepts only unit weights and fixed scalar bandwidths;
7. event-rate bootstrap is conditional on fixed exposure;
8. relative-risk cases and controls are resampled independently within group;
9. first-order separability requires complete product measured support;
10. the initial event-time permutation test explicitly assumes a Poisson or independent
    exchangeable-event interpretation;
11. finite Monte Carlo p-values use the plus-one rule;
12. non-Poisson tests, global envelopes, process pools, distributed execution, GPU,
    approximate kernels, PostGIS, and Zarr remain excluded.

## Exact next development unit

Implement only:

```text
0.0.16 Progress subunit 01: deterministic execution foundation
```

The unit must add immutable `ExecutionPlan`, conservative memory-budget resolution,
legacy-chunk compatibility, deterministic sequential/thread target-chunk execution,
metadata, tests, guide, API page, benchmark, and:

```text
HANDOFF_0.0.16_PROGRESS_01_EXECUTION_PLAN.md
```

Bootstrap and separability numerical implementation must not begin until that progress
unit passes the complete repository CI matrix.

## Validation boundary

This file is a status record added after CI #234. Its own later commit must not be confused
with the previously validated head. Inspect PR #16 and the latest workflow before claiming
that a newer branch head is validated. No unobserved result is asserted here.
