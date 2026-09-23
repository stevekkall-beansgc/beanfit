# beanfit

**What local AI actually fits — and runs well — on THIS device.**

beanfit detects your hardware, ranks local models by quant × runtime fit with
honest speed estimates, and tells you exactly how to run the best one.

```
$ beanfit
beanfit · Apple M5 Max · 128.0 GiB unified
Metal working-set cap ~96.0 GiB → model budget 96.0 GiB (~600 GB/s ±40% est [BW estimate])

MODEL                     QUANT      TOTAL   TOK/S  FIT    SCORE
----------------------------------------------------------------
Gemma 3 27B               q4_K_M     17.9G    28.5  yes    122.3
Qwen3 30B-A3B (MoE)       q4_K_M     19.9G    25.6  yes    121.8
...
Pick: Gemma 3 27B (q4_K_M) — quality 9/10, ~28.5 tok/s est (±40%). Verify: ollama run --verbose.
Run it:
  $ ollama pull gemma3:27b && ollama run gemma3:27b
```

## Install

```bash
# Run directly from a source clone (zero Python dependencies; package is not
# published to PyPI).
git clone https://github.com/stevekkall-beansgc/beanfit && cd beanfit
PYTHONPATH=src python3 -m beanfit
```

## Five-minute showcase

1. **Run the CLI (1 minute).** From the clone, try both renderers:
   ```bash
   PYTHONPATH=src python3 -m beanfit
   PYTHONPATH=src python3 -m beanfit --json
   ```
   [`src/beanfit/cli.py`](src/beanfit/cli.py) shows argument parsing, hardware
   detection, evaluation, and renderer selection in one small entry point.
2. **Follow the core path (1 minute).** Start at
   [`src/beanfit/hw/macos.py`](src/beanfit/hw/macos.py), then read
   [`src/beanfit/engine/evaluate.py`](src/beanfit/engine/evaluate.py) and
   [`src/beanfit/emit/table.py`](src/beanfit/emit/table.py).
   [`src/beanfit/catalog/models.py`](src/beanfit/catalog/models.py) holds the
   pinned model metadata used by that path.
3. **Verify the contracts (2 minutes).** Run the complete stdlib suite:
   ```bash
   PYTHONPATH=src python3 -m unittest discover -s tests -q
   ```
   [`tests/test_cli.py`](tests/test_cli.py) and
   [`tests/test_hw_macos.py`](tests/test_hw_macos.py) make the CLI and hardware
   behavior directly checkable with fixtures and mocks.
4. **Read the estimate model (1 minute).**
   [`src/beanfit/engine/estimate.py`](src/beanfit/engine/estimate.py)
   centralizes the decode formula, context assumption, quantization factors,
   and uncertainty bands. Its `assumptions()` output is included in every JSON
   response by [`src/beanfit/emit/json_out.py`](src/beanfit/emit/json_out.py).

**Not a benchmark:** beanfit does not run model inference or measure tok/s,
quality, thermals, prompts, runtime behavior, or context limits. Its speed
numbers are estimates from static catalog and bandwidth inputs, so validate a
generated command on the target machine.

The fit showcase ends here. Activation and payment material is isolated under
[Synthetic activation candidate](#synthetic-activation-candidate-separate) and
is not evidence for the fit CLI's estimates.

## Why another fit-checker?

llmfit, paddock, ModelFit & friends answer *"which model fits?"* beanfit is
building toward **whole-stack configuration**: runtime choice (MLX-first on
Apple Silicon), context budget, agent-harness configs (`num_ctx`, sub-agent
model tiers, `mcp.json` sizing), emitted as runnable commands — not tables.
See [ROADMAP.md](ROADMAP.md) for the full plan.

## Status: v0.4.2 (fit-estimate honesty and unsupported-hardware safeguards)

Works today on Apple Silicon Macs. Stdlib only, zero runtime dependencies.

- ✅ packaged CLI (`beanfit` / `python -m beanfit`), module layout, 3-OS CI
- ✅ scheduled weekly and manual live catalog validation; MLX repository names
  were selected from registry checks, not guessed
- ✅ honesty bands: every speed number carries its uncertainty and source class
- 🚧 Phase 1: Windows / Linux / discrete-GPU detection ([ROADMAP.md](ROADMAP.md))
- 🚧 Phase 3: `beanfit init` — emit full stack config for your agent tooling

## Honesty policy

Speed numbers are **estimates with explicit uncertainty bands** (±25% when
bandwidth comes from public spec sheets, ±40% for pre-release estimates,
±50% for unknown chips) and every `--json` output ships the full estimation
model in `assumptions`. Verify against reality with `ollama run --verbose`.

Model tags are checked against ollama.com and Hugging Face by a scheduled
weekly workflow and can be checked manually with `scripts/validate_catalog.py`.
That check is not yet part of the release gate, so a release is **not**
guaranteed to contain live tags; verify them again before relying on a command.
MLX repo names were selected from live registry lookups because name-guessing
produced broken launch commands in v0.1. The current selector tries q4 first
and does not automatically choose q8 when both quantizations fit.

## Privacy

No telemetry in this version. A documented, opt-in anonymous beacon is
planned with `init` (roadmap Phase 3) — it will be off by default and
described here before it ships.

## Use cases

```bash
beanfit                       # chat picks
beanfit --use-case coding     # coding/reasoning weights
beanfit --json                # machine-readable + full assumptions (agent consumption)
```

## Development

```bash
git clone https://github.com/stevekkall-beansgc/beanfit && cd beanfit
PYTHONPATH=src python3 -m unittest discover -s tests   # stdlib only, no install needed
python scripts/validate_catalog.py                     # live registry check
```

### Static check (pinned Ruff)

`scripts/static_check.py` is the one scripted static-check entry point for
`src/`, `scripts/`, and `tests/`. The Ruff version is pinned in
`requirements-lint.txt` (single pin source); the script refuses to run any
other Ruff. CI's `lint` job installs that pin and runs this check as a
non-ignored job — the regression test in `tests/test_static_check.py`
keeps that wiring from silently drifting.

```bash
pip install -r requirements-lint.txt
python scripts/static_check.py   # ruff 0.16.8, targets src/ scripts/ tests/
```

Rule set is deliberately modest and meaningful: pyflakes `F` (syntax,
undefined names, unused imports, basic errors) plus syntax-level runtime
errors (`E9`). Configured under `[tool.ruff]` in `pyproject.toml`.

## Security

Report suspected vulnerabilities through the private channel described in
[SECURITY.md](SECURITY.md). Do not post exploit details in public issues, pull
requests, or discussions.

---

**Agents:** see [AGENTS.md](AGENTS.md) before changing anything here.

## Synthetic activation candidate (separate)

This material is separate from the fit CLI above. The
[first-dollar activation package](docs/activation/README.md) contains a
synthetic-only order ledger, Stripe test transport, correction/refund controls,
anonymized five-prospect distribution plan, and verification receipts. It is not
live, customer-ready, or evidence for the fit estimates. Run
`python3 scripts/check_activation_qa.py` for its central QA registration and
`python3 scripts/activation_demo.py` for the offline end-to-end fixture; neither
creates provider payments.
