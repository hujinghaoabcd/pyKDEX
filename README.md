# pyKDEX

**pyKDEX** is an extensible Python framework for spatial, spatiotemporal,
network, and network-time kernel density estimation.

The package follows the engineering conventions of pyGWRx while keeping the
KDE architecture composition-based: domains, metrics, kernels, bandwidths,
corrections, supports, and estimators are independent components.

> Status: spatial KDE and data-foundation development release. Validated event,
> support, boundary, dataset, provenance, and fingerprint objects are available.
> Network and temporal estimators are not yet exposed as working models.

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
