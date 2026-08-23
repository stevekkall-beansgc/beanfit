# beanfit

**What local AI actually fits — and runs well — on THIS device.**

beanfit detects your Apple Silicon hardware (chip, unified memory, Metal
working-set cap), then ranks local models by quant × runtime fit with honest
speed estimates, and tells you exactly how to run the best one.

```
$ python3 beanfit.py
beanfit · Apple M5 Max · 128.0 GiB unified
Metal working-set cap ~96.0 GiB → model budget 96.0 GiB (600 GB/s est BW)

MODEL                     QUANT      TOTAL   TOK/S   FIT    SCORE
----------------------------------------------------------------
Gemma 4 31B               q4_K_M     20.4G    25.0  yes    121.8
Qwen3.6 35B-A3B (MoE)     q4_K_M     22.4G    22.7  yes    121.4
...
Pick: Gemma 4 31B (q4_K_M) — quality 9/10, ~25.0 tok/s est.
Run it:
  $ ollama pull gemma4:31b && ollama run gemma4:31b
```

## Why another fit-checker?

llmfit, paddock, ModelFit & friends answer *"which model fits?"* beanfit is
building toward **whole-stack configuration**: runtime choice (MLX-first on
Apple Silicon), context budget, agent-harness configs (`num_ctx`, sub-agent
model tiers, `mcp.json` sizing), emitted as runnable commands — not tables.

## Status: v0.1 (prototype)

Works today on Apple Silicon Macs. Stdlib only, single file.

- ✅ hardware detection incl. Metal cap · ranked catalog · launch commands
- 🚧 next: `beanfit init` — emit full stack config for your agent tooling
- 🚧 next: drift-watch — "a better model for YOUR machine just landed"

## Honesty policy

Speed numbers are bandwidth-model **estimates**, flagged per chip family
(M5 values are estimates until public spec sheets settle). Model tags are
reality-checked against ollama.com at each release. Estimates ship their
assumptions in-source; verify with `ollama run --verbose`.

## Privacy

No telemetry in v0.1. A documented, opt-in anonymous beacon is planned with
`init` — it will be off by default and described here before it ships.

## Use cases

```bash
python3 beanfit.py                    # chat picks
python3 beanfit.py --use-case coding  # coding/reasoning weights
python3 beanfit.py --json             # machine-readable (agent consumption)
```
