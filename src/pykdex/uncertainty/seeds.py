# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Private reproducible random-stream ledger for logical replicates."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pykdex.data._utils import stable_fingerprint


def _normalize_entropy(value: int | tuple[int, ...]) -> tuple[int, ...]:
    values = (value,) if isinstance(value, int) else tuple(value)
    if not values or any(item < 0 for item in values):
        raise ValueError("seed entropy must contain non-negative integers.")
    return tuple(int(item) for item in values)


@dataclass(frozen=True)
class SeedLedger:
    """Recorded root entropy and one stable spawn key per logical task."""

    root_entropy: tuple[int, ...]
    child_spawn_keys: tuple[tuple[int, ...], ...]
    bit_generator_name: str = "PCG64"

    def __post_init__(self) -> None:
        entropy = _normalize_entropy(self.root_entropy)
        keys = tuple(tuple(int(item) for item in key) for key in self.child_spawn_keys)
        if not keys:
            raise ValueError("child_spawn_keys must contain at least one logical task.")
        if any(any(item < 0 for item in key) for key in keys):
            raise ValueError("spawn keys must contain non-negative integers.")
        if len(set(keys)) != len(keys):
            raise ValueError("child_spawn_keys must be unique.")
        generator = str(self.bit_generator_name).strip()
        if generator != "PCG64":
            raise ValueError("bit_generator_name must be 'PCG64'.")
        object.__setattr__(self, "root_entropy", entropy)
        object.__setattr__(self, "child_spawn_keys", keys)
        object.__setattr__(self, "bit_generator_name", generator)

    @property
    def n_logical_tasks(self) -> int:
        """Number of deterministic child streams."""
        return len(self.child_spawn_keys)

    @property
    def fingerprint(self) -> str:
        """Deterministic seed-ledger fingerprint."""
        return stable_fingerprint(
            "SeedLedger",
            self.root_entropy,
            self.child_spawn_keys,
            self.bit_generator_name,
        )

    def generator(self, logical_index: int) -> np.random.Generator:
        """Reconstruct the random generator assigned to one logical task."""
        if isinstance(logical_index, (bool, np.bool_)) or not isinstance(
            logical_index,
            (int, np.integer),
        ):
            raise TypeError("logical_index must be an integer.")
        index = int(logical_index)
        if index < 0 or index >= self.n_logical_tasks:
            raise IndexError("logical_index is outside the seed ledger.")
        sequence = np.random.SeedSequence(
            entropy=self.root_entropy,
            spawn_key=self.child_spawn_keys[index],
        )
        return np.random.Generator(np.random.PCG64(sequence))

    def to_metadata(self) -> dict[str, object]:
        """Return a JSON-compatible seed audit record."""
        return {
            "root_entropy": list(self.root_entropy),
            "n_logical_tasks": self.n_logical_tasks,
            "child_spawn_keys": [list(key) for key in self.child_spawn_keys],
            "bit_generator_name": self.bit_generator_name,
            "seed_ledger_fingerprint": self.fingerprint,
        }


def build_seed_ledger(
    random_state: int | tuple[int, ...] | None,
    n_logical_tasks: int,
) -> SeedLedger:
    """Create all child streams in logical task order before scheduling."""
    if isinstance(n_logical_tasks, (bool, np.bool_)) or not isinstance(
        n_logical_tasks,
        (int, np.integer),
    ):
        raise TypeError("n_logical_tasks must be a positive integer.")
    count = int(n_logical_tasks)
    if count <= 0:
        raise ValueError("n_logical_tasks must be greater than zero.")
    if random_state is None:
        generated = np.random.SeedSequence()
        raw_entropy = generated.entropy
        if isinstance(raw_entropy, (int, np.integer)):
            entropy = (int(raw_entropy),)
        else:
            entropy = tuple(int(item) for item in raw_entropy)
    elif isinstance(random_state, (bool, np.bool_)):
        raise TypeError("random_state must contain non-negative integer entropy.")
    elif isinstance(random_state, (int, np.integer)):
        if int(random_state) < 0:
            raise ValueError("random_state must be non-negative.")
        entropy = (int(random_state),)
    else:
        entropy = _normalize_entropy(random_state)

    root = np.random.SeedSequence(entropy=entropy)
    children = root.spawn(count)
    return SeedLedger(
        root_entropy=entropy,
        child_spawn_keys=tuple(tuple(child.spawn_key) for child in children),
    )
