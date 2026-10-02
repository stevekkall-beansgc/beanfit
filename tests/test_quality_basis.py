import contextlib
import hashlib
import io
import json
import unittest
from pathlib import Path
from unittest import mock

from beanfit.catalog.models import CATALOG
from beanfit.cli import main
from beanfit.emit import render_table
from beanfit.engine import evaluate
from tests.fixtures import M5_MAX_128


ROOT = Path(__file__).resolve().parents[1]


class QualityBasis(unittest.TestCase):
    def cli_json(self, argv):
        output = io.StringIO()
        with mock.patch("beanfit.cli.detect", return_value=M5_MAX_128):
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(argv), 0)
        return json.loads(output.getvalue())

    def test_catalog_export_identifies_every_legacy_rating(self):
        doc = self.cli_json(["--export-catalog"])
        basis = doc["quality_basis"]
        self.assertEqual(basis["basis"], "legacy_editorial")
        self.assertEqual(basis["metadata_as_of"], "2026-10-02")
        self.assertIsNone(basis["original_assignment_date"])
        self.assertIsNone(basis["empirical_evidence"])
        self.assertEqual(basis["rubric_status"], "proposed_not_applied_or_calibrated")
        self.assertEqual(basis["inventory"], [
            {"runtime_tag": entry.runtime_tag,
             "coding": entry.qual_coding,
             "reasoning": entry.qual_reasoning,
             "chat": entry.qual_chat}
            for entry in CATALOG
        ])
        # Additive metadata must not redefine the existing catalog hash/schema.
        encoded = json.dumps(doc["models"], sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(doc["catalog_sha256"], hashlib.sha256(encoded).hexdigest())
        self.assertEqual(doc["artifact_schema"], 1)

    def test_all_use_cases_expose_basis_without_changing_ranked_rows(self):
        for use_case in ("chat", "coding", "reasoning"):
            with self.subTest(use_case=use_case):
                doc = self.cli_json(["--json", "--use-case", use_case])
                self.assertEqual(doc["ranked"], evaluate(M5_MAX_128, use_case))
                basis = doc["quality_basis"]
                self.assertEqual(basis["selected_use_case"], use_case)
                self.assertEqual(basis["selected_catalog_field"], f"qual_{use_case}")
                self.assertIn("unknown", basis["assignment_method"])
                self.assertIn("not an accuracy", basis["interpretation"])
                self.assertEqual(len(basis["inventory"]), 8)

    def test_table_discloses_unknown_historical_basis(self):
        out = render_table(M5_MAX_128, evaluate(M5_MAX_128, "chat"), "chat")
        self.assertIn("historical assignment basis unknown", out)
        self.assertIn("metadata as of 2026-10-02", out)
        self.assertIn("docs/QUALITY-BASIS.md", out)

    def test_docs_inventory_matches_export_and_separates_future_rubric(self):
        text = (ROOT / "docs" / "QUALITY-BASIS.md").read_text(encoding="utf-8")
        for entry in CATALOG:
            self.assertIn(
                f"| `{entry.runtime_tag}` | {entry.qual_coding} | "
                f"{entry.qual_reasoning} | {entry.qual_chat} |", text
            )
        self.assertIn("2026-10-02", text)
        self.assertIn("Proposed future rubric", text)
        self.assertIn("has not been applied", text)
        self.assertIn("owner approval", text)
        self.assertIn("122.3", text)


if __name__ == "__main__":
    unittest.main()
