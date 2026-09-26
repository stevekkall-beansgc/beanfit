# Focused extraction pass — 2026-09-26

This is a new, frozen synthetic experiment for extracting editable draft fields.
It does not revise scores from the earlier mixed-task screens. No model in this
experiment is physically qualified for an iPhone.

## Results

| Configuration | Exact correct, including required abstention | Correct among schema-accepted drafts | Answerable coverage | Contract |
|---|---:|---:|---:|---|
| LFM2.5-1.2B-Instruct-Q4_K_M.gguf | 30/48 | 30/48 | 100% | Fail |
| LFM2.5-350M-QAD-Q4_0.gguf | 6/48 | 4/8 | 20% | Fail |
| Qwen3.5-0.8B-Q4_K_M.gguf | 40/48 | 34/38 | 90% | Fail |
| granite-4.0-350m-Q4_K_M.gguf | 12/48 | 12/36 | 70% | Fail |
| deterministic-key-value-baseline | 10/48 | 2/2 | 5% | Fail |

All 192 inference trials completed with no process failures or timeouts. The
normalizer did not rescue any incorrect draft in this pass. Qwen3.5 0.8B was
strongest; its two factual failure types were the injected budget and copying
facts despite an absent target. It also abstained on two answerable cases,
which reduces coverage but is not an accepted wrong answer. The raw exact score
counts those abstentions as mismatches; the revised contract treats them separately.

Granite invented missing values and mixed entities. LFM2.5 QAD frequently
abstained or emitted invalid field types. The planned LFM2.5 1.2B control was
added only after the smaller models failed; it used the unchanged prompt and
cases and still mixed entities, missed corrections and invented defaults.
Its verified file is 730.90 MB; increasing size did not improve on Qwen here.
The deterministic baseline's accepted draft was correct, but it covered only
one of twenty answerable cases, so it also fails.

**Decision:** no configuration meets this experimental extraction contract.
Qwen3.5 0.8B is the best measured lead for further work on this feature, replacing
the smaller Liquid model as the lead under this specific schema. The evidence
supports improving source grounding, target checks and feature-specific training
before another broad model search. Those would be new configurations evaluated
on fresh cases; do not retrofit a whitelist around these known failures.
Do not proceed to production qualification or claim phone memory savings.

## Contract

Input: one named target project and a short English document. Output: exactly
`project`, `status`, `owner`, `budget`, or the explicit object `{"abstain":true}`.
Missing fields use JSON null. Status is active/paused/cancelled/null. Budget is a
nonnegative number/null. The user-facing use case is editable drafts, not tool
execution. No production UI or iPhone app was added.

Twenty-four fresh cases were fixed before inference; each ran twice with greedy
sampling. Twenty cases are answerable, four require abstention. Cases include
paraphrases, absent fields, zero/decimal budgets, distractors, entity separation,
negation, changes/corrections, document authorship, two injected instructions,
missing targets, empty input, conflicts and unreadable text. These are authored
synthetic examples, not independent production data or a statistically validated
held-out benchmark. No prompt was tuned using this pass's outputs.

The experimental acceptance gate, fixed before reviewing outputs, requires:
100% factual accuracy of schema-accepted drafts, at least 80% coverage of
answerable inputs, explicit abstention for every unsupported input, complete
runs, and no accepted incorrect critical-case answers. Coverage prevents an
always-abstaining model from passing. These are pilot gates, not a claim that a
small passing sample establishes 100% real-world reliability.

The offline validator accepts outer whitespace, a single enclosing code/JSON
fence, string-edge trimming and status capitalization normalization. It rejects
malformed JSON, duplicate/extra/missing keys, numeric strings, booleans as budgets,
nonfinite/negative budgets and invalid enums. It never rewrites factual values.
No constrained decoder, retries, fine-tuning or source-aware factual verifier was
used. Schema acceptance is not factual verification; expected facts are used
only by the evaluator. The validator is a Python prototype, not yet ported to a
native iPhone application.

## Evidence and reproduction

`workload.json` includes the frozen prompt, expected objects and acceptance
policy. `evaluation.json` contains validator-level results, including raw schema
validity, exact correctness, accepted-answer accuracy and coverage. `receipts.json`
retains inference outputs, model pins, hashes and raw evidence locations.
The inference runner's legacy summary is strict raw-output scoring; use
`evaluation.json` for this pass's normalization/abstention-aware contract.

Reproduce using the original simulator runner with `--template granite4`, `lfm2`
or `qwen3-no-thinking`, the matching artifact SHA, this workload and a new output
directory. Then run:

```sh
python3 scripts/extraction_eval.py \
  --workload experiments/iphone/simulator/extraction-v2/workload.json \
  --results /path/to/candidate/result.json \
  --output /path/to/evaluation.json
```

The deterministic comparison only accepts complete anchored key/value records
and abstains on prose. It is a deliberately conservative baseline, not proof of
the best possible deterministic extractor. It reads no expected answers.

All model inference used the existing CPU-only iOS Simulator binary, llama.cpp
revision `2145525a4081d66ff1a87cf43ef809f95a85ac0c`, inside BeanFit-Model-Test,
iOS 27.0. The model-specific chat templates were inspected; Granite has no added
BOS, Liquid gets an automatic BOS, and Qwen3.5 uses its non-thinking prefix.
Artifact downloads were SHA-256 verified. Context remains prompt length plus
128 output tokens minus one; this pass does not measure a fixed-context phone
memory budget. No phone installation, RAM, battery, thermal or device-speed
claim is made. Source metadata, templates and raw logs are retained at
`/Users/stephenkall/beans/outputs/beanfit-extraction-v2-20260926/`.

## Validation

All 222 unit tests, repository docs and registered offline E2Es passed through
qa-kit; Ruff and whitespace checks passed. New tests cover normalization,
invalid/duplicate values, abstention coverage, accepted factual errors, baseline
limits, and Granite's native role template. Changes remain local and unmerged;
review was by the same author. The simulator was shut down after testing.
