# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Typed, non-executable codecs for workspace components."""

from __future__ import annotations

import base64
import math
from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from pykdex.data import DataProvenance
from pykdex.data.validation import DataIssue, DataValidationReport
from pykdex.persistence._archive import BundleReader, BundleWriter
from pykdex.temporal import BaseTimeDomain, CyclicTimeDomain, LinearTimeDomain


def encode_value(value: Any) -> dict[str, Any]:
    """Encode a supported Python/NumPy value while preserving its type."""
    if value is None:
        return {"type": "none"}
    if isinstance(value, np.generic):
        if value.dtype.hasobject:
            raise TypeError("Object-backed NumPy scalars cannot be persisted safely.")
        return {
            "type": "numpy_scalar",
            "dtype": value.dtype.str,
            "value": base64.b64encode(np.asarray(value).tobytes()).decode("ascii"),
        }
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, str):
        return {"type": "str", "value": value}
    if isinstance(value, bytes):
        return {
            "type": "bytes",
            "value": base64.b64encode(value).decode("ascii"),
        }
    if isinstance(value, int):
        return {"type": "int", "value": str(value)}
    if isinstance(value, float):
        if math.isnan(value):
            encoded = "nan"
        elif math.isinf(value):
            encoded = "inf" if value > 0 else "-inf"
        else:
            encoded = value.hex()
        return {"type": "float", "value": encoded}
    if isinstance(value, tuple):
        return {"type": "tuple", "items": [encode_value(item) for item in value]}
    if isinstance(value, list):
        return {"type": "list", "items": [encode_value(item) for item in value]}
    if isinstance(value, Mapping):
        return {
            "type": "mapping",
            "items": [
                [encode_value(key), encode_value(item)] for key, item in value.items()
            ],
        }
    if isinstance(value, np.ndarray):
        return {
            "type": "ndarray",
            "dtype": value.dtype.str,
            "shape": list(value.shape),
            "items": [
                encode_value(item) for item in np.asarray(value).reshape(-1, order="C")
            ],
        }
    raise TypeError(
        "Workspace metadata contains an unsupported value of type "
        f"{type(value).__qualname__!r}."
    )


def decode_value(value: Any) -> Any:
    """Decode one value from the closed typed-value schema."""
    if not isinstance(value, Mapping):
        raise ValueError("Typed workspace values must be JSON objects.")
    kind = value.get("type")
    if kind == "none":
        _require_keys(value, {"type"})
        return None
    if kind == "bool":
        _require_keys(value, {"type", "value"})
        if not isinstance(value["value"], bool):
            raise ValueError("Encoded bool has an invalid value.")
        return value["value"]
    if kind == "str":
        _require_keys(value, {"type", "value"})
        if not isinstance(value["value"], str):
            raise ValueError("Encoded string has an invalid value.")
        return value["value"]
    if kind == "bytes":
        _require_keys(value, {"type", "value"})
        try:
            return base64.b64decode(value["value"], validate=True)
        except (TypeError, ValueError) as exc:
            raise ValueError("Encoded bytes have an invalid base64 value.") from exc
    if kind == "int":
        _require_keys(value, {"type", "value"})
        try:
            return int(value["value"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Encoded integer has an invalid value.") from exc
    if kind == "float":
        _require_keys(value, {"type", "value"})
        encoded = value["value"]
        if encoded == "nan":
            return float("nan")
        if encoded == "inf":
            return float("inf")
        if encoded == "-inf":
            return float("-inf")
        try:
            return float.fromhex(encoded)
        except (TypeError, ValueError) as exc:
            raise ValueError("Encoded float has an invalid value.") from exc
    if kind == "numpy_scalar":
        _require_keys(value, {"type", "dtype", "value"})
        try:
            dtype = np.dtype(value["dtype"])
            if dtype.hasobject:
                raise ValueError("Object-backed NumPy scalar dtype is forbidden.")
            payload = base64.b64decode(value["value"], validate=True)
            if len(payload) != dtype.itemsize:
                raise ValueError("Encoded NumPy scalar has the wrong byte size.")
            return np.frombuffer(payload, dtype=dtype, count=1)[0]
        except (TypeError, ValueError) as exc:
            raise ValueError("Encoded NumPy scalar is invalid.") from exc
    if kind in {"tuple", "list"}:
        _require_keys(value, {"type", "items"})
        items = value["items"]
        if not isinstance(items, list):
            raise ValueError("Encoded sequence items must be a list.")
        decoded = [decode_value(item) for item in items]
        return tuple(decoded) if kind == "tuple" else decoded
    if kind == "mapping":
        _require_keys(value, {"type", "items"})
        items = value["items"]
        if not isinstance(items, list):
            raise ValueError("Encoded mapping items must be a list.")
        decoded_mapping: dict[Any, Any] = {}
        for pair in items:
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError("Encoded mapping entries must be key-value pairs.")
            key = decode_value(pair[0])
            try:
                decoded_mapping[key] = decode_value(pair[1])
            except TypeError as exc:
                raise ValueError("Encoded mapping key is not hashable.") from exc
        return decoded_mapping
    if kind == "ndarray":
        _require_keys(value, {"type", "dtype", "shape", "items"})
        shape = value["shape"]
        items = value["items"]
        if (
            not isinstance(shape, list)
            or any(
                isinstance(item, bool) or not isinstance(item, int) or item < 0
                for item in shape
            )
            or not isinstance(items, list)
        ):
            raise ValueError("Encoded ndarray shape or items are invalid.")
        try:
            array = np.asarray(
                [decode_value(item) for item in items],
                dtype=np.dtype(value["dtype"]),
            )
            return array.reshape(tuple(shape))
        except (TypeError, ValueError) as exc:
            raise ValueError("Encoded ndarray is invalid.") from exc
    raise ValueError(f"Unknown typed workspace value kind: {kind!r}.")


def _require_keys(value: Mapping[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise ValueError(f"Typed workspace value keys must be {sorted(expected)!r}.")


def add_array(
    writer: BundleWriter,
    path: str,
    value: np.ndarray,
) -> dict[str, Any]:
    """Store an array as NPY, or typed JSON when it has object dtype."""
    array = np.asarray(value)
    if array.dtype.hasobject:
        payload_path = writer.add_json(
            f"{path}.json",
            {
                "dtype": array.dtype.str,
                "shape": list(array.shape),
                "items": [encode_value(item) for item in array.reshape(-1, order="C")],
            },
        )
        return {"encoding": "typed-json", "path": payload_path}
    payload_path = writer.add_array(f"{path}.npy", array)
    return {
        "encoding": "npy",
        "path": payload_path,
        "dtype": array.dtype.str,
        "shape": list(array.shape),
    }


def read_array(reader: BundleReader, record: Any) -> np.ndarray:
    """Read an exact array from a validated component record."""
    if not isinstance(record, Mapping):
        raise ValueError("Array component records must be mappings.")
    encoding = record.get("encoding")
    path = record.get("path")
    if not isinstance(path, str):
        raise ValueError("Array component path must be a string.")
    if encoding == "npy":
        if set(record) != {"encoding", "path", "dtype", "shape"}:
            raise ValueError("NPY array component has unknown keys.")
        array = reader.read_array(path)
        if array.dtype.str != record["dtype"] or list(array.shape) != record["shape"]:
            raise ValueError(f"Workspace array {path!r} dtype or shape mismatch.")
        if array.dtype.hasobject:
            raise ValueError("Object arrays are forbidden in NPY workspace payloads.")
        return array
    if encoding == "typed-json":
        if set(record) != {"encoding", "path"}:
            raise ValueError("Typed array component has unknown keys.")
        decoded = reader.read_json(path)
        if not isinstance(decoded, Mapping) or set(decoded) != {
            "dtype",
            "shape",
            "items",
        }:
            raise ValueError(f"Typed workspace array {path!r} is invalid.")
        shape = decoded["shape"]
        items = decoded["items"]
        if (
            not isinstance(shape, list)
            or any(
                isinstance(item, bool) or not isinstance(item, int) or item < 0
                for item in shape
            )
            or not isinstance(items, list)
            or math.prod(shape) != len(items)
        ):
            raise ValueError(f"Typed workspace array {path!r} shape is invalid.")
        try:
            array = np.empty(len(items), dtype=np.dtype(decoded["dtype"]))
            array[:] = [decode_value(item) for item in items]
            return array.reshape(tuple(shape))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Typed workspace array {path!r} is invalid.") from exc
    raise ValueError(f"Unknown workspace array encoding: {encoding!r}.")


def add_geometries(
    writer: BundleWriter,
    prefix: str,
    geometries: tuple[Any, ...],
) -> dict[str, Any]:
    """Store WKB as concatenated uint8 data and integer offsets."""
    chunks = [bytes(geometry.wkb) for geometry in geometries]
    offsets = np.zeros(len(chunks) + 1, dtype=np.int64)
    if chunks:
        offsets[1:] = np.cumsum([len(chunk) for chunk in chunks], dtype=np.int64)
        data = np.frombuffer(b"".join(chunks), dtype=np.uint8).copy()
    else:
        data = np.empty(0, dtype=np.uint8)
    return {
        "data": add_array(writer, f"{prefix}/wkb_data", data),
        "offsets": add_array(writer, f"{prefix}/wkb_offsets", offsets),
        "count": len(chunks),
    }


def read_geometries(reader: BundleReader, record: Any) -> tuple[Any, ...]:
    """Reconstruct Shapely geometries from WKB payloads."""
    if not isinstance(record, Mapping) or set(record) != {
        "data",
        "offsets",
        "count",
    }:
        raise ValueError("Geometry component record is invalid.")
    data = read_array(reader, record["data"])
    offsets = read_array(reader, record["offsets"])
    count = record["count"]
    if (
        data.dtype != np.uint8
        or offsets.dtype != np.int64
        or offsets.ndim != 1
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count < 0
        or offsets.shape != (count + 1,)
        or offsets[0] != 0
        or offsets[-1] != data.size
        or np.any(np.diff(offsets) < 0)
    ):
        raise ValueError("Geometry WKB offsets are invalid.")
    try:
        from shapely.wkb import loads
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Workspace geometry loading requires the 'network' dependencies."
        ) from exc
    payload = data.tobytes()
    return tuple(
        loads(payload[int(offsets[index]) : int(offsets[index + 1])])
        for index in range(count)
    )


def encode_provenance(value: DataProvenance) -> dict[str, Any]:
    """Encode provenance inline in the manifest."""
    return {
        "source": encode_value(value.source),
        "transformations": encode_value(value.transformations),
        "metadata": encode_value(dict(value.metadata)),
    }


def decode_provenance(value: Any) -> DataProvenance:
    """Decode provenance from the manifest."""
    if not isinstance(value, Mapping) or set(value) != {
        "source",
        "transformations",
        "metadata",
    }:
        raise ValueError("Provenance component is invalid.")
    return DataProvenance(
        source=decode_value(value["source"]),
        transformations=decode_value(value["transformations"]),
        metadata=decode_value(value["metadata"]),
    )


def encode_report(value: DataValidationReport) -> dict[str, Any]:
    """Encode validation issues and statistics."""
    return {
        "issues": [
            {
                "severity": issue.severity,
                "code": issue.code,
                "message": issue.message,
                "context": encode_value(dict(issue.context)),
            }
            for issue in value.issues
        ],
        "statistics": encode_value(dict(value.statistics)),
    }


def decode_report(value: Any) -> DataValidationReport:
    """Decode a validation report."""
    if not isinstance(value, Mapping) or set(value) != {"issues", "statistics"}:
        raise ValueError("Validation report component is invalid.")
    issues = value["issues"]
    if not isinstance(issues, list):
        raise ValueError("Validation report issues must be a list.")
    decoded_issues = []
    for issue in issues:
        if not isinstance(issue, Mapping) or set(issue) != {
            "severity",
            "code",
            "message",
            "context",
        }:
            raise ValueError("Validation issue component is invalid.")
        decoded_issues.append(
            DataIssue(
                severity=issue["severity"],
                code=issue["code"],
                message=issue["message"],
                context=decode_value(issue["context"]),
            )
        )
    return DataValidationReport(
        tuple(decoded_issues),
        decode_value(value["statistics"]),
    )


def add_frame(
    writer: BundleWriter,
    prefix: str,
    frame: pd.DataFrame,
) -> dict[str, Any]:
    """Store a DataFrame as typed columns with no executable format."""
    if len({repr(column) for column in frame.columns}) != len(frame.columns):
        raise ValueError("Persisted DataFrames must have unique column labels.")
    columns = []
    for index, column in enumerate(frame.columns.tolist()):
        columns.append(
            {
                "label": encode_value(column),
                "array": add_array(
                    writer,
                    f"{prefix}/column_{index}",
                    frame.iloc[:, index].to_numpy(),
                ),
            }
        )
    return {
        "columns": columns,
        "index": add_array(writer, f"{prefix}/index", frame.index.to_numpy()),
        "index_name": encode_value(frame.index.name),
    }


def read_frame(reader: BundleReader, record: Any) -> pd.DataFrame:
    """Reconstruct a DataFrame from typed columns."""
    if not isinstance(record, Mapping) or set(record) != {
        "columns",
        "index",
        "index_name",
    }:
        raise ValueError("DataFrame component is invalid.")
    columns = record["columns"]
    if not isinstance(columns, list):
        raise ValueError("DataFrame columns component must be a list.")
    data: dict[Any, np.ndarray] = {}
    length: int | None = None
    for column in columns:
        if not isinstance(column, Mapping) or set(column) != {"label", "array"}:
            raise ValueError("DataFrame column component is invalid.")
        label = decode_value(column["label"])
        array = read_array(reader, column["array"])
        if array.ndim != 1:
            raise ValueError("Persisted DataFrame columns must be one-dimensional.")
        if length is None:
            length = array.shape[0]
        elif length != array.shape[0]:
            raise ValueError("Persisted DataFrame columns have unequal lengths.")
        data[label] = array
    index = read_array(reader, record["index"])
    if index.ndim != 1 or (length is not None and index.shape[0] != length):
        raise ValueError("Persisted DataFrame index has the wrong length.")
    frame = pd.DataFrame(data, index=index)
    frame.index.name = decode_value(record["index_name"])
    return frame


def encode_time_domain(domain: BaseTimeDomain) -> dict[str, Any]:
    """Encode one built-in temporal domain."""
    if isinstance(domain, LinearTimeDomain):
        return {"kind": "linear"}
    if isinstance(domain, CyclicTimeDomain):
        return {
            "kind": "cyclic",
            "period": domain.period.hex(),
            "origin": domain.origin.hex(),
        }
    raise TypeError(
        "Workspace persistence currently supports LinearTimeDomain and "
        "CyclicTimeDomain only."
    )


def decode_time_domain(value: Any) -> BaseTimeDomain:
    """Decode one built-in temporal domain."""
    if not isinstance(value, Mapping):
        raise ValueError("Time-domain component must be a mapping.")
    if value == {"kind": "linear"}:
        return LinearTimeDomain()
    if set(value) == {"kind", "period", "origin"} and value["kind"] == "cyclic":
        try:
            return CyclicTimeDomain(
                period=float.fromhex(value["period"]),
                origin=float.fromhex(value["origin"]),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("Cyclic time-domain values are invalid.") from exc
    raise ValueError("Unknown or invalid time-domain component.")
