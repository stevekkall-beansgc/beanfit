from __future__ import annotations

# (family, variant) -> (GB/s, source)
# source: spec_sheet = published number; estimate = pre-release figure,
# flagged as such everywhere it is displayed; unknown_fallback = no data.
# M5 values are ESTIMATES until public spec sheets settle.
BANDWIDTH: dict[tuple[str, str], tuple[int, str]] = {
    ("M1", ""): (68, "spec_sheet"),
    ("M1", "Pro"): (200, "spec_sheet"),
    ("M1", "Max"): (400, "spec_sheet"),
    ("M1", "Ultra"): (800, "spec_sheet"),
    ("M2", ""): (100, "spec_sheet"),
    ("M2", "Pro"): (200, "spec_sheet"),
    ("M2", "Max"): (400, "spec_sheet"),
    ("M2", "Ultra"): (800, "spec_sheet"),
    ("M3", ""): (100, "spec_sheet"),
    ("M3", "Pro"): (150, "spec_sheet"),
    ("M3", "Max"): (400, "spec_sheet"),
    ("M3", "Ultra"): (800, "spec_sheet"),
    ("M4", ""): (120, "spec_sheet"),
    ("M4", "Pro"): (273, "spec_sheet"),
    ("M4", "Max"): (546, "spec_sheet"),
    ("M5", ""): (150, "estimate"),
    ("M5", "Pro"): (330, "estimate"),
    ("M5", "Max"): (600, "estimate"),
}

FALLBACK_GBS = 60.0
FALLBACK_SOURCE = "unknown_fallback"


def lookup(family: str, variant: str) -> tuple[float, str]:
    """Return (bandwidth GB/s, source class); conservative on unknown chips.

    Only exact (family, variant) matches count — unknown variants are never
    rescued by the family's base value.
    """
    hit = BANDWIDTH.get((family, variant))
    if hit is None:
        return FALLBACK_GBS, FALLBACK_SOURCE
    return float(hit[0]), hit[1]
