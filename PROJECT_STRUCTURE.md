# pyKDEX active project structure

```text
pyKDEX/
├── src/pykdex/
│   ├── core/          fitted-state, validation, protocols, and results
│   ├── kernels/       normalized radial kernels and registry
│   ├── bandwidths/    bandwidth strategies
│   ├── metrics/       distance strategies
│   ├── estimators/    user-facing estimators
│   └── py.typed       inline typing marker
├── examples/          isolated runnable examples and API coverage map
├── tests/             numerical, behavioural, and packaging tests
├── docs/              MkDocs user and developer documentation
├── tools/             coverage and distribution verification utilities
└── .github/workflows/ continuous integration
```

The first baseline intentionally exposes only implemented and tested symbols.
Empty placeholder packages for future network and temporal algorithms are not
published as fake working APIs.
