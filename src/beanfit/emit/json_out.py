from __future__ import annotations

import json

from beanfit.engine.estimate import assumptions


def render_json(hw: dict, rows: list[dict], use_case: str, version: str) -> str:
    return json.dumps({
        "version": version,
        "hardware": hw,
        "use_case": use_case,
        "assumptions": assumptions(),
        "claim_limits": {
            "speed": "static estimate; not measured inference",
            "uncertainty": "assumed bands; not calibrated confidence intervals",
            "quality": "illustrative editorial catalog ratings; no validated rubric",
            "architecture": "shared total-footprint formula; no MoE active-expert traffic model",
        },
        "ranked": rows,
    }, indent=2)
