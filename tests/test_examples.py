"""Smoke tests for runnable examples and API coverage."""

import subprocess
import sys
from pathlib import Path


def test_examples_run_standalone():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, str(root / "examples" / "run_all.py")],
        check=True,
        cwd=root,
    )


def test_public_api_coverage_map_is_current():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, str(root / "examples" / "validate_coverage.py")],
        check=True,
        cwd=root,
    )
