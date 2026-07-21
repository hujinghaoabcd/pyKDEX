# pyKDEX handoff

## Current status

- development version: `0.0.6`;
- public estimators: `SpatialKDE` and fixed-bandwidth `NetworkKDE`;
- scalar spatial bandwidths: fixed, likelihood CV, and Gaussian LSCV;
- event-specific spatial bandwidths: kNN and Abramson;
- structured spatial data, measured support, boundaries, provenance, and datasets;
- canonical `LinearNetwork` with directed and parallel edges;
- GeoDataFrame, NetworkX, and OSMnx conversion;
- auditable event snapping, measured lixels, and reusable `NetworkWorkspace`;
- exact directed and undirected event-to-support network distances;
- simple geodesic, discontinuous equal-split, and continuous equal-split junction policies;
- immutable signed propagation records and traces;
- measured `NetworkField` results with integration and tabular/geospatial export;
- density and intensity targets using accepted snapped-event weights;
- tests: 118 passed;
- branch-coverage gate: passed at the required 80% minimum;
- formatting, linting, typing, documentation, build, and installation checks pass;
- Linux, Windows, and macOS CI passes on Python 3.11-3.14;
- no runtime dependency on external KDE implementations.

## Next recommended development unit

Add network-specific bandwidth selection and adaptive bandwidths without changing
the validated junction-propagation contract:

1. add reusable event-to-event network-distance assets;
2. implement weighted leave-one-out likelihood for fixed network bandwidths;
3. implement lixel-integrated least-squares cross-validation;
4. return immutable optimization traces and bandwidth-selection results;
5. implement network k-nearest-neighbour event bandwidths;
6. cache compatible event-event and event-lixel neighbourhoods in workspaces;
7. validate single-line analytical objectives, disconnected components, duplicated
   locations, weighted events, and directed networks;
8. add memory, cutoff, and repeated-evaluation benchmarks on generated grids.

Heat-equation Gaussian network KDE, temporal-network KDE, and uncertainty should
remain separate later development units.
