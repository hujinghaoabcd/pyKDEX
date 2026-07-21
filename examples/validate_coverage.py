# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Validate that every top-level public symbol has an example mapping."""

from __future__ import annotations

import csv
from pathlib import Path

import pykdex


def main() -> None:
    root = Path(__file__).resolve().parent
    with (root / "API_COVERAGE.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    mapped = {row["symbol"] for row in rows}
    public = {name for name in pykdex.__all__ if name != "__version__"}
    missing = sorted(public - mapped)
    stale = sorted(mapped - public)
    if missing or stale:
        raise SystemExit(f"missing={missing}, stale={stale}")
    for row in rows:
        if not (root / row["example"]).is_file():
            raise SystemExit(f"Missing example file: {row['example']}")
    print(f"Validated {len(public)} public symbols.")


if __name__ == "__main__":
    main()
