# pyKDEX

**pyKDEX** is an extensible Python framework for spatial, spatiotemporal,
network, and network-time kernel density estimation.

The package follows the engineering conventions of pyGWRx while keeping the
KDE architecture composition-based: domains, metrics, kernels, bandwidths,
corrections, supports, and estimators are independent components.

> Status: spatial KDE includes scalar, sample-point, balloon, matrix, and boundary-corrected estimators. Ordinary product-kernel spatiotemporal KDE supports linear/cyclic time and measured space-time grids. Fixed/adaptive radial network KDE, measured finite-element heat-equation NetworkKDE, and fixed/adaptive temporal-network KDE are implemented alongside canonical networks, auditable snapping, reusable assets, and bandwidth selection.

## Installation

```bash
python -m pip install -e ".[test]"
```

## Quick start

```python
import numpy as np
from pykdex import SpatialKDE

rng = np.random.default_rng(42)
events = rng.normal(size=(200, 2))
support = rng.normal(size=(20, 2))

model = SpatialKDE(kernel="gaussian", bandwidth=0.5, target="density")
model.fit(events)
result = model.predict_result(support)

print(result.values)
print(result.to_frame().head())
```



## Structured data workflow

```python
from pykdex import GridSupport, SpatialEvents, SpatialKDE

events = SpatialEvents.from_array(
    coordinates,
    weights=weights,
    crs="EPSG:3857",
    spatial_unit="m",
)
grid = GridSupport.from_bounds(
    bounds,
    resolution=100.0,
    crs="EPSG:3857",
    spatial_unit="m",
)
result = SpatialKDE(bandwidth=500.0).fit_predict(events, grid)
print(result.integral())
```

## Network data preparation

```python
from pykdex import NetworkWorkspace, load_t_junction

dataset = load_t_junction()
workspace = NetworkWorkspace.prepare(
    dataset.network,
    dataset.raw_events,
    lixel_length=0.25,
    max_snap_distance=0.2,
)
print(workspace.summary())
```

Install external graph adapters with `python -m pip install "pyKDEX[network]"`.
OSM downloads additionally require `python -m pip install "pyKDEX[osm]"`.

## Bandwidth selection and adaptation

```python
from pykdex import (
    AbramsonBandwidth,
    KNNBandwidth,
    LikelihoodCVBandwidth,
    SpatialKDE,
)

selected = SpatialKDE(
    bandwidth=LikelihoodCVBandwidth(bounds=(0.1, 2.0))
).fit(events)

knn = SpatialKDE(bandwidth=KNNBandwidth(k=20)).fit(events)
adaptive = SpatialKDE(bandwidth=AbramsonBandwidth(0.5)).fit(events)
```


## Spatial boundaries, matrices, and balloon bandwidths

```python
import numpy as np
from pykdex import (
    BalloonKNNBandwidth,
    BandwidthMatrix,
    SpatialBoundary,
    SpatialKDE,
)

boundary = SpatialBoundary.from_bounds((0.0, 0.0, 1000.0, 1000.0))
corrected = SpatialKDE(
    bandwidth=100.0,
    boundary=boundary,
    boundary_correction="renormalization",
).fit(events)

anisotropic = SpatialKDE(
    bandwidth=BandwidthMatrix(np.array([[40000.0, 12000.0], [12000.0, 16000.0]]))
).fit(events)

balloon = SpatialKDE(
    bandwidth=BalloonKNNBandwidth(k=20, minimum_bandwidth=10.0)
).fit(events)
```

Renormalization supports Polygon/MultiPolygon study areas. Rectangular Gaussian domains use analytical probabilities; general polygons use deterministic measured-cell quadrature. Reflection is explicit and restricted to axis-aligned rectangles with scalar, event-specific scalar, or diagonal matrix bandwidths.

## Network bandwidth selection and adaptation

```python
from pykdex import (
    NetworkKDE,
    NetworkKNNBandwidth,
    NetworkLikelihoodCVBandwidth,
)

selected_network = NetworkKDE(
    bandwidth=NetworkLikelihoodCVBandwidth(bounds=(100.0, 3000.0)),
    junction_policy="simple",
).fit(workspace)

adaptive_network = NetworkKDE(
    bandwidth=NetworkKNNBandwidth(k=20, minimum_bandwidth=5.0),
    junction_policy="continuous",
).fit(workspace)
```

Network LSCV uses actual lixel lengths for the squared-density integral. Event-to-event
distance assets and upper-bound propagation traces are reused during optimization.

## Heat-equation network KDE

```python
from pykdex import HeatNetworkKDE

heat = HeatNetworkKDE(
    diffusion_time=2500.0,
    mesh_size=25.0,
).fit_predict(workspace)

print(heat.integral())
```

Heat smoothing is an independent metric-graph engine, not a kernel name passed
to `NetworkKDE`. Shared finite-element vertex values enforce continuity,
Kirchhoff balance controls junction flux, and terminal vertices use zero-flux
Neumann conditions. The output contains exactly integrated lixel cell averages.

## Ordinary spatiotemporal KDE

```python
from pykdex import (
    CyclicTimeDomain,
    SpatiotemporalEvents,
    SpatiotemporalKDE,
    SpatiotemporalPointSupport,
)

time_of_day = CyclicTimeDomain(period=24.0)
events_st = SpatiotemporalEvents.from_arrays(
    coordinates,
    event_hours,
    spatial_unit="km",
    temporal_unit="hours",
    time_domain=time_of_day,
)
support_st = SpatiotemporalPointSupport.from_arrays(
    query_coordinates,
    query_hours,
    spatial_unit="km",
    temporal_unit="hours",
    time_domain=time_of_day,
)
result_st = SpatiotemporalKDE(
    spatial_bandwidth=0.5,
    temporal_bandwidth=2.0,
).fit_predict(events_st, support_st)
```

Spatial and temporal units remain independent. Cyclic kernels use periodic
image sums, and measured space-time grids can be exported with the optional
`pyKDEX[array]` dependencies.

## Temporal-network KDE

```python
from pykdex import NetworkTimeWorkspace, TemporalNetworkKDE

network_time = NetworkTimeWorkspace.prepare(
    network,
    spatial_events,
    event_times,
    temporal_unit="hours",
    lixel_length=25.0,
    temporal_resolution=1.0,
    temporal_bounds=(0.0, 24.0),
    max_snap_distance=50.0,
)
field = TemporalNetworkKDE(
    spatial_bandwidth=500.0,
    temporal_bandwidth=2.0,
    junction_policy="continuous",
).fit_predict(network_time)

print(field.integral())
```

`ArixelSupport` uses actual lixel length multiplied by actual temporal-cell
width. Network distances and temporal offsets are stored as a factorized
reusable asset rather than an expanded event-by-arixel matrix.

## Persistent prepared workspaces

```python
workspace = (
    workspace.with_event_lixel_distances(cutoff=1000.0)
    .with_event_event_distances()
)
workspace.save("city-network.pykdex")

restored = NetworkWorkspace.load("city-network.pykdex")
assert restored.fingerprint == workspace.fingerprint
```

The portable format contains canonical JSON, non-object NumPy arrays, and WKB
geometry. It never uses pickle. Every payload has a declared byte size and
SHA-256 digest, and loading reconstructs and validates the full object graph.
Use `format="directory"` for an inspectable directory bundle.

## Initial design commitments

- independent in-package numerical implementation;
- no runtime calls to spNetwork, spatstat, PyNKDV, or other KDE packages;
- single NumPy/SciPy numerical route with hidden future acceleration;
- atomic fitted-state replacement and strict input validation;
- structured result objects and geospatial export;
- static reference fixtures for independent numerical validation;
- complete public-API example coverage as the package grows.

## Licence

MIT. See `THIRD_PARTY_NOTICES.md` for research references and implementation
independence notes.
