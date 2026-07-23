"""Smoke-test an installed pyKDEX distribution outside the source tree."""

from importlib.resources import files

import numpy as np

import pykdex

assert pykdex.__version__ == "0.0.9"
assert files("pykdex").joinpath("py.typed").is_file()
events = pykdex.SpatialEvents.from_array([[0.0, 0.0], [1.0, 1.0]])
support = pykdex.GridSupport.from_bounds((0.0, 0.0, 1.0, 1.0), resolution=0.5)
model = pykdex.SpatialKDE(bandwidth=1.0).fit(events)
values = model.evaluate(np.array([[0.5, 0.5]]))
result = model.predict_result(support)
assert values.shape == (1,)
assert np.isfinite(values[0]) and values[0] > 0.0
assert result.to_grid().shape == support.shape
print("Installed pyKDEX distribution smoke test passed.")
