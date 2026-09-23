import re
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PIN = REPO_ROOT / "requirements-lint.txt"
ENTRY = REPO_ROOT / "scripts" / "static_check.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import static_check


def job_block(yaml_text, job_name):
    """Slice the YAML block for a top-level job (2-space job keys)."""
    marker = f"  {job_name}:\n"
    start = yaml_text.index(marker) + len(marker)
    rest = yaml_text[start:]
    nxt = re.search(r"\n  [a-z0-9_-]+:", rest)
    end = start + (nxt.start() if nxt else len(rest))
    return yaml_text[start:end]


class StaticCheckContract(unittest.TestCase):
    def test_single_pin_source(self):
        pins = [ln for ln in PIN.read_text().splitlines() if ln and not ln.startswith("#")]
        self.assertEqual(pins, ["ruff==0.16.8"])

    def test_ci_has_non_ignored_lint_job_calling_pinned_entry(self):
        ci = CI.read_text()
        block = job_block(ci, "lint")
        self.assertIn("pip install -r requirements-lint.txt", block)
        self.assertIn("python scripts/static_check.py", block)
        self.assertNotIn("continue-on-error", block)

    def test_entry_point_enforces_the_pin(self):
        src = ENTRY.read_text()
        self.assertIn("requirements-lint.txt", src)
        self.assertIn("--version", src)
        for target in ("src", "scripts", "tests"):
            self.assertIn(target, src)

    def test_nearby_version_does_not_satisfy_exact_pin(self):
        with mock.patch.object(static_check.subprocess, "run") as run:
            run.return_value.stdout = "ruff 0.16.8.1\n"
            with self.assertRaises(SystemExit):
                static_check.check_version("/fake/ruff", "0.16.8")


if __name__ == "__main__":
    unittest.main()
