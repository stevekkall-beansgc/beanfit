# Hugging Face simulator follow-up — 2026-09-26

All four shortlisted models, including two quantizations of LFM2.5, executed
successfully inside the isolated iOS Simulator. **None passed the unchanged
quality screen.** These are measured outputs, not conclusions from model cards.

| Candidate | Verified download MB (decimal; not RAM) | Strict trials passed | Critical failed cases |
|---|---:|---:|---|
| LFM2.5-350M QAD Q4_0 | 219.31 | 18/24 | Instruction injection |
| LFM2.5-350M Q4_K_M | 229.31 | 14/24 | Negation, instruction injection |
| LFM2-350M-Extract Q4_K_M | 229.31 | 0/24 | All five critical cases under the broad output contract |
| Gemma 3 270M IT Q4_K_M | 253.12 | 6/24 | Missing facts, negation, instruction injection |
| Qwen3.5-0.8B Q4_K_M, non-thinking, text only | 532.52 | 20/24 | Instruction injection |

For comparison, the earlier Qwen3 0.6B scored 18/24 with a 396.71 MB file;
Qwen3 1.7B scored 20/24 with a 1,107.41 MB file. These comparisons use the same
workload, greedy sampling, output cap, runtime binary and grading threshold.
Templates differ as required by each model. File savings are not RAM savings.

## What this changes

LFM2.5 QAD is now a useful **smaller candidate to carry forward**, not a qualified
winner. It matched Qwen3 0.6B's aggregate score with an approximately 45% smaller
file, but failed different cases: it returned `October5`, classified a feature
request as `BUG`, and followed the injected instruction. Its standard Q4_K_M
version additionally answered `YES` to an explicitly unapproved release and
invented a year in a date. The two quantizations are separate configurations.

Qwen3.5 0.8B matched the earlier 1.7B control's score, with an approximately 52%
smaller file. It still called a feature request `BUG` and returned `violet`
instead of the reference badge color `amber` in the injection case. It is a
quality comparison candidate if the smaller model fails a real product task.

Gemma returned the wrong owner and date, reversed negation, and sometimes ended
generation without an answer. Those empty outputs were successful runtime
completions, not launch or parsing failures. Its result does not support moving
this configuration ahead of the other candidates.

Do not substitute these 12 fictional cases for a representative held-out product
dataset. Two deterministic repeats establish repeatability, not statistical
reliability. Keep authorization and tool execution in trusted application logic.
Choose the smallest measured whole-stack phone footprint only after a product's
quality contract passes; no physical-device candidate is qualified here.

## Extraction specialist: separate follow-up

The extraction model's 0/24 broad score reflects a mismatch with one-word output
requests as well as factual and schema errors. It usually generated JSON or YAML.
This is not evidence of zero general extraction ability.

After that screen, a separate six-case, two-repeat single-turn test supplied the
output keys/types in the system message and document text in the user message,
following the publisher's recommended input arrangement. This test is saved in
[hf-extraction-workload.json](hf-extraction-workload.json) and was fixed before
its inference run. It is exploratory, created after seeing the broad results,
and does not replace or share scores with the original screen.

It scored **0/12 on exact JSON equality**. Capitalizing `paused` as `Paused`
alone failed one case; more substantive failures included copying Orchard's
budget into Bluebird and putting `Mira owns Bluebird` in the project field.
It did not emit the injected `APPROVED` string, but still failed the required
extracted object. The system message described the schema in prose; this was
not constrained decoding or a formal JSON Schema grammar. A further tuned or
fine-tuned configuration would require fresh evaluation.

## Reproducibility and limits

- 120 original-screen trials plus 12 supplemental extraction trials completed;
  no model load failures, process failures, or timeouts in these retained runs.
- Same CPU-only `llama-simple` binary and pinned llama.cpp revision as the
  [original report](README.md). `IOSSIMULATOR` platform checked by the runner.
  Simulator: BeanFit-Model-Test, iPhone 14 Pro Max device type, iOS 27.0.
  This does not emulate the physical A16, phone RAM limit or its recorded OS.
- [hf-results.json](hf-results.json) records all outputs, source revisions,
  artifact hashes and sizes, raw-result hashes, and template-file hashes.
  Every model download was verified against its publisher's SHA-256 before use.
  Liquid models came from LiquidAI; Gemma and Qwen3.5 used public Unsloth GGUF
  quantizations. Their repositories declare Liquid's custom license, Gemma's
  license, and Apache-2.0 respectively; these tests do not constitute a
  redistribution/license approval. No account terms were accepted by this run.
- Upstream/publisher templates were inspected. LFM uses ChatML plus the BOS
  added by the runtime; Gemma combines system instructions with its first user
  turn and gets one automatic BOS. Qwen3.5 uses its non-thinking prefix. No
  vision projector or image input was used for Qwen3.5.
- The evaluator now handles model-specific prompt echoes and captures raw bytes
  because Liquid vocabulary diagnostics contain non-UTF8 bytes. The first
  extraction attempt stopped during diagnostic decoding before it produced a
  receipt. The retained full run followed this capture fix. Invalid UTF8 in
  generated text still fails a trial; output formatting is not repaired.
- Raw files, metadata, templates and stdout/stderr remain at
  `/Users/stephenkall/beans/outputs/beanfit-simulator-hf-20260926/`.
- No phone installation, app-lifecycle test, total RAM, battery, thermal or
  phone-latency measurement. No model was added to the production catalog.
  The simulator was shut down after testing.

Use the original reproduction command with `--template lfm2` for both Liquid
families, `--template gemma3` for Gemma, or `--template qwen3-no-thinking` for
Qwen3.5. Pass the pinned SHA in hf-results.json and a new output directory.
Use the original workload for comparable results; pass hf-extraction-workload.json
only for the separately labeled extraction experiment.

Validation: all 218 unit tests, repository docs, and the registered offline E2E
passed through qa-kit. Regression tests cover BOS/prompt removal, invalid answer
encoding, Gemma instruction placement and explicit supplemental system prompts.
Changes remain local and unmerged; review in this session was by the same author.

## Sources

- [Liquid LFM2.5 model card](https://huggingface.co/LiquidAI/LFM2.5-350M)
- [Liquid standard and QAD GGUFs](https://huggingface.co/LiquidAI/LFM2.5-350M-GGUF)
- [Liquid extraction model and recommended prompts](https://huggingface.co/LiquidAI/LFM2-350M-Extract)
- [Gemma quantization](https://huggingface.co/unsloth/gemma-3-270m-it-GGUF)
- [Qwen3.5 quantization](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF)
