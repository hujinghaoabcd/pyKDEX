# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Manifest contract for portable workspace archives."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

WORKSPACE_FORMAT = "pykdex-workspace"
WORKSPACE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class WorkspaceManifest:
    """Validated public description of a persisted workspace.

    The manifest never executes code. It records the workspace kind, schema
    version, expected fingerprint, component metadata, and the SHA-256 digest
    and byte size of every payload.
    """

    workspace_kind: str
    workspace_fingerprint: str
    payloads: Mapping[str, Mapping[str, Any]]
    components: Mapping[str, Any]
    writer_version: str
    schema_version: int = WORKSPACE_SCHEMA_VERSION
    format: str = WORKSPACE_FORMAT

    def __post_init__(self) -> None:
        if self.format != WORKSPACE_FORMAT:
            raise ValueError(
                f"Unsupported workspace format {self.format!r}; "
                f"expected {WORKSPACE_FORMAT!r}."
            )
        if isinstance(self.schema_version, bool) or not isinstance(
            self.schema_version, int
        ):
            raise TypeError("schema_version must be an integer.")
        if self.schema_version != WORKSPACE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported workspace schema version {self.schema_version}; "
                f"expected {WORKSPACE_SCHEMA_VERSION}."
            )
        if self.workspace_kind not in {"network", "network_time"}:
            raise ValueError("workspace_kind must be 'network' or 'network_time'.")
        if not isinstance(self.workspace_fingerprint, str) or not (
            self.workspace_fingerprint
        ):
            raise ValueError("workspace_fingerprint must be a non-empty string.")
        if not isinstance(self.writer_version, str) or not self.writer_version:
            raise ValueError("writer_version must be a non-empty string.")
        normalized_payloads: dict[str, Mapping[str, Any]] = {}
        for path, record in self.payloads.items():
            if not isinstance(path, str) or not path:
                raise ValueError("payload paths must be non-empty strings.")
            if not isinstance(record, Mapping):
                raise TypeError("payload records must be mappings.")
            digest = record.get("sha256")
            size = record.get("size")
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)
            ):
                raise ValueError(f"payload {path!r} has an invalid SHA-256 digest.")
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                raise ValueError(f"payload {path!r} has an invalid byte size.")
            normalized_payloads[path] = MappingProxyType(dict(record))
        object.__setattr__(self, "payloads", MappingProxyType(normalized_payloads))
        object.__setattr__(self, "components", MappingProxyType(dict(self.components)))

    def to_dict(self) -> dict[str, Any]:
        """Return a canonical JSON-compatible representation."""
        return {
            "format": self.format,
            "schema_version": self.schema_version,
            "workspace_kind": self.workspace_kind,
            "workspace_fingerprint": self.workspace_fingerprint,
            "writer_version": self.writer_version,
            "payloads": {path: dict(record) for path, record in self.payloads.items()},
            "components": dict(self.components),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "WorkspaceManifest":
        """Validate and construct a manifest from decoded JSON."""
        required = {
            "format",
            "schema_version",
            "workspace_kind",
            "workspace_fingerprint",
            "writer_version",
            "payloads",
            "components",
        }
        missing = required.difference(value)
        extra = set(value).difference(required)
        if missing:
            raise ValueError(f"Workspace manifest is missing: {sorted(missing)!r}.")
        if extra:
            raise ValueError(
                f"Workspace manifest contains unknown keys: {sorted(extra)!r}."
            )
        payloads = value["payloads"]
        components = value["components"]
        if not isinstance(payloads, Mapping) or not isinstance(components, Mapping):
            raise TypeError("manifest payloads and components must be mappings.")
        return cls(
            format=value["format"],
            schema_version=value["schema_version"],
            workspace_kind=value["workspace_kind"],
            workspace_fingerprint=value["workspace_fingerprint"],
            writer_version=value["writer_version"],
            payloads=payloads,
            components=components,
        )
