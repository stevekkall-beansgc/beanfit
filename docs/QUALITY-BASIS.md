# Quality basis: static Mac CLI catalog

Metadata snapshot date: **2026-10-02**. The inventory below records the catalog
at source revision `42de7df153c5bdfda8199f924ec35ce8cbae9cbd`, with package
identity `0.5.2`. This is the date these explanatory metadata were frozen, not
the date the ratings were assigned or models were tested. Original assignment
dates, authors/reviewers, task sets, results, and assignment procedure are
**unknown**: no such provenance is recorded alongside these values. This
document does not reconstruct a historical rubric from the numbers.

The file's Git history supplies a narrower provenance trail: source commit
`f1851979a03f70c1bbc036be5314f504e09f29c5` (2026-08-23) already contains the
current rows' rating triples under the model identities used at that time.
Catalog correction `1388752f290c4261409b33ecd4faa65f558a6836` (2026-09-08)
changes several names, tags and memory inputs while preserving all 24 retained
rating integers. It also removes a ninth row. These are recorded source-change
dates, not evidence of the date or process of assigning a model judgment.
In particular, inheriting a triple after a model identity correction is not
empirical validation for the corrected model. This snapshot inventories only
the eight current rows; historical report samples are not rewritten.

## Existing labels and audience

Every value in this inventory is a **legacy illustrative editorial rating**.
None is a measured quality label. The intended use is a starting shortlist for
Apple Silicon users who will evaluate local models on their own tasks. The
comparison is relative preference inside this eight-row catalog; it does not
establish performance against other models, a task success rate, or general
accuracy. A `9/10` does not mean 90% correct, and a one-point difference has no
established empirical meaning. Rating uncertainty is unknown: there is no
calibration, error distribution, confidence interval, or evidence supporting
precise differences. No new reviewer judgments are assigned here.

| Catalog runtime tag | Coding (`qual_coding`) | Reasoning (`qual_reasoning`) | Chat (`qual_chat`) |
| --- | ---: | ---: | ---: |
| `qwen3:8b` | 7 | 7 | 8 |
| `phi4-reasoning:14b` | 7 | 8 | 7 |
| `gpt-oss:20b` | 9 | 8 | 8 |
| `gemma3:27b` | 9 | 8 | 9 |
| `qwen3:30b-a3b` | 9 | 9 | 9 |
| `llama4:scout` | 8 | 7 | 8 |
| `deepseek-coder-v2:16b` | 9 | 6 | 5 |
| `mistral-small3.1:24b` | 8 | 7 | 8 |

`coding`, `reasoning`, and `chat` are the CLI's three use-case selectors. Their
names suggest code tasks, reasoning tasks, and conversation respectively, but
the historical tasks and judging criteria behind each rating are unknown.
These names do not guarantee language coverage, factuality, tool use, safety,
or instruction following. Each row's three integers share the editorial basis
above, including repeated values across models. They are not quant-specific or
runtime-specific observations; the selector reuses them for q4 and q8.

`--json` and `--export-catalog` expose the complete inventory and provenance
limits in additive `quality_basis` metadata. Existing `quality`, catalog
fields, catalog SHA-256 semantics, and artifact schema remain unchanged. The
selected JSON field identifies exactly which catalog column supplied each
ranked row. The text renderer also discloses the unknown historical basis.

## Deterministic application of the existing values

The implementation is [`evaluate.py`](../src/beanfit/engine/evaluate.py).
`--use-case chat` selects `qual_chat`, `coding` selects `qual_coding`, and
`reasoning` selects `qual_reasoning`. No judging or model inference happens.
For each row the selector tries q4 first, then q8, and uses the first whose
weight plus half of its 32k KV allowance fits the device budget. It uses the
unchanged static speed estimate and scores:

```text
score = round(12 * selected_editorial_rating
              + 0.15 * min(estimated_tok_s, 60)
              + (10 if fits else -40), 1)
```

For a row that does not fit, speed is zero. Rows sort by descending score;
equal scores retain their catalog order. The text `Pick` is the first fitting
row in that order, if any. A no-fit row still has a numeric score, so ordering
alone is not proof that a row fits. An editorial point contributes 12 score
units; the capped speed term contributes at most 9. The score is a ranking
heuristic, not an accuracy percentage, probability, or measured quality result.

Examples from the existing synthetic M5 Max / 128 GiB profile (600 GB/s assumed
bandwidth and 96 GiB model budget):

- Chat: Gemma 3's editorial input is 9 and its estimated speed is 28.5 tok/s.
  `round(9 * 12 + 28.5 * 0.15 + 10, 1)` is **122.3**. Qwen3 30B-A3B also
  has chat input 9 but 25.6 estimated tok/s, giving **121.8**. The difference
  follows the speed tie-breaker, not a measured chat comparison.
- Coding: DeepSeek Coder V2, Gemma 3, gpt-oss, and Qwen3 30B-A3B all have
  input 9. DeepSeek's 47.9 estimated tok/s gives **125.2**, making it the
  existing coding pick for this fixture. This is not a coding benchmark.
- Reasoning: Qwen3 30B-A3B's input 9 and 25.6 estimated tok/s give **121.8**.
  This reflects the catalog preference and static estimate, not proof of
  superior reasoning. A no-fit row with input 9 instead scores **68.0**
  (`9 * 12 - 40`); its quality input is not reduced by the fit failure.

These examples explain existing behavior. No catalog integer, model pin,
formula, quant policy, or golden ranking was changed to create them.

## Empirical evidence is a separate basis

The Mac catalog has no attached empirical quality evidence. Registry liveness
or the existence of a pinned model repository does not supply it. Speed
measurements alone cannot establish answer quality. Product-specific mobile
or iPhone receipts elsewhere in this repository cover their own workloads,
models and runtime configurations; they do not validate these Mac ratings.
No inference, download, new measurement, or external benchmark was used for
this metadata snapshot.

A future empirical label must name its exact task set, model artifact revision,
quantization, runtime/version, prompt/template, configuration, observation date,
raw outcomes, scoring code or reviewed judgments, and applicability limits.
Valid external evidence would need the same relevant identities and explicit
mismatches. Missing prerequisites leave the empirical result unknown; they
must not be replaced with the editorial integers.

## Proposed future rubric

This proposal **has not been applied** to any catalog model, has not been
calibrated, and is pending **owner approval**. It is a reproducible evaluation
protocol for future work, not a historical explanation or an approved release
gate. It produces separate workload-specific results; it does not reinterpret
the legacy 0-10 values.

1. Freeze a public or synthetic task manifest before model runs. Use 20 tasks
   per use case and record intended user, input, allowed tools, expected output,
   pass criteria, timeout and failure treatment. Hash the manifest and scoring
   code. An incomplete manifest blocks comparison. Select tasks for a named
   audience; this task count is a proposed practical starting point, not a
   statistically established sample size.
2. Coding tasks use deterministic executable assertions covering the requested
   behavior, including specified edge cases. Reasoning tasks use verifiable
   reference answers and a fixed checker for accepted outputs. For chat, use
   bounded synthetic scenarios with explicit required facts, prohibited claims,
   and instructions. Score deterministic constraints mechanically; any remaining
   subjective criterion requires two independent blinded reviewers with written
   reasons. Retain both judgments and a recorded adjudication; unresolved
   disagreement leaves that task unknown, not silently passed.
3. Freeze artifact identity, quantization, runtime, hardware, generation settings,
   prompt/template, context limit, and seed policy. Run each task three times
   under that frozen configuration. Retain raw outputs and failures for all
   60 attempts per use case. Mark runtime failures and timeouts failed according
   to the predeclared policy. A missing output or unresolved judgment makes the
   aggregate incomplete; do not drop it from the denominator.
4. Report `passed / 60` with every outcome and the configuration. If complete,
   a separate empirical workload index may be `10 * passed / 60`, with no
   integer rounding or categorical adjectives. For example, **45/60 gives 7.5**
   for that frozen workload only; **60/60 gives 10**, without proving general
   accuracy. These are arithmetic examples, not observed model results.
5. Repeat on a separately frozen holdout task set and report both results,
   repetitions, reviewer agreement and differences without merging away a
   failure. Reproducible arithmetic does not establish representative task
   coverage or calibration. Obtain owner approval for the protocol and any
   decision thresholds before adopting or publishing new model judgments.

Until that work exists, the catalog remains editorial with unknown historical
assignment basis and unquantified uncertainty. Independent review and owner
acceptance of this explanatory candidate are separate from empirical validation.
