# Requirements review — 2026-09-26

Recommendation: keep the smallest-qualified-stack objective, but qualify one
product feature at a time. The existing fictional simulator screen is a useful
diagnostic, not a universal product acceptance test. Its 90% floor and 12 cases
were experimental choices, not user-approved production requirements.

This is a proposal for the next evaluation. It changes no existing scores,
critical cases, selector logic or qualification status.

## What to change

| Area | Proposed product contract |
|---|---|
| Scope | Name one feature, input sources, supported language, output schema and allowed actions. Separate extraction, classification, action selection and conversation. |
| Evaluation unit | Model + quantization + prompt/template + decoding constraints + deterministic validator/normalizer + runtime. Pin the entire configuration. |
| Formatting | Permit only predeclared, unambiguous normalization that the shipped app actually performs. Report raw schema validity separately from final task correctness. |
| Correctness | Wrong entity, invented values, reversed negation, incorrect action and instruction-contaminated answers remain failures. Valid JSON alone does not establish truth. |
| Abstention | Permit an explicit unsupported/unknown result where the product permits it. Measure accuracy of accepted answers AND coverage, so rejecting everything cannot qualify. |
| Tool permissions | The model proposes a bounded action; trusted application code validates arguments, checks permissions and controls execution. Test rejection end to end. |
| Instruction injection | Retain adversarial data cases. Distinguish corrupted answers from unauthorized actions. Blocking execution does not make a wrong answer correct. |
| Evidence | Create varied held-out cases before further tuning; include missing facts, conflicting entities, paraphrases, negation, malformed input, and unsupported requests. Two identical greedy repeats are not 24 independent quality examples. |
| Acceptance | Set thresholds by product consequence before the held-out run. Keep critical errors explicit; do not lower the existing floor after seeing scores to declare a winner. |
| Memory | Measure peak deployed-stack memory on the phone, including validators and required retrieval/speech components. Keep context bounded and count loaded models together when concurrent. |

## What the current failures tell us

LFM2.5 QAD returned `October5`, a likely formatting issue a declared date parser
could handle. Its `BUG` classification and injected `violet` answer are substantive
errors. Standard LFM2.5 invented a year and reversed negation: normalization must
not conceal either. The extraction specialist's capitalized status is potentially
normalizable; assigning another project's budget is not.

Every newly tested configuration chose BUG for the sole FEATURE example. Before
attributing this to general inability, audit the task prompt and harness with
balanced examples, label-order swaps, few-shot variants and a trusted reference
runtime for a small control subset. The system instruction to use only supplied
facts may be poorly matched to an undefined classification task. This is a
hypothesis, not an identified runtime bug. Preserve the original baseline.

For constrained output, use a schema or grammar only if the actual app/runtime
supports it, then test that configuration afresh. A grammar can constrain syntax
and allowed labels; it cannot ensure the selected fact or label is correct.

## Bounded next candidate search

1. **IBM Granite 4.0 350M**: another instruction-tuned family at the same small
   scale, with publisher-owned GGUFs and Apache-2.0 metadata. The Q4_K_M listing
   is about 237 MB (download, not RAM). Best next general small-model comparison.
   [Model card](https://huggingface.co/ibm-granite/granite-4.0-350m),
   [GGUFs](https://huggingface.co/ibm-granite/granite-4.0-350m-GGUF).
2. **FunctionGemma 270M**: relevant if the selected feature maps user requests
   to a small set of app actions. Google explicitly positions it for task-specific
   fine-tuning, not direct dialogue; it has a different chat format from Gemma.
   Its published Android results do not establish iPhone compatibility or RAM.
   [Model card](https://huggingface.co/google/functiongemma-270m-it).
3. **LFM2.5 1.2B Instruct**: a larger quality control for extraction or RAG if
   the smaller candidates fail the selected feature. Official GGUFs exist;
   publisher memory claims are not our phone measurements.
   [Model card](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct),
   [GGUFs](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF).

These are researched candidates, not newly downloaded, tested, or qualified
models. Verify artifact revision/hash, template and runtime support before use.
Also retain LFM2.5 350M QAD and Qwen3.5 0.8B as measured baselines. Compare a
deterministic implementation or compact classifier if the feature permits it.

## Selected first capability

The user delegated the choice on 2026-09-26. Start with **structured fact
extraction into editable draft fields**: short English input, one named target
entity, a small declared schema, and explicit nulls for missing facts. Outputs
are drafts for review, not authority to execute an action. The existing fictional
project/status/owner/budget schema can remain a development fixture; it is not
evidence of an approved real product feature or representative input distribution.

Keep three questions separate: did it produce valid fields, are the values
supported by the correct source entity, and how often does it return a usable
draft rather than abstain? Errors such as invented values and cross-entity budget
leakage remain critical. Define permitted normalization before evaluation.

Next build varied development/held-out datasets for this bounded contract, then
compare LFM2.5 350M QAD, Qwen3.5 0.8B and Granite 350M with the same validator.
Include a deterministic baseline. FunctionGemma is deferred until an action
selection feature is needed. Add LFM2.5 1.2B only for a documented unmet quality
requirement. Promote passing configurations to phone memory/latency tests;
simulator quality results do not confer physical qualification. General
conversation remains a separate requirement and may need a larger model.
