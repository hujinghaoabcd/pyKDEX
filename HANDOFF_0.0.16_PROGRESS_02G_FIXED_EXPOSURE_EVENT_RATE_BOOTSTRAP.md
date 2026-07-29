# pyKDEX 0.0.16 progress 02G: fixed-exposure event-rate Bootstrap

## Status

This development unit is complete on Draft PR #16.

Validated numerical implementation head:

```text
50686d4a05195c41d40c9acd0ec010d3a67c17f4
```

Validation:

```text
CI #416
run id 30416870784
conclusion: success
```

The package version remains `0.0.15`. PR #16 remains open, Draft, unmerged, and mergeable.

## Public API

Dedicated uncertainty transformation:

```python
from pykdex.uncertainty import bootstrap_event_rate

rate_bootstrap = bootstrap_event_rate(
    intensity_bootstrap,
    exposure,
    event_unit="event",
    zero_policy="raise",
)
```

This operation is intentionally separate from `bootstrap_kde`. It consumes an
already completed `BootstrapResult` whose ensemble family is `intensity`.

## Statistical meaning

The transformation propagates only the event-resampling uncertainty already
stored in the source intensity ensemble.

Exposure is:

- measured on the same exact support;
- treated as fixed;
- applied identically to observed and replicate intensity fields;
- never resampled;
- never assigned an implicit variance model.

The returned pointwise percentile intervals are therefore conditional on fixed
exposure. They do not represent uncertainty in population, traffic volume,
person-time, monitoring effort, or any other exposure measurement.

## Transformation

For every valid support element `j` and replicate `b`:

```text
rate[b, j] = intensity[b, j] / effective_exposure[j]
```

The observed field is transformed by the same denominator. The source event
count, seed ledger, logical replicate identities, and Bootstrap plan are retained.
No KDE is refitted and no new random stream is generated.

## Accepted source

The source must be:

- a `BootstrapResult`;
- produced by `operation="bootstrap_kde"`;
- represented by `FieldEnsemble(field_family="intensity")`;
- defined on the exact same measured-support fingerprint as the exposure.

This permits all completed measured intensity Bootstrap families:

```text
spatial_grid
network_lixel
spatiotemporal_grid
network_time_arixel
```

A measured `SpatiotemporalPointSupport` can also be transformed generically when
a valid intensity ensemble already exists, although no built-in ordinary
Bootstrap estimator adapter currently produces that support family.

Probability-density ensembles are rejected because density has discarded total
event mass.

## Denominator policy

The existing explicit risk policy is reused without modification:

```text
raise
nan
minimum
```

Rules:

- `raise`: reject exposure at or below `validity_threshold` before allocating the
  complete rate output;
- `nan`: mark those support columns invalid and retain NaN in observed, replicate,
  and interval arrays;
- `minimum`: replace exposure below the explicit positive
  `minimum_denominator`; adjusted cells remain valid.

No epsilon, pseudocount, clipping rule, or undocumented denominator is added.

The output validity mask is:

```text
source intensity valid mask
AND
finite effective exposure mask
```

For `minimum`, the explicit floor is finite, so adjusted cells remain valid. The
original invalid and adjusted exposure counts remain separately recorded.

## Fingerprints and provenance

Observed event-rate identity is derived from:

- source observed-intensity fingerprint;
- fixed exposure fingerprint;
- denominator-policy fingerprint;
- event unit;
- exact measured-support fingerprint.

Each replicate event-rate fingerprint is derived from its source replicate
fingerprint plus the same fixed exposure and policy contract.

Statistical fingerprints deliberately exclude the optional transformation memory
budget. Changing that operational budget does not change event-rate identity.

Metadata records:

```text
source_bootstrap_fingerprint
source_intensity_ensemble_fingerprint
source_observed_intensity_fingerprint
exposure_fingerprint
exposure_unit
exposure_representation
support_fingerprint
support_kind
event_unit
rate_unit
fixed_exposure = true
conditional_on_fixed_exposure = true
event_uncertainty = true
exposure_uncertainty = false
zero_policy
validity_threshold
minimum_denominator
invalid_denominator_count
adjusted_denominator_count
source_invalid_count
output_invalid_count
memory_model
```

The source seed metadata, seed-ledger fingerprint, replicate execution metadata,
and confidence level are preserved.

## Memory contract

`bootstrap_event_rate` accepts an explicit optional `memory_budget_bytes`.

It does not silently reuse the source estimator's execution budget because that
budget described the earlier KDE operation rather than this derived-field peak.

Preflight includes:

- the already resident source intensity ensemble;
- exposure values and support measure;
- effective denominator and masks;
- the complete event-rate replicate matrix;
- observed event-rate values;
- output validity mask;
- conservative elementwise working storage.

If the estimated peak exceeds the explicit budget, the operation raises
`MemoryError` before allocating the complete output ensemble.

## Returned result

The function returns:

```text
BootstrapResult(
    operation="bootstrap_event_rate",
    field_family="event_rate",
)
```

The source `BootstrapPlan`, random-state metadata, confidence level, and
estimator-family label are retained. A new `FieldEnsemble` and
`PointwiseInterval` are created for event rates.

## Tests added

```text
tests/test_bootstrap_event_rate.py
```

Coverage includes:

- spatial grid transformation;
- network lixel transformation;
- ordinary space-time product-grid transformation;
- network-time arixel transformation;
- exact manual matrix division;
- observed estimate and standard-error scaling;
- `raise`, `nan`, and `minimum` policies;
- explicit validity threshold;
- source and denominator invalid-mask combination;
- support mismatch;
- density source rejection;
- derived-operation source rejection;
- event-unit and metadata validation;
- memory-budget validation and fail-fast error;
- source and exposure immutability;
- fingerprint independence from memory budget;
- exposure-dependent derived identity.

## Files added or changed

```text
src/pykdex/uncertainty/event_rate.py
src/pykdex/uncertainty/__init__.py
tests/test_bootstrap_event_rate.py
examples/23_fixed_exposure_event_rate_bootstrap.py
HANDOFF_0.0.16_PROGRESS_02G_FIXED_EXPOSURE_EVENT_RATE_BOOTSTRAP.md
docs/development/handoff-0.0.16-progress-02g-fixed-exposure-event-rate-bootstrap.md
docs/guides/bootstrap.md
docs/api/uncertainty.md
HANDOFF_NEXT_CONVERSATION.md
mkdocs.yml
```

## CI evidence

Clean implementation head `50686d4a05195c41d40c9acd0ec010d3a67c17f4`
passed CI #416 (`30416870784`), including:

- Black;
- isort;
- Ruff;
- mypy;
- public API example coverage;
- strict MkDocs;
- full tests and branch coverage;
- source and wheel builds;
- Twine and archive verification;
- installed-wheel smoke;
- Linux, Windows, and macOS;
- Python 3.11, 3.12, 3.13, and 3.14.

## Exact next unit

Begin 02H with a detailed design for independent case-control relative-risk
Bootstrap before numerical implementation.

The design must resolve:

1. how independently generated case and control density ensembles are paired;
2. whether the initial implementation requires equal replicate counts;
3. how distinct seed-ledger identities prove independent within-group resampling;
4. how shared fixed bandwidth and estimator contracts are validated from ensemble
   metadata;
5. how density normalization is checked for every observed and replicate field;
6. how the explicit control-denominator policy propagates to relative-risk and
   log-relative-risk masks;
7. how zero case density produces raw risk zero and log risk `-inf` without being
   mistaken for an invalid denominator;
8. how complete raw-risk and log-risk ensembles are budgeted;
9. whether the first release returns both fields in one result container or two
   linked `BootstrapResult` objects;
10. how the API rejects pooled case-control resampling and shared random streams.

Do not begin uncertain-exposure Bootstrap, pooled case-control resampling,
separability diagnostics, or permutation testing during 02H.
