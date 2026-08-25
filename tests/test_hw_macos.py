import unittest
from unittest import mock

from beanfit.hw import macos


def fake_sh(outputs):
    def _sh(*args):
        return outputs.get(args, "")
    return _sh


class DetectMacOS(unittest.TestCase):
    def test_apple_silicon_defaults(self):
        outputs = {
            ("sysctl", "-n", "machdep.cpu.brand_string"): "Apple M4 Pro",
            ("sysctl", "-n", "hw.memsize"): str(48 * 2**30),
        }
        with mock.patch.object(macos, "sh", fake_sh(outputs)):
            hw = macos.detect()
        self.assertEqual(hw["family"], "M4")
        self.assertEqual(hw["variant"], "Pro")
        self.assertEqual(hw["arch"], "apple_silicon")
        self.assertEqual(hw["backend"], "unified")
        self.assertEqual(hw["ram_gib"], 48.0)
        self.assertEqual(hw["metal_cap_gib"], 36.0)   # 75% default
        self.assertEqual(hw["model_budget_gib"], 36.0)
        self.assertEqual(hw["mem_bandwidth_gbs"], 273.0)
        self.assertEqual(hw["bw_source"], "spec_sheet")

    def test_wired_limit_override(self):
        outputs = {
            ("sysctl", "-n", "machdep.cpu.brand_string"): "Apple M1 Max",
            ("sysctl", "-n", "hw.memsize"): str(64 * 2**30),
            ("sysctl", "-n", "iogpu.wired_limit_mb"): str(56 * 1024),
        }
        with mock.patch.object(macos, "sh", fake_sh(outputs)):
            hw = macos.detect()
        self.assertAlmostEqual(hw["metal_cap_gib"], 56.0)
        self.assertAlmostEqual(hw["model_budget_gib"], 56.0)

    def test_unknown_chip_falls_back_conservative(self):
        outputs = {
            ("sysctl", "-n", "machdep.cpu.brand_string"): "Apple M99 Ultra",
            ("sysctl", "-n", "hw.memsize"): str(32 * 2**30),
        }
        with mock.patch.object(macos, "sh", fake_sh(outputs)):
            hw = macos.detect()
        self.assertEqual(hw["family"], "M99")
        self.assertEqual(hw["mem_bandwidth_gbs"], 60.0)
        self.assertEqual(hw["bw_source"], "unknown_fallback")

    def test_intel_mac_flags_arch_other(self):
        outputs = {
            ("sysctl", "-n", "machdep.cpu.brand_string"): "Intel(R) Core(TM) i9",
            ("sysctl", "-n", "hw.memsize"): str(16 * 2**30),
        }
        with mock.patch.object(macos, "sh", fake_sh(outputs)):
            hw = macos.detect()
        self.assertEqual(hw["arch"], "other")
        self.assertEqual(hw["backend"], "unknown")
        self.assertEqual(hw["metal_cap_gib"], 12.0)
        self.assertEqual(hw["model_budget_gib"], 12.0)
        self.assertEqual(hw["metal_cap_gib"], hw["model_budget_gib"])


if __name__ == "__main__":
    unittest.main()
