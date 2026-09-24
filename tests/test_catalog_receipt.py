import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from beanfit import __version__


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_catalog as catalog_cli


def validator_sha256():
    return hashlib.sha256(
        (ROOT / "scripts" / "validate_catalog.py").read_bytes()
    ).hexdigest()


def result(ok=True, blocking=True, status=200, error=None):
    return {
        "model": "fixture",
        "kind": "ollama",
        "id": "fixture:tag",
        "url": "https://ollama.com/library/fixture:tag",
        "status": status,
        "ok": ok,
        "blocking": blocking,
        "error": error,
    }


class CatalogReceiptFormatting(unittest.TestCase):
    def test_pass_receipt_contains_identity_and_scope(self):
        receipt = catalog_cli.build_receipt(
            [result()],
            "a" * 40,
            __version__,
            "2026-09-24T12:00:00Z",
        )

        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["source_revision"], "a" * 40)
        self.assertEqual(receipt["source"]["revision"], "a" * 40)
        self.assertEqual(receipt["package_version"], __version__)
        self.assertNotIn("validator_version", receipt)
        self.assertEqual(
            receipt["validator"],
            {
                "entrypoint": "scripts/validate_catalog.py",
                "hash_algorithm": "sha256",
                "hash_scope": "scripts/validate_catalog.py bytes",
                "sha256": validator_sha256(),
            },
        )
        self.assertEqual(receipt["validated_at"], "2026-09-24T12:00:00Z")
        self.assertEqual(receipt["summary"], {"total": 1, "pass": 1, "warn": 0, "fail": 0})
        self.assertEqual(receipt["results"][0]["result"], "PASS")
        self.assertIn("point-in-time", receipt["limitations"])
        self.assertIn("not performance evidence", receipt["limitations"])
        json.dumps(receipt)

    def test_validator_hash_tracks_exact_entrypoint(self):
        self.assertEqual(catalog_cli.validator_sha256(), validator_sha256())

    def test_warn_and_fail_are_distinct_in_receipt(self):
        receipt = catalog_cli.build_receipt(
            [result(), result(ok=False, blocking=False, status=503, error="offline")],
            "b" * 40,
            __version__,
            "2026-09-24T12:00:00Z",
        )
        self.assertEqual(receipt["status"], "WARN")
        self.assertEqual(receipt["summary"]["pass"], 1)
        self.assertEqual(receipt["summary"]["warn"], 1)
        self.assertEqual(receipt["summary"]["fail"], 0)

        receipt = catalog_cli.build_receipt(
            [result(ok=False, status=None, error="connection refused")],
            "b" * 40,
            __version__,
            "2026-09-24T12:00:00Z",
        )
        self.assertEqual(receipt["status"], "FAIL")
        self.assertEqual(receipt["summary"]["fail"], 1)
        self.assertEqual(receipt["results"][0]["error"], "connection refused")

        dirty = catalog_cli.build_receipt(
            [result()], "b" * 40, __version__, "2026-09-24T12:00:00Z", source_dirty=True
        )
        self.assertEqual(dirty["status"], "WARN")
        self.assertTrue(dirty["source"]["dirty"])

    def test_receipt_file_is_valid_json(self):
        receipt = catalog_cli.build_receipt(
            [result()], "c" * 40, __version__, "2026-09-24T12:00:00Z"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "catalog-receipt.json"
            catalog_cli.write_receipt(path, receipt)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), receipt)


class CatalogReceiptEntryPoint(unittest.TestCase):
    def test_main_uses_validator_and_writes_receipt_offline(self):
        fixture = [result()]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog-receipt.json"
            with mock.patch.object(
                catalog_cli, "source_revision", return_value="d" * 40
            ), mock.patch.object(
                catalog_cli, "source_tree_dirty", return_value=False
            ), mock.patch.object(
                catalog_cli, "validate_catalog", return_value=fixture
            ) as validator, mock.patch.object(
                catalog_cli, "utc_timestamp", side_effect=[
                    "2026-09-24T12:00:00Z", "2026-09-24T12:00:01Z"
                ]
            ), contextlib.redirect_stdout(io.StringIO()) as output:
                code = catalog_cli.main(["--receipt", str(path)])

            self.assertEqual(code, 0)
            validator.assert_called_once()
            self.assertIn("PASS", output.getvalue())
            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(written["source_revision"], "d" * 40)
            self.assertEqual(written["package_version"], __version__)
            self.assertEqual(written["validator"]["sha256"], validator_sha256())
            self.assertEqual(written["status"], "PASS")

    def test_dirty_release_receipt_is_refused_before_network(self):
        with mock.patch.object(
            catalog_cli, "source_revision", return_value="e" * 40
        ), mock.patch.object(
            catalog_cli, "source_tree_dirty", return_value=True
        ), mock.patch.object(catalog_cli, "validate_catalog") as validator:
            code = catalog_cli.main(["--receipt", "unused.json"])

        self.assertEqual(code, 2)
        validator.assert_not_called()

    def test_network_failure_writes_fail_receipt(self):
        fixture = [result(ok=False, status=None, error="network unreachable")]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog-receipt.json"
            with mock.patch.object(
                catalog_cli, "source_revision", return_value="f" * 40
            ), mock.patch.object(
                catalog_cli, "source_tree_dirty", return_value=False
            ), mock.patch.object(
                catalog_cli, "validate_catalog", return_value=fixture
            ), mock.patch.object(
                catalog_cli,
                "utc_timestamp",
                side_effect=["2026-09-24T12:00:00Z", "2026-09-24T12:00:01Z"],
            ), contextlib.redirect_stdout(io.StringIO()):
                code = catalog_cli.main(["--receipt", str(path)])

            self.assertEqual(code, 1)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))["status"], "FAIL"
            )


if __name__ == "__main__":
    unittest.main()
