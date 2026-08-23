from __future__ import annotations

import sys

from beanfit.profile import DeviceProfile


class UnsupportedPlatform(RuntimeError):
    pass


def detect() -> DeviceProfile:
    """Detect the host device and return a normalized profile.

    macOS is implemented; Windows/Linux detectors land in roadmap Phase 1.
    """
    if sys.platform == "darwin":
        from beanfit.hw import macos

        return macos.detect()
    raise UnsupportedPlatform(
        f"hardware detection for '{sys.platform}' ships in beanfit Phase 1 "
        f"(see ROADMAP.md). Today: Apple Silicon Macs."
    )
