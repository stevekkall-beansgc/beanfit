# October 6 outcome — development candidate, release blocked

Baseline: `0146ed9c535b771d22946c73fba58511268683f3`, clean canonical BeanFit
checkout. Isolated branch: `codex/beanfit-pocket-20261006`. No changes to Picks,
personalization, Beanshop, iMessage or Commons; no publication or weights redistribution.
The approval-first bundle was explicitly approved in this task on October 6.
Operating agreement read: `BEANA-CONTINUATION-2026-10-06-r3`, BeanLabs source
`4b38a41f689d42ab030e5093e43e34c3e04be01f`. Registry/release standard read.

## Implemented capability

Pocket's real shopping boundary uses `https://beanshop.top/mcp`, anonymous and
stateless, US/USD. Reviewed filters become `search_products`; exact returned
variant/options/seller must pass `review_variant` within the retained cents ceiling
before a merchant URL appears. No generated offer identifiers/URLs, no caching,
no live result/image export, no checkout/persistence. Redirects are rejected.
Inference uses the existing embedded llama.cpp/LocalInferenceClient; no remote
inference. The selected public flow uses manual filters/bounded deterministic
parser. Model suggestions remain disabled unless explicitly enabled experimentally.

## Actual evidence

| Check | Outcome |
| --- | --- |
| Native Swift contracts | Passed, including reviewer abstention regressions, cents ceilings, malformed results and exact review identity |
| Repository Python suite | 237 tests passed |
| Owned offline E2E and activation demo | Passed, synthetic, zero provider calls |
| Manifest-owned QA | Docs/unit/E2E 3/3 passed on isolated source |
| Simulator and development device builds | Passed |
| Owned simulator runtime E2E | 10/10 passed; historical sample/runtime flow only |
| Independent FAVA source review | No unresolved actionable source findings; independently reran native contracts and diff check |
| Development phone installation | Passed, existing Apple team; renewed profile expires October 13 |
| Physical phone launch | Passed after Steve trusted/opened the renewed profile; intermittent Mac device-tunnel failures retained |
| Initial native live attempt | Launch timed out, no qualification file recovered; outcome unknown, no retry |
| Repeated physical complete flow / background UI / restart | Unrun |
| Complete resident/dirty/mapped whole-stack memory | Unrun; sampled app footprint is insufficient |
| Matched 30-minute thermal/battery baseline | Unrun |
| Exact-commit CI / durable distribution / Steve release acceptance | Unrun, no release authorized |

The first added regression failed on `purchase coffee`; the bounded baseline was
fixed and the failure log retained. A sandboxed simulator build failed because
Swift/Xcode services were inaccessible; the existing approved environment build
subsequently passed. Device reads also experienced locked-device/tunnel errors.
None of those attempts are erased or counted as successes.

## Unchanged model gate results (simulator only)

First eight requests supplied independently by FAVA before output inspection;
12 additional frozen regression requests. Raw outputs and failures are retained
in the task's evidence directory, separate from any live catalog results.

| Candidate | Exact semantic cases | No-model baseline | Extraction p95 | Cancellation | Sampled app peak |
| --- | --- | --- | --- | --- | --- |
| Liquid350M | 2/20 passed, 18 failed | 20/20 passed | 0.451 s | 1.02 ms | 283.6 MiB |
| Qwen08 | 5/20 passed, 15 failed | 20/20 passed | 1.649 s | 2.70 ms | 738.1 MiB |

Both fail frozen correction/budget/abstention gates. Neither qualifies. The
sampled footprint includes simulator/runtime effects and omits mapped/system
accounting; it is not an iPhone RAM requirement. Do not spend 30 minutes on battery
qualification for a model already rejected by semantic gates. No gates were relaxed.
The bounded baseline is the simplest useful candidate; its complete real-phone/live-product
flow still needs proof before a release claim.

## Physical phone follow-up after profile trust

The complete Liquid report from source `71e7569841df56ea2131c69e774bac12cf630b8b`
was recovered after intermittent tunnel failures. Actual iPhone14ProMax
(iPhone15,3), iOS26.6.1: model **2/20**, unchanged no-model parser **20/20**;
extraction p95 **2.055 seconds**, verify/load **0.458 seconds**, cancellation
**1.624 milliseconds**. Sampled app peak **109,200,520 bytes**; this is process-only,
not complete memory qualification. Unmatched battery readings are not a battery
pass. Liquid is rejected on semantics; longer battery qualification is unwarranted.

The test runner now atomically checkpoints each completed synthetic probe and
marks incomplete/interrupted runs. This retains no live offers or merchant URLs.
FAVA reviewed this narrow fix with no findings; device and simulator builds and
native contracts passed. Simulator execution retained all20 completed probes.
Qwen was successfully launched on the physical phone, but retrieval remained
intermittent. A missing or partial report is not a pass.

## Sources and next checkpoint

OpenClaw's [llama.cpp provider](https://docs.openclaw.ai/plugins/llama-cpp)
already offers hardware-aware setup, pinned runtime/model verification and tool
verification; broad desktop selector growth has substantial overlap. Its
[iOS app](https://docs.openclaw.ai/platforms/ios) requires a Gateway on another
device. That is not standalone on-device inference qualification.

License text was read before cached model comparison: LiquidAI's exact GGUF
revision `657e078c94084481950a2d555a941481f715536b` uses LFM Open License v1.0;
commercial use has a revenue limitation and redistribution has notice obligations.
Local research testing only; redistribution/commercial release is not approved.
The [Qwen upstream card](https://huggingface.co/Qwen/Qwen3.5-0.8B) and cached
Unsloth metadata declare Apache-2.0; exact quantized file hash remains checked on
load. Pinned llama.cpp is `2145525a4081d66ff1a87cf43ef809f95a85ac0c`.

Next: retrieve the Qwen physical report over a stable unlocked/USB connection.
Reconcile the uncertain live attempt before any new live
proof; coordinate shared 24/hour capacity. Qualify the no-model real shopping flow,
then complete applicable lifecycle/resources/durable-distribution gates and obtain
Steve acceptance. Signing/tests/reviewer approval alone are not release acceptance.
