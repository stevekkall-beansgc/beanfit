# Contributing to beanfit

beanfit is a public, standard-library-only Python project. This guide is
self-contained: a clean checkout and the commands below are enough to set up,
test, and inspect the project. It does not depend on private project-management
documents, credentials, cloud accounts, or private test runners.

## Requirements

- Git.
- Python 3.10 or newer.
- Network access only for installing the pinned Ruff version and for the
  explicitly live catalog check.

## Clean-checkout setup

Run these commands from a fresh clone:

```sh
git clone https://github.com/stevekkall-beansgc/beanfit.git
cd beanfit
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-lint.txt
git status --short
```

The final command should print nothing. The runtime and unit tests need only
the Python standard library; the install above is for the repository's pinned
static check. On Windows, activate the environment with
`.venv\Scripts\Activate.ps1` instead.

## Local verification

Run the complete offline test suite:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

Run the offline activation demonstration:

```sh
python3 scripts/activation_demo.py
```

Run the pinned static check after installing `requirements-lint.txt`:

```sh
python3 scripts/static_check.py
```

## Catalog validation and release receipts

The ordinary catalog command performs live HTTP GETs against Ollama and the
pinned Hugging Face repositories. Run it explicitly when you want a live
check:

```sh
python3 scripts/validate_catalog.py --json
```

For a release-time receipt, an operator must manually run the following from a
clean checkout of the exact release commit and write the machine-readable
receipt to the ignored local artifact directory:

```sh
git status --porcelain
git rev-parse HEAD
python3 scripts/validate_catalog.py --receipt .catalog-receipts/catalog-validation.json
```

The `git status --porcelain` output must be empty; the validator refuses a
receipt from a dirty checkout. There is no automatic release-gate integration.
The receipt records the full source Git revision, package version, SHA-256 of `scripts/validate_catalog.py`,
UTC start and completion times, every `PASS`,
`WARN`, or `FAIL` result, and the overall status. A blocking failure exits
nonzero. If a registry is unreachable, the receipt records a `FAIL` and the
command exits nonzero; it must not be reported as a pass. Registry liveness is
a point-in-time observation, not performance evidence: HTTP 200 does not
measure speed, quality, quantization, hardware fit, or future availability.
`--allow-dirty` is only for local diagnosis and is not a release receipt.
Archive the generated JSON with the release rather than replacing it with a
hand-written summary.

The deterministic pull-request workflow runs tests, static checks, and the
offline demo. Live registry traffic stays in the separate manual/scheduled
catalog workflow so third-party availability cannot make PR CI flaky.

For a new catalog row, use a verified Ollama tag and a deliberately pinned HF
MLX repository, or document why no MLX repository is used. Run the live
validator before relying on an emitted command; do not replace a failed pin
with a guessed name.

## Product boundaries

This contribution path does not implement `beanfit init` and does not expand
hardware detection beyond the currently supported Apple Silicon path. Those are
separate product choices, not prerequisites for this contribution; see
`ROADMAP.md` before proposing either as incidental scope.

## Before opening a change

- Keep changes focused and preserve the existing uncertainty bands and
  assumptions in fit output.
- Never commit credentials, private keys, customer data, or generated private
  material.
- Add or update offline tests for behavior changes.
- Include the commands you ran and the results in the pull request.
