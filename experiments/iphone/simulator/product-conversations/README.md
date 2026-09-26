# Product conversation pilot — 2026-09-26

**Qwen3.5 2B passed the small Jumping Beans shopping screen. No tested model
passed the voice-transcript or broader conversation screen.** This is a
provisional shortlist result, not production acceptance or phone qualification.

## Results

| Configuration | File MB, not RAM | Shopping turns | Voice-transcript turns | General conversation turns |
|---|---:|---:|---:|---:|
| LFM2.5 350M QAD Q4_0 | 219.31 | 1/6 | 2/6 | 5/6 |
| Qwen3.5 0.8B Q4_K_M | 532.52 | 4/6 | 0/6 | 3/6 |
| LFM2.5 1.2B Instruct Q4_K_M | 730.90 | 1/6 | 3/6 | 2/6 |
| Qwen3.5 2B Q4_K_M | 1,280.84 | 6/6 | 2/6 | 3/6 |

Each lane contains three two-turn scenarios. All 72 inference turns completed.
The second user turn receives the model's actual first response, not a supplied
ideal answer. The model/context is reloaded and replayed each turn; this does not
measure a persistent interactive server's latency or cache behavior.

The per-lane rule was fixed before inference: at least 5/6 passing turns AND
all critical turns pass. Liquid 350M's 5/6 conversation score still fails because
its owner-update summary omitted the required paused/usability-testing context.
These small, heterogeneous rubric scores must not be treated as rankings of
general intelligence or expected real-world percentages.

Qwen 2B correctly carried blue/$100 preferences, stated no match, compared
verified prices/straps, acknowledged unknown waterproofing/delivery, rejected
an untrusted $1 merchant price and disclosed inability to buy/save. Its language
was stiff and repeated unnecessary clarification/disclaimer questions. It is a
candidate for a bounded, reviewed shopping interface, not a polished assistant.

In transcript-style turns it ignored a black-strap correction, falsely said a
$180 watch fit a $150 budget, and invented a premium/affordability comparison.
Qwen 0.8B also lost preferences and repeated incorrect relative-price claims.
Liquid models frequently echoed requests, fabricated offers, or lost corrections.
For general conversation, models usually acknowledged unknown budget/date and
tool limitations, but often failed to give the requested useful plan or preserve
all summary requirements. Qwen 2B's first planning answer was relevant but 105
words against the fixed 90-word cap; its follow-up adaptation was useful.

## Product-shaped test, not an integration

The fictional shopping catalog uses verified IDs, USD prices and strap colors.
The roles mirror Jumping Beans V2's preference, provenance and reviewed-action
boundaries. No live catalog, merchant invocation, purchase, save, memory write,
WebMCP adapter or production account was used. The Nina lane uses explicitly
fictional project context, not private BeanMind data. Live retrieval, persistent
memory and actual tool invocation remain untested. No running Nina or Jumping
Beans service was changed.

`workload.json` holds the predeclared questions, system instructions and semantic
rubric. `reviewed-results.json` includes every answer and a reason for every
manual pass/fail. Review was by the same author, not blind or independent; results
are a small exploratory pilot. Semantic review avoids demanding one exact answer
string, but is still subjective and needs user/independent review on more cases.
One generation per turn; no retries or prompt tuning on these outputs. Each
scenario resets conversation history. No long-session conversational claim.

## Hugging Face review

- [Qwen3.5 2B](https://huggingface.co/Qwen/Qwen3.5-2B) is a larger comparison
  appropriate to conversation/agent prototyping. Downloaded the pinned
  [Unsloth Q4_K_M artifact](https://huggingface.co/unsloth/Qwen3.5-2B-GGUF),
  verified its SHA, and tested text-only non-thinking mode. No vision projector.
- [LFM2.5 1.2B Instruct](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct)
  and the already measured 350M/0.8B configurations were retested for conversation;
  extraction failures alone were not used to exclude them.
- [FunctionGemma 270M](https://huggingface.co/google/functiongemma-270m-it)
  is intended for task-specific function-calling fine-tuning, not direct dialogue.
  Deferred until testing a bounded action router; no new qualification claim.
- [Qwen3.5 4B](https://huggingface.co/Qwen/Qwen3.5-4B) remains a possible larger
  conversational control. Neither it nor Nina's existing Mac Qwen3 4B was tested
  here. This pass does not demonstrate parity with current Nina.
- [LFM2.5 Audio 1.5B](https://huggingface.co/LiquidAI/LFM2.5-Audio-1.5B) is an
  English audio/text model with separate encoder and audio-generation components
  and publisher-listed CPU GGUF support. It is a relevant direct-speech research
  candidate, but the text-only runner cannot test it. No audio weights were
  downloaded and iOS runtime integration/memory remain unverified.
- [Whisper tiny.en](https://huggingface.co/openai/whisper-tiny.en) is a smaller
  ASR candidate to compare against the existing base.en recognizer later.
  [Kokoro 82M](https://huggingface.co/hexgrad/Kokoro-82M) remains a TTS candidate;
  publisher model size does not represent the full speech runtime footprint.

## Actual speech component checks

Using existing local Mac assets, generated three clean Samantha audio clips and
transcribed them with faster-whisper base.en CPU int8. All three retained the
intended budget correction, black/not-blue preference and stop/no-purchase
meaning. Inputs had verified nonzero duration and amplitude. This is only a
three-clip synthetic component smoke check, not human ASR accuracy, noisy-input
robustness or an iPhone benchmark. A first sandboxed synthesis attempt produced
empty audio and was excluded; rerunning with speech-service access produced the
valid clips. An attempted verifier import was also corrected to use the existing
audio decoder rather than installing another dependency.

The existing local Kokoro model then synthesized the first Qwen2B shopping reply
into a 12.15-second WAV. The artifact has verified nonzero samples, but no
subjective listening score is claimed. `speech-components.json` records source
text, actual transcripts, WAV hash and component receipts. These ASR clips were
not fed through an integrated ASR/LLM/TTS conversation; voice interruption in the
model screen was a textual instruction, not an acoustic barge-in test.

## Next bounded work

1. Expand Jumping Beans shopping cases with real schema and representative
   consented or synthetic journeys; review Qwen2B answers and reduce redundant
   questions. Keep catalog facts, eligibility, permissions and confirmations in
   trusted application code. Compare memory only after quality acceptance.
2. For voice, evaluate actual human utterances/noise, pass recognizer outputs
   through the conversation engine, then synthesize replies. Test interruption,
   turn detection and corrections end to end. Compare tiny/base ASR and platform
   speech options with a whole-stack memory budget.
3. For general Nina conversation, compare a larger conversational control against
   the current 4B experience using multi-turn context, useful planning and user
   preference evaluation. Do not infer conversational fitness from extraction.
4. On the iPhone 14 Pro Max, confirm current OS/signing and use a signed native
   harness. Measure sustained peak memory, end-of-speech-to-first-audio delay,
   battery and thermals with the exact chosen runtime and context caps. No phone
   installation was performed in this session.

## Reproduction and validation

`artifacts.json` pins model repos/revisions/bytes/hashes, llama.cpp revision,
runner and workload hashes. The simulator is BeanFit-Model-Test, iOS 27.0,
arm64 IOSSIMULATOR binary, CPU-only with Metal/Accelerate disabled. It was shut
down after testing. Mac-backed simulator speed is not phone speed. There are no
whole-stack memory measurements or physical-device winners.

Use `scripts/conversation_probe.py` with the pinned model hash, original
simulator binary, booted simulator ID, workload, model template and a new output
directory. Review outputs against each turn's rubric. Raw receipts/stdout/stderr,
HF metadata and speech files are retained in
`/Users/stephenkall/beans/outputs/beanfit-product-conversations-20260926/`.

All 224 unit tests, repository docs and registered offline E2Es passed via qa-kit.
New tests cover actual assistant-history replay and model-specific echo removal.
Ruff and whitespace checks passed. Changes are local and unmerged. No source
modifications, release or deployment were made to Jumping Beans or Nina.
