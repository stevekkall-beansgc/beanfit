import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_REPORT_URL = (
    "https://github.com/stevekkall-beansgc/beanfit/security/advisories/new"
)


class SecurityPolicy(unittest.TestCase):
    def test_private_reporting_route(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")

        self.assertIn("[SECURITY.md](SECURITY.md)", readme)
        self.assertIn(PRIVATE_REPORT_URL, security)
        self.assertIn("## Supported versions", security)
        self.assertIn("## Scope", security)
        self.assertIn("Do not post exploit details", security)


class ShowcaseRoute(unittest.TestCase):
    def test_required_reading_links_and_limitations(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for path in (
            "src/beanfit/cli.py",
            "src/beanfit/hw/macos.py",
            "src/beanfit/engine/evaluate.py",
            "tests/test_cli.py",
            "tests/test_hw_macos.py",
            "src/beanfit/engine/estimate.py",
        ):
            with self.subTest(path=path):
                self.assertIn(f"]({path})", readme)

        self.assertIn("**Not a benchmark:**", readme)
        self.assertIn("synthetic-only", readme)


class PublicContributionGuide(unittest.TestCase):
    def test_setup_and_verification_commands_are_explicit(self):
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

        for command in (
            "git clone https://github.com/stevekkall-beansgc/beanfit.git",
            "python3 -m venv .venv",
            "python3 -m pip install -r requirements-lint.txt",
            "PYTHONPATH=src python3 -m unittest discover -s tests",
            "python3 scripts/activation_demo.py",
            "python3 scripts/static_check.py",
            "python3 scripts/validate_catalog.py --json",
            "git rev-parse HEAD",
            "--receipt .catalog-receipts/catalog-validation.json",
        ):
            with self.subTest(command=command):
                self.assertIn(command, contributing)

        self.assertNotIn("github.com/stevekkall-beansgc/agency", contributing)
        self.assertNotIn("qa-kit", contributing)
        self.assertNotIn("~/beans", contributing)

    def test_receipt_and_product_boundaries_are_documented(self):
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("point-in-time", contributing)
        self.assertIn("not performance evidence", contributing)
        self.assertIn("unreachable", contributing)
        self.assertIn("must not be reported", contributing)
        self.assertIn("no automatic release-gate integration", contributing.lower())
        self.assertIn("SHA-256 of `scripts/validate_catalog.py`", contributing)
        self.assertIn("`beanfit init`", contributing)
        self.assertIn("hardware detection", contributing)
        self.assertIn("separate product choices", contributing)
        self.assertIn("point-in-time", readme)
        self.assertIn("no automatic release-gate integration", readme.lower())
        self.assertIn("clean checkout of the exact release commit", readme)
        self.assertIn("SHA-256 of `scripts/validate_catalog.py`", readme)
        self.assertNotIn("Release-time validation writes", readme)

    def test_live_catalog_validation_is_not_in_pr_ci(self):
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        catalog = (ROOT / ".github" / "workflows" / "catalog.yml").read_text(
            encoding="utf-8"
        )
        gate = (ROOT / ".github" / "workflows" / "gate.yml").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("validate_catalog.py", ci)
        self.assertNotIn("--receipt", catalog)
        self.assertNotIn("validate_catalog.py", gate)
        self.assertIn("validate_catalog.py", catalog)
        self.assertIn("deterministic pull-request workflow", contributing)
        self.assertIn("no automatic release-gate integration", contributing.lower())


if __name__ == "__main__":
    unittest.main()
