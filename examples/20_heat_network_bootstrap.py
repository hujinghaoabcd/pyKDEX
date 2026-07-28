"""Run a reproducible ordinary Bootstrap for heat-equation network KDE."""

from pykdex import HeatNetworkKDE, NetworkWorkspace, SpatialEvents, load_t_junction
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde


def main() -> None:
    network = load_t_junction().network
    events = SpatialEvents.from_array(
        [[-0.75, 0.0], [0.50, 0.0], [0.0, 0.50]],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    workspace = NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=0.25,
        max_snap_distance=0.05,
    )

    result = bootstrap_kde(
        HeatNetworkKDE(
            diffusion_time=0.08,
            mesh_size=0.25,
            target="density",
        ),
        workspace,
        plan=BootstrapPlan(
            n_resamples=49,
            confidence_level=0.95,
            random_state=20260729,
            execution_plan=ExecutionPlan(
                memory_budget_bytes=512 * 1024 * 1024,
                replicate_chunk_size=2,
                n_jobs=2,
                backend="thread",
            ),
        ),
    )

    print("observed", result.interval.estimate[:5])
    print("lower", result.interval.lower[:5])
    print("upper", result.interval.upper[:5])
    print("solver", result.metadata["solver"])
    print("maximum heat DOFs", result.metadata["max_n_dofs"])


if __name__ == "__main__":
    main()
