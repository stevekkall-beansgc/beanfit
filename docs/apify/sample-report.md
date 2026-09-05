# Beanfit Compatibility Evidence Report

Contract: BF-CER-v1.0 · Generated: 2026-09-04T22:12:51.722222+00:00

## Accepted inputs

- device_chip: "Apple M4 Pro" (buyer-supplied)
- memory_gib: 48 (buyer-supplied)
- use_case: "coding" (buyer-supplied)
- operating_system: "macOS 15.6 arm64" (buyer-supplied)
- preferred_runtime: "no preference" (documented fallback)
- latency_preference: "balanced" (documented fallback)
- minimum_context_tokens: 16384 (documented fallback)
- installed_runtime_versions: {} (documented fallback)
- constraints: "" (documented fallback)

## Versioned evidence

- beanfit: `0.2.0.dev0`
- repository_revision: `e8ec4507b89b3b0471894515e1f80794eb92664f`
- catalog_sha256: `087bae391f4e2271660f986683ce907b48fb2bbb235912ffbed3b636114627cc`
- catalog_hash_scope: `src/beanfit/catalog/models.py bytes`
- report_source_sha256: `2eba6e0e142cbae80d6fac1239b4f744334142ce3c68f22d7fe4643176d8c2a1`
- Bandwidth: 273 GB/s; source: spec_sheet.
- Live registry validation: not performed; offline catalog membership only.

## Fit and memory math

Buyer-supplied RAM: 48 GiB. Fallback Metal cap: 36 GiB (75% RAM). Model budget: 36 GiB = max(4, min(36, 48 - 4)).

Assumptions:
```json
{
  "budget_rule": "min(unified-memory cap, RAM - 4 GiB OS headroom), floor 4 GiB",
  "context_assumption": "half of a 32k-token KV cache included in total GiB",
  "formula": "tok/s \u2248 mem_bandwidth_GBs / total_weights_gib * 0.85 * quant_speedup",
  "quant_speedup": {
    "q4_K_M": 1.0,
    "q8_0": 0.62
  },
  "score_weights": {
    "fit_bonus": 10,
    "no_fit_penalty": -40,
    "quality_weight": 12,
    "speed_cap_tok_s": 60,
    "speed_tiebreak": 0.15
  },
  "uncertainty_pct_by_bw_source": {
    "estimate": 40,
    "spec_sheet": 25,
    "unknown_fallback": 50
  }
}
```

## Ranked compatible options

| Rank | Model | Quant | Total GiB | Estimated tok/s | Estimated band tok/s |
|---:|---|---|---:|---:|---|
| 1 | DeepSeek Coder V2 16B | q4_K_M | 11.15 | 20.8 | 15.61–26.01 (±25%) |
| 2 | gpt-oss 20b (MXFP4) | q4_K_M | 13.2 | 17.6 | 13.18–21.97 (±25%) |
| 3 | Gemma 4 31B | q4_K_M | 20.4 | 11.4 | 8.53–14.22 (±25%) |
| 4 | Qwen3.6 35B-A3B (MoE) | q4_K_M | 22.45 | 10.3 | 7.75–12.92 (±25%) |
| 5 | Llama 4 Scout 17B | q4_K_M | 11.75 | 19.7 | 14.81–24.69 (±25%) |
| 6 | Mistral Small 3.2 24B | q4_K_M | 15.8 | 14.7 | 11.02–18.36 (±25%) |
| 7 | Qwen3.5 9B Instruct | q4_K_M | 6.65 | 34.9 | 26.17–43.62 (±25%) |
| 8 | Phi-4-reasoning 14B | q4_K_M | 9.9 | 23.4 | 17.58–29.30 (±25%) |

Top choice: DeepSeek Coder V2 16B. Unrounded memory calculation: 10.5 + 1.3 / 2 = 11.15 GiB <= 36 GiB budget; headroom 24.85 GiB; budget use 30.9722%.
Estimated decode uses bandwidth / unrounded total × 0.85 × quant speedup; the table includes its uncertainty band.

## Catalog-pinned commands

Primary ollama path:
```sh
ollama pull deepseek-coder-v2:16b && ollama run deepseek-coder-v2:16b
```
Alternate mlx path:
```sh
pip install mlx-lm && mlx_lm.generate --model mlx-community/DeepSeek-Coder-V2-Lite-Instruct-4bit
```

## Local verification checklist

- Check the cited runtime tag/repository still exists and confirm downloaded quantization and native context capacity.
- Record installed runtime versions; run the chosen catalog command locally using a non-sensitive test prompt.
- For Ollama use its --verbose option locally; compare measured throughput and memory pressure with the estimated band. This report does not claim a measured benchmark.
- Stop if memory pressure is excessive. Retain the report and local measurements; never send secrets or private prompts to support.

## Uncertainty and limitations

- This is technical compatibility information, not a measured benchmark. No model is downloaded or executed to create this report.
- Actual performance may fall outside the uncertainty band with thermals, OS pressure, context, prompt shape, runtime version, and model implementation.
- The catalog budgets half of a 32k-token KV cache (16384 tokens). A requested context at or below that assumption does not guarantee a model's native context capacity; verify the model and runtime locally. Launch commands do not configure context.
- Balanced ordering uses the original Beanfit score; quality ordering sorts by catalog quality then original score; speed ordering sorts by estimated decode speed then original score. These are deterministic adapter orderings, not new benchmarks. Nonempty workload constraints require manual review because arbitrary prose and personal-data content cannot be reliably interpreted or screened by this automated path.
- The GPU working-set cap is a 75% RAM fallback, not measured on the buyer's device. Bandwidth is a versioned table lookup or explicitly labeled fallback.
- Catalog quality scores and memory values are illustrative estimates. Fit does not prove output quality, model license suitability, privacy policy, or production reliability.
- Catalog membership is checked offline; live registry tag availability and exact installed quantization are not verified. Generic runtime tags may resolve to a different quantization; verify the downloaded artifact before relying on memory estimates.
- GB/s and GiB retain the original Beanfit estimator convention; this is an engineering approximation, not a precision physical model.
- No investment advice, managed execution, performance or income promises, customer-fund custody, or trading/brokerage action is included.

## Correction, refund, and support policy

- USD $12 covers one device, one use case, and one report revision; delivery within one business day after complete input is accepted.
- If delivery misses the SLA, the buyer may choose a full refund or a new agreed delivery time.
- An operator-caused defect reported within seven calendar days receives one corrected report within one business day at no charge; if it cannot be corrected, issue a full refund.
- For an incorrect or incomplete buyer-supplied device profile, one corrected run is included if requested within seven days; the SLA restarts on receipt of complete inputs.
- A runtime/catalog change after the timestamp is not a defect and requires a new order, unless the cited tag was already invalid at delivery.
- Support is limited to one clarification thread and one correction. No remote access, ongoing tuning, production incident support, installation, custom benchmarking, production deployment, unrelated troubleshooting, or unsupported configuration generation is included.
- Preference disagreement is not a defect. A wrong accepted input, dead catalog tag, arithmetic error, missing required section, or command not matching the cited catalog is a defect.
- Refunds and reversals are separate state events against the original transaction ID; they reduce promotion-eligible revenue and never overwrite earlier ledger entries.
