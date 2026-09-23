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


if __name__ == "__main__":
    unittest.main()
