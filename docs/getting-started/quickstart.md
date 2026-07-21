# Quick start

```python
import numpy as np
from pykdex import SpatialKDE

events = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
support = np.array([[0.25, 0.25], [0.75, 0.75]])

result = SpatialKDE(bandwidth=0.5).fit_predict(events, support)
print(result.to_frame())
```
