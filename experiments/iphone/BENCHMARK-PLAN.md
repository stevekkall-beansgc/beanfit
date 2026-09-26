# Bounded prototype and acceptance plan

These are proposed experiments and product targets, **not measured results**.
Owner: current BeanFit research task, Hub 1233. Hardware access and phone
installation remain dependencies; this document does not authorize them.

## Work completed without a phone

`NativeTextProbe.swift` is an iOS 26+ library component with no application
entrypoint. Its default call checks availability without generating anything.
An explicit `run(infer: true)` uses a fresh Apple on-device session, a fixed
fictional fact and a 64-token output cap. It records OS build, machine ID, model
variant when exposed, reported context, thermal state, first nonempty streamed
text and total generation time. It exports no transcript or private data.

The compiler marks simulator execution explicitly. A non-phone native idiom
is unsupported. Cache warmth is unknown; first text is a framework delivery
measurement, **not first token**, and character counts are not token counts.
The component has no deadline wrapper: its future harness must enforce a
30-second trial deadline, cancel the task and record a timeout separately.
Cancellation is cooperative; terminate a stuck test app through the harness.
It does not download assets, request permissions, install an app or prove
offline behavior. There is no voice implementation.

`receipt.py` validates one receipt and reports its limited evidence class.
It does not authenticate receipts, rank models, average failures away, or
certify fit. Physical text success can only become a physical text observation.
Speech, battery, quality and network-isolation evidence need a later schema.

From this worktree:

```sh
sh experiments/iphone/typecheck.sh
PYTHONPATH=src python3 -m unittest tests.test_iphone_experiment -v
# Only after a future authorized harness exports a real receipt:
python3 experiments/iphone/receipt.py /path/to/text-receipt.json
```

Tests use synthetic in-memory records and temporary files. No phone result
file is provided. The SDK check does not run the model or simulator.

## Trial A: native Apple baseline (one phone, one English locale)

Timebox: one implementation day after device access, followed by a 60–90 minute
measurement session. Confirm exact physical model, iOS build, language, available
storage and Apple Intelligence readiness first. Do not assume the simulator's
name is the user's phone. No purchase or OS upgrade is implicit.

1. Wrap the probe in a small foreground test app. Add explicit start/cancel,
   a timeout, receipt export and app build/source hash. Validate denied and
   unavailable states. Sign/install only after separate authorization.
2. Record runtime readiness without inference. Install required OS language/
   speech assets only with authorization. Test with Wi-Fi and cellular disabled
   after preparation; airplane mode alone can leave Wi-Fi enabled.
3. Run 20 fixed fictional text cases: eight context recall/synthesis, four
   missing/stale facts, four instruction-following/injection cases, and four
   corrections/multi-turn cases. Fix instructions and a 128-token cap. Record
   context token count where available; test both a short pack and about
   2,000 input tokens. Reset sessions deliberately and test context overflow.
4. Run three repeats per case. Separate first launch, first inference and repeat
   runs; record unknown system cache warmth rather than claiming a true cold
   model load. Report n, every failure, median and nearest-rank p95 per stratum.
   Do not pool unlike context lengths or missing observations.
5. Add native ASR and TTS after text works. Use 20 consented, nonprivate utterances
   with reference transcripts: names such as Nina-Beana, corrections, pauses,
   quiet speech and background noise. Record word error rate and task meaning,
   endpoint delay, ASR final delay, model first-text/full-answer delay, TTS first
   audio and end-of-speech-to-first-audio. Test mic denial, interruptions,
   cancellation, playback feedback and re-entry after lock/background.
6. Run 20 minutes of alternating conversation plus a matched idle baseline at
   fixed brightness, power mode, connectivity and ambient conditions, unplugged.
   Record battery start/end, coarse percentage resolution, thermal state,
   throughput trend, crashes and memory warnings. Repeat if practical; one short
   session cannot establish all-day battery life.

Use Instruments/device diagnostics to capture process physical footprint and
peak allocations, identifying whether system model/speech services are excluded.
Never report app RSS as total stack RAM. Note if tooling changes the thermal
or energy conditions. Retain timestamped raw receipts and observer notes locally.

## Trial B: one downloadable challenger

Timebox: one implementation day, only if A is unavailable or fails quality.
Use MLX Swift and Qwen3 0.6B 4-bit; advance once to 1.7B if needed. Resolve exact
runtime/source revisions, tokenizer, weights, license and checksums. Use local
file loading with network fetching disabled after preparation. Record download
bytes separately from installed and peak resident bytes. Start at 2,048 context
tokens and 128 output tokens, with non-thinking mode verified.

Reuse A's cases, locale, speech stack and energy procedure. Compare only matched
prompt/output/context settings. Test loading under memory pressure and after
app termination. Do not expand to 3B/4B or more runtimes unless there is measured
headroom and a specific unresolved quality need. Stop on repeated termination,
serious/critical heat, or a test that needs paid infrastructure.

## Trial C: browser feasibility, not production migration

Timebox: half a day after a candidate and expected quality are known. Feature
probe Safari and Home Screen mode independently. Choose the smallest *verified*
WebLLM model artifact; do not substitute MLX weights or guess a compiled library.
Pin runtime, weights and library. Check GPU buffer limits, shader features,
storage quota/persistence, first load, cache reload, network-off restart and
`device.lost`. Stage delivery without publishing the running Nina service.

Start text-only; then prove local ASR/TTS. A working web microphone is not local
speech recognition. If the browser has no verified offline ASR, report “text
prototype only” and stop. Repeat background/lock/interruption and 20-minute
tests. No Mac proxy may be present in the “phone-independent” acceptance run.

## Proposed stop/go criteria

| Area | Target chosen for this pilot, not a prediction |
|---|---|
| Grounding | At least 18/20 cases correct; 100% of missing/current facts acknowledged; no invented project status |
| Privacy | No private-context network egress; airplane/network-disabled text + speech pass; tool-off mode makes zero app web requests |
| Conversation | p95 end-of-speech to first audio ≤4 seconds warm, ≤8 seconds first turn; report all components |
| Turn behavior | At least 19/20 turns endpoint correctly; no self-transcription of playback; cancel stops audible output within 500 ms |
| Memory/reliability | Zero terminations or unrecovered allocation/device-loss errors in the bounded run; no universal RAM-cap inference |
| Thermal/battery | No serious/critical thermal state; final-quartile warm latency ≤1.5× first-quartile; target ≤5 percentage points incremental battery over 20-minute matched idle, repeat before acceptance |
| Voice preference | Steve rates intelligibility and naturalness acceptable relative to released Nina, using blinded short samples if possible |
| Context | Changed/unapproved source rejected; expired pack labeled stale; no network needed to read approved cached pack |
| Distribution | User accepts a concrete signing/maintenance option before calling the app usable long-term |

Failures stay in the denominator. A tiny low-power model that gives incorrect
answers loses to a slightly slower model meeting the quality floor. Passing
these targets is evidence for the tested phone/build/settings only.

## BeanFit integration after evidence

Add a separate mobile observation contract; do not force iPhone through the
Mac `DeviceProfile` memory floor or estimated score. Selection order: capability
→ provenance/license → complete-stack fit → quality floor → observed latency/
energy → user preference. Missing evidence returns “needs device benchmark”.
Keep `published`, `estimated`, `synthetic`, `simulator`, and `physical_device`
classes distinct, and include hardware/OS/runtime/model/context in every result.

Before any merge: obtain independent corroborative and adversarial review,
disposition findings, register the eventual app's unit/E2E entrypoints in QA,
and secure explicit integration approval. This session's review is same-author
only. No new production flow, catalog row, service or cloud deployment is made.
