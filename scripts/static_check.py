#!/usr/bin/env python3
"""Pinned static check entry point (Ruff) for src/, scripts/, tests/.

This is the single scripted way to run the repo's static check. It MUST NOT
run without the pinned Ruff version: the pin lives only in
requirements-lint.txt, and this script refuses to run any other Ruff
available on PATH. Installing elsewhere (CI) or locally both use that one
file, so the checked-in behavior never silently drifts across Ruff releases.

Usage:
    pip install -r requirements-lint.txt
    python scripts/static_check.py

The rule set is deliberately modest and meaningful: pyflakes syntax /
undefined-name / import / basic-error checks (F) plus syntax-level runtime
errors (E9). Configuration lives in the [tool.ruff] table of pyproject.toml;
see the comments there for the rationale. This script only enforces the pin
and runs the check. Intentionally stdlib-only so it runs before any package
install.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN_FILE = ROOT / "requirements-lint.txt"
TARGETS = ["src", "scripts", "tests"]

PIN_RE = re.compile(r"^ruff==([0-9]+(?:\.[0-9]+)+)\s*$")


def pinned_version() -> str:
    """Single pin source: the exact ruff version requirements-lint.txt demands."""
    if not PIN_FILE.exists():
        sys.exit(f"static-check: missing pin file {PIN_FILE.relative_to(ROOT)}")
    for line in PIN_FILE.read_text().splitlines():
        m = PIN_RE.match(line)
        if m:
            return m.group(1)
    sys.exit(f"static-check: no standalone `ruff==X.Y.Z` pin in {PIN_FILE.relative_to(ROOT)}")


def check_version(exe: str, expected: str) -> None:
    """Refuse to run a Ruff that is not the pinned version."""
    out = subprocess.run([exe, "--version"], check=True,
                         capture_output=True, text=True).stdout.strip()
    if out != f"ruff {expected}":
        sys.exit(
            f"static-check: found {out}, but {PIN_FILE.name} pins ruff=={expected}.\n"
            f"Install the pinned version:  pip install -r {PIN_FILE.name}"
        )


def main() -> int:
    expected = pinned_version()
    exe = shutil.which("ruff") or shutil.which("ruff.exe")
    if exe is None:
        sys.exit(
            f"static-check: ruff not on PATH.\n"
            f"Install the pinned version:  pip install -r {PIN_FILE.name}"
        )
    check_version(exe, expected)
    cmd = [exe, "check", *TARGETS]
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode == 0:
        print(f"static-check: ruff {expected} clean on {', '.join(TARGETS)}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
