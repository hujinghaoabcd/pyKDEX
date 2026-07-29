# Uncertainty API

## Bootstrap plan

::: pykdex.uncertainty.BootstrapPlan

## Bootstrap result

::: pykdex.uncertainty.BootstrapResult

## Field ensemble

::: pykdex.uncertainty.FieldEnsemble

## Pointwise interval

::: pykdex.uncertainty.PointwiseInterval

## Built-in KDE bootstrap dispatch

`bootstrap_kde` currently dispatches closed ordinary-Bootstrap adapters for:

```text
SpatialKDE + SpatialEvents + GridSupport
NetworkKDE + NetworkWorkspace
HeatNetworkKDE + NetworkWorkspace
SpatiotemporalKDE + SpatiotemporalEvents + SpatiotemporalGridSupport
TemporalNetworkKDE + NetworkTimeWorkspace
```

::: pykdex.uncertainty.bootstrap_kde

## Fixed-exposure event-rate Bootstrap

Transform a completed intensity Bootstrap into event-rate uncertainty conditional on one
fixed measured exposure field.

::: pykdex.uncertainty.bootstrap_event_rate

## Pointwise percentile summary

::: pykdex.uncertainty.pointwise_percentile_interval
