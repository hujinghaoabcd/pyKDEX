# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Compare simple, discontinuous, and continuous network KDE fields."""

from __future__ import annotations

from pykdex import (
    ContinuousJunctionPolicy,
    DiscontinuousJunctionPolicy,
    NetworkField,
    NetworkKDE,
    NetworkWorkspace,
    SimpleJunctionPolicy,
    get_junction_policy,
    load_t_junction,
    trace_network_propagation,
)


def main() -> None:
    dataset = load_t_junction()
    workspace = NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=0.05,
        max_snap_distance=0.25,
    )

    policies = (
        SimpleJunctionPolicy(),
        DiscontinuousJunctionPolicy(),
        ContinuousJunctionPolicy(),
    )
    fields: list[NetworkField] = []
    for policy in policies:
        model = NetworkKDE(
            bandwidth=0.8,
            kernel="epanechnikov",
            junction_policy=policy,
            target="density",
        )
        field = model.fit_predict(workspace)
        fields.append(field)
        print(policy.name, field.integral())

    resolved = get_junction_policy("continuous")
    assert workspace.events is not None
    trace = trace_network_propagation(
        workspace.network,
        int(workspace.events.edge_indices[0]),
        float(workspace.events.offsets[0]),
        cutoff=0.8,
        junction_policy=resolved,
        source_id=workspace.events.event_ids[0],
    )
    print(fields[-1].to_frame().head())
    print(trace.to_frame().head())


if __name__ == "__main__":
    main()
