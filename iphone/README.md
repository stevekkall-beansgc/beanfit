# BeanFit Pocket — native iPhone prototype

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
The renewed profile expires October 13 at 13:56:10 UTC / 09:56:10 America/New_York.
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
and a 90-second cancellation deadline. It uses four CPU threads; Metal and
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

Developer smoke launches support `--model=qwen08`, `--model=liquid350`, and
`--model=qwen2`. They write Documents/smoke.json and beanfit-measurements.json.
These tiny functional checks are not a quality benchmark or a model winner.

Memory is sampled app-process physical footprint every 20ms. It includes the
native model context while running but can miss peaks and excludes unaccounted
system services. Clean memory-mapped model pages may not be charged to this
footprint; these values are not total resident RAM or a fit budget. Exports label simulator/device evidence, include failed runs,
and always state `qualified: false`. Whole-product memory, repeated reliability,
latency budgets, thermal behavior, and capability-specific quality remain release
gates. Choose the smallest model that passes those gates; do not select by file
size alone.

## Paused checkpoint

See [the next-phase plan](NEXT-PHASE-PLAN.md) for the agreed purpose, remaining
product work, qualification gates, and exact resume point.
