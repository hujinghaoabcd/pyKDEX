# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Ordinary bootstrap uncertainty for radial network KDE."""

from pykdex import NetworkKDE, NetworkWorkspace, SpatialEvents, load_t_junction
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde


def main() -> None:
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        [[-0.75, 0.0], [0.5, 0.0], [0.0, 0.75]],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    workspace = NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=0.1,
        max_snap_distance=0.05,
    ).with_event_lixel_distances(cutoff=0.8)

    result = bootstrap_kde(
        NetworkKDE(
            bandwidth=0.8,
            kernel="epanechnikov",
            junction_policy="simple",
            target="density",
        ),
        workspace,
        plan=BootstrapPlan(
            n_resamples=8,
            confidence_level=0.8,
            random_state=20260728,
            execution_plan=ExecutionPlan(
                memory_budget_bytes=None,
                target_chunk_size=5,
                replicate_chunk_size=2,
                n_jobs=2,
                backend="thread",
            ),
        ),
    )

    print("observed first lixels:", result.interval.estimate[:5])
    print("lower first lixels:", result.interval.lower[:5])
    print("upper first lixels:", result.interval.upper[:5])
    print("replicate matrix:", result.ensemble.replicate_values.shape)
    print("support fingerprint:", result.ensemble.descriptor.fingerprint)


if __name__ == "__main__":
    main()
