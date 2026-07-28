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
```

::: pykdex.uncertainty.bootstrap_kde

## Pointwise percentile summary

::: pykdex.uncertainty.pointwise_percentile_interval
