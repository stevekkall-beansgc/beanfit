import json
import unittest
from unittest import mock

from beanfit import __version__
from beanfit.cli import main
from tests.fixtures import M5_MAX_128


class CliJson(unittest.TestCase):
    def run_json(self, argv, profile):
        with mock.patch("beanfit.cli.detect", return_value=profile):
            import contextlib
            import io
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(argv)
        return code, out.getvalue()

    def test_json_contract(self):
        code, out = self.run_json(["--json", "--use-case", "coding"], M5_MAX_128)
        self.assertEqual(code, 0)
        doc = json.loads(out)
        for key in ("version", "hardware", "use_case", "assumptions", "ranked"):
            self.assertIn(key, doc)
        self.assertEqual(doc["version"], __version__)
        self.assertEqual(doc["hardware"]["bw_source"], "estimate")
        self.assertIn("formula", doc["assumptions"])
        top = doc["ranked"][0]
        self.assertEqual(top["est_uncertainty_pct"], 40)

    def test_unsupported_platform_exits_2(self):
        from beanfit.hw import UnsupportedPlatform
        exc = UnsupportedPlatform(
            "hardware detection for 'win32' ships in beanfit Phase 1 (see ROADMAP.md)."
        )
        with mock.patch("beanfit.cli.detect", side_effect=exc):
            import contextlib
            import io
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = main(["--json"])
        self.assertEqual(code, 2)
        self.assertIn("Phase 1", err.getvalue())


if __name__ == "__main__":
    unittest.main()
