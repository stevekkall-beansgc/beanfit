"""Exact fixtures for owned CI controls, not a general YAML validator.

The fixture freezes the pre-hardening event/runner/command contract. Only the
reviewed read ceilings, action identities and checkout persistence are added.
It says nothing about hosted execution or the inherited compliance workflow.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = "actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 # existing v5 ref"
PYTHON = "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # existing v5 ref"
CEILING = "permissions:\n  contents: read\n\n"

BASE_CI = '''name: ci

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        os: ${{ fromJSON(github.event_name == 'pull_request' && '["macos-latest","ubuntu-latest","windows-latest"]' || '["beans-mac"]') }}
        python: ${{ fromJSON(github.event_name == 'pull_request' && '["3.10","3.13"]' || '["system"]') }}
    runs-on: ${{ matrix.os }}
    env:
      PYTHONPATH: src
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        if: matrix.python != 'system'
        with:
          python-version: ${{ matrix.python }}
      - name: Prepare system Python
        if: matrix.python == 'system'
        run: |
          python3 -m venv "$RUNNER_TEMP/beanfit-venv"
          echo "$RUNNER_TEMP/beanfit-venv/bin" >> "$GITHUB_PATH"
      - name: Unit tests
        if: github.event_name != 'push'
        run: python -m unittest discover -s tests -v
      - name: Validate with Task on trusted main push
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        run: task validate

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install pinned Ruff
        run: pip install -r requirements-lint.txt
      - name: Pinned static check (ruff 0.16.8)
        run: python scripts/static_check.py

  activation-e2e:
    runs-on: ${{ github.event_name == 'pull_request' && 'ubuntu-latest' || 'beans-mac' }}
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        if: github.event_name == 'pull_request'
        with:
          python-version: "3.12"
      - name: Prepare system Python
        if: github.event_name != 'pull_request'
        run: |
          python3 -m venv "$RUNNER_TEMP/beanfit-venv"
          echo "$RUNNER_TEMP/beanfit-venv/bin" >> "$GITHUB_PATH"
      - name: Offline synthetic activation from a shallow checkout
        run: python scripts/activation_demo.py

  package-smoke:
    strategy:
      matrix:
        os: ${{ fromJSON(github.event_name == 'pull_request' && '["macos-latest","ubuntu-latest","windows-latest"]' || '["beans-mac"]') }}
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        if: github.event_name == 'pull_request'
        with:
          python-version: "3.12"
      - name: Prepare system Python
        if: github.event_name != 'pull_request'
        run: |
          python3 -m venv "$RUNNER_TEMP/beanfit-venv"
          echo "$RUNNER_TEMP/beanfit-venv/bin" >> "$GITHUB_PATH"
      - name: Install package and exercise entry points
        run: |
          pip install .
          beanfit --version
          python -m beanfit --help
'''
BASE_GATE = '''name: gate
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  compliance:
    uses: stevekkall-beansgc/gate-kit/.github/workflows/compliance.yml@v0.4.11
    with:
      repo: beanfit
      full: false
      runner: ${{ github.event_name == 'pull_request' && 'ubuntu-latest' || 'beans-mac' }}
'''


def hardened_fixture(baseline):
    """Apply only the three approved textual edits to the reviewed fixture."""
    text = baseline.replace("concurrency:\n", CEILING + "concurrency:\n", 1)
    text = text.replace(
        "      - uses: actions/checkout@v5\n",
        f"      - uses: {CHECKOUT}\n"
        "        with:\n"
        "          persist-credentials: false\n",
    )
    return text.replace("actions/setup-python@v5", PYTHON)


EXPECTED = {"ci.yml": hardened_fixture(BASE_CI), "gate.yml": hardened_fixture(BASE_GATE)}


def assert_contract(case, name, text):
    # Exact comparison deliberately fails on extra/duplicate YAML controls,
    # checkout ref/token/repository overrides, hidden steps or shell masking.
    # No YAML-library dependency or generalized parsing semantics are claimed.
    case.assertEqual(text, EXPECTED[name])


class OwnedWorkflowContract(unittest.TestCase):
    def test_checked_in_ci_preserves_contract_with_hardening(self):
        assert_contract(self, "ci.yml", (ROOT / ".github/workflows/ci.yml").read_text())

    def test_checked_in_gate_preserves_contract_with_read_ceiling(self):
        assert_contract(self, "gate.yml", (ROOT / ".github/workflows/gate.yml").read_text())

    def test_old_workflows_fail_the_contract(self):
        for name, baseline in (("ci.yml", BASE_CI), ("gate.yml", BASE_GATE)):
            with self.subTest(workflow=name), self.assertRaises(AssertionError):
                assert_contract(self, name, baseline)

    def test_permission_ceiling_mutations_are_rejected(self):
        for name, text in EXPECTED.items():
            mutations = (
                text.replace(CEILING, ""),
                text.replace("contents: read", "contents: write"),
                text.replace("contents: read", "contents: read\n  actions: write"),
                text.replace("jobs:\n", "jobs:\n  hidden:\n    permissions: write-all\n"),
                text.replace("jobs:\n", "permissions: write-all\njobs:\n"),
            )
            for mutated in mutations:
                with self.subTest(workflow=name, mutation=mutated), self.assertRaises(AssertionError):
                    assert_contract(self, name, mutated)

    def test_checkout_credentials_and_event_defaults_are_protected(self):
        text = EXPECTED["ci.yml"]
        for index in range(4):
            marker = "          persist-credentials: false"
            chunks = text.split(marker)
            for change in (
                "          persist-credentials: true",
                "          persist-credentials: false\n          ref: main",
                "          persist-credentials: false\n          repository: other/repo",
                "          persist-credentials: false\n          token: ${{ secrets.OTHER }}",
                "          persist-credentials: false\n        if: false",
                "          persist-credentials: false\n          fetch-depth: 0",
            ):
                mutated = marker.join(chunks[:index + 1]) + change + marker.join(chunks[index + 1:])
                with self.subTest(checkout=index, mutation=change), self.assertRaises(AssertionError):
                    assert_contract(self, "ci.yml", mutated)

    def test_step_failure_propagation_mutations_are_rejected(self):
        text = EXPECTED["ci.yml"]
        commands = (
            "python -m unittest discover -s tests -v", "task validate",
            "pip install -r requirements-lint.txt", "python scripts/static_check.py",
            "python scripts/activation_demo.py", "pip install .",
        )
        for command in commands:
            for suffix in (" || true", " || exit 0"):
                with self.subTest(command=command, suffix=suffix), self.assertRaises(AssertionError):
                    assert_contract(self, "ci.yml", text.replace(command, command + suffix))
        for control in ("continue-on-error: true", "if: false"):
            for line in text.splitlines():
                if line.startswith("        run:"):
                    mutated = text.replace(line, f"        {control}\n{line}", 1)
                    with self.subTest(run=line, control=control), self.assertRaises(AssertionError):
                        assert_contract(self, "ci.yml", mutated)
        for control in ("continue-on-error: true", "if: false"):
            gate = EXPECTED["gate.yml"].replace("  compliance:\n", f"  compliance:\n    {control}\n")
            with self.subTest(workflow="gate.yml", control=control), self.assertRaises(AssertionError):
                assert_contract(self, "gate.yml", gate)

    def test_wrong_or_mutable_action_identities_are_rejected(self):
        for action in (CHECKOUT, PYTHON):
            for replacement in (action.split("@")[0] + "@v5", action.replace("@", "@0", 1)):
                with self.subTest(action=action, replacement=replacement), self.assertRaises(AssertionError):
                    assert_contract(self, "ci.yml", EXPECTED["ci.yml"].replace(action, replacement))


if __name__ == "__main__":
    unittest.main()
