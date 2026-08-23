import unittest

from beanfit.engine.estimate import band_for, decode_tok_s
from beanfit.hw.bandwidth import FALLBACK_GBS, lookup


class Estimate(unittest.TestCase):
    def test_v01_reference_number(self):
        # M5 Max 128GB / Gemma 31B q4: 600/20.4*0.85 = 25.0 tok/s (README example)
        self.assertAlmostEqual(decode_tok_s(600.0, 20.4, "q4_K_M"), 25.0, places=1)

    def test_q8_slower_than_q4_same_footprint(self):
        self.assertLess(decode_tok_s(400.0, 20.0, "q8_0"),
                        decode_tok_s(400.0, 20.0, "q4_K_M"))

    def test_bands(self):
        self.assertEqual(band_for("spec_sheet"), 25)
        self.assertEqual(band_for("estimate"), 40)
        self.assertEqual(band_for("unknown_fallback"), 50)
        self.assertEqual(band_for("mystery"), 50)


class Bandwidth(unittest.TestCase):
    def test_known_chip(self):
        self.assertEqual(lookup("M3", "Max"), (400.0, "spec_sheet"))

    def test_variant_fallback_uses_family_base(self):
        gbs, source = lookup("M2", "UltraFusionX")  # unknown variant
        self.assertEqual((gbs, source), (100.0, "spec_sheet"))

    def test_unknown_family(self):
        self.assertEqual(lookup("M99", ""), (FALLBACK_GBS, "unknown_fallback"))


if __name__ == "__main__":
    unittest.main()
