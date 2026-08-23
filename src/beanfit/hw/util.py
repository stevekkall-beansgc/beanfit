from __future__ import annotations

import subprocess


def sh(*args: str) -> str:
    try:
        return subprocess.check_output(args, text=True).strip()
    except Exception:
        return ""
