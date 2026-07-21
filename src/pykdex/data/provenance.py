# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Data provenance and transformation records.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Mapping

from pykdex.data._utils import stable_fingerprint


@dataclass(frozen=True)
class DataProvenance:
    """Describe the origin and deterministic transformations of a data object.

    Args:
        source: Human-readable source name or path.
        transformations: Ordered transformation descriptions.
        metadata: Additional JSON-like metadata.
    """

    source: str | None = None
    transformations: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.source is not None:
            if not isinstance(self.source, str) or not self.source.strip():
                raise ValueError("source must be a non-empty string or None.")
            object.__setattr__(self, "source", self.source.strip())
        transformations = tuple(str(item).strip() for item in self.transformations)
        if any(not item for item in transformations):
            raise ValueError("transformations must not contain empty values.")
        object.__setattr__(self, "transformations", transformations)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def fingerprint(self) -> str:
        """Return a deterministic fingerprint of provenance metadata."""
        return stable_fingerprint(
            self.source,
            self.transformations,
            dict(self.metadata),
        )

    def with_transformation(
        self,
        description: str,
        **metadata: Any,
    ) -> "DataProvenance":
        """Return a new provenance record with one appended transformation."""
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-empty string.")
        merged = dict(self.metadata)
        merged.update(metadata)
        return replace(
            self,
            transformations=self.transformations + (description.strip(),),
            metadata=merged,
        )
