# Network-time data and arixels

Network-time analysis has three different kinds of ownership:

- `NetworkTimeEvents` owns accepted along-edge event locations and their
  one-to-one temporal coordinates;
- `ArixelSupport` owns the evaluation cells and their
  length-times-time measure;
- `NetworkTimeWorkspace` owns reusable preparation decisions and optional
  distance assets.

Keeping these separate prevents a rejected event, a changed lixel partition,
or a different time domain from being reused accidentally.

## Build from raw observations

```python
workspace = NetworkTimeWorkspace.prepare(
    network,
    spatial_events,
    times,
    temporal_unit="minutes",
    lixel_length=25.0,
    temporal_resolution=15.0,
    temporal_bounds=(0.0, 24.0 * 60.0),
    max_snap_distance=30.0,
)
```

For ordinary elapsed time, supply `temporal_bounds`. For a cyclic domain,
omit them to use one complete period:

```python
workspace = NetworkTimeWorkspace.prepare(
    network,
    spatial_events,
    hour_of_day,
    temporal_unit="hours",
    lixel_length=25.0,
    temporal_resolution=1.0,
    time_domain=CyclicTimeDomain(period=24.0),
)
```

CRS and spatial units remain attached to the network objects. Temporal unit,
origin, timezone, and domain remain attached to the temporal objects. No
automatic spatial or temporal unit conversion is performed.

## Build from an existing network workspace

If topology, snapping, and lixels have already been prepared:

```python
temporal = TemporalCoordinates.from_array(
    accepted_times,
    temporal_unit="hours",
    domain=domain,
)
arixels = ArixelSupport.from_lixels(
    network_workspace.lixels,
    temporal_resolution=1.0,
    temporal_unit="hours",
    time_domain=domain,
)
workspace = NetworkTimeWorkspace.from_network_workspace(
    network_workspace,
    temporal,
    arixels,
)
```

`accepted_times` must already follow the order of the accepted
`NetworkEvents`. The higher-level `prepare()` constructor is safer when raw
events may be rejected because it performs stable-ID alignment automatically.

## Fingerprint rules

Distance assets are accepted only when all of the following match:

- canonical network and base workspace;
- accepted event locations, weights, IDs, and times;
- lixel partition and temporal cell edges;
- time domain, unit, origin, and timezone;
- directed traversal mode and distance cutoff.

These checks make stale cache reuse fail explicitly.
