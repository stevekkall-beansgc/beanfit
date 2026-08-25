from __future__ import annotations

import platform
import re

from beanfit.hw.bandwidth import lookup
from beanfit.hw.util import sh
from beanfit.profile import MODEL_BUDGET_FLOOR_GIB, OS_HEADROOM_GIB, DeviceProfile

DEFAULT_WIRED_RATIO = 0.75


def detect() -> DeviceProfile:
    chip = sh("sysctl", "-n", "machdep.cpu.brand_string") or platform.machine()
    ram_bytes = int(sh("sysctl", "-n", "hw.memsize") or 0)
    wired = int(sh("sysctl", "-n", "iogpu.wired_limit_mb") or 0)  # 0 => default

    ram_gib = ram_bytes / 2**30 if ram_bytes else 8.0
    m = re.search(r"Apple (M\d+)(?:\s*(Pro|Max|Ultra))?", chip)
    fam, var = (m.group(1), m.group(2) or "") if m else ("", "")
    is_as = fam.startswith("M")
    bw, bw_source = lookup(fam, var)

    if is_as:
        # macOS caps GPU-wired memory at ~75% of RAM by default.
        metal_cap_gib = (wired / 1024) if wired > 0 else round(ram_gib * DEFAULT_WIRED_RATIO, 1)
        budget_gib = max(MODEL_BUDGET_FLOOR_GIB, min(metal_cap_gib, ram_gib - OS_HEADROOM_GIB))
    else:
        # No Metal GPU-wired limit exists — derive the cap from RAM alone,
        # never from a fabricated GPU percentage.
        metal_cap_gib = model_budget = round(
            max(MODEL_BUDGET_FLOOR_GIB, ram_gib - OS_HEADROOM_GIB), 1
        )
        budget_gib = model_budget

    return DeviceProfile(
        os="macos",
        arch="apple_silicon" if is_as else "other",
        backend="unified" if is_as else "unknown",
        chip=chip,
        family=fam,
        variant=var,
        ram_gib=round(ram_gib, 1),
        metal_cap_gib=metal_cap_gib,
        model_budget_gib=round(budget_gib, 1),
        mem_bandwidth_gbs=bw,
        bw_source=bw_source,
    )
