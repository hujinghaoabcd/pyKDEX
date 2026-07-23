# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Reusable heat plans, batch diffusion times, and heat-specific CV."""

from __future__ import annotations

from pykdex import (
    BaseHeatTime,
    FixedHeatTime,
    HeatComputePlan,
    HeatLeastSquaresCV,
    HeatLeastSquaresCVTime,
    HeatLikelihoodCV,
    HeatLikelihoodCVTime,
    HeatNetworkBatchResult,
    HeatNetworkExperiment,
    HeatNetworkKDE,
    HeatSelectionCache,
    NetworkWorkspace,
    build_heat_compute_plan,
    load_t_junction,
)


def main() -> None:
    dataset = load_t_junction()
    workspace = NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=0.1,
        max_snap_distance=0.25,
    )
    plan: HeatComputePlan = build_heat_compute_plan(workspace, mesh_size=0.1)
    batch: HeatNetworkBatchResult = HeatNetworkExperiment(
        [0.02, 0.08, 0.2],
        mesh_size=0.1,
    ).run(workspace, compute_plan=plan)

    likelihood = HeatLikelihoodCV(bounds=(0.01, 0.3), maxiter=20)
    likelihood_result = likelihood.select(workspace, compute_plan=plan)
    likelihood_cache: HeatSelectionCache | None = likelihood.cache_
    least_squares = HeatLeastSquaresCV(bounds=(0.01, 0.3), maxiter=20)
    least_squares_result = least_squares.select(workspace, compute_plan=plan)

    fixed: BaseHeatTime = FixedHeatTime(0.08)
    selected_model = HeatNetworkKDE(
        diffusion_time=HeatLikelihoodCVTime(bounds=(0.01, 0.3), maxiter=20),
        mesh_size=0.1,
    ).fit(workspace, compute_plan=plan)
    alternate_strategy = HeatLeastSquaresCVTime(
        bounds=(0.01, 0.3),
        maxiter=20,
    )

    print("plan solver", plan.solver)
    print("plan bytes", plan.memory_bytes)
    print("batch integrals", [field.integral() for field in batch.fields])
    print("likelihood time", likelihood_result.bandwidth)
    print("least-squares time", least_squares_result.bandwidth)
    print("cache ready", likelihood_cache is not None)
    print("fixed time", fixed.resolve(workspace, compute_plan=plan))
    print("selected time", selected_model.diffusion_time_)
    print("alternate strategy", type(alternate_strategy).__name__)


if __name__ == "__main__":
    main()
