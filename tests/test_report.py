import copy
import hashlib
import json
import unittest
from pathlib import Path

from beanfit.catalog.models import CATALOG, MLX_REPOS
from beanfit.report import InputRejected, NeedsReview, generate_report, validate_input

INPUT = dict(device_chip="Apple M4 Pro", memory_gib=48, use_case="coding", operating_system="macOS 15.6 arm64")
META = dict(generated_at="2026-09-04T18:00:00Z", repository_revision="e8ec4507b89b3b0471894515e1f80794eb92664f")


class ReportTests(unittest.TestCase):
    def test_deterministic_json_and_original_ranking(self):
        before = copy.deepcopy(INPUT)
        report = generate_report(INPUT, **META)
        self.assertEqual(report, generate_report(INPUT, **META))
        self.assertEqual(INPUT, before)
        json.dumps(report, allow_nan=False)
        self.assertEqual(report["ranked_options"][0]["runtime_tag"], "deepseek-coder-v2:16b")
        self.assertGreaterEqual(len(report["ranked_options"]), 3)
        self.assertEqual(report["device_profile"]["model_budget_gib"], 36)
        top = report["ranked_options"][0]
        self.assertAlmostEqual(top["calculation_total_gib"], 11.15)
        self.assertAlmostEqual(top["headroom_gib"], 24.85)
        self.assertEqual(top["est_tok_s"], 20.8)
        estimate = 273 / 11.15 * .85
        self.assertAlmostEqual(top["estimate_band_tok_s"][0], estimate * .75)
        self.assertAlmostEqual(top["estimate_band_tok_s"][1], estimate * 1.25)
        self.assertEqual(report["provenance"]["memory_gib"], "buyer-supplied")
        self.assertEqual(report["provenance"]["minimum_context_tokens"], "documented fallback")

    def test_catalog_hash_and_commands_pinned(self):
        report = generate_report(INPUT, **META)
        expected = hashlib.sha256(Path("src/beanfit/catalog/models.py").read_bytes()).hexdigest()
        self.assertEqual(report["versions"]["catalog_sha256"], expected)
        tags = {row.runtime_tag for row in CATALOG}
        for row in report["ranked_options"]:
            self.assertIn(row["runtime_tag"], tags)
        self.assertEqual(report["commands"][0]["catalog_tag"], report["ranked_options"][0]["runtime_tag"])
        self.assertIn(report["commands"][1]["catalog_tag"], MLX_REPOS.values())

    def test_unknown_chip_fallback_band(self):
        report = generate_report(dict(INPUT, device_chip="Apple M9 Ultra"), **META)
        self.assertEqual(report["device_profile"]["bw_source"], "unknown_fallback")
        self.assertTrue(all(row["est_uncertainty_pct"] == 50 for row in report["ranked_options"]))

    def test_estimated_chip_band(self):
        report = generate_report(dict(INPUT, device_chip="Apple M5 Pro"), **META)
        self.assertTrue(all(row["est_uncertainty_pct"] == 40 for row in report["ranked_options"]))

    def test_no_fit_explicit(self):
        report = generate_report(dict(INPUT, memory_gib=8), **META)
        self.assertEqual(report["ranked_options"], [])
        self.assertEqual(report["commands"], [])
        self.assertIn("Fewer than three", report["markdown"])

    def test_mlx_preference(self):
        report = generate_report(dict(INPUT, preferred_runtime="mlx"), **META)
        self.assertEqual(report["commands"][0]["runtime"], "mlx")

    def test_context_within_assumption_and_explicit_limitations(self):
        report = generate_report(dict(INPUT, minimum_context_tokens=8192, installed_runtime_versions={"ollama":"0.12.3", "mlx":"0.24.0"}), **META)
        self.assertEqual(report["accepted_inputs"]["minimum_context_tokens"], 8192)
        self.assertIn("does not guarantee", report["markdown"])
        self.assertIn("not a measured benchmark", report["markdown"])
        self.assertIn("one business day", report["markdown"])
        self.assertIn("seven calendar days", report["markdown"])
        self.assertIn("one clarification thread", report["markdown"])
        self.assertIn("full refund", report["markdown"])
        self.assertIn("original transaction ID", report["markdown"])

    def test_rejections_never_echo_private_payloads(self):
        invalid = [None, [], {}, dict(INPUT, token="SECRET_CANARY"), dict(INPUT, device_chip="SECRET_CANARY"), dict(INPUT, operating_system="SECRET_CANARY"), dict(INPUT, constraints="SECRET_CANARY"), dict(INPUT, installed_runtime_versions={"ollama":"SECRET_CANARY"}), dict(INPUT, use_case="SECRET_CANARY")]
        for item in invalid:
            with self.subTest(item=type(item)):
                with self.assertRaises(InputRejected) as caught:
                    generate_report(item, **META)
                self.assertNotIn("SECRET_CANARY", str(caught.exception))

    def test_strict_types_and_supported_bounds(self):
        cases = [("memory_gib", v) for v in [True, 0, -1, 1, 3, 4, 7, 1.5, "48", 4097, None]]
        cases += [("minimum_context_tokens", v) for v in [True, 0, -1, 16385, "8192", None]]
        cases += [("latency_preference", v) for v in ["fastest", [], None]]
        cases += [("preferred_runtime", v) for v in ["bash", [], None]]
        cases += [("constraints", v) for v in ["a " * 501, "private customer record", 0, None]]
        cases += [("installed_runtime_versions", v) for v in ["1.0", {"other":"1.0"}, {"mlx":"1.0; echo bad"}, {"mlx":None}]]
        cases += [("operating_system", v) for v in ["macOS", "macOS 15 x86_64", "Linux arm64", "macOS 15 arm64\nmalicious"]]
        for field, val in cases:
            with self.subTest(field=field, value=val):
                with self.assertRaises(InputRejected):
                    validate_input(dict(INPUT, **{field:val}))

    def test_latency_preferences_order_existing_estimates(self):
        balanced = generate_report(INPUT, **META)
        original = {row["runtime_tag"]: row for row in balanced["ranked_options"]}
        for preference, key in [("quality", "quality"), ("speed", "est_tok_s")]:
            report = generate_report(dict(INPUT, latency_preference=preference), **META)
            ordering = [(row[key], row["score"]) for row in report["ranked_options"]]
            self.assertEqual(ordering, sorted(ordering, reverse=True))
            for row in report["ranked_options"]:
                for field in ["est_tok_s", "estimate_band_tok_s", "calculation_total_gib", "score"]:
                    self.assertEqual(row[field], original[row["runtime_tag"]][field])
            self.assertIn("deterministic adapter ordering", report["markdown"])

    def test_nested_and_secret_patterns_rejected_without_echo(self):
        secrets = ["-----BEGIN PRIVATE KEY-----", "Bearer xxxxx", "apify_api_CANARY123", "customer@example.com", "customer SSN 123-45-6789", {"private": ["nested secret"]}]
        for payload in secrets:
            for field in ["constraints", "installed_runtime_versions", "operating_system", "device_chip", "preferred_runtime", "latency_preference"]:
                with self.subTest(field=field, payload_type=type(payload)):
                    with self.assertRaises(InputRejected) as caught:
                        generate_report(dict(INPUT, **{field:payload}), **META)
                    self.assertNotIn(str(payload), str(caught.exception))

    def test_valid_unsupported_inputs_need_review(self):
        for extra in [{"minimum_context_tokens": 16385}, {"constraints": "Prefer a model suitable for short code explanations."}, {"constraints": "workload " * 500}]:
            with self.subTest(extra=list(extra)):
                with self.assertRaises(NeedsReview) as caught:
                    generate_report(dict(INPUT, **extra), **META)
                self.assertEqual(caught.exception.code, "NEEDS_REVIEW")
                self.assertIn("No report was generated", str(caught.exception))
                if "constraints" in extra:
                    self.assertNotIn(extra["constraints"], str(caught.exception))

    def test_sensitive_or_malformed_input_is_not_review_status(self):
        for extra in [{"constraints": "workload " * 501}, {"constraints": {"nested": "value"}}, {"minimum_context_tokens": 0}, {"minimum_context_tokens": 16385, "constraints": "api_key=CANARY"}, {"constraints": "Customer email jane@example.com"}, {"constraints": "-----BEGIN PRIVATE KEY-----"}]:
            with self.subTest(extra=list(extra)):
                with self.assertRaises(InputRejected) as caught:
                    generate_report(dict(INPUT, **extra), **META)
                self.assertEqual(caught.exception.code, "INVALID_INPUT")
                self.assertNotIsInstance(caught.exception, NeedsReview)

    def test_bad_provenance_rejected(self):
        for meta in [dict(META, repository_revision="main"), dict(META, generated_at="2026-09-04"), dict(META, generated_at="invalid")]:
            with self.assertRaises(InputRejected):
                generate_report(INPUT, **meta)


if __name__ == "__main__":
    unittest.main()
