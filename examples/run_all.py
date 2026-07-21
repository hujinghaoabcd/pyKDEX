# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Execute every numbered example in an isolated subprocess."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    scripts = sorted(root.glob("[0-9][0-9]_*.py"))
    for script in scripts:
        subprocess.run([sys.executable, str(script)], check=True, cwd=root.parent)
    print(f"Executed {len(scripts)} examples successfully.")


if __name__ == "__main__":
    main()
