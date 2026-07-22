# pyKDEX

**pyKDEX** 是一个面向普通空间、时空、线性网络及时空网络核密度估计的可扩展 Python 框架。

项目沿用 pyGWRx 的工程规范，但 KDE 使用组合式架构：定义域、距离、核函数、带宽、修正方法、评估支撑和估计器彼此解耦。

当前版本已实现固定带宽、交叉验证和自适应空间 KDE，并已公开固定及自适应 `NetworkKDE`。路网部分支持统一路网对象、NetworkX/OSMnx 适配、事件吸附、lixel、事件—事件距离资产、网络似然交叉验证、基于 lixel 积分的 LSCV 以及网络 k 近邻带宽。时空 KDE 和时空路网 KDE 尚未公开。

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


## 路网带宽选择

```python
from pykdex import NetworkKDE, NetworkKNNBandwidth, NetworkLikelihoodCVBandwidth

selected = NetworkKDE(
    bandwidth=NetworkLikelihoodCVBandwidth(bounds=(100.0, 3000.0)),
    junction_policy="simple",
).fit(workspace)

adaptive = NetworkKDE(
    bandwidth=NetworkKNNBandwidth(k=20, minimum_bandwidth=5.0),
    junction_policy="continuous",
).fit(workspace)
```

网络 LSCV 使用每个 lixel 的实际长度进行积分；路径型策略在带宽搜索上界预先构建传播轨迹，并在优化过程中重复利用。
