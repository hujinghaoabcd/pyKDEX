# pyKDEX active project structure

```text
pyKDEX/
├── src/pykdex/
│   ├── core/          fitted-state, validation, protocols, and results
│   ├── data/          events, support, boundaries, datasets, and provenance
│   ├── datasets/      deterministic spatial and network fixtures
│   ├── network/       topology, snapping, lixels, workspaces, heat, and bundles
│   ├── temporal/      linear and cyclic time domains
│   ├── spatiotemporal/ ordinary space-time distance and evaluation assets
│   ├── network_time/  network-time events, arixels, distances, and workspaces
│   ├── adapters/      NetworkX and OSMnx conversion and acquisition
│   ├── kernels/       normalized radial kernels and registry
│   ├── bandwidths/    spatial and network bandwidth strategies
│   ├── metrics/       distance strategies
│   ├── estimators/    user-facing estimators
│   ├── selection/     spatial/network CV objectives and scalar optimization
│   └── py.typed       inline typing marker
├── examples/          isolated runnable examples and API coverage map
├── tests/             numerical, behavioural, data, and packaging tests
├── docs/              MkDocs user and developer documentation
├── tools/             coverage and distribution verification utilities
├── benchmarks/        deterministic opt-in performance scripts
└── .github/workflows/ continuous integration
```

Only implemented and tested symbols enter the public API. Future estimator
families are added with complete data and numerical contracts rather than
empty placeholder classes.
