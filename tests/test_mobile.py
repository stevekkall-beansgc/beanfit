"""Synthetic observations test policy, never claim actual device measurements."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from beanfit.mobile import EvidenceError, select

ROOT = Path(__file__).resolve().parents[1]


def profile():
    return {"schema": "beanfit.mobile.profile.v1", "product": "fictional badge extraction",
            "device": "fixture phone", "os_build": "fixture OS", "stack_id": "text-only-v1",
            "memory_method": "fixture whole-stack accounting",
            "workload_sha256": hashlib.sha256(b"fictional-eval-v1").hexdigest(),
            "context_tokens": 2048, "output_limit_tokens": 128,
            "memory_budget_bytes": 1_000_000_000, "headroom_fraction": .2,
            "min_quality": .75, "max_p95_latency_ms": 4000,
            "min_repeats": 2, "case_ids": ["recall", "missing-fact"],
            "critical_case_ids": ["missing-fact"]}


def receipt(cid="small", peak=300_000_000, *, kind="physical_device"):
    p = profile()
    return {**{k: p[k] for k in ("device", "os_build", "stack_id", "memory_method",
                                "workload_sha256", "context_tokens", "output_limit_tokens")},
            "schema": "beanfit.mobile.receipt.v1", "evidence_kind": kind,
            "recorded_at": "2026-09-26T00:00:00Z", "evidence_ref": "synthetic-test-only",
            "candidate": {"id": cid, "runtime": "fixture", "runtime_revision": "fixture-v1",
                          "model_revision": "fixture-v1", "weights_bytes": 100_000_000},
            "memory_scope": "whole_stack_incremental_peak", "inference_location": "on_device",
            "offline_verified": True,
            "trials": [{"id": f"{case}-{i}", "case_id": case, "quality_pass": True,
                        "outcome": "completed", "peak_stack_bytes": peak, "latency_ms": 1000}
                       for case in p["case_ids"] for i in range(2)]}


class MobileTests(unittest.TestCase):
    def test_smallest_qualified_wins_over_quality_maximizer(self):
        small = receipt()
        small["trials"][0]["quality_pass"] = False
        large = receipt("large", 700_000_000)
        result = select(profile(), [large, small])
        self.assertEqual(result["selection"]["id"], "small")
        self.assertEqual(result["ranking"], ["small", "large"])

    def test_smaller_unqualified_model_loses(self):
        tiny = receipt("tiny", 100_000_000)
        tiny["trials"][0]["quality_pass"] = False
        tiny["trials"][1]["quality_pass"] = False
        result = select(profile(), [tiny, receipt()])
        self.assertEqual(result["selection"]["id"], "small")

    def test_critical_failure_overrides_average(self):
        row = receipt()
        row["trials"][2]["quality_pass"] = False
        result = select(profile(), [row])
        self.assertIsNone(result["selection"])
        self.assertIn("critical_case_failed", result["candidates"][0]["reasons"])

    def test_peak_not_average_or_weight_size_is_objective(self):
        row = receipt("spiky", 100_000_000)
        row["candidate"]["weights_bytes"] = 1
        row["trials"][3]["peak_stack_bytes"] = 600_000_000
        result = select(profile(), [row, receipt()])
        self.assertEqual(result["selection"]["id"], "small")

    def test_headroom_budget(self):
        self.assertIsNone(select(profile(), [receipt(peak=900_000_000)])["selection"])

    def test_p95_latency_and_tie_break(self):
        row = receipt("slow")
        row["trials"][3]["latency_ms"] = 5000
        self.assertIsNone(select(profile(), [row])["selection"])
        row["trials"][3]["latency_ms"] = 3000
        self.assertEqual(select(profile(), [row, receipt()])["selection"]["id"], "small")

    def test_simulator_and_synthetic_never_qualify(self):
        for kind in ("simulator", "synthetic"):
            result = select(profile(), [receipt(kind=kind)])
            self.assertIsNone(result["selection"])
            self.assertTrue(result["candidates"][0]["passes_demo_gates"])

    def test_incomparable_profiles_fail_closed(self):
        for key, value in (("device", "other"), ("os_build", "other"), ("context_tokens", True),
                           ("output_limit_tokens", 256), ("stack_id", "speech"),
                           ("workload_sha256", "0" * 64), ("memory_method", "RSS"),
                           ("offline_verified", False), ("inference_location", "cloud"),
                           ("memory_scope", "weights_only")):
            row = receipt(); row[key] = value
            with self.subTest(key=key):
                self.assertIsNone(select(profile(), [row])["selection"])

    def test_incomplete_and_unbalanced_cases_rejected(self):
        for trials in (receipt()["trials"][:2], receipt()["trials"][:3]):
            row = receipt(); row["trials"] = trials
            self.assertIsNone(select(profile(), [row])["selection"])

    def test_failed_trial_not_dropped_from_denominator(self):
        row = receipt()
        row["trials"][0].update(outcome="timeout", quality_pass=False, peak_stack_bytes=None, latency_ms=None)
        result = select(profile(), [row])
        self.assertIsNone(result["selection"])
        self.assertEqual(result["candidates"][0]["quality"], .75)
        self.assertEqual(result["candidates"][0]["failed_trials"], 1)

    def test_nonfinite_boolean_negative_and_huge_metrics_rejected(self):
        for value in (True, -1, float("nan"), float("inf"), 10**400, "10"):
            row = receipt(); row["trials"][0]["latency_ms"] = value
            self.assertIsNone(select(profile(), [row])["selection"])

    def test_duplicate_trials_and_candidates(self):
        row = receipt(); row["trials"][1]["id"] = row["trials"][0]["id"]
        self.assertIsNone(select(profile(), [row])["selection"])
        with self.assertRaises(EvidenceError):
            select(profile(), [receipt(), receipt()])

    def test_invalid_duplicate_cannot_hide_failed_evidence(self):
        bad = receipt()
        bad["trials"] = []
        with self.assertRaises(EvidenceError):
            select(profile(), [bad, receipt()])

    def test_all_failures_stay_unqualified(self):
        row = receipt()
        for trial in row["trials"]:
            trial.update(outcome="failed", quality_pass=False, peak_stack_bytes=None, latency_ms=None)
        result = select(profile(), [row])
        self.assertIsNone(result["selection"])
        self.assertEqual(result["candidates"][0]["quality"], 0)

    def test_profile_requires_real_contract(self):
        for key, value in (("min_quality", True), ("min_repeats", 0), ("case_ids", []),
                           ("critical_case_ids", ["unknown"]), ("memory_budget_bytes", None)):
            p = profile(); p[key] = value
            with self.subTest(key=key), self.assertRaises(EvidenceError):
                select(p, [])

    def test_no_evidence_no_winner(self):
        self.assertEqual(select(profile(), [])["status"], "needs_device_evidence")

    def test_cli_valid_invalid_and_mac_cli_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "profile.json"; r = Path(tmp) / "receipts.json"
            p.write_text(json.dumps(profile())); r.write_text(json.dumps([receipt(kind="synthetic")]))
            cmd = [sys.executable, "-m", "beanfit", "mobile", "--profile", str(p), "--receipts", str(r)]
            run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIsNone(json.loads(run.stdout)["selection"])
            p.write_text("{}")
            run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
