# 0.0.15 progress 03: shared-bandwidth relative risk

This page summarizes the third numerical subunit of pyKDEX 0.0.15. The complete,
recoverable engineering record is
`HANDOFF_0.0.15_PROGRESS_03_RELATIVE_RISK.md` in the repository root.

## Scope

This subunit implements shared-fixed-bandwidth case-control relative risk on measured
spatial, network, space-time, and network-time supports. It is distinct from the
exposure-adjusted event rate implemented in progress subunit 02.

For independently normalized case and control densities,

```text
relative_risk_j = case_density_j / control_density_j
log_relative_risk_j = log(case_density_j) - log(control_density_j)
```

Both densities must integrate to approximately one using the actual cell, lixel,
space-time, or arixel measures. The tolerance is explicit and no automatic
renormalization is performed.

## Closed density adapters

The internal adapter accepts only:

- `SpatialKDEResult`;
- `NetworkField`;
- `SpatiotemporalKDEResult`;
- `NetworkTimeField`.

Both inputs require `target="density"`. Compatibility is based on exact measured
support and shared estimator configuration rather than array shape or complete metadata
equality.

Event fingerprints, event counts, and weights may differ. Support identity, fixed
bandwidths, kernels, metrics, boundary or junction policies, direction, network
identity, CRS, units, and temporal domain must agree where applicable.

Spatial results require an explicit `GridSupport` because the result object does not
retain the complete grid geometry. The other three result families can infer their
embedded measured support.

## Shared fixed bandwidths

The initial implementation accepts only positive scalar fixed bandwidths:

- one scalar for spatial and network density;
- one spatial scalar and one temporal scalar for space-time and network-time density.

Adaptive arrays, spatial bandwidth matrices, and unequal case/control bandwidths are
rejected. Bandwidth selection is outside this subunit.

## RelativeRiskField

The immutable field retains:

- raw and log relative risk;
- original case and control density;
- effective control density after denominator handling;
- invalid and adjusted control masks;
- exact measured support;
- shared bandwidth and estimator contract;
- separate case and control source fingerprints and metadata;
- density integrals and normalization tolerance;
- deterministic fingerprint and table/grid/geospatial exports.

The functional API is:

```python
risk = estimate_relative_risk(
    case_density,
    control_density,
    support=grid_support,
    zero_policy="raise",
    normalization_tolerance=1e-6,
)
```

`support` is required only for spatial results.

## Zero-density behavior

No epsilon or pseudocount is hidden.

- zero case density with a valid control gives raw risk `0` and log risk `-inf`;
- invalid control density follows explicit `raise`, `nan`, or `minimum` policy;
- positive-infinite raw risk is never stored;
- minimum flooring retains both original invalid and adjusted masks.

## Analytical validation

Tests cover:

- reciprocal raw risk and sign-reversed log risk after swapping case and control;
- control-weighted normalization;
- density-integral tolerance;
- all denominator policies;
- zero-case negative-infinite log risk;
- rejection of intensity, non-normalized density, adaptive bandwidth, unequal bandwidth,
  estimator-contract mismatch, and support mismatch;
- unequal-measure spatial grids;
- lixel networks;
- cyclic ordinary space-time grids;
- cyclic network-time arixels.

The first CI run stopped at Black formatting. A temporary branch-only formatter
produced exact Black/isort output and was deleted immediately. Corrected implementation
CI `#177` (`30353630091`) passed quality, strict documentation, coverage,
distributions, isolated-wheel smoke testing, and Linux/Windows/macOS tests on Python
3.11-3.14.

## Next subunit

Complete the 0.0.15 release surface:

1. finalize top-level exports and signatures;
2. add the public risk guide and API reference;
3. add an executable end-to-end example and API mapping;
4. update README, roadmap, release notes, and version metadata;
5. create the final 0.0.15 handoff;
6. complete PR, merge, and post-merge `main` validation.

Bandwidth selection, adaptive risk, inference, uncertainty, and scalable execution stay
outside the finalization unit.
