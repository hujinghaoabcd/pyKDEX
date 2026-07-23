# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Safe local bundle primitives used by workspace persistence."""

from __future__ import annotations

import hashlib
import io
import json
import os
import secrets
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import numpy as np

from pykdex.persistence.manifest import WorkspaceManifest

DEFAULT_MAX_PAYLOAD_BYTES = 1_073_741_824
_MANIFEST_PATH = "manifest.json"
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def canonical_json(value: Any) -> bytes:
    """Encode JSON deterministically and reject non-standard numeric values."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def decode_json(payload: bytes, *, name: str) -> Any:
    """Decode one UTF-8 JSON payload with a concise corruption error."""
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{name} is not valid UTF-8 JSON.") from exc


def _safe_payload_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in value
        or value == _MANIFEST_PATH
    ):
        raise ValueError(f"Unsafe workspace payload path: {value!r}.")
    return value


class BundleWriter:
    """Collect deterministic payloads before an atomic local write."""

    def __init__(self) -> None:
        self.payloads: dict[str, bytes] = {}

    def add_bytes(self, path: str, payload: bytes) -> str:
        """Add one uniquely named binary payload."""
        normalized = _safe_payload_path(path)
        if normalized in self.payloads:
            raise ValueError(f"Duplicate workspace payload path: {normalized!r}.")
        self.payloads[normalized] = bytes(payload)
        return normalized

    def add_json(self, path: str, value: Any) -> str:
        """Add canonical JSON."""
        return self.add_bytes(path, canonical_json(value))

    def add_array(self, path: str, values: Any) -> str:
        """Add a non-object NumPy array without pickle."""
        array = np.asarray(values)
        if array.dtype.hasobject:
            raise TypeError(
                f"{path} has object dtype; use the typed-value codec instead."
            )
        buffer = io.BytesIO()
        np.save(buffer, array, allow_pickle=False)
        return self.add_bytes(path, buffer.getvalue())

    def payload_records(self) -> dict[str, dict[str, Any]]:
        """Return sorted checksum and size records."""
        return {
            path: {
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
            }
            for path, payload in sorted(self.payloads.items())
        }


class BundleReader:
    """Checksum-verifying payload reader."""

    def __init__(
        self,
        payloads: Mapping[str, bytes],
        manifest: WorkspaceManifest,
    ) -> None:
        self._payloads = dict(payloads)
        self.manifest = manifest

    def read_bytes(self, path: str) -> bytes:
        """Return a verified payload already loaded from the bundle."""
        try:
            return self._payloads[path]
        except KeyError as exc:
            raise ValueError(f"Workspace payload {path!r} is missing.") from exc

    def read_json(self, path: str) -> Any:
        """Decode one verified JSON payload."""
        return decode_json(self.read_bytes(path), name=path)

    def read_array(self, path: str) -> np.ndarray:
        """Load a verified NumPy payload with pickle permanently disabled."""
        try:
            array = np.load(
                io.BytesIO(self.read_bytes(path)),
                allow_pickle=False,
            )
        except (OSError, ValueError, EOFError) as exc:
            raise ValueError(f"Workspace array {path!r} is invalid.") from exc
        if not isinstance(array, np.ndarray):
            raise ValueError(f"Workspace payload {path!r} is not a NumPy array.")
        return array


def write_bundle(
    path: str | os.PathLike[str],
    *,
    format: str,
    overwrite: bool,
    manifest: WorkspaceManifest,
    writer: BundleWriter,
) -> Path:
    """Atomically write a directory or deterministic ZIP archive."""
    destination = Path(path)
    normalized_format = str(format).strip().lower()
    if normalized_format not in {"archive", "directory"}:
        raise ValueError("format must be either 'archive' or 'directory'.")
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Workspace destination already exists: {destination}.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = canonical_json(manifest.to_dict())
    if normalized_format == "archive":
        return _write_archive(
            destination,
            overwrite=overwrite,
            manifest_bytes=manifest_bytes,
            payloads=writer.payloads,
        )
    return _write_directory(
        destination,
        overwrite=overwrite,
        manifest_bytes=manifest_bytes,
        payloads=writer.payloads,
    )


def _write_archive(
    destination: Path,
    *,
    overwrite: bool,
    manifest_bytes: bytes,
    payloads: Mapping[str, bytes],
) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for name, payload in [
                (_MANIFEST_PATH, manifest_bytes),
                *sorted(payloads.items()),
            ]:
                info = zipfile.ZipInfo(name, date_time=_ZIP_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, payload, compresslevel=9)
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        if destination.exists() and destination.is_dir():
            raise IsADirectoryError(
                f"Archive destination is a directory: {destination}."
            )
        if destination.exists() and not overwrite:
            raise FileExistsError(
                f"Workspace destination already exists: {destination}."
            )
        os.replace(temporary, destination)
        return destination
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_directory(
    destination: Path,
    *,
    overwrite: bool,
    manifest_bytes: bytes,
    payloads: Mapping[str, bytes],
) -> Path:
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
        )
    )
    backup: Path | None = None
    try:
        for name, payload in [
            (_MANIFEST_PATH, manifest_bytes),
            *sorted(payloads.items()),
        ]:
            output = temporary / PurePosixPath(name)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        if destination.exists():
            if not overwrite:
                raise FileExistsError(
                    f"Workspace destination already exists: {destination}."
                )
            backup = destination.with_name(
                f".{destination.name}.{secrets.token_hex(8)}.backup"
            )
            os.replace(destination, backup)
        try:
            os.replace(temporary, destination)
        except BaseException:
            if backup is not None and backup.exists() and not destination.exists():
                os.replace(backup, destination)
            raise
        if backup is not None:
            if backup.is_dir():
                shutil.rmtree(backup)
            else:
                backup.unlink()
        return destination
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def read_bundle(
    path: str | os.PathLike[str],
    *,
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
) -> BundleReader:
    """Read and verify an archive or directory without extracting it."""
    if isinstance(max_payload_bytes, bool) or not isinstance(max_payload_bytes, int):
        raise TypeError("max_payload_bytes must be an integer.")
    if max_payload_bytes <= 0:
        raise ValueError("max_payload_bytes must be positive.")
    source = Path(path)
    if source.is_dir():
        raw = _read_directory(source, max_payload_bytes=max_payload_bytes)
    elif source.is_file():
        raw = _read_archive(source, max_payload_bytes=max_payload_bytes)
    else:
        raise FileNotFoundError(f"Workspace path does not exist: {source}.")
    try:
        manifest_payload = raw.pop(_MANIFEST_PATH)
    except KeyError as exc:
        raise ValueError("Workspace manifest.json is missing.") from exc
    decoded = decode_json(manifest_payload, name=_MANIFEST_PATH)
    if not isinstance(decoded, Mapping):
        raise ValueError("Workspace manifest must be a JSON object.")
    manifest = WorkspaceManifest.from_dict(decoded)
    expected = set(manifest.payloads)
    actual = set(raw)
    if expected != actual:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise ValueError(
            "Workspace payload inventory mismatch: "
            f"missing={missing!r}, unexpected={unexpected!r}."
        )
    declared_total = sum(int(record["size"]) for record in manifest.payloads.values())
    if declared_total > max_payload_bytes:
        raise ValueError("Workspace declared payload size exceeds the safety limit.")
    for name, payload in raw.items():
        record = manifest.payloads[name]
        if len(payload) != record["size"]:
            raise ValueError(f"Workspace payload {name!r} has the wrong byte size.")
        digest = hashlib.sha256(payload).hexdigest()
        if digest != record["sha256"]:
            raise ValueError(f"Workspace payload {name!r} failed SHA-256 validation.")
    return BundleReader(raw, manifest)


def _read_archive(path: Path, *, max_payload_bytes: int) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(path, mode="r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos if not info.is_dir()]
            if len(names) != len(set(names)):
                raise ValueError("Workspace archive contains duplicate paths.")
            total = 0
            payloads: dict[str, bytes] = {}
            for info in infos:
                if info.is_dir():
                    continue
                if info.filename != _MANIFEST_PATH:
                    _safe_payload_path(info.filename)
                total += info.file_size
                if total > max_payload_bytes:
                    raise ValueError(
                        "Workspace archive exceeds the payload safety limit."
                    )
                payloads[info.filename] = archive.read(info)
            return payloads
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError(f"Workspace archive is not a valid ZIP file: {path}.") from exc


def _read_directory(path: Path, *, max_payload_bytes: int) -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}
    total = 0
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise ValueError("Workspace directories must not contain symbolic links.")
        if not item.is_file():
            continue
        relative = item.relative_to(path).as_posix()
        if relative != _MANIFEST_PATH:
            _safe_payload_path(relative)
        size = item.stat().st_size
        total += size
        if total > max_payload_bytes:
            raise ValueError("Workspace directory exceeds the payload safety limit.")
        payloads[relative] = item.read_bytes()
    return payloads
