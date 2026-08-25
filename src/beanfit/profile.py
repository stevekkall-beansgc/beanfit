from __future__ import annotations

from typing import TypedDict

# Shared budget-model knobs: reserve this much RAM for OS + apps, and never
# promise a model budget below this floor. Used by every platform detector.
OS_HEADROOM_GIB = 4.0
MODEL_BUDGET_FLOOR_GIB = 4.0


class DeviceProfile(TypedDict):
    """Normalized hardware description the scoring engine consumes.

    The engine must never branch on OS/platform — only on these fields
    (roadmap T1.1). `bw_source` drives the honesty band on every speed
    number we print.
    """

    os: str
    arch: str                 # apple_silicon | other (Phase 1 adds discrete/cpu backends)
    backend: str              # unified | unknown (Phase 1: discrete | cpu)
    chip: str
    family: str
    variant: str
    ram_gib: float
    metal_cap_gib: float      # unified-memory usable cap (name kept for continuity)
    model_budget_gib: float
    mem_bandwidth_gbs: float
    bw_source: str            # spec_sheet | estimate | unknown_fallback
