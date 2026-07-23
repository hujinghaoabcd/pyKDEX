# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Portable workspace persistence, integrity, and safety contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

from pykdex import (
    CyclicTimeDomain,
    NetworkTimeWorkspace,
    NetworkWorkspace,
    SpatialEvents,
    WorkspaceManifest,
    load_osmnx_fixture,
    load_t_junction,
)
from pykdex.persistence._archive import read_bundle


def _network_workspace(*, rejected: bool = False) -> NetworkWorkspace:
    dataset = load_t_junction()
    if rejected:
        ids = np.empty(2, dtype=object)
        ids[:] = [("accepted", 1), ("rejected", 2)]
        events = SpatialEvents.from_array(
            [[-0.75, 0.0], [20.0, 20.0]],
            ids=ids,
            marks=np.asarray([np.int64(7), np.int64(9)], dtype=object),
            crs=dataset.network.crs,
            spatial_unit=dataset.network.spatial_unit,
        )
    else:
        events = dataset.raw_events
    return (
        NetworkWorkspace.prepare(
            dataset.network,
            events,
            lixel_length=0.25,
            max_snap_distance=0.2,
        )
        .with_event_lixel_distances(cutoff=0.8)
        .with_event_event_distances()
    )


def _time_workspace(*, cyclic: bool = False) -> NetworkTimeWorkspace:
    dataset = load_t_junction()
    domain = CyclicTimeDomain(period=24.0, origin=2.0) if cyclic else None
    bounds = None if cyclic else (0.0, 4.5)
    times = [3.0, 7.0, 23.0]
    return NetworkTimeWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        times,
        temporal_unit="hours",
        lixel_length=0.3,
        temporal_resolution=5.0 if cyclic else 1.0,
        temporal_bounds=bounds,
        time_domain=domain,
        temporal_origin="2026-01-01T00:00:00+00:00",
        timezone="UTC",
        max_snap_distance=0.2,
    ).with_distances(cutoff=1.1)


def _rewrite_zip(path: Path, transform) -> None:
    with zipfile.ZipFile(path) as archive:
        entries = {info.filename: archive.read(info) for info in archive.infolist()}
    transform(entries)
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)


def test_network_archive_round_trip_is_exact_and_deterministic(tmp_path: Path) -> None:
    workspace = _network_workspace(rejected=True)
    first = tmp_path / "first.pykdex"
    second = tmp_path / "second.pykdex"

    assert workspace.save(first) == first
    workspace.save(second)
    loaded = NetworkWorkspace.load(first)

    assert first.read_bytes() == second.read_bytes()
    assert loaded.fingerprint == workspace.fingerprint
    assert loaded.summary() == workspace.summary()
    assert loaded.distance_asset is not None
    assert loaded.event_distance_asset is not None
    assert loaded.distance_asset.fingerprint == workspace.distance_asset.fingerprint
    assert (
        loaded.event_distance_asset.fingerprint
        == workspace.event_distance_asset.fingerprint
    )
    assert loaded.snap_result.report == workspace.snap_result.report
    assert loaded.snap_result.rejected.to_dict("records") == (
        workspace.snap_result.rejected.to_dict("records")
    )
    assert loaded.events is not None
    assert isinstance(loaded.events.event_ids[0], tuple)
    assert isinstance(loaded.events.marks[0], np.int64)
    assert not loaded.distance_asset.distances.flags.writeable


def test_network_time_archive_preserves_linear_and_cyclic_time(tmp_path: Path) -> None:
    for cyclic in (False, True):
        workspace = _time_workspace(cyclic=cyclic)
        path = tmp_path / f"time-{cyclic}.pykdex"

        workspace.save(path)
        loaded = NetworkTimeWorkspace.load(path)

        assert loaded.fingerprint == workspace.fingerprint
        assert type(loaded.events.temporal.domain) is type(
            workspace.events.temporal.domain
        )
        assert loaded.events.temporal.domain.fingerprint == (
            workspace.events.temporal.domain.fingerprint
        )
        assert loaded.arixels.fingerprint == workspace.arixels.fingerprint
        assert loaded.distance_asset is not None
        assert loaded.distance_asset.fingerprint == workspace.distance_asset.fingerprint
        np.testing.assert_array_equal(
            loaded.distance_asset.temporal_offsets,
            workspace.distance_asset.temporal_offsets,
        )


def test_directory_backend_round_trip_and_overwrite(tmp_path: Path) -> None:
    workspace = _network_workspace()
    path = tmp_path / "workspace-directory"

    workspace.save(path, format="directory")
    assert (path / "manifest.json").is_file()
    assert NetworkWorkspace.load(path).fingerprint == workspace.fingerprint
    with pytest.raises(FileExistsError):
        workspace.save(path, format="directory")

    workspace.save(path, format="directory", overwrite=True)
    assert NetworkWorkspace.load(path).fingerprint == workspace.fingerprint


def test_osmnx_multidigraph_ids_attributes_and_direction_round_trip(
    tmp_path: Path,
) -> None:
    dataset = load_osmnx_fixture()
    workspace = NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=25.0,
        max_snap_distance=25.0,
    )
    path = tmp_path / "osmnx.pykdex"

    workspace.save(path)
    loaded = NetworkWorkspace.load(path)

    assert loaded.fingerprint == workspace.fingerprint
    assert loaded.network.directed
    assert loaded.network.edge_ids.tolist() == workspace.network.edge_ids.tolist()
    assert loaded.network.edge_keys.tolist() == workspace.network.edge_keys.tolist()
    assert set(loaded.network.edge_attributes) == set(workspace.network.edge_attributes)


def test_payload_corruption_and_inventory_changes_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.pykdex"
    _network_workspace().save(path)
    reader = read_bundle(path)
    target = next(iter(reader.manifest.payloads))

    def corrupt(entries):
        entries[target] += b"corruption"

    _rewrite_zip(path, corrupt)
    with pytest.raises(ValueError, match="wrong byte size|SHA-256"):
        NetworkWorkspace.load(path)

    _network_workspace().save(path, overwrite=True)

    def add_unknown(entries):
        entries["unknown.bin"] = b"x"

    _rewrite_zip(path, add_unknown)
    with pytest.raises(ValueError, match="inventory mismatch"):
        NetworkWorkspace.load(path)


def test_schema_kind_manifest_and_payload_limit_guards(tmp_path: Path) -> None:
    path = tmp_path / "guards.pykdex"
    _network_workspace().save(path)

    def future_schema(entries):
        manifest = json.loads(entries["manifest.json"])
        manifest["schema_version"] = 999
        entries["manifest.json"] = json.dumps(manifest).encode()

    _rewrite_zip(path, future_schema)
    with pytest.raises(ValueError, match="schema version"):
        NetworkWorkspace.load(path)

    time_path = tmp_path / "time.pykdex"
    _time_workspace().save(time_path)
    with pytest.raises(ValueError, match="kind mismatch"):
        NetworkWorkspace.load(time_path)
    with pytest.raises(ValueError, match="safety limit"):
        NetworkTimeWorkspace.load(time_path, max_payload_bytes=1)


def test_atomic_archive_failure_keeps_existing_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pykdex.persistence._archive as archive_module

    path = tmp_path / "atomic.pykdex"
    path.write_bytes(b"original")

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(archive_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        _network_workspace().save(path, overwrite=True)
    assert path.read_bytes() == b"original"
    assert not list(tmp_path.glob(".atomic.pykdex.*.tmp"))


def test_cross_process_reload_has_identical_fingerprint(tmp_path: Path) -> None:
    path = tmp_path / "cross-process.pykdex"
    workspace = _time_workspace(cyclic=True)
    workspace.save(path)

    script = (
        "from pykdex import NetworkTimeWorkspace; "
        f"print(NetworkTimeWorkspace.load({str(path)!r}).fingerprint)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONHASHSEED": "123"},
    )
    assert completed.stdout.strip() == workspace.fingerprint


def test_unsupported_metadata_and_existing_destinations_fail_safely(
    tmp_path: Path,
) -> None:
    dataset = load_t_junction()
    object.__setattr__(dataset.network, "metadata", {"unsafe": object()})
    workspace = NetworkWorkspace.prepare(
        dataset.network,
        dataset.raw_events,
        lixel_length=0.5,
        max_snap_distance=0.2,
    )
    with pytest.raises(TypeError, match="unsupported"):
        workspace.save(tmp_path / "unsafe.pykdex")

    valid = _network_workspace()
    path = tmp_path / "existing.pykdex"
    valid.save(path)
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        valid.save(path)
    assert path.read_bytes() == before


def test_manifest_contract_rejects_invalid_format_digest_and_keys() -> None:
    valid = {
        "format": "pykdex-workspace",
        "schema_version": 1,
        "workspace_kind": "network",
        "workspace_fingerprint": "abc",
        "writer_version": "0.0.14",
        "payloads": {
            "arrays/a.npy": {
                "sha256": "0" * 64,
                "size": 1,
            }
        },
        "components": {},
    }
    manifest = WorkspaceManifest.from_dict(valid)
    assert manifest.to_dict() == valid
    with pytest.raises(ValueError, match="unknown keys"):
        WorkspaceManifest.from_dict({**valid, "future": True})
    with pytest.raises(ValueError, match="SHA-256"):
        WorkspaceManifest.from_dict(
            {
                **valid,
                "payloads": {"arrays/a.npy": {"sha256": "invalid", "size": 1}},
            }
        )
