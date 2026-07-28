# 0.0.15 progress 01: exposure-field foundation

This page summarizes the first completed subunit of pyKDEX 0.0.15. The complete,
recoverable engineering record is
`HANDOFF_0.0.15_PROGRESS_01_EXPOSURE_FIELD.md` in the repository root.

## Scope

The subunit adds the denominator data model required by later exposure-adjusted event
rates and case-control relative risk. It does not yet divide an event intensity by
exposure or calculate a case-control density ratio.

## Measured-support contract

Risk fields accept only validated measured pyKDEX supports:

- `GridSupport`;
- `LixelSupport`;
- `SpatiotemporalPointSupport` with explicit `support_measure`;
- `SpatiotemporalGridSupport`;
- `ArixelSupport`.

`SupportDescriptor` retains the support kind, stable identifiers, positive integration
measures, fingerprint, CRS, spatial and temporal units, time-domain fingerprint, and
native output shape. Equal array shape is not treated as support compatibility.

## Exposure convention

`ExposureField` stores exposure density `e_j` with respect to each support measure
`m_j`. Per-element amount and total exposure are

```text
E_j = e_j * m_j
E_total = sum_j e_j * m_j
```

Construction is available from density or from per-element amounts. The amount
constructor divides by the actual cell, lixel, space-time, or arixel measure, including
remainder elements with non-nominal size.

The field is immutable, retains an explicit exposure unit and provenance, provides a
deterministic fingerprint, and exports tabular, grid, or geospatial forms when the
underlying support supports them.

## Validation

The focused tests cover spatial grids, measured space-time points, space-time grids,
network lixels, and network-time arixels. They verify exact amount-density conversion,
integration, support identity, domain metadata, immutability, zero fields, and invalid
input rejection.

PR CI run #146 (`30348884054`) passed the complete quality, coverage, distribution, and
Linux/Windows/macOS Python 3.11-3.14 matrix. A first run found only a Black formatting
failure; it was corrected, and the temporary formatting diagnostic workflow was
removed before the clean run.

## Next subunit

The next implementation step adds explicit denominator policies, a closed intensity
result adapter, `EventRateField`, and `estimate_event_rate(...)`. The first version will
support `raise`, `nan`, and explicit positive-minimum denominator handling and will
reject probability-density numerators.
