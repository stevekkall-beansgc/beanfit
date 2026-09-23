import unittest

from beanfit.engine.estimate import assumptions, band_for, decode_tok_s, DECODE_FACTOR, KV_CACHE_HALF, KV_CACHE_TOKENS, INCLUDED_KV_TOKENS
from beanfit.hw.bandwidth import FALLBACK_GBS, FALLBACK_SOURCE, lookup


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


class CentralizedConstants(unittest.TestCase):
    def test_decode_factor_constant(self):
        self.assertEqual(DECODE_FACTOR, 0.85)

    def test_kv_cache_half_constant(self):
        self.assertEqual(KV_CACHE_HALF, 0.5)

    def test_kv_cache_tokens_constant(self):
        self.assertEqual(KV_CACHE_TOKENS, 32768)

    def test_included_kv_tokens_constant(self):
        self.assertEqual(INCLUDED_KV_TOKENS, 16384)

    def test_decode_tok_s_uses_constant(self):
        self.assertAlmostEqual(decode_tok_s(600.0, 20.4, "q4_K_M"), 25.0, places=1)

    def test_assumptions_formula_derives_from_constant(self):
        a = assumptions()
        self.assertIn(str(DECODE_FACTOR), a["formula"])
        self.assertIn("weights_plus_included_kv_gib", a["formula"])

    def test_assumptions_context_derives_from_constant(self):
        a = assumptions()
        self.assertIn(f"{KV_CACHE_TOKENS // 1024}k-token", a["context_assumption"])
        self.assertIn(f"({INCLUDED_KV_TOKENS} tokens)", a["context_assumption"])

    def test_decode_factor_in_report_text(self):
        from beanfit.report import generate_report
        report = generate_report(
            dict(device_chip="Apple M4 Pro", memory_gib=48,
                 use_case="coding", operating_system="macOS 15.6 arm64"),
            generated_at="2026-09-04T18:00:00Z",
            repository_revision="e8ec4507b89b3b0471894515e1f80794eb92664f",
        )
        self.assertIn("0.85", report["markdown"])
        self.assertIn("16384", report["markdown"])

    def test_assumptions_text_in_report(self):
        from beanfit.report import generate_report
        report = generate_report(
            dict(device_chip="Apple M4 Pro", memory_gib=48,
                 use_case="coding", operating_system="macOS 15.6 arm64"),
            generated_at="2026-09-04T18:00:00Z",
            repository_revision="e8ec4507b89b3b0471894515e1f80794eb92664f",
        )
        self.assertIn("32k-token", report["assumptions"]["context_assumption"])
        self.assertIn("16384 tokens", report["assumptions"]["context_assumption"])


class Bandwidth(unittest.TestCase):
    def test_known_chip(self):
        self.assertEqual(lookup("M3", "Max"), (400.0, "spec_sheet"))

    def test_unknown_variant_gets_conservative_fallback(self):
        gbs, source = lookup("M2", "UltraFusionX")  # unknown variant: no rescue
        self.assertEqual((gbs, source), (FALLBACK_GBS, "unknown_fallback"))

    def test_exact_pin_required_m5_ultra(self):
        self.assertEqual(lookup("M5", "Ultra"), (60.0, FALLBACK_SOURCE))

    def test_unknown_family(self):
        self.assertEqual(lookup("M99", ""), (FALLBACK_GBS, "unknown_fallback"))


if __name__ == "__main__":
    unittest.main()
