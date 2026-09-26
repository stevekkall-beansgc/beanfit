# iPhone product enablement — checkpoint and next phase

Status: paused after the native prototype checkpoint, 2026-09-26.
Resume only on a new user instruction. This release preserves the implementation,
physical-device evidence, and this plan; it does not enable a live product.

## Goal and decision rule

Enable our products to use local inference on an iPhone. Choose the smallest
**qualified complete product stack**, minimizing memory while meeting the chosen
feature's quality, responsiveness, and reliability requirements. Model download
size and parameter count are screening signals, not fit or quality proof.

## What exists

BeanFit Pocket runs a pinned llama.cpp CPU runtime on an iPhone 14 Pro Max. Model
files are checked against pinned sizes and SHA256 values. Products can embed the
runtime and call `LocalInferenceClient`; the included shopping adapter produces
editable suggestions before deterministic sample-catalog filtering.

Liquid 350M and Qwen3.5 0.8B each passed ten short functional checks on the phone.
These are prototype receipts, not production qualification. See
[evidence](evidence/2026-09-26/README.md) and [build instructions](README.md).
No live Jumping Beans, Bean Mind, tools, or voice integration is included.

## Next deliverable: one real Jumping Beans feature

1. Identify the actual iOS product host. If Jumping Beans remains a web product,
   implement an explicit native host/bridge; a separate BeanFit app cannot act as
   a shared background inference daemon for other iOS apps.
2. Connect a real shopping preference request to the embedded runtime. Return
   typed, editable filters. Keep catalog truth, availability, pricing, and all
   actions in deterministic product code. Require review before applying changes.
3. Start qualification with Liquid 350M, retain 0.8B as the next candidate, and
   consider 2B only if smaller candidates cannot meet the same requirements.
   Include a non-model parsing baseline. Do not relax correctness simply to make
   a smaller model pass.
4. Freeze the task contract and quantitative acceptance thresholds before model
   comparisons. Test unseen representative requests, corrections, ambiguity,
   missing preferences, unsupported requests, and malicious input. Record failures
   and abstentions. A tiny same-author demonstration is insufficient.
5. Measure the complete deployed stack on the phone: resident and dirty memory,
   mapped model pages, native host/bridge, context, and relevant services. Include
   startup and repeated runs, cancellation, background/foreground transitions,
   low-memory behavior, thermal behavior, and battery impact. Separate simulator
   evidence from phone results; sampled physical footprint alone is insufficient.
6. Select the lowest-memory candidate that passes every frozen gate. If none
   passes, narrow the feature explicitly or evaluate another model; make no
   unsupported production-fit claim.

Done means the real product completes this one flow on the target phone using
local inference, with reviewed quality and complete resource evidence. It does
not mean an installed standalone demo alone unlocks all products.

## Then: Bean Mind, tools, and voice

Expose only the required Bean Mind context and narrow tool interfaces through
application code. Specify what works offline and what still needs network access.
The language model has no automatic access to Bean Mind or existing tools.

Treat voice as a separate whole-stack qualification: audio capture, speech
recognition, dialogue state, local model, speech output, interruptions, permissions,
and app lifecycle. Compare the entire stack's memory and latency. Do not promote
text-only results to conversational or voice readiness.

## Release gates and resume point

Before production: real host integration, frozen capability tests, repeated phone
runs, full memory accounting, model/runtime license review, privacy review of any
connected tools, and durable distribution. The current development installation
expires on 2026-10-03 unless refreshed. No App Store, TestFlight, or model-weight
redistribution is part of this checkpoint.

Resume with the native host decision and the real Jumping Beans preference flow.
Keep this prototype and its raw receipts as the baseline; do not restart broad
model research without a concrete unmet requirement.
