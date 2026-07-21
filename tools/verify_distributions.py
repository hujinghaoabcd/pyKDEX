"""Verify required content in built wheel and sdist archives."""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

REQUIRED = {"LICENSE", "README.md", "THIRD_PARTY_NOTICES.md"}


def main() -> None:
    dist = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    archives = sorted(dist.glob("*"))
    if not archives:
        raise SystemExit("No distributions found.")
    for archive in archives:
        if archive.suffix == ".whl":
            with zipfile.ZipFile(archive) as handle:
                names = set(handle.namelist())
            if not any(name.endswith("pykdex/py.typed") for name in names):
                raise SystemExit(f"{archive.name}: py.typed missing")
        elif archive.name.endswith(".tar.gz"):
            with tarfile.open(archive) as handle:
                names = {Path(name).name for name in handle.getnames()}
            missing = REQUIRED - names
            if missing:
                raise SystemExit(f"{archive.name}: missing {sorted(missing)}")
    print(f"Verified {len(archives)} distribution archives.")


if __name__ == "__main__":
    main()
