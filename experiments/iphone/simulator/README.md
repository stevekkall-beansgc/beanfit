# Actual iOS Simulator model tests — 2026-09-26

**Four downloadable models ran successfully in an iOS Simulator process. None
passed the complete fixed quality screen.** This is real model execution using
fictional inputs, not synthetic inference or a Mac-hosted model-server call.

| Candidate | Verified file size (decimal MB, not RAM) | Strict trials passed | Critical failures | Full screen |
|---|---:|---:|---|---|
| SmolLM2 135M Instruct Q4_K_M | 105.45 | 4/24 | Missing facts, instruction handling, bounded action output | Fail |
| SmolLM2 360M Instruct Q4_K_M | 270.59 | 6/24 | Missing-fact output contract, negation, instruction handling | Fail |
| Qwen3 0.6B Q4_K_M, non-thinking | 396.71 | 18/24 | Instruction handling | Fail |
| Qwen3 1.7B Q4_K_M, non-thinking | 1,107.41 | 20/24 | Instruction handling | Fail |

## Decision

Do not name a qualified general-purpose model yet. Qwen 0.6B is the smallest
promising **lead for narrow extraction** in this comparison: it answered the
color, owner, date, missing-fact and active-project questions correctly in both
runs. It failed the feature label, returned fenced rather than raw JSON, and
followed an injected instruction in the reference data. The 1.7B control fixed
raw JSON output but still failed classification and the injection case. Paying
more memory for that increase did not satisfy the complete contract.

SmolLM2 135M invented a budget (100000) when the source gave none. SmolLM2 360M
frequently conveyed the correct fact but failed the exact output contract; its
score must not be read as only 25% factual accuracy. The tests assess strict
product integration behavior, not general conversational ability.

Next, define one real product feature and its representative dataset, with
structured output validation and trusted application logic controlling tools.
Consider a deterministic/classifier baseline before an LLM. Do not rely on any
LLM alone to enforce authorization or resist untrusted instructions. A revised
prompt or constrained-generation runtime is a **new candidate configuration**
and must rerun all cases; the original results and thresholds remain intact.
This is preferable to repeatedly growing the model without a measured benefit.

## What actually ran

- A newly created, isolated simulator named `BeanFit-Model-Test`, device type
  iPhone 14 Pro Max, running **iOS 27.0**. This is not the physical phone's
  last-recorded iOS 26.6.1, and does not emulate its A16 or memory limit.
- Xcode 27.0 (27A266a), iOS Simulator 27 SDK, arm64 target with deployment
  minimum iOS 26.0. `vtool` verified `IOSSIMULATOR`, not `MACOS`.
- Pinned llama.cpp commit in [artifacts.json](artifacts.json), built as static
  libraries with its `llama-simple` executable; launched via `simctl spawn` in
  the booted simulator. This is a command-line runtime test, not a signed app,
  UIKit lifecycle test or distribution test.
- CPU-only: Metal, Accelerate, BLAS and OpenMP disabled. No hosted inference
  backend, API key, Groq or paid service. The runtime read local GGUF files.
  Network isolation was not independently instrumented, so no audited zero-
  egress claim is made.
- Two greedy repeats per case, 12 fixed fictional cases, 96 output tokens.
  Context followed upstream `llama-simple`: prompt length plus output cap minus
  one. This is a short-context screen, not the future fixed-2K memory benchmark.
- SmolLM's ChatML layout was checked against the upstream tokenizer config;
  Qwen used the non-thinking assistant prefix. The executable echoes prompts;
  the runner removes the exact echoed prefix before scoring generated text.
- Every model's byte count and SHA-256 matched the pinned publisher metadata
  before loading. Apache-2.0 was declared by each artifact repository. No model
  was installed on the physical phone or added to BeanFit's production catalog.

## Test contract and evidence

[workload.json](workload.json) was written before the candidate comparisons.
The gate was at least 90% success and every critical case passing. Exact text
comparison ignores surrounding whitespace, letter case and trailing periods;
JSON must parse directly with the exact required object and no duplicate keys.
Code fences are not silently stripped. Two identical greedy runs check basic
repeatability; they do not establish statistical reliability or diverse quality.

[results.json](results.json) contains the individual outputs and verdicts,
artifact hashes, raw-result hashes and evidence paths. Raw stdout/stderr and full
receipts are retained under:

`/Users/stephenkall/beans/outputs/beanfit-simulator-20260926/`

No phone RAM, battery, thermal result or qualified device selection is emitted.
Model file size and llama.cpp allocation logs are not whole-stack peak memory.
The simulator report uses its own `beanfit.simulator.quality.v1` schema and
cannot be promoted into a physical-device BeanFit winner.

## Reproduce

The source revision, runtime/build versions, model revisions, file names, byte
counts and SHA-256 pins are in [artifacts.json](artifacts.json). Dependencies and
model files live only in the local output folder, not Git. Build from the pinned
source using:

```sh
sh experiments/iphone/simulator/build.sh /path/to/pinned/llama.cpp /path/to/cmake /path/to/build
```

Create/boot a separate simulator using Xcode, then run from the BeanFit worktree:

```sh
python3 scripts/simulator_eval.py \
  --binary /path/to/build/bin/llama-simple \
  --model /path/to/pinned/model.gguf \
  --sha256 THE_VERIFIED_MODEL_SHA256 \
  --simulator THE_BOOTED_SIMULATOR_ID \
  --workload experiments/iphone/simulator/workload.json \
  --template qwen3-no-thinking \
  --output /path/to/new-result-directory
```

Use `--template chatml` for SmolLM2. Output directories must be new. The runner
checks the model digest, binary platform and booted simulator identity. It does
not download dependencies, models, or connect to inference services. A trial
has a 30-second launcher timeout and a bounded model token limit. On timeout,
inspect the simulator for a lingering child process before rerunning; killing
`simctl` is not a guaranteed cancellation of its spawned process. No timeouts
occurred in this session.

## Phone-stage handoff

Use the disconnected physical iPhone 14 Pro Max once available. First confirm
its live OS/build and obtain a signed native harness with local artifact import;
this simulator executable is not itself an installable app. Start with Qwen
0.6B for a narrowed product contract, or compare it to 1.7B as a control—neither
is prequalified for the full screen above. Preserve the same model hash and
prompt/quant configuration across simulator and device tests.

Measure launch/load/prefill/decode peaks, fixed context, repeat turns, interruption,
thermal endurance and battery on the phone. Record all co-resident product
components and reserve. CPU simulator throughput must not enter the phone's
speed estimates. A Metal-enabled build is a distinct runtime configuration and
needs validation on hardware. Actual phone installation remains for the next
stage; nothing was installed on the phone during this session.

## Validation

BeanFit docs, all 214 unit tests, both existing offline E2Es, and pinned Ruff
0.16.8 pass. Five new evaluator tests cover strict grading, duplicate JSON keys,
critical failures, missing case coverage and the simulator/physical boundary.
The 96 actual simulator trials all completed without process failure or timeout.
Their quality failures are retained; test-runner success is not model acceptance.
Same-author review only. Changes remain isolated and unmerged.
