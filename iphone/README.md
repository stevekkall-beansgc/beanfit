# BeanFit Pocket — native iPhone prototype

For developers building local AI experiences in Legume Labs apps. Import a
supported model to try short text requests on an iPhone, or review shopping
filters before searching the public merchant catalog. Local inference works
without a server; catalog searches need internet.

Start with [Build and run](#build-and-run). You need Xcode, iOS 26 or newer,
and a separately obtained model file. [Tests and evidence](#tests-and-evidence)
explain how to check the prototype without treating a simulator as phone proof.

## October 23: no-phone refinement

The current source fixes editor focus across background/reopen and observes
UIKit lifecycle notifications as well as SwiftUI scene state. This matters in
the beanSprout host: its SwiftUI view did not inherit background scene state,
so the previous containing app could keep the model loaded. The same real
copy/edit/background/reload/dismiss tests now cover both app hosts in disposable
simulators. This does not qualify physical phone memory, heat or latency.

Summaries/rewrites use revised Qwen2 instructions with bounded output cleanup.
The cleanup removes simple reported editorial output-control annotations and
explicit rewrite labels. Ambiguous leading Draft status is retained or restored.
It normalizes a few model-added causal transitions when the
source has no recognized causal wording. It retains uncertain mixed clauses,
requested literal/security text and business quotations. This is a limited
style policy, not a semantic fact checker or prompt-injection security boundary.
The UI marks normalized drafts for comparison with the original. Synthetic
reports retain raw model text and edit counts; ordinary drafts stay in memory.
Reply drafts still use the separate facts formatter without model inference.

The original 36-case packet and additional frozen/regression packets retain
all failures. See [the October 23 evidence and review](evidence/2026-10-23/README.md).
The Mac results are source validation, not phone acceptance. Voice notes and
search remain deferred. BeanFit's CLI, native chooser and companion now place
Qwen2 first for comparison and hold the failed LFM1.2B text configuration.

Two reproducible local harnesses are available:

```sh
python3 iphone/scripts/mac_text_preflight.py --help
python3 iphone/scripts/simulator_text_ui.py --help
```

The first snapshots the actual Swift adapter before compiling it with a supplied,
separately reviewed local native library. It verifies the pinned GGUF on load
and records source, packet and library hashes. The second uses prebuilt simulator
apps and an `.xctestrun` specification, creates its own account-free simulator,
runs both host UI tests, requires finalized results plus background unload
receipts, and deletes only its temporary simulator. Neither accesses a phone,
downloads weights, creates signing assets or calls an AI provider. Raw Xcode
bundles stay private; use the sanitized JSON reports when sharing evidence.

## October 22: text acceptance in progress

The development apps expose **Write with local AI** in Pocket and the beanSprout
containing app. Summarize and Rewrite use the pinned Qwen3.5 2B Q4_K_M candidate
(`qwen2`, 1,280,835,840 bytes), with CPU inference, a 2,048-token context,
2,400 UTF-8 input bytes and at most 192 output tokens. Import the exact model
from Files, tap **Load model**, write a short passage and choose **Write draft**.
Review the result before **Copy reviewed draft**. No automatic model download,
sending, saving or tool access is enabled.

**Draft a reply** is a separate local formatter: enter your own complete facts
and questions in the facts field. Supported “Ask…” directions become questions;
other factual sentences are retained. The incoming message has no instruction
channel and no model is loaded for this task. This preserves facts with much
less memory, but is not a claim that an AI model passed reply-generation tests.
Unsupported Ask directions fail with an instruction to write the question directly.

Edits retire output. Stop, Done, backgrounding, memory warnings and serious heat
cancel and unload. The model releases after 30 seconds idle, uses two CPU threads
at nominal temperature and one at fair, and spaces AI draft starts by 15 seconds.
Loading requires model bytes plus 384 MiB of OS-reported available process memory.
That value is a process budget, not free system RAM.

The [frozen 36-case acceptance protocol](Tests/TEXT-ACCEPTANCE.md) supersedes the
six-case functional demonstration for release decisions. Initial LFM2.5 1.2B phone
runs exposed critical factual failures; a later prompt variant reached serious
heat and stopped. Failed attempts are retained. Qwen3.5 0.8B/2B and LFM1.2B were
compared locally; Mac preflights are not phone qualification. Qwen2 with greedy
sampling and the formatter is the current candidate, not a production selection.

On iPhone 14 Pro Max / iOS 26.6.1, Pocket's revised resource packet passed five
load/write/unload cycles, short-draft timing, Stop, idle unloading and injected
warning/heat handlers. Peak resident memory including mapped pages was 1,384.5
MiB; the conservative peak footprint plus full GGUF was 1,369.5 MiB, below the
frozen 1,536 MiB cap. The subsequent quality packet completed four cases before
an interrupted operation; it did not pass the full acceptance gate. The user
needed the phone, so further physical tests stopped. Full quality, five-minute
thermal runs, real UI lifecycle checks and the Instruments cross-check remain
pending, including the corresponding beanSprout runs. Every raw receipt keeps
`qualified: false`. See [the acceptance checkpoint](evidence/2026-10-22-acceptance/README.md).

beanSprout embeds the shared runtime only in its containing app, excluding the
Messages extension and App Clip. Its preserved native baseline is unmerged and
not approved for publication. WebMCP token renewal and fresh member catalogs fix
the local web release gates (870 assertions passed); those source fixes have not
been deployed. Voice notes and search remain deferred.

Run a physical packet after building/signing the candidate:

```sh
xcrun devicectl list devices --json-output /private/tmp/connected-devices.json
python3 iphone/scripts/device_text_qualification.py \
  --inventory /private/tmp/connected-devices.json \
  --bundle com.beanlabs.BeanFitPocket --phase resource --model-id qwen2 \
  --app /absolute/path/BeanFitPocket.app \
  --model /absolute/path/Qwen3.5-2B-Q4_K_M.gguf \
  --output /absolute/path/text-phone-evidence
```

Use `--phase quality` and `--phase thermal` separately. For beanSprout use
`com.jumpingbeans.v2.imessageprototype` and its prepared app. Device identifiers
stay in private inventory; retained reports contain synthetic text only. Explicit
`--text-smoke`/`--text-qualify` launches export synthetic test results; ordinary
drafts are not exported. Simulator synthetic runs may bypass unavailable process
headroom for functional checks only; they are labelled simulator and never phone
memory evidence. Keep all failed runs when comparing candidates.

## October 15 model refresh candidate

The model chooser now shares BeanFit's pinned on-device catalog with the web
companion. Select an experience and optionally prefer smaller downloads. Five
text configurations can be imported: LFM2.5 230M, 350M QAD, 1.2B Instruct and
Qwen3.5 0.8B/2B. The initial general-text comparison is 1.2B Instruct; this is
an editorial starting point, not a qualified recommendation.

Known Liquid350/Qwen08 shopping failures remain excluded from shopping trial
suggestions. The normal shopping preview still uses reviewed manual filters or
the bounded parser. LFM2.5-2.6B is cataloged but held out for reasoning-aware
runtime support; vision and speech entries require additional integration.
A test memory allowance conservatively excludes files that reach that allowance.
File size is not resident memory; reviewed memory measurements own qualification.
Smaller files still need measurement. Loading is blocked while the
reported thermal state is serious or critical.

Sources and exact files are visible in the chooser. No model is newly qualified,
no phone installation is implied, and existing measurement limits still apply.
See [catalog/suggestion contracts](../README-REFERENCE.md#on-device-catalog-and-suggestions).


## October 6 candidate

The native host now supports reviewed US/USD filters over the current anonymous
Beanshop catalog. **Inference stays on-device; catalog search and merchant links
need internet.** The default flow needs no model: enter product keywords and an
optional USD maximum, choose whether the maximum is inclusive, confirm review,
and search. The bounded parser accepts coffee/watch keywords with `under $30`,
`at most $30`, `up to $30`, and explicit `, actually ...` corrections. Unknown
prose abstains; other product keywords can be entered manually.

Search results are current-interaction discovery evidence. Tap **Review this exact
variant** before a merchant link becomes available. The engine owns catalog truth,
prices and qualification. Shipping, tax, checkout stock and merchant trust remain
unknown until merchant confirmation. No checkout or preference persistence exists.
Results/images are never written to disk, cached, or exported; no image bytes are
loaded. Another catalog action, edits, Stop, backgrounding or restart retire handoffs.
All clients share the existing provider capacity; there are no automatic retries.

Local model suggestions are disabled in the normal preview: Liquid350M passed
2/20 and Qwen08 5/20 frozen simulator semantic cases; the no-model baseline passed
20/20. The failures include corrections, budget boundaries and abstention. This
candidate is not a qualified model/product release. See [the frozen packet](QUALIFICATION-2026-10-06.md)
and [the outcome](QUALIFICATION-RESULTS-2026-10-06.md).

The existing development team built and installed the candidate on October 6.
That profile expired October 13 at 13:56:10 UTC / 09:56:10 America/New_York;
a new phone installation needs a renewed profile.
iOS launch is blocked until the person trusts its existing development profile
in Settings → General → VPN & Device Management, then opens Pocket. If the device
is locked, unlock it before developer-tool launches. Installation success does
not prove launch, local inference or real catalog handoff.

For a local-only preliminary qualification run on a trusted phone:

```sh
xcrun devicectl device process launch --device YOUR_PHONE --terminate-existing \
  com.beanlabs.BeanFitPocket --qualify-catalog --model=liquid350
```

Repeat with `--model=qwen08` only using the already imported exact pinned file.
The report in Documents/catalog-qualification.json retains synthetic prompts,
raw model outputs/failures and cancellation evidence; it always says unqualified.
Use `--experimental-catalog` only for deliberate model-suggestion investigation.
`--live-catalog` additionally attempts one search and one exact review: do not use
it without confirmed shared capacity and authorization, and never automatically
retry an uncertain attempt. This session's first live launch timed out with no
recovered report; its outcome remains unknown.

An installable SwiftUI host for an embedded local inference interface. Product
code calls `LocalInferenceClient`; `EmbeddedInference` implements it with a
single llama.cpp engine. `ShoppingAdapter` demonstrates a Jumping Beans flow:
request → suggested typed filters → explicit user review → deterministic sample
catalog results. Models cannot buy, save preferences, or invoke external tools.

This is an iPhone runtime prototype, not a production-qualified model selection.
The existing Python mobile selector remains separate. These measurements cannot
be used as whole-stack qualification receipts.

## Build and run

Requires Apple Silicon, Xcode, an iOS 26+ target, CMake, and llama.cpp source pinned
to `2145525a4081d66ff1a87cf43ef809f95a85ac0c`. No dependencies or models are downloaded
by the build. Use an output directory outside Git. For example:

```sh
export BF_LLAMA_SOURCE=/absolute/path/to/pinned/llama.cpp
export BF_OUTPUT=/absolute/path/to/build-output
bash iphone/scripts/build.sh iphonesimulator
# A development team and trusted device are required for phone installation.
export BF_TEAM=YOUR_APPLE_TEAM_ID
bash iphone/scripts/build.sh iphoneos
```

Install `BeanFitPocket.app` from the appropriate build's Products directory using
Xcode or Apple's device tools. On a phone, trust the development profile if iOS
requests it. Development installation is temporary; it is not App Store or
TestFlight distribution.

Import the exact GGUF selected in the app using Files, or copy it into the app's
Documents/Models directory with Apple's developer tools. File sizes and SHA256
identities are pinned in `BeanFitRuntime/Models.swift`. Every load rechecks both.
The app performs no model downloads and has no remote inference fallback.

Load a model, run a local prompt, or suggest shopping filters. Review and edit
filters, then tap **Apply reviewed filters** to search the synthetic catalog.
Use **Unload** to release the model and **Share measurements** to export JSON.

## Product integration

Embed BeanFitRuntime sources and native archives in each product's native iOS
host, using that host's bridging header. Inject a `LocalInferenceClient` into
product adapters. The included Jumping Beans adapter is an example, not an
integration with the live Jumping Beans website, Bean Mind, or existing tools.
A separate app does not provide a shared inference daemon to other iOS apps.
A web product needs a native host/bridge before it can call this interface.

Only one model is resident per engine. Contexts are created per request and freed
afterward. Generation has a 2048-token context, a 256-token hard output maximum,
and a 90-second cancellation deadline. It uses two CPU threads at nominal thermal state and one at fair; Metal and
Accelerate are disabled in this first build. Stop cancels inference; unloading
waits for serialized native work. Backgrounding and memory warnings request
cancellation and unloading. Import/hash verification is not instantaneously
cancellable. No microphone, speech recognition, speech synthesis, persistent
conversation, tool execution, or Bean Mind integration is included yet.

## Tests and evidence

```sh
bash iphone/scripts/test_contracts.sh
PYTHONPATH=src python3 -m unittest discover -s tests
python3 iphone/scripts/simulator_e2e.py \
  --device BOOTED_SIMULATOR_UUID --app /absolute/path/BeanFitPocket.app \
  --model /absolute/path/Qwen3.5-0.8B-Q4_K_M.gguf --output /absolute/path/evidence
```

The owned simulator E2E runs existing offline E2Es, installs the app, imports the
pinned model, launches `--smoke`, and verifies ten actual app checks. The native
contract tests cover invalid suggestions, catalog boundaries, and tampered model
files. They run in Python's unit suite on macOS and are explicitly skipped on
other hosts. Native E2E registration requires Xcode, a booted simulator, the built
app, and the pinned model; the session's QA manifest supplies those paths.

Developer smoke launches accept `--model=liquid230`, `--model=liquid350`,
`--model=liquid12`, `--model=qwen08`, and `--model=qwen2`. The simulator E2E
accepts the same catalog IDs through `--model-id` (default `qwen08`) with a
matching `--model` file. They write Documents/smoke.json and beanfit-measurements.json.
These tiny functional checks are not a quality benchmark or a model winner.

Memory is sampled app-process physical footprint every 20ms. It includes the
native model context while running but can miss peaks and excludes unaccounted
system services. Clean memory-mapped model pages may not be charged to this
footprint; these values are not total resident RAM or a fit budget. Exports label simulator/device evidence, include failed runs,
and always state `qualified: false`. Whole-product memory, repeated reliability,
latency budgets, thermal behavior, and capability-specific quality remain release
gates. Choose the smallest model that passes those gates; do not select by file
size alone.

## Next checkpoint

See [the next-phase plan](NEXT-PHASE-PLAN.md) for the agreed purpose, remaining
product work, qualification gates, and exact resume point.
