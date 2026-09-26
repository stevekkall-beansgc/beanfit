# BeanFit mobile: smallest qualified model

Updated 2026-09-26 after scope clarification. This is a BeanFit capability for
product teams, not a Nina app or a BeanMind/tool-connection implementation.
This document supersedes the earlier Apple-first recommendation **for the
identified test phone** and the voice-led ordering in BENCHMARK-PLAN.md.

## Intended outcome

Given a product's evaluation contract and comparable observations from an
actual iPhone, return the lowest measured memory candidate that satisfies the
contract. If none qualifies, return no selection and explain the unmet gates.
“Smallest” means **peak incremental memory of the deployed stack**, including
loading, prefill, generation and any product-required speech/retrieval runtime.
Parameter count and download size only help order experiments; they do not win
selection. Quality is a minimum gate, not a score to maximize at any memory cost.

A deterministic algorithm or small task-specific model should be evaluated
before an LLM when it can meet the feature requirements. Products can choose
different models. No general-purpose assistant model is imposed on the fleet.

## Identified device

The previous physical test phone was **iPhone 14 Pro Max (iPhone15,3)** on
**iOS 26.6.1, build 23G83**. The 2026-09-04 native-iMessage session record
identifies that model/OS, and Xcode's known-device inventory read on 2026-09-26
agrees. The device was disconnected; the recorded OS is not a fresh live probe.
The iPhone 17/17 Pro simulator names must not be used as its hardware identity.

Private local evidence:
- `/Users/stephenkall/beans/products/jumping-beans/experiments/native-imessage-entry/SESSION_MEMORY_2026-09-04.md`
- `/Users/stephenkall/beans/outputs/beanfit-iphone-20260926/device-inventory.json`

This phone is outside Apple's Apple Intelligence eligibility list. The original
FoundationModels text probe remains a research artifact for eligible phones;
it is not this device's runtime path. Use downloadable native models here.
[Apple requirements](https://support.apple.com/en-us/121115).

## Selection contract implemented in this prototype

| Requirement | Acceptance |
|---|---|
| Product-specific quality | Explicit dataset hash, case IDs, quality floor and must-pass cases; no built-in subjective model-quality scores |
| Comparable trials | Same phone, OS build, stack ID, context/output limits, evaluation dataset and memory accounting method |
| Coverage | Equal repeats across every required case; at least the product's minimum repeats |
| Reliability | Every included trial must complete; timeouts/failures remain in the denominator and disqualify the candidate |
| Critical correctness | Every critical-case repeat must pass, even if the average meets the floor |
| Memory | Maximum observed complete-stack incremental peak plus an explicit reserve must fit the product's budget |
| Latency | Nearest-rank p95 of measured trial latency must meet a product-supplied limit |
| Objective | Among qualified physical observations, minimum peak bytes; latency breaks ties; ID provides deterministic final ordering |
| Honest evidence | Synthetic/simulator observations never produce a real selection; weights-only/app-RSS-only accounting is rejected |
| Isolation | No cloud fallback, networking, model downloads, phone installs or paid inference in the selector |

Implemented as `beanfit mobile --profile ... --receipts ...` in `src/beanfit/mobile.py`.
The existing Mac CLI and its golden rankings are unchanged. Public Python
`select(profile, receipts)` is the shared selection function. Invalid profiles
exit nonzero; individual invalid receipts are retained as rejected rows. A valid
run with no qualified candidate returns `needs_device_evidence` and null selection.

Receipts are **self-reported**, not attested. An operator must inspect the linked
raw logs, quality judgments and memory collection method. This function cannot
detect fabricated claims or prove model compatibility. A selection is only the
smallest qualifying option **among the supplied tested candidates**, not proof
of the global smallest possible model. An OS/runtime/model/quant/context/stack
change requires a new evaluation.

## Candidate ladder for the physical benchmark

Start with narrow product features such as bounded extraction/classification.
Use deterministic processing as the zero-model baseline. Then investigate
SmolLM2 135M and 360M Instruct, Qwen3 0.6B, and only then a roughly 1–1.7B model.
These are trial candidates, not qualified recommendations or new BeanFit catalog
entries. Smaller models may fail the quality gate; a larger passing model wins
in that case. Do not assume a model marketed for mobile meets our product needs.
[135M source](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct),
[360M source](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct),
[Qwen3 0.6B source](https://huggingface.co/Qwen/Qwen3-0.6B).

Use one native runtime first (llama.cpp's iOS route is a candidate; MLX Swift is
an alternative). Before any real run, verify the model architecture against the
chosen runtime, pin runtime commit, model/quant artifact revision and hashes,
review licensing, and measure file sizes. No quantized artifact URL is guessed
here. Test quantization as part of candidate identity; lower precision can save
memory while harming correctness. Keep context and output caps small and matched.
Load one candidate at a time and release it before the next.

Do not stop solely on parameter ordering: different runtimes/architectures can
reverse the actual memory order. Once the first model passes, compare any smaller
plausible alternatives and quantizations before declaring the measured winner.
Avoid testing larger models without a specific unmet requirement.

## Product contract still required for real qualification

The repository includes a **synthetic** example contract, not user-approved
thresholds for every product. Each real product must provide representative
inputs, expected output/scoring rubric, critical failure cases, latency limit,
context requirements and an acceptable incremental memory budget. Do not derive
a process memory cap from nominal phone RAM. Physical observations must include
peak load/prefill/decode and any concurrent feature components. If system-managed
allocations cannot be accounted for comparably, leave selection unknown.

Freshness, thermal endurance and battery remain additional product acceptance
checks; the current selector does not certify them. Source artifacts and raw
measurement logs must be reviewed before integration or deployment.

## Delivered boundary and next gate

Delivered: offline qualification/ranking module, CLI, synthetic contract and
receipts, unit tests, owned CLI E2E, updated requirements, and identified target.
Not delivered: iPhone runtime adapter/downloader, physical benchmarking, product
quality datasets, automatic installation, or production product integrations.
Those remain the next bounded stage; no claim of a model running on this phone
has been made. The phone is disconnected and prior instructions prohibit phone
installation without a separate authorization.

The mistakenly started NinaPhone app draft is preserved outside this branch at
`/Users/stephenkall/beans/outputs/beanfit-iphone-20260926/set-aside/NinaPhone`.
No app was built, installed, or connected to services.

## Validation receipt

The isolated BeanFit candidate passes 209 unit tests, including 17 new mobile
policy/CLI tests, the combined activation/mobile offline E2E, docs checks and
pinned Ruff 0.16.8. Tests cover smaller-but-unqualified rejection, minimum-memory
selection, critical failures, peak-versus-average memory, reserve, latency,
failed trials, incomplete/uneven coverage, duplicate receipts, profile mismatch,
nonfinite metrics and rejection of synthetic/simulator qualification.

Paired QA registration is isolated in
`/Users/stephenkall/beans/worktrees/beanfit-mobile-qa-20260926`. The production
registry is unchanged; the two candidates must land together if later approved.
Validation reports are under
`/Users/stephenkall/beans/outputs/beanfit-iphone-20260926/qa-mobile/` and
`qa-kit-mobile/`. Same-author review only; independent review and explicit
integration approval remain before merge. No paid service, Groq call, device
installation, model download or physical inference ran.
