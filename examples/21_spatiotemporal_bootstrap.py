"""Run a reproducible ordinary Bootstrap for a measured space-time KDE field."""

from pykdex import (
    CyclicTimeDomain,
    GridSupport,
    SpatiotemporalEvents,
    SpatiotemporalGridSupport,
    SpatiotemporalKDE,
)
from pykdex.execution import ExecutionPlan
from pykdex.uncertainty import BootstrapPlan, bootstrap_kde


def main() -> None:
    time_domain = CyclicTimeDomain(24.0)
    events = SpatiotemporalEvents.from_arrays(
        [[0.25, 0.25], [1.0, 0.75], [1.75, 0.25]],
        [23.5, 0.5, 8.0],
        spatial_unit="km",
        temporal_unit="hours",
        time_domain=time_domain,
        temporal_origin="study-hour-zero",
        timezone="UTC",
    )
    spatial = GridSupport.from_bounds(
        (0.0, 0.0, 2.0, 1.0),
        resolution=0.5,
        spatial_unit="km",
    )
    support = SpatiotemporalGridSupport.from_spatial_grid(
        spatial,
        temporal_resolution=6.0,
        temporal_unit="hours",
        time_domain=time_domain,
        temporal_origin="study-hour-zero",
        timezone="UTC",
    )

    result = bootstrap_kde(
        SpatiotemporalKDE(
            spatial_bandwidth=0.7,
            temporal_bandwidth=2.0,
            spatial_kernel="epanechnikov",
            temporal_kernel="gaussian",
            target="density",
        ),
        events,
        support,
        plan=BootstrapPlan(
            n_resamples=49,
            confidence_level=0.95,
            random_state=20260729,
            execution_plan=ExecutionPlan(
                memory_budget_bytes=512 * 1024 * 1024,
                target_chunk_size=16,
                replicate_chunk_size=2,
                n_jobs=2,
                backend="thread",
            ),
        ),
    )

    print("observed", result.interval.estimate[:5])
    print("lower", result.interval.lower[:5])
    print("upper", result.interval.upper[:5])
    print("time domain", result.metadata["time_domain"])
    print("resampling unit", result.metadata["resampling_unit"])


if __name__ == "__main__":
    main()
