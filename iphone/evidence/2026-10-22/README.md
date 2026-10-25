# Local text integration — physical iPhone checkpoint, October 22

Pocket and the actual beanSprout containing app embed the same BeanFit text
adapter and view. Both development candidates run Summarize, Rewrite and Draft
a reply locally on iPhone 14 Pro Max (iPhone15,3), iOS 26.6.1. Voice notes and
search were deferred. No public native release is claimed.

Model: LFM2.5-1.2B-Instruct-Q4_K_M.gguf, 730,895,168 bytes, SHA256
`b1b3de114215d9507409a662a501a631095a479a419584e8a2ded6304b19b4f5`.
Runtime: llama.cpp `2145525a4081d66ff1a87cf43ef809f95a85ac0c`, CPU four
threads, context 2,048 tokens, draft output at most 192 tokens, 90-second native
deadline. There is no remote model or automatic model download.

The accompanying reports retain the frozen synthetic inputs/outputs, basic
lexical checks and sampled process measurements. Six probes repeat twice, then
the same model actions used by Load, Write draft and Stop exercise cancellation,
stale-output retirement and unloading. The synthetic runner changes model fields
and invokes actions; it is not a gesture-driven test of typing or clipboard use.
Screens were visually reviewed separately using synthetic data only.

| Development app | Final functional checks | Memory warnings | Model unloaded |
| --- | --- | --- | --- |
| Pocket | 13/13 | 0 | yes |
| beanSprout | 13/13 | 0 | yes |

Drafts took approximately 2–3 seconds in this packet. Exact per-run ranges and
source hashes are in [summary.json](summary.json). Raw receipts are
[Pocket](pocket-phone-report.json) and [beanSprout](beansprout-phone-report.json),
with their corresponding measurements files. BeanFit QA passed docs, 252 unit
tests including Swift contracts, and offline E2Es. Host preparation/isolation and
the 14 existing beanSprout Swift package tests passed. Its complete product gate
still fails the two existing freshness checks described below.

The tiny packet is not representative writing-quality acceptance. For example,
the date summary preserves facts but returns two sentences despite the prompt
asking for one. No model comparison, production winner or RAM budget follows
from these receipts. `qualified` remains false. Process-footprint samples omit
some mapped/system allocations and may miss peaks. Zero warnings during this
packet cannot establish low-memory reliability or thermal endurance.

Earlier attempts remain in the local session artifact directory rather than
being replaced by successful results. Two early scripted runs cancelled during
programmatic field updates. Equal-value edit guards and read-only bindings for
the explicit synthetic run resolved the harness interaction; normal interactive
fields remain editable when idle. Subsequent adapter-only passes were retained
before the final tests were strengthened to use the product model's actions.
After repeated runs, a final Pocket attempt was correctly refused by its thermal
load guard. That hold is retained, and the guard was not weakened for a retry.
The final Pocket build passed after cooldown. Retained failed/held reports sit
beside the final receipts; no attempt was removed to present a clean history.

Review was performed by the implementing agent. Remaining gates include unseen
representative quality, manual interaction, background/foreground and low-memory
stress, complete memory accounting, thermal/battery endurance, model/license
review, and durable distribution. beanSprout also retains its existing web-token
margin and inventory-freshness failures. Its local baseline snapshot contains
unmerged work; it must not be published as part of a text-only change.

The local session directory is
`outputs/beanfit-text-integration-20261022` under the Bean workspace; it contains
build logs, prepared host/source manifests, synthetic screens, retained attempts,
QA logs and gate provenance. Neither signing credentials nor device identifiers
are included in these committed evidence files.
