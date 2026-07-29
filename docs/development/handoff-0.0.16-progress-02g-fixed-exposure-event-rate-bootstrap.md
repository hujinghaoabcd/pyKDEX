# pyKDEX 0.0.16 progress 02G: fixed-exposure event-rate Bootstrap

## Completion record

The fixed-exposure event-rate Bootstrap transformation is complete on Draft PR
#16. Package metadata remains at `0.0.15`; the PR remains Draft and unmerged.

Validated implementation head:

```text
50686d4a05195c41d40c9acd0ec010d3a67c17f4
```

Full validation:

```text
CI #416
run id 30416870784
conclusion: success
```

## Public operation

```python
from pykdex.uncertainty import bootstrap_event_rate
```

The function transforms a completed `bootstrap_kde` intensity result using one
fixed `ExposureField`. It creates an `event_rate` ensemble and pointwise interval
without refitting KDE or generating new random streams.

## Inferential boundary

Only event-resampling uncertainty is propagated. Exposure is conditioned upon,
never resampled, and explicitly labelled `exposure_uncertainty=False`.

The operation accepts exact measured supports, reuses the existing explicit
`raise`, `nan`, or `minimum` denominator policy, and introduces no hidden epsilon.

## Identity and execution

Source seed metadata and replicate identities are retained. Derived field
fingerprints combine source intensity identity, fixed exposure, denominator
policy, event unit, and support. Optional memory budgets are operational and do
not change statistical identity.

## Memory

The preflight peak includes the resident source intensity ensemble and the
complete transformed output ensemble. A dedicated optional budget is used rather
than silently reusing the earlier KDE execution budget.

## Next unit

02H begins with detailed design for independent case-control relative-risk
Bootstrap. Do not immediately implement numerical ratios before resolving equal
replicate counts, independent seed ledgers, shared bandwidth metadata,
normalization checks, raw/log linked outputs, and complete memory accounting.
