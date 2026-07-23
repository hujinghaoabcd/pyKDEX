# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Portable serializers for network and temporal-network workspaces."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pykdex.data import TemporalCoordinates
from pykdex.network import (
    LinearNetwork,
    LixelSupport,
    NetworkDistanceAsset,
    NetworkEvents,
    NetworkWorkspace,
    SnapResult,
)
from pykdex.network_time import (
    ArixelSupport,
    NetworkTimeDistanceAsset,
    NetworkTimeEvents,
    NetworkTimeWorkspace,
)
from pykdex.persistence._archive import (
    DEFAULT_MAX_PAYLOAD_BYTES,
    BundleReader,
    BundleWriter,
    read_bundle,
    write_bundle,
)
from pykdex.persistence._codec import (
    add_array,
    add_frame,
    add_geometries,
    decode_provenance,
    decode_report,
    decode_time_domain,
    decode_value,
    encode_provenance,
    encode_report,
    encode_time_domain,
    encode_value,
    read_array,
    read_frame,
    read_geometries,
)
from pykdex.persistence.manifest import WorkspaceManifest

_WRITER_VERSION = "0.0.14"


def save_network_workspace(
    workspace: NetworkWorkspace,
    path: str | os.PathLike[str],
    *,
    format: str = "archive",
    overwrite: bool = False,
) -> Path:
    """Save a network workspace to a local directory or ZIP archive.

    Writes are prepared next to the destination and atomically renamed into
    place. Existing destinations are protected unless ``overwrite=True``.
    """
    if not isinstance(workspace, NetworkWorkspace):
        raise TypeError("workspace must be a NetworkWorkspace instance.")
    workspace.validate().raise_for_errors()
    writer = BundleWriter()
    components = _encode_network_workspace(writer, workspace, "network_workspace")
    manifest = WorkspaceManifest(
        workspace_kind="network",
        workspace_fingerprint=workspace.fingerprint,
        writer_version=_WRITER_VERSION,
        payloads=writer.payload_records(),
        components=components,
    )
    return write_bundle(
        path,
        format=format,
        overwrite=overwrite,
        manifest=manifest,
        writer=writer,
    )


def load_network_workspace(
    path: str | os.PathLike[str],
    *,
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
) -> NetworkWorkspace:
    """Load and validate a persisted network workspace."""
    reader = read_bundle(path, max_payload_bytes=max_payload_bytes)
    if reader.manifest.workspace_kind != "network":
        raise ValueError(
            "Workspace kind mismatch: expected 'network', found "
            f"{reader.manifest.workspace_kind!r}."
        )
    workspace = _decode_network_workspace(
        reader,
        reader.manifest.components,
    )
    _verify_workspace_fingerprint(workspace.fingerprint, reader.manifest)
    workspace.validate().raise_for_errors()
    return workspace


def save_network_time_workspace(
    workspace: NetworkTimeWorkspace,
    path: str | os.PathLike[str],
    *,
    format: str = "archive",
    overwrite: bool = False,
) -> Path:
    """Save a temporal-network workspace to a local directory or ZIP archive."""
    if not isinstance(workspace, NetworkTimeWorkspace):
        raise TypeError("workspace must be a NetworkTimeWorkspace instance.")
    workspace.validate().raise_for_errors()
    writer = BundleWriter()
    components = _encode_network_time_workspace(
        writer,
        workspace,
        "network_time_workspace",
    )
    manifest = WorkspaceManifest(
        workspace_kind="network_time",
        workspace_fingerprint=workspace.fingerprint,
        writer_version=_WRITER_VERSION,
        payloads=writer.payload_records(),
        components=components,
    )
    return write_bundle(
        path,
        format=format,
        overwrite=overwrite,
        manifest=manifest,
        writer=writer,
    )


def load_network_time_workspace(
    path: str | os.PathLike[str],
    *,
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
) -> NetworkTimeWorkspace:
    """Load and validate a persisted temporal-network workspace."""
    reader = read_bundle(path, max_payload_bytes=max_payload_bytes)
    if reader.manifest.workspace_kind != "network_time":
        raise ValueError(
            "Workspace kind mismatch: expected 'network_time', found "
            f"{reader.manifest.workspace_kind!r}."
        )
    workspace = _decode_network_time_workspace(
        reader,
        reader.manifest.components,
    )
    _verify_workspace_fingerprint(workspace.fingerprint, reader.manifest)
    workspace.validate().raise_for_errors()
    return workspace


def _verify_workspace_fingerprint(
    actual: str,
    manifest: WorkspaceManifest,
) -> None:
    if actual != manifest.workspace_fingerprint:
        raise ValueError(
            "Loaded workspace fingerprint does not match its manifest; "
            "component metadata may be corrupt or incompatible."
        )


def _encode_network_workspace(
    writer: BundleWriter,
    workspace: NetworkWorkspace,
    prefix: str,
) -> dict[str, Any]:
    return {
        "network": _encode_network(writer, workspace.network, f"{prefix}/network"),
        "snap_result": _encode_snap_result(
            writer,
            workspace.snap_result,
            f"{prefix}/snap_result",
        ),
        "lixels": _encode_lixels(
            writer,
            workspace.lixels,
            f"{prefix}/lixels",
        ),
        "distance_asset": (
            None
            if workspace.distance_asset is None
            else _encode_distance_asset(
                writer,
                workspace.distance_asset,
                f"{prefix}/distance_asset",
            )
        ),
        "event_distance_asset": (
            None
            if workspace.event_distance_asset is None
            else _encode_distance_asset(
                writer,
                workspace.event_distance_asset,
                f"{prefix}/event_distance_asset",
            )
        ),
    }


def _decode_network_workspace(
    reader: BundleReader,
    value: Any,
) -> NetworkWorkspace:
    record = _component(
        value,
        {
            "network",
            "snap_result",
            "lixels",
            "distance_asset",
            "event_distance_asset",
        },
        name="network workspace",
    )
    return NetworkWorkspace(
        network=_decode_network(reader, record["network"]),
        snap_result=_decode_snap_result(reader, record["snap_result"]),
        lixels=_decode_lixels(reader, record["lixels"]),
        distance_asset=(
            None
            if record["distance_asset"] is None
            else _decode_distance_asset(reader, record["distance_asset"])
        ),
        event_distance_asset=(
            None
            if record["event_distance_asset"] is None
            else _decode_distance_asset(reader, record["event_distance_asset"])
        ),
    )


def _encode_network(
    writer: BundleWriter,
    network: LinearNetwork,
    prefix: str,
) -> dict[str, Any]:
    return {
        "node_ids": add_array(writer, f"{prefix}/node_ids", network.node_ids),
        "node_coordinates": add_array(
            writer, f"{prefix}/node_coordinates", network.node_coordinates
        ),
        "edge_ids": add_array(writer, f"{prefix}/edge_ids", network.edge_ids),
        "edge_u": add_array(writer, f"{prefix}/edge_u", network.edge_u),
        "edge_v": add_array(writer, f"{prefix}/edge_v", network.edge_v),
        "edge_keys": add_array(writer, f"{prefix}/edge_keys", network.edge_keys),
        "edge_geometries": add_geometries(
            writer, f"{prefix}/edge_geometries", network.edge_geometries
        ),
        "edge_lengths": add_array(
            writer, f"{prefix}/edge_lengths", network.edge_lengths
        ),
        "edge_costs": add_array(writer, f"{prefix}/edge_costs", network.edge_costs),
        "directed": network.directed,
        "crs": network.crs,
        "spatial_unit": network.spatial_unit,
        "edge_attributes": {
            name: add_array(
                writer,
                f"{prefix}/edge_attributes/{index}",
                values,
            )
            for index, (name, values) in enumerate(network.edge_attributes.items())
        },
        "metadata": encode_value(dict(network.metadata)),
        "provenance": encode_provenance(network.provenance),
    }


def _decode_network(reader: BundleReader, value: Any) -> LinearNetwork:
    record = _component(
        value,
        {
            "node_ids",
            "node_coordinates",
            "edge_ids",
            "edge_u",
            "edge_v",
            "edge_keys",
            "edge_geometries",
            "edge_lengths",
            "edge_costs",
            "directed",
            "crs",
            "spatial_unit",
            "edge_attributes",
            "metadata",
            "provenance",
        },
        name="network",
    )
    attributes = record["edge_attributes"]
    if not isinstance(attributes, Mapping) or any(
        not isinstance(name, str) for name in attributes
    ):
        raise ValueError("Network edge_attributes component is invalid.")
    return LinearNetwork(
        node_ids=read_array(reader, record["node_ids"]),
        node_coordinates=read_array(reader, record["node_coordinates"]),
        edge_ids=read_array(reader, record["edge_ids"]),
        edge_u=read_array(reader, record["edge_u"]),
        edge_v=read_array(reader, record["edge_v"]),
        edge_keys=read_array(reader, record["edge_keys"]),
        edge_geometries=read_geometries(reader, record["edge_geometries"]),
        edge_lengths=read_array(reader, record["edge_lengths"]),
        edge_costs=read_array(reader, record["edge_costs"]),
        directed=record["directed"],
        crs=record["crs"],
        spatial_unit=record["spatial_unit"],
        edge_attributes={
            name: read_array(reader, array_record)
            for name, array_record in attributes.items()
        },
        metadata=decode_value(record["metadata"]),
        provenance=decode_provenance(record["provenance"]),
    )


def _encode_network_events(
    writer: BundleWriter,
    events: NetworkEvents,
    prefix: str,
) -> dict[str, Any]:
    arrays = {
        name: add_array(writer, f"{prefix}/{name}", getattr(events, name))
        for name in (
            "event_ids",
            "edge_indices",
            "edge_ids",
            "offsets",
            "coordinates",
            "original_coordinates",
            "weights",
            "snap_distances",
            "snap_status",
        )
    }
    return {
        **arrays,
        "network_fingerprint": events.network_fingerprint,
        "crs": events.crs,
        "spatial_unit": events.spatial_unit,
        "marks": (
            None
            if events.marks is None
            else add_array(writer, f"{prefix}/marks", events.marks)
        ),
        "provenance": encode_provenance(events.provenance),
    }


def _decode_network_events(reader: BundleReader, value: Any) -> NetworkEvents:
    array_names = {
        "event_ids",
        "edge_indices",
        "edge_ids",
        "offsets",
        "coordinates",
        "original_coordinates",
        "weights",
        "snap_distances",
        "snap_status",
    }
    record = _component(
        value,
        array_names
        | {
            "network_fingerprint",
            "crs",
            "spatial_unit",
            "marks",
            "provenance",
        },
        name="network events",
    )
    arrays = {name: read_array(reader, record[name]) for name in array_names}
    return NetworkEvents(
        **arrays,
        network_fingerprint=record["network_fingerprint"],
        crs=record["crs"],
        spatial_unit=record["spatial_unit"],
        marks=None if record["marks"] is None else read_array(reader, record["marks"]),
        provenance=decode_provenance(record["provenance"]),
    )


def _encode_snap_result(
    writer: BundleWriter,
    result: SnapResult,
    prefix: str,
) -> dict[str, Any]:
    return {
        "events": (
            None
            if result.events is None
            else _encode_network_events(writer, result.events, f"{prefix}/events")
        ),
        "rejected": add_frame(writer, f"{prefix}/rejected", result.rejected),
        "report": encode_report(result.report),
        "parameters": encode_value(dict(result.parameters)),
    }


def _decode_snap_result(reader: BundleReader, value: Any) -> SnapResult:
    record = _component(
        value,
        {"events", "rejected", "report", "parameters"},
        name="snap result",
    )
    return SnapResult(
        events=(
            None
            if record["events"] is None
            else _decode_network_events(reader, record["events"])
        ),
        rejected=read_frame(reader, record["rejected"]),
        report=decode_report(record["report"]),
        parameters=decode_value(record["parameters"]),
    )


def _encode_lixels(
    writer: BundleWriter,
    lixels: LixelSupport,
    prefix: str,
) -> dict[str, Any]:
    arrays = {
        name: add_array(writer, f"{prefix}/{name}", getattr(lixels, name))
        for name in (
            "lixel_ids",
            "edge_indices",
            "edge_ids",
            "start_offsets",
            "end_offsets",
            "center_offsets",
            "lengths",
            "center_coordinates",
        )
    }
    return {
        **arrays,
        "geometries": add_geometries(
            writer,
            f"{prefix}/geometries",
            lixels.geometries,
        ),
        "network_fingerprint": lixels.network_fingerprint,
        "target_length": lixels.target_length.hex(),
        "crs": lixels.crs,
        "spatial_unit": lixels.spatial_unit,
        "provenance": encode_provenance(lixels.provenance),
    }


def _decode_lixels(reader: BundleReader, value: Any) -> LixelSupport:
    array_names = {
        "lixel_ids",
        "edge_indices",
        "edge_ids",
        "start_offsets",
        "end_offsets",
        "center_offsets",
        "lengths",
        "center_coordinates",
    }
    record = _component(
        value,
        array_names
        | {
            "geometries",
            "network_fingerprint",
            "target_length",
            "crs",
            "spatial_unit",
            "provenance",
        },
        name="lixel support",
    )
    try:
        target_length = float.fromhex(record["target_length"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Lixel target_length is invalid.") from exc
    arrays = {name: read_array(reader, record[name]) for name in array_names}
    return LixelSupport(
        **arrays,
        geometries=read_geometries(reader, record["geometries"]),
        network_fingerprint=record["network_fingerprint"],
        target_length=target_length,
        crs=record["crs"],
        spatial_unit=record["spatial_unit"],
        provenance=decode_provenance(record["provenance"]),
    )


def _encode_distance_asset(
    writer: BundleWriter,
    asset: NetworkDistanceAsset,
    prefix: str,
) -> dict[str, Any]:
    arrays = {
        name: add_array(writer, f"{prefix}/{name}", getattr(asset, name))
        for name in (
            "source_ids",
            "target_ids",
            "row_indices",
            "column_indices",
            "distances",
        )
    }
    return {
        **arrays,
        "network_fingerprint": asset.network_fingerprint,
        "source_fingerprint": asset.source_fingerprint,
        "target_fingerprint": asset.target_fingerprint,
        "weight": asset.weight,
        "directed": asset.directed,
        "cutoff": None if asset.cutoff is None else asset.cutoff.hex(),
        "metadata": encode_value(dict(asset.metadata)),
    }


def _decode_distance_asset(
    reader: BundleReader,
    value: Any,
) -> NetworkDistanceAsset:
    array_names = {
        "source_ids",
        "target_ids",
        "row_indices",
        "column_indices",
        "distances",
    }
    record = _component(
        value,
        array_names
        | {
            "network_fingerprint",
            "source_fingerprint",
            "target_fingerprint",
            "weight",
            "directed",
            "cutoff",
            "metadata",
        },
        name="network distance asset",
    )
    try:
        cutoff = None if record["cutoff"] is None else float.fromhex(record["cutoff"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Network distance cutoff is invalid.") from exc
    arrays = {name: read_array(reader, record[name]) for name in array_names}
    return NetworkDistanceAsset(
        **arrays,
        network_fingerprint=record["network_fingerprint"],
        source_fingerprint=record["source_fingerprint"],
        target_fingerprint=record["target_fingerprint"],
        weight=record["weight"],
        directed=record["directed"],
        cutoff=cutoff,
        metadata=decode_value(record["metadata"]),
    )


def _encode_temporal(
    writer: BundleWriter,
    temporal: TemporalCoordinates,
    prefix: str,
) -> dict[str, Any]:
    return {
        "values": add_array(writer, f"{prefix}/values", temporal.values),
        "domain": encode_time_domain(temporal.domain),
        "temporal_unit": temporal.temporal_unit,
        "temporal_origin": temporal.temporal_origin,
        "timezone": temporal.timezone,
        "provenance": encode_provenance(temporal.provenance),
    }


def _decode_temporal(reader: BundleReader, value: Any) -> TemporalCoordinates:
    record = _component(
        value,
        {
            "values",
            "domain",
            "temporal_unit",
            "temporal_origin",
            "timezone",
            "provenance",
        },
        name="temporal coordinates",
    )
    return TemporalCoordinates(
        values=read_array(reader, record["values"]),
        domain=decode_time_domain(record["domain"]),
        temporal_unit=record["temporal_unit"],
        temporal_origin=record["temporal_origin"],
        timezone=record["timezone"],
        provenance=decode_provenance(record["provenance"]),
    )


def _encode_network_time_workspace(
    writer: BundleWriter,
    workspace: NetworkTimeWorkspace,
    prefix: str,
) -> dict[str, Any]:
    return {
        "network_workspace": _encode_network_workspace(
            writer,
            workspace.network_workspace,
            f"{prefix}/network_workspace",
        ),
        "events": {
            "temporal": _encode_temporal(
                writer,
                workspace.events.temporal,
                f"{prefix}/events/temporal",
            ),
            "provenance": encode_provenance(workspace.events.provenance),
        },
        "arixels": {
            "time_edges": add_array(
                writer,
                f"{prefix}/arixels/time_edges",
                workspace.arixels.time_edges,
            ),
            "time_domain": encode_time_domain(workspace.arixels.time_domain),
            "temporal_unit": workspace.arixels.temporal_unit,
            "temporal_origin": workspace.arixels.temporal_origin,
            "timezone": workspace.arixels.timezone,
            "provenance": encode_provenance(workspace.arixels.provenance),
        },
        "distance_asset": (
            None
            if workspace.distance_asset is None
            else {
                "network_distances": _encode_distance_asset(
                    writer,
                    workspace.distance_asset.network_distances,
                    f"{prefix}/distance_asset/network_distances",
                ),
                "temporal_offsets": add_array(
                    writer,
                    f"{prefix}/distance_asset/temporal_offsets",
                    workspace.distance_asset.temporal_offsets,
                ),
                "temporal_distances": add_array(
                    writer,
                    f"{prefix}/distance_asset/temporal_distances",
                    workspace.distance_asset.temporal_distances,
                ),
                "event_fingerprint": workspace.distance_asset.event_fingerprint,
                "support_fingerprint": workspace.distance_asset.support_fingerprint,
                "time_domain_fingerprint": (
                    workspace.distance_asset.time_domain_fingerprint
                ),
                "workspace_fingerprint": (
                    workspace.distance_asset.workspace_fingerprint
                ),
            }
        ),
    }


def _decode_network_time_workspace(
    reader: BundleReader,
    value: Any,
) -> NetworkTimeWorkspace:
    record = _component(
        value,
        {"network_workspace", "events", "arixels", "distance_asset"},
        name="network-time workspace",
    )
    network_workspace = _decode_network_workspace(
        reader,
        record["network_workspace"],
    )
    if network_workspace.events is None:
        raise ValueError(
            "Persisted network-time workspace has no accepted network events."
        )
    events_record = _component(
        record["events"],
        {"temporal", "provenance"},
        name="network-time events",
    )
    events = NetworkTimeEvents(
        network_events=network_workspace.events,
        temporal=_decode_temporal(reader, events_record["temporal"]),
        provenance=decode_provenance(events_record["provenance"]),
    )
    arixel_record = _component(
        record["arixels"],
        {
            "time_edges",
            "time_domain",
            "temporal_unit",
            "temporal_origin",
            "timezone",
            "provenance",
        },
        name="arixel support",
    )
    arixels = ArixelSupport(
        lixels=network_workspace.lixels,
        time_edges=read_array(reader, arixel_record["time_edges"]),
        time_domain=decode_time_domain(arixel_record["time_domain"]),
        temporal_unit=arixel_record["temporal_unit"],
        temporal_origin=arixel_record["temporal_origin"],
        timezone=arixel_record["timezone"],
        provenance=decode_provenance(arixel_record["provenance"]),
    )
    distance_record = record["distance_asset"]
    distance_asset = None
    if distance_record is not None:
        component = _component(
            distance_record,
            {
                "network_distances",
                "temporal_offsets",
                "temporal_distances",
                "event_fingerprint",
                "support_fingerprint",
                "time_domain_fingerprint",
                "workspace_fingerprint",
            },
            name="network-time distance asset",
        )
        distance_asset = NetworkTimeDistanceAsset(
            network_distances=_decode_distance_asset(
                reader,
                component["network_distances"],
            ),
            temporal_offsets=read_array(reader, component["temporal_offsets"]),
            temporal_distances=read_array(reader, component["temporal_distances"]),
            event_fingerprint=component["event_fingerprint"],
            support_fingerprint=component["support_fingerprint"],
            time_domain_fingerprint=component["time_domain_fingerprint"],
            workspace_fingerprint=component["workspace_fingerprint"],
        )
    return NetworkTimeWorkspace(
        network_workspace=network_workspace,
        events=events,
        arixels=arixels,
        distance_asset=distance_asset,
    )


def _component(
    value: Any,
    keys: set[str],
    *,
    name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(
            f"Persisted {name} component must contain exactly {sorted(keys)!r}."
        )
    return value
