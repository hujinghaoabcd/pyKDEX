# 0.0.10 reusable heat plans, batch times, and selection

The complete recoverable engineering record is
`HANDOFF_0.0.10_HEAT_SELECTION_BATCH.md` at the repository root.

Version 0.0.10 separates the measured heat operator from reusable numerical
decomposition and source injection. It adds:

- `HeatComputePlan` and `build_heat_compute_plan`;
- dense eigendecomposition and sparse-generator reuse;
- multi-source, multi-time heat evolution;
- `HeatNetworkExperiment` and `HeatNetworkBatchResult`;
- heat leave-one-out likelihood;
- exact finite-element heat LSCV;
- fixed and selected diffusion-time strategies;
- strict network/event/support/mesh fingerprint compatibility;
- a deterministic grid benchmark and detailed recovery record.

The authoritative smoothing parameter is positive diffusion time \(t\).
Equivalent Gaussian bandwidth \(\sqrt{2t}\) is interpretive metadata only.

The full root handoff contains equations, cache contracts, implementation
locations, validation evidence, limitations, recovery commands, and the
0.0.11 temporal-data/STKDE development order.
