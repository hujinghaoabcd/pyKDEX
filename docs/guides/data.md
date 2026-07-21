# Data objects

pyKDEX accepts NumPy arrays and pandas DataFrames for lightweight workflows, but
reproducible geospatial analysis should use the validated data objects in
`pykdex.data`.

## Spatial events

`SpatialEvents` owns event coordinates, weights, identifiers, marks, CRS, units,
and provenance. Arrays are copied and made read-only.

```python
from pykdex import SpatialEvents

events = SpatialEvents.from_array(
    coordinates,
    weights=severity,
    ids=event_ids,
    crs="EPSG:3857",
    spatial_unit="m",
)
```

`SpatialKDE.fit(events)` automatically uses the weights stored in the object.
Passing a second `weights` argument is rejected to avoid ambiguous inputs.

## Point and grid support

`PointSupport` stores arbitrary evaluation locations. `GridSupport` additionally
stores one area per cell, including smaller remainder cells at the grid boundary.
This allows a result to approximate its integral directly.

```python
from pykdex import GridSupport, SpatialKDE

grid = GridSupport.from_bounds(
    (0.0, 0.0, 1000.0, 800.0),
    resolution=25.0,
    crs="EPSG:3857",
    spatial_unit="m",
)
result = SpatialKDE(bandwidth=100.0).fit_predict(events, grid)
print(result.integral())
image = result.to_grid()
```

## Boundaries and datasets

`SpatialBoundary` records a polygonal study area. `KDEDataset` bundles events,
support, a boundary, expected reference values, and provenance.

```python
from pykdex import KDEDataset, SpatialBoundary

boundary = SpatialBoundary.from_bounds((0.0, 0.0, 1000.0, 800.0))
dataset = KDEDataset(
    name="example",
    events=events,
    support=grid,
    boundary=boundary,
)
report = dataset.validate()
report.raise_for_errors()
```

Validation reports use stable issue codes for dimension, CRS, unit, duplicate,
and boundary checks. Warnings do not make a report invalid; errors do.

## Fingerprints and provenance

Every structured data object exposes a deterministic `fingerprint`. It changes
when relevant content or provenance changes and will later identify reusable
network workspaces and distance assets.
