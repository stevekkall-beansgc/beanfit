import unittest

from beanfit.engine import evaluate
from tests.fixtures import INTEL_MAC_16, M2_BASE_8, M4_PRO_48, M5_MAX_128


class EvaluateGolden(unittest.TestCase):
    def test_m5max_chat_top_pick(self):
        rows = evaluate(M5_MAX_128, "chat")
        self.assertEqual(rows[0]["name"], "Gemma 4 31B")
        self.assertEqual(rows[0]["quant"], "q4_K_M")
        self.assertAlmostEqual(rows[0]["score"], 121.8, places=1)

    def test_m5max_coding_top_pick(self):
        rows = evaluate(M5_MAX_128, "coding")
        self.assertEqual(rows[0]["name"], "DeepSeek Coder V2 16B")

    def test_scores_descend_and_fit_flags_match_rows(self):
        rows = evaluate(M5_MAX_128, "chat")
        scores = [r["score"] for r in rows]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for r in rows:
            if r["fits"]:
                self.assertGreater(r["score"], 0)
                self.assertIn("est_tok_s", r)
            else:
                self.assertNotIn("est_tok_s", r)


class EvaluateEdges(unittest.TestCase):
    def test_tiny_budget_fits_nothing(self):
        rows = evaluate(M2_BASE_8, "chat")
        self.assertTrue(rows)
        self.assertFalse(any(r["fits"] for r in rows))

    def test_every_catalog_model_present_for_any_profile(self):
        for hw in (M5_MAX_128, M2_BASE_8, INTEL_MAC_16):
            rows = evaluate(hw, "reasoning")
            self.assertEqual(len(rows), 9)

    def test_uncertainty_band_follows_bw_source(self):
        by_source = {}
        for hw in (M5_MAX_128, M4_PRO_48, INTEL_MAC_16):
            band = next(r["est_uncertainty_pct"] for r in evaluate(hw, "chat") if r["fits"])
            by_source[hw["bw_source"]] = band
        self.assertEqual(by_source["estimate"], 40)
        self.assertEqual(by_source["spec_sheet"], 25)
        self.assertEqual(by_source["unknown_fallback"], 50)


if __name__ == "__main__":
    unittest.main()
