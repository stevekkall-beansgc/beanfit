from __future__ import annotations

import json

from beanfit.engine.estimate import assumptions


def render_json(hw: dict, rows: list[dict], use_case: str, version: str) -> str:
    return json.dumps({
        "version": version,
        "hardware": hw,
        "use_case": use_case,
        "assumptions": assumptions(),
        "ranked": rows,
    }, indent=2)
