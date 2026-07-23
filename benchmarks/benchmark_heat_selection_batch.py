"""Deterministic grid benchmark for reusable heat plans and batch times."""

from __future__ import annotations

from time import perf_counter

import numpy as np

from pykdex import (
    HeatLikelihoodCV,
    HeatNetworkExperiment,
    HeatNetworkKDE,
    NetworkWorkspace,
    SpatialEvents,
    build_heat_compute_plan,
    make_grid_network,
)


def main() -> None:
    network = make_grid_network(6, 6, spacing=100.0)
    rng = np.random.default_rng(42)
    events = SpatialEvents.from_array(
        rng.uniform(0.0, 600.0, size=(32, 2)),
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    workspace = NetworkWorkspace.prepare(
        network,
        events,
        lixel_length=100.0,
        max_snap_distance=75.0,
    )
    diffusion_times = [500.0, 2_000.0, 8_000.0, 20_000.0]

    started = perf_counter()
    plan = build_heat_compute_plan(workspace, mesh_size=100.0)
    plan_seconds = perf_counter() - started

    started = perf_counter()
    batch = HeatNetworkExperiment(
        diffusion_times,
        mesh_size=100.0,
    ).run(workspace, compute_plan=plan)
    batch_seconds = perf_counter() - started

    started = perf_counter()
    independent = [
        HeatNetworkKDE(time, mesh_size=100.0).fit_predict(workspace)
        for time in diffusion_times
    ]
    independent_seconds = perf_counter() - started

    started = perf_counter()
    selected = HeatLikelihoodCV(
        bounds=(250.0, 30_000.0),
        maxiter=15,
    ).select(workspace, compute_plan=plan)
    selection_seconds = perf_counter() - started

    maximum_difference = max(
        float(np.max(np.abs(batch_field.values - independent_field.values)))
        for batch_field, independent_field in zip(
            batch.fields, independent, strict=True
        )
    )
    print(
        {
            "n_nodes": network.n_nodes,
            "n_edges": network.n_edges,
            "n_events": workspace.events.n_events if workspace.events else 0,
            "n_lixels": workspace.lixels.n_lixels,
            "n_heat_dofs": plan.operator.n_dofs,
            "n_heat_segments": plan.operator.n_segments,
            "solver": plan.solver,
            "plan_memory_bytes": plan.memory_bytes,
            "plan_seconds": round(plan_seconds, 6),
            "batch_seconds": round(batch_seconds, 6),
            "independent_seconds": round(independent_seconds, 6),
            "batch_speedup_excluding_plan": round(
                independent_seconds / max(batch_seconds, np.finfo(float).eps),
                3,
            ),
            "selection_seconds": round(selection_seconds, 6),
            "selected_diffusion_time": selected.bandwidth,
            "maximum_batch_difference": maximum_difference,
        }
    )


if __name__ == "__main__":
    main()
