import unittest
from unittest import mock

from beanfit.hw import UnsupportedPlatform, macos


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

    def test_intel_mac_fails_closed(self):
        outputs = {
            ("sysctl", "-n", "machdep.cpu.brand_string"): "Intel(R) Core(TM) i9",
        }
        probe = mock.Mock(side_effect=fake_sh(outputs))
        with mock.patch.object(macos, "sh", probe), mock.patch.object(macos, "lookup") as lookup:
            with self.assertRaises(UnsupportedPlatform) as raised:
                macos.detect()
        message = str(raised.exception)
        self.assertIn("unsupported platform", message)
        self.assertIn("Apple Silicon Macs only", message)
        self.assertIn("no hardware, throughput, fit, or launch recommendations", message)
        probe.assert_called_once_with("sysctl", "-n", "machdep.cpu.brand_string")
        lookup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
