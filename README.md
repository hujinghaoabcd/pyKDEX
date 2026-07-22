# pyKDEX

**pyKDEX** is an extensible Python framework for spatial, spatiotemporal,
network, and network-time kernel density estimation.

The package follows the engineering conventions of pyGWRx while keeping the
KDE architecture composition-based: domains, metrics, kernels, bandwidths,
corrections, supports, and estimators are independent components.

> Status: spatial KDE and fixed/adaptive network KDE are available. Canonical
> networks, OSMnx/NetworkX adapters, auditable snapping, lixels, reusable distance
> assets, junction policies, network CV bandwidth selection, and kNN network
> bandwidths are implemented.

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
