# 0.0.13 network-time bandwidths handoff

The complete recovery record is stored at the repository root in
`HANDOFF_0.0.13_NETWORK_TIME_BANDWIDTHS.md`.

Version 0.0.13 adds:

- factorized `NetworkTimeSelectionCache`;
- weighted network-time LOO likelihood;
- arixel-measured network-time LSCV;
- deterministic joint and separate candidate experiments;
- explicit `NetworkTimeBandwidths`;
- independent spatial/temporal `NetworkTimeKNNBandwidth`;
- event-specific sample-point evaluation in `TemporalNetworkKDE`;
- scalar or adaptive bandwidth metadata in `NetworkTimeField`.

The source-event ownership rule is fundamental:

\[
\hat f(l,t)=\sum_i a_i
K^G_{h_{s,i}}(x_i\rightarrow l)
K^T_{h_{t,i}}(t-t_i).
\]

Only an event's own diagonal index is removed for LOO and kNN. Other
zero-distance observations remain valid, so duplicate locations or times need
explicit positive floors.

Selection caches exact event-event network distances, time offsets, and either
event-lixel distances or maximum-bandwidth propagation traces. It never
allocates an event-by-arixel distance cube.

See the root handoff for full mathematics, validation, exclusions, source
inventory, and the 0.0.14 persistence implementation order.

