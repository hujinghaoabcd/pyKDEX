# pyKDEX handoff

## Current status

- development version: `0.0.2`;
- public estimator: `SpatialKDE`;
- scalar bandwidths: fixed, likelihood CV, and Gaussian LSCV;
- event-specific bandwidths: kNN and Abramson;
- tests: 57 passed;
- branch coverage: 84.1%;
- formatting, linting, typing, strict documentation, build, and installation
  checks pass locally;
- no runtime dependency on external KDE implementations.

## Next recommended development unit

Complete the ordinary spatial KDE family before introducing time or networks:

1. reflection and renormalization boundary correction;
2. anisotropic bandwidth matrices;
3. balloon kNN bandwidths;
4. relative-risk density ratios with denominator safeguards;
5. bootstrap uncertainty for spatial density and intensity;
6. independent mass, boundary-bias, and analytical Gaussian tests.

Do not expose temporal or network placeholder models before their mathematical
contracts and reference fixtures are implemented.
