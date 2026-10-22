# Text acceptance checkpoint — October 22, 2026

**Incomplete; no release qualification.** Physical testing stopped when the user
needed the iPhone. Voice notes and search remain deferred. [summary.json](summary.json)
records the exact scope; [the frozen protocol](../../Tests/TEXT-ACCEPTANCE.md)
remains unchanged. All packet data are synthetic and device identifiers are
excluded. Raw Instruments/XCTest bundles stay private outside Git.

## Findings and candidate

The initial LFM2.5 1.2B physical packet had critical errors in s07, w03 and r09:
conflicting dates treated as confirmed, a request converted to a promise, and a
quoted override executed. Its authored review passed 29/36 factual and 29/36 task
cases. The revised prompt variant stopped after 15 cases when iOS reported serious
heat. This failed run is retained; protective unloading does not turn it into a
thermal pass.

Three pinned models were screened with the same frozen cases locally: LFM1.2B,
Qwen0.8B and Qwen2. The compact-prompt phrase screens passed 23/36, 31/36 and
34/36 respectively. More elaborate prompts and vendor sampling presets did not
remove factual failures. Raw variants remain beside this document; they are Mac
preflights, never phone heat/memory evidence or a claim that all smaller models
were exhaustively optimized.

The current pipeline uses Qwen2 greedy summaries/rewrites and a separate local
facts formatter for replies. The formatter retains supplied fact sentences,
turns supported Ask directions into questions, and excludes the incoming message.
It has no model quality or memory claim. The combined Mac preflight passes 35/36
phrase screens; the implementing agent's authored review finds 36/36 factual,
33/36 task/clarity and zero critical failures. s08 repeats irrelevant quoted
material, w01 retains a lowercase opening, and w11 explains the irrelevant sticker.
These are recorded defects, not hidden passes. This is not independent user
research, phone quality acceptance, multilingual or open-ended chat validation.

## Physical evidence

Pocket's Qwen2/formatter resource build passed its 124-second packet:

- Resident peak including mapped pages: 1,384.5 MiB; frozen cap 1,536 MiB.
- Peak charged footprint plus the entire GGUF: 1,369.5 MiB; same cap.
- Five load/write/unload cycles; unloaded resident growth 53.9 MiB, under 64 MiB.
- Stop/unload about 37 ms; idle unload, blank/oversize guards and edit retirement passed.
- Injected warning/heat policies passed; these were not real OS pressure events.
- Actual thermal samples remained nominal; zero real memory warnings.

This is not a five-minute sustained-use result. The next physical quality packet
completed four correct summaries, then an operation was interrupted without a
recorded model error or hot state. Its error text was the stale writing status;
the precise trigger is unproven. Source now reports stop status immediately and
records synthetic flow events to diagnose the next occurrence. Do not assert the
underlying interruption is fixed until the exact final phone build completes.

The resource receipt predates those diagnostic/status changes. Build hashes in
`resource-build-source-manifest.json` identify its shared source. Re-run exact
final source after the phone returns. The latest beanSprout source builds but was
not installed before the user left. Its full corresponding packets remain pending.

Initial actual-phone UI tests reached typing/generation but failed the old
model's blue-folder content assertion; copy/background/dismissal steps were not
reached. VM Tracker initially could not resolve the CoreDevice identifier; no
cross-check is claimed. Use the private inventory's actual UDID mapping for the
next Instruments attach, and retain profiler overhead separately from latency.

## Resume

Rebuild/install exact final candidates, import the pinned Qwen2 file into both
apps, complete all 36 quality cases with authored review, then run resource and
20-request/5-minute thermal packets per app. Run actual UI tests for copy, editing,
background/reopen and dismissal; extract lifecycle timing receipts. Finish an
app-only VM Tracker cross-check. Preserve failed runs. A phone receipt never
waives the unmerged native-baseline review or public release gates.

The diagnostic simulator run completed all 36 cases (35 phrase screens), so the
physical interruption did not reproduce there. Four outputs differ from the Mac
CLI preflight. In w05 the rewrite adds disappointment and an extra information
request; those additions require review and are not evidence that phone quality
passed. The simulator explicitly bypasses unavailable process headroom for
synthetic flow checks; it cannot replace any physical memory/heat gate.

Simulator UI automation observed typing, the Thursday/blue content checks, copy
status, edit retirement and a real background/foreground transition. It then
waited for application idleness after reactivation and was stopped without a full
UI pass. Keyboard navigation and duplicate Load controls were improved; full
reload/dismissal automation remains pending. Simulator lifecycle timings are
retained separately and never count as phone latency proof. The temporary
account-free simulator was removed; no further physical phone operations ran.
