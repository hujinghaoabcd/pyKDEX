# Built-in datasets

The first data release contains deterministic synthetic bundles rather than
large third-party downloads.

```python
from pykdex import load_bimodal_points, load_bounded_square

bimodal = load_bimodal_points(random_state=42)
bounded = load_bounded_square()
```

`load_bimodal_points` provides weighted-ready spatial events, a measured regular
grid, and a rectangular boundary. `load_bounded_square` places events near the
edge of a unit square for future boundary-correction validation.

Synthetic generators accept `random_state` and produce stable fingerprints.
Road-network fixtures, including T-junction, ring, directed, parallel-edge, and
small OSMnx-derived networks, belong to the next development unit.
