# Core concepts

A pyKDEX estimator is composed from independent concepts:

- **domain**: Euclidean space, space-time, a linear network, or network-time;
- **metric**: Euclidean, anisotropic, temporal, or shortest-path distance;
- **kernel**: a normalized influence function;
- **bandwidth**: a spatial or temporal scale strategy;
- **correction**: boundary, junction, exposure, or normalization behaviour;
- **support**: explicit locations where estimates are evaluated;
- **target**: probability density, event intensity, rate, or relative risk.

Only implemented combinations are publicly exposed.
