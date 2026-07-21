# pyKDEX

**pyKDEX** 是一个面向普通空间、时空、线性网络及时空网络核密度估计的可扩展 Python 框架。

项目沿用 pyGWRx 的工程规范，但 KDE 使用组合式架构：定义域、距离、核函数、带宽、修正方法、评估支撑和估计器彼此解耦。

当前版本已实现固定带宽、似然交叉验证、Gaussian LSCV、k 近邻自适应带宽和 Abramson 自适应带宽。路网 KDE、时空 KDE 和时空路网 KDE 尚未作为可用模型公开。

## 快速开始

```python
import numpy as np
from pykdex import SpatialKDE

rng = np.random.default_rng(42)
events = rng.normal(size=(200, 2))
support = rng.normal(size=(20, 2))

model = SpatialKDE(kernel="gaussian", bandwidth=0.5, target="density")
result = model.fit(events).predict_result(support)
print(result.to_frame().head())
```
