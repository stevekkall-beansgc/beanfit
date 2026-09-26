# BeanFit on iPhone: feasibility decision

Research date: 2026-09-26. Base: `c4072e9`. Hub task: **1233**, gated.
Status: isolated research candidate; no phone installation or physical-device
measurement. This is not a released BeanFit capability.

**Recommendation: benchmark a native Apple on-device stack first.** Use
`SystemLanguageModel.default`, on-device speech recognition, and
`AVSpeechSynthesizer`. Keep a small MLX Swift model as the controlled alternative.
Use WebLLM as a separate distribution experiment, after native establishes the
quality and latency target. This recommendation is an engineering inference,
not a measured comparison.

An eligible iPhone can plausibly run Nina without an awake Mac or per-request
inference charges. That does not establish acceptable conversation quality,
battery life, permanent free distribution, or fresh web knowledge. No phone
model or OS version was established in this session. The historical iPhone 17
Pro *simulator* entry in BeanMind does not identify Steve's physical phone.

## What was established

| Evidence | Result | What it does not establish |
|---|---|---|
| BeanFit source inspection | Mac budget includes a 4 GiB floor and a 16,384-token KV assumption | Neither is a usable iOS memory budget |
| Primary documentation | Apple native, MLX Swift, llama.cpp, MLC, and Safari WebGPU paths exist | A particular phone can sustain the whole Nina stack |
| Local compiler | Xcode 27.0 / build 27A266a; iOS 27 simulator and device SDKs typecheck the iOS 26+ probe | Linking, launch, signing, inference, microphone or voice success |
| Offline receipt tests | Synthetic/simulator rows cannot become physical voice or fit proof | Authenticity of externally supplied receipts |
| Physical iPhone | **Not tested** | Latency, memory, heat, battery, voice preference and offline reliability remain unknown |

The existing Nina v1 release uses the Mac for inference and speech. Its phone
connection and previous Mac speech results are not on-phone benchmarks. The
separate Cloudflare pilot is outside this investigation.

## Three paths

| Path | Eligibility and setup | Benefit | Main uncertainty | Decision |
|---|---|---|---|---|
| Apple Foundation Models | iOS 26+ framework, eligible Apple Intelligence device, enabled/ready model, supported locale | System-managed weights; explicit native on-device model | Small context, changing OS model, quality/refusals, availability | First benchmark |
| Downloadable native | MLX Swift/llama.cpp/MLC build plus supported model, local assets and license | Exact weights, quantization and context control | App memory, peak loading, heat, speech coexistence | Compare one small model next |
| WebGPU/WebLLM | Safari 26+ WebGPU, secure origin, successful adapter/model feature checks, downloaded assets | No custom native signing; local browser inference | Tab eviction, storage loss, audio lifecycle, GPU limits | Experimental fallback |

### Apple Foundation Models

`SystemLanguageModel` is the on-device text model. Select that class explicitly;
the expanding Foundation Models framework also exposes other model backends.
Do not route this experiment to Private Cloud Compute or third-party servers.
Apple documents offline operation and no inference fee for the on-device
framework. [SystemLanguageModel](https://developer.apple.com/documentation/foundationmodels/systemlanguagemodel),
[framework introduction](https://developer.apple.com/videos/play/wwdc2025/286/),
[Apple model report](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates).

The current Apple eligibility list includes iPhone 15 Pro/Pro Max, iPhone 16
models and later, and iPhone Air; ordinary iPhone 15 is not included. OS support
alone is insufficient: check runtime availability and locale. Apple's September
2026 guidance describes iOS 27 asset storage up to 14 GB on specified higher-end
devices and up to 8 GB on other eligible devices. Those are *system storage*,
not application RAM or a single model's weight size. Availability also depends
on language and region. [Apple requirements](https://support.apple.com/en-us/121115).

Treat the older 4,096-token context guidance as a conservative starting point;
read `contextSize` rather than making it a timeless constant. Instructions,
history, schemas, tool results and answers share the budget. The installed
SDK exposes `tokenCount` from iOS 26.4 and `variant` from iOS 27. OS updates can
change the model, so revalidate by OS build; exact Apple weight hashes cannot be
pinned like a downloaded model. [Context management](https://developer.apple.com/documentation/foundationmodels/managing-the-context-window),
[framework updates](https://developer.apple.com/documentation/updates/foundationmodels).

Apple's 2026 research describes multiple on-device and server models, including
more capable speech features. This is **not** proof that every model or Siri
voice is exposed through the app API on every eligible phone. Benchmark the
actual selected runtime. [Apple's third-generation report](https://machinelearning.apple.com/research/introducing-third-generation-of-apple-foundation-models).

### Downloadable native models

Use **MLX Swift**, not Python `mlx-lm` or Mac Ollama commands, for the first
alternative. Its package supports iOS 17; the optional FoundationModels bridge
requires the 27 SDK/API. Runtime minimum OS does not certify model fit on older
phones. Pin the chosen release and all dependencies before downloading weights.
BeanFit's roadmap statement “MLX=macOS-only” is too broad for Swift and should
be revised in a separately reviewed product integration.
[MLX Swift package](https://github.com/ml-explore/mlx-swift/blob/main/Package.swift),
[MLX Swift LM](https://github.com/ml-explore/mlx-swift-lm).

Start with Qwen3 0.6B 4-bit as a low-memory control, then 1.7B 4-bit if the smaller
model cannot follow the contextual QA tasks. Both MLX repositories exist, but
this investigation has **not** downloaded/hash-verified their files or measured
their runtime memory. The 0.6B card lists 335 MB; that is published artifact
metadata, not total resident memory. Neither candidate has been added to
BeanFit's catalog. Resolve an immutable revision, hash every artifact, measure
bytes and review its license before a trial.
[0.6B MLX](https://huggingface.co/mlx-community/Qwen3-0.6B-4bit),
[1.7B MLX](https://huggingface.co/mlx-community/Qwen3-1.7B-4bit).

Disable Qwen's thinking mode through the actual chat template and verify the
emitted output; do not spend the spoken-response budget generating hidden
reasoning. Its upstream card documents the switch and Apache-2.0 license.
[Qwen3 model card](https://huggingface.co/Qwen/Qwen3-0.6B).

llama.cpp supplies an iPhone SwiftUI sample and an XCFramework build route for
GGUF models. MLC supplies an iOS Swift SDK and compiled model libraries; its
documentation explicitly separates context-window KV cost from prefill
temporary memory. They are credible alternatives, but testing all three native
runtimes initially would enlarge the experiment without answering the core
question. [llama.cpp iPhone example](https://github.com/ggml-org/llama.cpp/tree/master/examples/llama.swiftui),
[MLC iOS](https://llm.mlc.ai/docs/deploy/ios.html).

### Browser WebGPU and WebLLM

Safari 26 shipped WebGPU on iOS. That removes the old blanket “Safari cannot
run WebGPU” objection. It does not prove a particular WebLLM compiled model
works: probe `navigator.gpu`, adapter limits/features, required shader features,
model loading and generation on the actual OS/browser.
[WebKit release](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/).

WebLLM runs inference in the browser and supports workers. Pin its package,
compiled model library and weights together. An API shaped like a hosted chat
API does not mean remote inference. Cache the application, runtime, tokenizer,
model and context; a cached weight file alone does not make an offline app.
[WebLLM documentation](https://webllm.mlc.ai/docs/),
[model/runtime configuration](https://webllm.mlc.ai/docs/user/basic_usage.html).

WebKit can evict origin storage under pressure; storage estimates are not RAM
budgets or guaranteed free disk. Request persistence, check its result, and
provide a recoverable missing-assets state. Test Safari and Home Screen modes
separately. Backgrounding, locking and audio interruption require actual
lifecycle tests; no always-listening claim is justified.
[WebKit storage policy](https://webkit.org/blog/14403/updates-to-storage-policy/).

## Voice, memory and offline context

Use SpeechAnalyzer/SpeechTranscriber where available on iOS 26+, checking
`isAvailable`, supported locale and installed assets. These are system-managed
on-device models; assets may require an initial download. Apple's older
SFSpeechRecognizer can use servers, so a fallback must check on-device support
and require on-device recognition or stop. [SpeechAnalyzer](https://developer.apple.com/videos/play/wwdc2025/277/),
[SpeechTranscriber capability checks](https://developer.apple.com/documentation/speech/speechtranscriber),
[on-device request setting](https://developer.apple.com/documentation/speech/sfspeechrecognitionrequest/requiresondevicerecognition).

For synthesis, start with an installed AVSpeechSynthesizer voice. Apple documents
on-device processing; record the voice identifier and test the downloaded voice
in airplane mode. Naturalness is a listening decision, not a framework checkbox.
The existing Mac Kokoro voice is not automatically portable. WhisperKit is a
possible native ASR alternative with extra model/storage cost; its smallest
model is described as a debugging choice, not the quality baseline. No Argmax
Pro subscription is needed or proposed.
[Apple speech synthesis](https://developer.apple.com/documentation/avfoundation/speech-synthesis),
[WhisperKit open-source repository](https://github.com/argmaxinc/argmax-oss-swift).

Proposed Nina loop: one tap → local microphone + endpoint detection → final
transcript → local retrieval → bounded model answer → sentence-level synthesis
→ listening resumes. Mute recognition during playback initially; add explicit
interruption. Pause cleanly on background/lock/audio interruption. Browser
SpeechRecognition availability alone does not prove offline ASR; browser voice
must pass offline tests or use a separate local ASR engine.

Do not estimate mobile tok/s from Mac bandwidth. Download size, GPU allocations,
process footprint and system-managed model memory measure different things.
Measure peak loading, prefill, decode, ASR and TTS overlap. For design only,
dense 4-bit payload arithmetic gives roughly 0.28/0.79/1.40 GiB for 0.6/1.7/3B
parameters. This is an idealized lower bound with unbounded overhead, **not a
fit estimate**: scales, higher-precision tensors, KV cache, buffers, copies and
speech add memory. Leave mobile fit and speed unknown until measured.

Export a deliberately small approved BeanMind context pack to the app sandbox:
source ID, exact content hash, approval revision, timestamp, expiry/revocation
policy and dated text. Begin with local lexical retrieval rather than a second
embedding model. Verify integrity and trusted approval at import; changed or
missing provenance fails closed. Retrieval cannot approve new content. An
expired pack must say it is stale; offline cannot promise immediate revocation
or current Hub state. Keep conversations local, bounded and deletable. Initial
benchmarks use fictional data only.

Current web answers still need internet and an independently validated data
source. A local model does not provide live search. Keep web lookup optional,
read-only and outside the offline loop; send only an explicitly public query,
never project snippets or private history. Browser CORS and rate limits can
block direct fetches. No proxy/service, credentials, search-provider commitment,
Groq fallback, or Cloudflare work is introduced here.

## Distribution and meaning of “without a Mac”

Free Personal Team testing requires signing in to Xcode, has limited app/device
slots and provisioning that expires after seven days. Rebuild/reinstall is
needed after expiration. Therefore it removes the *running Mac server*, but
does not offer maintenance-free permanent native distribution. Standard App
Store/TestFlight distribution requires program membership, currently USD 99
per year; that is separate from inference cost and is not authorized here.
[Free account limits](https://developer.apple.com/help/account/basics/about-your-developer-account),
[program membership](https://developer.apple.com/programs/whats-included/).

A browser app avoids custom native signing, but needs an initial trusted HTTPS
delivery path and durable cached assets. Its voice and offline behavior remain
experimental. An existing local-model app or an explicitly on-device Shortcuts
flow could validate utility without building Nina's complete app, but is not
assumed to provide Nina's context controls or conversational UX.

Proceed to the [bounded benchmark plan](BENCHMARK-PLAN.md). Stop before phone
installation, downloads, provider changes, publication or integration unless
those next actions are explicitly authorized.

## Validation and review receipt

On 2026-09-26 the isolated candidate passed 192 Python tests (including eight
new synthetic receipt checks), the registered offline synthetic activation E2E,
QA docs checks, pinned Ruff 0.16.8 and both Swift SDK typechecks. QA used the
existing BeanFit commands with a temporary manifest pointing to this worktree;
the production registry was not edited. Logs are in
`/Users/stephenkall/beans/outputs/beanfit-iphone-20260926/`;
the final QA receipt is `qa/run-20260926T151336Z.json`.

Same-author adversarial pass: addressed Mac compatibility misclassification,
nonfinite/oversized timings, simulator promotion, missing measurements and
partial failures. Remaining limits: receipts are unauthenticated; native code
is typechecked only; no full app, timeout harness or speech integration exists;
no independent review was performed. All are disclosed and remain gates for
later integration. No product ranking, catalog or running service changed.
