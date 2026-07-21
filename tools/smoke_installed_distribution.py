"""Smoke-test an installed pyKDEX distribution outside the source tree."""

from importlib.resources import files

import numpy as np

import pykdex

assert pykdex.__version__ == "0.0.2"
assert files("pykdex").joinpath("py.typed").is_file()
model = pykdex.SpatialKDE(bandwidth=1.0).fit(np.array([[0.0], [1.0]]))
values = model.evaluate(np.array([[0.5]]))
assert values.shape == (1,)
assert np.isfinite(values[0]) and values[0] > 0.0
print("Installed pyKDEX distribution smoke test passed.")
