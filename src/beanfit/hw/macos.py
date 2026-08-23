from __future__ import annotations

import platform
import re

from beanfit.hw.bandwidth import lookup
from beanfit.hw.util import sh
from beanfit.profile import DeviceProfile


def detect() -> DeviceProfile:
    chip = sh("sysctl", "-n", "machdep.cpu.brand_string") or platform.machine()
    ram_bytes = int(sh("sysctl", "-n", "hw.memsize") or 0)
    wired = int(sh("sysctl", "-n", "iogpu.wired_limit_mb") or 0)  # 0 => default

    ram_gib = ram_bytes / 2**30 if ram_bytes else 8.0
    # macOS caps GPU-wired memory at ~75% of RAM by default.
    metal_cap_gib = (wired / 1024) if wired > 0 else round(ram_gib * 0.75, 1)
    # keep headroom for OS + apps regardless of cap
    budget_gib = max(4.0, min(metal_cap_gib, ram_gib - 4))

    m = re.search(r"Apple (M\d+)(?:\s*(Pro|Max|Ultra))?", chip)
    fam, var = (m.group(1), m.group(2) or "") if m else ("", "")
    bw, bw_source = lookup(fam, var)
    is_as = fam.startswith("M")
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
