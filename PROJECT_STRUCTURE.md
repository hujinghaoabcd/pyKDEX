# pyKDEX active project structure

```text
pyKDEX/
├── src/pykdex/
│   ├── core/          fitted-state, validation, protocols, and results
│   ├── data/          events, support, boundaries, datasets, and provenance
│   ├── datasets/      deterministic loaders and synthetic generators
│   ├── kernels/       normalized radial kernels and registry
│   ├── bandwidths/    bandwidth strategies
│   ├── metrics/       distance strategies
│   ├── estimators/    user-facing estimators
│   ├── selection/     CV objectives and scalar optimization
│   └── py.typed       inline typing marker
├── examples/          isolated runnable examples and API coverage map
├── tests/             numerical, behavioural, data, and packaging tests
├── docs/              MkDocs user and developer documentation
├── tools/             coverage and distribution verification utilities
└── .github/workflows/ continuous integration
```

Only implemented and tested symbols enter the public API. Future network and
temporal packages will be added with real data contracts rather than empty
placeholder classes.
