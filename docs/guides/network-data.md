# Network data foundation

pyKDEX normalizes GeoPandas, NetworkX, and OSMnx inputs to its own
`LinearNetwork`. Core estimators will never depend directly on an external graph
representation.

## Canonical network

`LinearNetwork` stores stable node and edge identifiers, planar geometry,
direction, parallel-edge keys, geometric lengths, routing costs, CRS, units,
attributes, provenance, and a deterministic fingerprint.

```python
from pykdex import load_osmnx_fixture

network = load_osmnx_fixture().network
print(network.n_nodes, network.n_edges)
print(network.validate().to_frame())
```

Crossing line geometries are not automatically interpreted as connected. This
prevents bridges, tunnels, and grade-separated OSM roads from being joined by
accident. GeoDataFrame topology is defined by explicit `u` and `v` fields or by
line endpoints.

## NetworkX and OSMnx

```python
from pykdex import LinearNetwork

network = LinearNetwork.from_networkx(graph)
network = LinearNetwork.from_osmnx(projected_osmnx_graph)
```

OSMnx graphs should be projected before snapping or lixelization because street
lengths are metric while an unprojected graph geometry is angular. The optional
online convenience function downloads and projects a graph before conversion:

```python
from pykdex import network_from_place

network = network_from_place("Nanjing, China", network_type="drive")
```

Online downloads are not part of the default test suite.

## Auditable event snapping

```python
from pykdex import snap_events

snap = snap_events(network, events, max_distance=50.0)
accepted = snap.events
rejected = snap.rejected
print(snap.report.to_frame())
```

Accepted events retain original and snapped coordinates, edge ID, edge index,
along-edge offset, distance, weight, mark, and a status. Events beyond the
maximum distance are returned rather than silently discarded. Equal-distance
edge ties are resolved deterministically and reported.

## Measured lixels

```python
from pykdex import LixelSupport

lixels = LixelSupport.from_network(network, length=20.0)
print(lixels.total_length)
```

The final lixel on an edge may be shorter than the target length. Every lixel
therefore stores its actual measure, and the partition is validated against the
complete network length. Future network-density integrals will use
`sum(value * lixel_length)` rather than an unweighted sum.

## Reusable workspace

```python
from pykdex import NetworkWorkspace

workspace = NetworkWorkspace.prepare(
    network,
    events,
    lixel_length=20.0,
    max_snap_distance=50.0,
)
```

A workspace is estimator-independent. It keeps the canonical network, snapping
result, measured lixels, validation reports, and fingerprints together so future
NKDE and temporal-network estimators can reuse preparation work.
