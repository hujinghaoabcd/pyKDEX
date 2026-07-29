# pyKDEX 0.0.16 design handoff: independent relative-risk Bootstrap

## Status

This is the recovery record for design-only subunit 02H. Numerical
relative-risk Bootstrap has not been implemented.

Primary design:

```text
docs/development/design-0.0.16-relative-risk-bootstrap.md
```

The package version remains `0.0.15`. Draft PR #16 remains open and unmerged.

## Proposed closed operation

```text
independent case density BootstrapResult
independent control density BootstrapResult
    -> linked raw relative-risk and log-relative-risk Bootstrap results
```

Provisional function name:

```text
bootstrap_relative_risk
```

Provisional linked return type:

```text
RelativeRiskBootstrapResult
```

No public symbol should be added until the implementation subunits pass full CI.

## Fixed design decisions

### Independent group resampling

- case and control ordinary Bootstrap ensembles are generated separately;
- the ratio operation generates no new random numbers;
- seed-ledger fingerprints must differ;
- source-event provenance must distinguish the groups;
- pooled observations, label resampling, and mark permutation are excluded.

### Equal replicate counts

The first release requires:

```text
B_case == B_control
```

Rows pair by the same logical replicate index. Unequal counts, truncation,
recycling, random rematching, and Cartesian expansion are rejected.

### Exact shared contract

Case and control must share:

- exact measured support;
- estimator family;
- normalized fixed estimator contract;
- fixed scalar bandwidths or fixed heat parameters;
- kernels, metric or junction policy;
- direction, boundary, network, and time-domain choices where applicable.

Before numerical implementation, all completed density Bootstrap adapters must
expose normalized auditable relative-risk contract metadata in addition to the
existing contract fingerprint.

### Complete probability densities

Observed and every replicate case/control field must be finite, non-negative, and
integrate to one within explicit `normalization_tolerance`.

The initial operation requires all-true source validity masks. It never silently
renormalizes rows or drops support cells.

### Denominator policy

Control density uses the existing explicit policy:

```text
raise
nan
minimum
```

No epsilon or pseudocount.

`nan` uses a conservative 1D support mask because current `FieldEnsemble` cannot
represent replicate-specific validity. A column is valid only when observed and
all replicate control densities are valid there. Complete observed and `(B, M)`
invalid/adjusted control masks remain in the linked result for audit.

### Zero case density

At a valid denominator:

```text
case = 0 -> raw risk = 0, log risk = -inf
```

This is valid case behavior, not denominator failure. Positive infinity is never
allowed.

### Linked outputs

The design returns a dedicated immutable container linking:

- raw-risk `BootstrapResult`;
- log-risk `BootstrapResult`;
- policy and normalization tolerance;
- case/control source and seed identities;
- deterministic pairing rule;
- observed and replicate denominator masks;
- shared metadata and fingerprint.

A plain tuple is not accepted because linkage would be unvalidated.

### Memory

Use an explicit derived-operation memory budget. Preflight includes resident case
and control ensembles, full raw and log output matrices, complete denominator
masks, observed fields, intervals, and working rows. Source KDE budgets are not
silently reused.

## Required implementation sequence

```text
02H-1 normalized shared density-contract metadata
02H-2 linked result and validation types
02H-3 paired raw/log transform and memory preflight
02H-4 analytical and independent numerical fixtures
02H-5 guide, example, API docs, and final handoff
```

Every subunit must update a detailed recovery record.

## Required tests

- equal densities -> raw one, log zero;
- reciprocal/negated swap identity;
- exact manual paired matrices;
- distinct seed ledgers and source events;
- equal replicate count and confidence level;
- exact support and contract equality;
- every observed/replicate density integrates to one;
- `raise`, conservative `nan`, and explicit `minimum` policies;
- zero case -> zero / `-inf`;
- log empirical quantiles with `-inf`;
- all measured support families;
- memory failure before output allocation;
- source immutability;
- independent NumPy reference fixtures.

## Methodological references

- Efron (1979), DOI 10.1214/aos/1176344552;
- Kelsall and Diggle (1995), Bernoulli 1:3-16;
- Kelsall and Diggle (1995), DOI 10.1002/sim.4780142106;
- Hazelton and Davies (2009), DOI 10.1002/bimj.200810495;
- Davies and Hazelton (2010), DOI 10.1002/sim.3995;
- Davies, Marshall, and Hazelton (2018), DOI 10.1002/sim.7577;
- Kern et al. (2003), DOI 10.1023/A:1026092103819.

## Do not implement yet

Until the design-only head passes strict docs and full CI, do not add:

- `bootstrap_relative_risk`;
- `RelativeRiskBootstrapResult`;
- numerical raw/log ratio ensembles;
- pooled case-control resampling;
- permutation p-values or tolerance contours;
- adaptive/independently selected bandwidths;
- unequal replicate counts;
- simultaneous bands;
- package version changes;
- ready-for-review transition or merge.
