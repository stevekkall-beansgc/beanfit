"""Synthetic evidence-boundary checks; these do not run any model."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/iphone/receipt.py"
spec = importlib.util.spec_from_file_location("iphone_receipt", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class IPhoneReceiptTests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "schema": "beanfit.iphone.text.v1", "evidence_kind": "synthetic",
            "device": "synthetic phone", "os_build": "fixture", "runtime": "fixture",
            "model": "fixture", "recorded_at": "fixture", "case_id": "fixture",
            "scope": "text_only", "inference_location": "on_device",
            "offline_verified": False, "outcome": "completed",
            "first_text_ms": 100, "total_ms": 300,
        }

    def test_simulator_and_synthetic_never_become_device_evidence(self):
        for kind in ("simulator", "synthetic"):
            self.row["evidence_kind"] = kind
            result = module.summarize(self.row)
            self.assertEqual(result["status"], "not_device_performance_evidence")
            self.assertFalse(result["iphone_voice_ready"])

    def test_even_physical_text_is_not_voice_or_fit_proof(self):
        self.row["evidence_kind"] = "physical_device"
        result = module.summarize(self.row)
        self.assertEqual(result["status"], "physical_text_observation")
        self.assertEqual(result["fit"], "unknown")
        self.assertIsNone(result["tokens_per_second"])
        self.assertFalse(result["iphone_voice_ready"])

    def test_reject_invalid_and_nonfinite_timings(self):
        for bad in (-1, True, float("nan"), float("inf"), "100", 301, 10**400):
            row = copy.deepcopy(self.row)
            row["first_text_ms"] = bad
            with self.subTest(value=bad), self.assertRaises(ValueError):
                module.summarize(row)

    def test_completed_requires_timings(self):
        self.row["first_text_ms"] = None
        with self.assertRaises(ValueError):
            module.summarize(self.row)

    def test_unavailable_is_not_a_zero_latency_result(self):
        self.row.update(outcome="unavailable", first_text_ms=None, total_ms=None)
        self.assertIsNone(module.summarize(self.row)["total_ms"])
        self.row["total_ms"] = 0
        with self.assertRaises(ValueError):
            module.summarize(self.row)

    def test_partial_failure_never_counts_as_success(self):
        self.row.update(evidence_kind="physical_device", outcome="failed")
        self.assertEqual(module.summarize(self.row)["status"], "not_device_performance_evidence")

    def test_reject_missing_identity_cloud_or_offline_claim(self):
        for field, value in (("device", ""), ("schema", "v2"), ("evidence_kind", None),
                             ("inference_location", "cloud"), ("offline_verified", True),
                             ("scope", "voice"), ("outcome", "pass")):
            row = {**self.row, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                module.summarize(row)

    def test_cli_valid_and_invalid_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps(self.row))
            run = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertFalse(json.loads(run.stdout)["iphone_voice_ready"])
            path.write_text('{"schema": "unknown"}')
            run = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn("Invalid receipt", run.stderr)
