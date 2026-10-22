# Text acceptance packet v1 — frozen before execution, October 22

Scope: short English summaries, rewrites and reply drafts in Pocket and the
beanSprout containing app on iPhone 14 Pro Max / iOS 26.6.1. Human review and
explicit copy remain required. Other phones, multilingual use, autonomous
actions, voice and search are outside this acceptance decision.

`TextQualityPacket.json` freezes 36 synthetic cases, twelve per task, before the
first run. Preserve every raw result. Automated required/forbidden phrases are
screens; an authored review must assess factuality, omissions, task fulfillment
and clarity against each written expectation. The implementing agent's review
is identified as such and is not represented as independent user research.

Acceptance: no invented or reversed dates, amounts, availability, commitments or
actions; no successful instruction override by quoted content. At least 35/36
cases must preserve the expected facts and at least 33/36 must satisfy task and
clarity requirements. No empty/truncated/runtime-error outputs. Formatting defects
are separate from critical factual failures. Run the complete frozen packet again
after prompt/runtime fixes; never edit expectations to excuse a model failure.

Resource acceptance on each containing app: sampled whole-process resident bytes
(including resident mapped pages) below 1.5 GiB, and the conservative sum of peak
charged process footprint plus the entire GGUF file below 1.5 GiB. Report both,
never substitute footprint for RAM. Capture internal/external/compressed bytes,
OS-reported available process memory, before/after unload and five load/unload
cycles. After warm-up, unloaded resident growth must stay within 64 MiB. Require
at least 384 MiB process headroom beyond model bytes before load. Instruments VM
Tracker is a separate cross-check; profiling overhead is not a latency result.
The CPU-only text stack uses no AI system service, audio service or GPU backend;
unrelated OS allocations are outside the app's budget and must not be called zero.

Responsiveness: p95 short drafts <=10 seconds, individual longer cases <=20
seconds; Stop and background-triggered unloading <=2 seconds. Exercise edits,
blank and oversized input, copy/dismissal, background/reopen, warning-handler
injection and thermal-state policy injection. Label injected events separately
from actual OS memory/thermal notifications. Do not create artificial system-wide
memory exhaustion on the user's phone.

Thermal acceptance: five minutes of short drafts at a 15-second start cadence
(20 requests) per app, with no serious/critical OS thermal state or real memory
warning and all drafts completing within the latency gate. Record actual thermal
states throughout, not just start/end. A real serious/critical state is a failed
sustained-use run even if the protective stop works. Keep failed runs and cool
before retrying a changed candidate. The product must refuse hot starts and
cancel/unload if serious/critical heat develops during work. Prefer two CPU
threads and a visible recovery state over hiding the condition.

These bounded tests can support a reviewed text pilot on the tested phone.
They do not establish battery endurance, comfort for every environment, worst-case
OS memory-pressure reliability, or production fit on all iPhone 14+ variants.
Public distribution still requires product/release gates and existing native
baseline review; a local test receipt alone is not release approval.
