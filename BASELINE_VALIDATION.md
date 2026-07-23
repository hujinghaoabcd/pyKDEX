# pyKDEX 0.0.10 validation

Validation date: 2026-07-23

## Implemented public functionality

- scalar, cross-validated, sample-point kNN, and Abramson spatial bandwidths;
- global positive-definite bandwidth matrices and query-centred balloon kNN;
- polygon study-domain validation, renormalization, and rectangular reflection;
- public fixed/adaptive `NetworkKDE` with three junction policies;
- exact reusable network distances, propagation traces, network CV, and network kNN;
- finite-element `HeatNetworkKDE` on undirected measured metric graphs;
- reusable `NetworkHeatOperator` and `HeatComputePlan` assets;
- ordered batched heat diffusion-time experiments;
- heat likelihood and exact finite-element least-squares diffusion-time selection;
- structured spatial/network data, support measures, provenance, snapping, and
  deterministic fingerprints.

## Heat-plan and batch validation

- dense plans reuse one read-only symmetric eigendecomposition;
- sparse plans retain a read-only generator and use Krylov exponential products;
- multi-source/multi-time output preserves requested order and duplicate times;
- sparse and dense routes agree numerically on the same measured operator;
- event heat-transition matrices are symmetric on undirected measured graphs;
- compute plans reject incompatible network, accepted-event, and lixel fingerprints;
- explicit estimator/experiment mesh size must agree with the supplied plan;
- batch fields equal independent `HeatNetworkKDE` fits;
- every density batch field integrates to one at numerical precision;
- long-form batch output records batch index and diffusion time;
- plan memory accounting covers sparse generator and optional spectral arrays.

## Heat-selection validation

- heat likelihood deletes only an event's own diagonal contribution;
- weighted LOO normalization uses total weight minus the target event weight;
- coincident distinct events remain valid contributors;
- heat LSCV integrates the squared piecewise-linear field exactly;
- explicit diffusion-time bounds are validated and searched on a log scale;
- automatic bounds derive from positive finite event network distances and map
  distance scale through \(t=h^2/2\);
- likelihood and LSCV selection are deterministic;
- both selection strategies integrate with `HeatNetworkKDE`;
- fitted metadata records selected time, equivalent Gaussian distance, plan
  identity, solver, memory, and mass diagnostics.

## Existing numerical validation retained

- scalar and matrix spatial bandwidth equivalence;
- SciPy multivariate-normal agreement for anisotropic Gaussian KDE;
- rectangular analytical and general-polygon measured boundary renormalization;
- reflection mass behavior and explicit unsupported-combination failures;
- event/lixel exact network distances and path propagation contracts;
- simple, discontinuous, and continuous `NetworkKDE` reference behavior;
- finite-interval Neumann and periodic-ring heat-kernel references;
- shared-junction continuity and Kirchhoff/Neumann heat conditions;
- per-component density/intensity mass conservation;
- atomic failed-fit state reset.

## Final observed validation

- pytest: `178 passed`;
- branch coverage: `81.67%`, above required `80%`;
- public API/example map: `91 public symbols`;
- executable examples: `12`;
- deterministic 6x6 grid benchmark: batch and independent fields differ by `0.0`;
- local sample benchmark: 81 heat DOFs, 116 segments, 57,220 plan bytes,
  approximately 3.14x batch speedup excluding plan construction;
- Black, isort, Ruff, mypy, strict MkDocs, distributions, and isolated wheel
  smoke: passed;
- PR #10 first complete GitHub Actions run `#118` (`29996503549`): success
  across quality, coverage, distributions, Linux/Windows/macOS, and Python
  3.11-3.14;
- final clean PR CI run `#119` (`29996740029`): success;
- PR #10 squash merge commit:
  `49bb6ba36f9ac1dc82a655ee23a06397dba0a529`;
- PR #10 merged and closed successfully.

## Deliberate exclusions

- directed heat flow and self-loop heat elements;
- variable diffusivity, drift, absorption, and alternate vertex/terminal conditions;
- persistent heat-plan serialization and incremental event-source updates;
- sparse multi-time Krylov interval acceleration beyond generator reuse;
- spatiotemporal and network-time KDE;
- exposure-adjusted risk, bootstrap uncertainty, workspace persistence, and
  compiled acceleration.
