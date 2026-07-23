# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Persist reusable network and network-time assets without pickle."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from pykdex import (
    NetworkTimeWorkspace,
    NetworkWorkspace,
    WorkspaceManifest,
    load_network_time_workspace,
    load_network_workspace,
    load_t_junction,
    save_network_time_workspace,
    save_network_workspace,
)

dataset = load_t_junction()
network_workspace = (
    NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=0.25,
        max_snap_distance=0.2,
    )
    .with_event_lixel_distances(cutoff=0.8)
    .with_event_event_distances()
)
network_time_workspace = NetworkTimeWorkspace.prepare(
    dataset.network,
    dataset.raw_events,
    [0.25, 1.25, 2.25],
    temporal_unit="hours",
    lixel_length=0.25,
    temporal_resolution=1.0,
    temporal_bounds=(0.0, 3.0),
    max_snap_distance=0.2,
).with_distances(cutoff=0.8)

with TemporaryDirectory() as temporary:
    root = Path(temporary)
    network_path = save_network_workspace(
        network_workspace,
        root / "network.pykdex",
    )
    time_path = save_network_time_workspace(
        network_time_workspace,
        root / "network-time-directory",
        format="directory",
    )

    restored_network = load_network_workspace(network_path)
    restored_time = load_network_time_workspace(time_path)

    # The object methods are equivalent to the public functional API.
    copy_path = network_workspace.save(root / "network-copy.pykdex")
    restored_copy = NetworkWorkspace.load(copy_path)
    restored_time_copy = NetworkTimeWorkspace.load(time_path)

    assert restored_network.fingerprint == network_workspace.fingerprint
    assert restored_copy.fingerprint == network_workspace.fingerprint
    assert restored_time.fingerprint == network_time_workspace.fingerprint
    assert restored_time_copy.fingerprint == network_time_workspace.fingerprint
    assert WorkspaceManifest.__name__ == "WorkspaceManifest"
    print(
        {
            "network_archive_bytes": network_path.stat().st_size,
            "network_fingerprint": restored_network.fingerprint,
            "network_time_fingerprint": restored_time.fingerprint,
        }
    )
