# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Heat-equation KDE with a reusable measured metric-graph operator."""

from __future__ import annotations

from pykdex import (
    HeatNetworkKDE,
    NetworkHeatOperator,
    NetworkWorkspace,
    build_network_heat_operator,
    load_t_junction,
)


def main() -> None:
    dataset = load_t_junction()
    workspace = NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=0.05,
        max_snap_distance=0.25,
    )
    operator: NetworkHeatOperator = build_network_heat_operator(
        workspace,
        mesh_size=0.025,
    )
    field = HeatNetworkKDE(
        diffusion_time=0.08,
        mesh_size=operator.mesh_size,
    ).fit_predict(workspace)

    print("heat DOFs", operator.n_dofs)
    print("heat segments", operator.n_segments)
    print("density integral", field.integral())
    print("junction condition", field.junction_policy)


if __name__ == "__main__":
    main()
