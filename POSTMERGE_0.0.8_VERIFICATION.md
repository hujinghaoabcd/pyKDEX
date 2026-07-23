# pyKDEX 0.0.8 post-merge verification

## Purpose

This document records the exact post-merge repository-state verification performed after the
pyKDEX 0.0.8 feature pull request was merged. It exists so a future conversation can distinguish
between feature-branch validation and validation of the actual repository state on `main`.

## Repository state under verification

- repository: `hujinghaoabcd/pyKDEX`;
- version: `0.0.8`;
- feature pull request: `#7 Add spatial boundary correction and anisotropic KDE`;
- feature squash merge commit: `9f0aef9e8be57cc9e1c6beb210225b421501a623`;
- post-merge handoff-record commit: `a7b1ae9461ab90c3ba7c89b6043693ffcb26e412`;
- exact verification source commit: `4e73ea1fc2812305f47c702444860e8c90ac9fd4`;
- verification pull request: `#8 Verify pyKDEX 0.0.8 post-merge repository state`;
- verification PR squash merge commit: `a865cec65bec76c5dd214b061c15dde32940a4aa`.

The verification branch was created directly from the exact current `main` source commit and only
changed Markdown recovery records. It did not introduce, replace, or temporarily modify the
permanent CI workflow.

## Verification runs

### Exact repository-state run

- GitHub Actions run: `#108`;
- run ID: `29975262281`;
- conclusion: `success`.

This run verified the post-merge source state before the actual run metadata was written into the
handoff record.

### Documentation-complete run

- GitHub Actions run: `#109`;
- run ID: `29975400636`;
- conclusion: `success`.

This second run verified the same source code together with the finalized post-merge recovery
record. It is the final observable CI result for the 0.0.8 unit.

## Checks completed

- `145 passed` in the regression test suite;
- branch coverage `81.41%`, above the required 80% threshold;
- Black formatting check;
- isort import-order check;
- Ruff static analysis;
- mypy type checking;
- 77 public symbols mapped to executable examples;
- strict MkDocs build;
- wheel and sdist construction;
- Twine metadata validation;
- distribution-content validation;
- installed-wheel smoke test;
- Linux, Windows, and macOS tests on Python 3.11, 3.12, 3.13, and 3.14.

## Infrastructure state

No temporary workflow was added for the post-merge verification. The repository's permanent
`.github/workflows/ci.yml` performed both runs. Earlier transfer, patch-application, export,
formatting, Ruff-fix, finalization, merge-recording, and diagnostic workflows were removed before
this verification.

## Final conclusion

pyKDEX 0.0.8 is complete, merged, documented, and verified against the actual post-merge
repository state. The next development unit may start from `main` without carrying forward any
pending 0.0.8 implementation or validation work.

The recommended next unit is `HeatNetworkKDE`, implemented as a separate metric-graph
heat-equation engine rather than as an alias for the ordinary Gaussian radial kernel.
