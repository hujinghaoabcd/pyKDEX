# Network distances and traversal

pyKDEX represents an arbitrary network position by an edge index and an offset
measured from that edge's `u` endpoint. `NetworkLocations` provides the common
representation used by events, lixel centres, and future network queries.

## Exact event-to-lixel distances

```python
from pykdex import NetworkWorkspace, load_t_junction

dataset = load_t_junction()
workspace = NetworkWorkspace.prepare(
    dataset.network,
    dataset.raw_events,
    lixel_length=0.25,
    max_snap_distance=0.2,
)
workspace = workspace.with_event_lixel_distances(cutoff=1.0)
asset = workspace.distance_asset
```

The distance calculation considers:

- direct travel between two positions on the same edge;
- each location's distance to eligible incident endpoints;
- node shortest paths between those endpoints;
- directed edge orientation;
- parallel edges and disconnected components;
- proportional conversion from geometric offset to edge cost.

With `weight="length"`, distances use the network length unit. With
`weight="cost"`, offsets are mapped proportionally to `edge_costs`, allowing
travel-time or impedance distances.

## Sparse assets

`NetworkDistanceAsset` stores only finite pairs that satisfy the optional
cutoff. It uses explicit row and column arrays rather than relying solely on a
sparse matrix, so a reachable distance of zero is retained unambiguously.

```python
frame = asset.to_frame()
dense = asset.to_dense()
target_indices, distances = asset.neighbors(0)
```

Omitted entries in `to_dense()` are `inf` by default and mean either
unreachable or beyond the requested cutoff.

## Truncated traversal

`truncated_traversal` starts at a network node and records every explicit edge
portion reachable within a cutoff.

```python
from pykdex import truncated_traversal

traversal = truncated_traversal(
    dataset.network,
    source_node_id=1,
    cutoff=0.75,
)
```

Parallel edges remain separate traversal states. Undirected traversal records
both possible orientations, and an edge cut by the distance limit records its
reachable fraction. These states provide the future foundation for simple,
discontinuous, and continuous junction propagation policies.
