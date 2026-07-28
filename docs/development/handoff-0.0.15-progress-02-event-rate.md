# 0.0.15 progress 02: exposure-adjusted event rates

This page summarizes the second development subunit of pyKDEX 0.0.15. The complete,
recoverable engineering record is
`HANDOFF_0.0.15_PROGRESS_02_EVENT_RATE.md` in the repository root.

## Scope

This subunit implements exposure-adjusted event rates on measured spatial, network,
space-time, and network-time supports. It builds on the immutable `ExposureField`
foundation and does not yet implement case-control relative risk.

For support measure `m_j`, event intensity `lambda_j`, and exposure density `e_j`, the
rate is

```text
q_j = lambda_j / e_j
```

The numerator must be an intensity field. Probability-density results are rejected
because their normalization has removed total event mass.

## Explicit denominator handling

`DenominatorPolicy` supports exactly:

- `raise`: reject denominators at or below an explicit validity threshold;
- `nan`: return `NaN` and retain an invalid-cell mask;
- `minimum`: floor denominators at an explicit positive minimum and retain both invalid
  and adjusted masks.

No hidden epsilon or infinite stored rate is allowed.

## Closed result adapters

The internal intensity adapter accepts only:

- `SpatialKDEResult`;
- `NetworkField`;
- `SpatiotemporalKDEResult`;
- `NetworkTimeField`.

Compatibility is based on measured-support fingerprints, identifiers, measures, CRS,
units, temporal domains, and estimator-specific metadata. Matching array shape is not
sufficient.

## EventRateField

The immutable result retains:

- rates and original event intensity;
- original and effective exposure;
- invalid and adjusted masks;
- event and exposure units;
- source intensity and exposure fingerprints;
- measured support and estimator metadata;
- event mass, exposure totals, and documented exposure-weighted summaries.

The functional API is:

```python
rate = estimate_event_rate(
    event_intensity,
    exposure,
    event_unit="events",
    zero_policy="raise",
)
```

These APIs are currently exported from `pykdex.risk`. Top-level exports and the final
example are deferred until the complete 0.0.15 API is stable.

## Validation

Analytical tests cover constant rates, event/exposure scaling, all denominator policies,
unequal spatial measures, lixel lengths, cyclic space-time grids, and cyclic arixels.

The first event-rate CI run stopped at Black formatting. A temporary branch-only
formatter workflow generated the exact Black/isort correction and was then deleted.
The corrected CI run is `#162` (`30351398127`); its complete conclusion must be copied
from GitHub only after it is observed.

## Next subunit

Implement shared-fixed-bandwidth case-control relative risk:

1. closed density-result adapters;
2. exact support and estimator compatibility;
3. separately normalized case and control densities;
4. raw and log relative-risk fields;
5. explicit control-denominator policies;
6. reciprocal, sign-reversal, normalization, and four-domain analytical tests.

Adaptive risk, independent bandwidths, bandwidth selection, inference, uncertainty,
separability diagnostics, and scalable execution remain excluded.
