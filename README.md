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
Gemma 4 31B               q4_K_M     20.4G    25.0  yes    121.8
Qwen3.6 35B-A3B (MoE)     q4_K_M     22.4G    22.7  yes    121.4
...
Pick: Gemma 4 31B (q4_K_M) — quality 9/10, ~25.0 tok/s est (±40%). Verify: ollama run --verbose.
Run it:
  $ ollama pull gemma4:31b && ollama run gemma4:31b
```

## Install

```bash
# pipx or uv (recommended)
pipx install beanfit        # or: uv tool install beanfit

# no installer? run straight from a clone
python3 -m beanfit
```

## Why another fit-checker?

llmfit, paddock, ModelFit & friends answer *"which model fits?"* beanfit is
building toward **whole-stack configuration**: runtime choice (MLX-first on
Apple Silicon), context budget, agent-harness configs (`num_ctx`, sub-agent
model tiers, `mcp.json` sizing), emitted as runnable commands — not tables.
See [ROADMAP.md](ROADMAP.md) for the full plan.

## Status: v0.3.0 (synthetic activation controls)

Works today on Apple Silicon Macs. Stdlib only, zero runtime dependencies.

- ✅ packaged CLI (`beanfit` / `python -m beanfit`), module layout, 3-OS CI
- ✅ catalog tags validated against live registries weekly (CI-enforced);
  MLX repos pinned to verified builds, not guessed
- ✅ honesty bands: every speed number carries its uncertainty and source class
- 🚧 Phase 1: Windows / Linux / discrete-GPU detection ([ROADMAP.md](ROADMAP.md))
- 🚧 Phase 3: `beanfit init` — emit full stack config for your agent tooling

## Honesty policy

Speed numbers are **estimates with explicit uncertainty bands** (±25% when
bandwidth comes from public spec sheets, ±40% for pre-release estimates,
±50% for unknown chips) and every `--json` output ships the full estimation
model in `assumptions`. Verify against reality with `ollama run --verbose`.

Model tags are checked against ollama.com and Hugging Face by CI weekly;
a release cannot ship with dead tags. MLX repo names are pinned from live
registry lookups because name-guessing produced broken launch commands in v0.1.

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

---

**Agents:** see [AGENTS.md](AGENTS.md) before changing anything here.

## BF-CER activation candidate

The [first-dollar activation package](docs/activation/README.md) contains a
synthetic-only order ledger, Stripe test transport, correction/refund controls,
anonymized five-prospect distribution plan and verification receipts. It is not live or
customer-ready. Run `python3 scripts/check_activation_qa.py` for its
central QA registration and `python3 scripts/activation_demo.py` for the offline
end-to-end fixture; neither creates provider payments.
