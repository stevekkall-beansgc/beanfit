# October 23 no-phone text review

This is source/Mac/simulator validation. Every receipt remains `qualified: false`.
No phone was installed, launched or used. Physical quality, memory, five-minute
heat, real warning behavior and Instruments checks remain required on the exact
final native builds. The earlier unexplained Pocket physical-quality interruption
has not been reproduced or proven resolved by these simulator results.

## Simulator and host fixes

The earlier iOS 27 editor could remain focused after a background/foreground
transition and leave XCTest waiting for UI idleness. The shared view now manages
focus explicitly, offers Done typing, and clears focus on deactivation. The
regression leaves the keyboard open while backgrounding, then requires model
unload, reload and actual dismissal.

The actual beanSprout host exposed a separate bug: UIKit-hosted SwiftUI did not
inherit the App scenePhase background event. Its Write action remained enabled
because the model was still loaded. The shared view now observes application
lifecycle notifications as well as scene state. Background handling is idempotent,
blocks new work until foreground activation, retires the draft and unloads.

The owned simulator runner uses a prebuilt xctestrun, fresh account-free simulator,
bounded subprocess group and finalized xcresult counts. It requires both tests,
no skips and both unload receipts before reporting success; it removes only its
own simulator. Older driver timeouts/failed host tests remain in private outputs
and are not counted as passes. Large raw Xcode bundles stay private.

Both Pocket and beanSprout passed the complete real typing/copy/edit/background/
reopen/reload/dismiss test on iOS 26.5 and iOS 27 simulators. These are four host/
runtime combinations, not four physical phones. Sanitized reports and separate
lifecycle receipts are retained here. Background unload times were under two
seconds in each simulator; no phone latency or thermal claim follows. Final
local build identities cover the same nine shared source files, both tested
simulator executables and both generic iPhone executables. Device signatures
verify using existing profiles; no profile was renewed or phone accessed. The
record is `build-identity.json`, not a store-distribution or provisioning claim.

## Text pipeline and honest evidence

Qwen3.5 2B remains the comparison candidate for short English summaries/rewrites.
The revised task asks for minimal copy edits and no added feelings, explanations,
offers or commitments. Replies still use the deterministic own-facts formatter,
with no model and no authority from the incoming message.

A bounded cleanup removes simple reported editorial model-control annotations
and explicit “Draft to polish/edit/rewrite” labels. Ambiguous “Draft:” status is
retained or restored so a tentative proposal does not become a commitment.
It conservatively retains mixed factual clauses, ordinary
business quotations and explicitly requested literal/security text. It also
normalizes a few sentence-level causal transitions when the source contains no
recognized causal wording. This is not semantic relevance classification, a
fact checker or a prompt-injection security boundary. Unrecognized forms may
remain and every draft needs human review. The UI flags normalized text for
comparison with the original; raw model text and edit counts remain in synthetic
reports so the cleanup is not represented as a model-only improvement.

The original 36-case acceptance packet is unchanged. The first 12-case holdout
was frozen in commit 0669c1b; its first run exposed two annotation variants and
an unsupported causal link. It was then promoted to a regression packet. The
next eight cases were frozen in b95103d, and the final four in 2ebfba2 before the
last transition cleanup. A later adversarial status guard deliberately preserves
ambiguous Draft status; it was not tuned on the four final cases. Earlier holdouts are not claimed as unseen final tests.
All were authored/reviewed by the implementing agent, not independent users.

Final results: original 36/36 phrase screens; first regression 11/12; second
regression 6/8; final holdout 4/4 (57/60 total). The unchanged hs24 screen misses the valid
paraphrase “photo not be published”; it stays false. Authored review records
60/60 factual and 57/60 task/clarity, zero critical failures. s12 retains all
facts but uses four sentences instead of the requested maximum three. hw03 and
hw21 retain ambiguous original Draft status; their frozen style expectations
ask to omit it and remain failed. Preserving tentative status takes priority.
These style failures remain visible. Passing this authored sample does not
establish open-ended quality, multilingual support or physical qualification.

The raw Qwen2 model still echoes some instructions. The combined pipeline's
improvement includes explicit non-model transformations and the reply formatter.
The pipeline before the final Draft-status guard was also run with LFM1.2B
and Qwen0.8B on the original packet, which has no ambiguous leading Draft label. Their phrase
scores (35/36 and 36/36) conceal issues: LFM's date-conflict wording is ambiguous
and rewrites remain poorly polished; Qwen0.8B omits drop-test observations in s12
and adds an unsupported relation to the winner. Smaller-file lexical success is
not a qualified writing result. Their raw comparisons are retained. This is a
bounded comparison, not exhaustive prompt optimization or proof of a universal
best model.

## Suggestions and release preparation

The canonical catalog and CLI/native/companion snapshots put Qwen2 first for
comparison and hold the earlier failed LFM1.2B text configuration. A larger memory
allowance or passing self-reported receipt cannot bypass that failure gate.
Existing shopping failures remain held. All candidates keep unknown memory fit,
no automatic selection and no production qualification. New live registry checks
verify pinned component metadata; they do not execute or qualify the other models.

The companion now binds the exact reviewed CLI package at aab9540. Only the
catalog JSON differs from its prior v0.8.0 caller profile; independent content
expectations and all Mac ranking/launch arithmetic are unchanged. Full local
HTTP/CLI/D1 tests pass without relaxing that exact-source check.

The web fixes have a separate current-main candidate in Hub task 1315, excluding
the native baseline. On final fetch, token renewal was already merged in V2
PR #27 and its exact token bytes agree; only inventory freshness remains in the
web implementation diff. The candidates also incorporate the newer CI updates. The native text candidate in task 1314 still
needs phone acceptance. No branch was pushed, no tag/Release was created and no
cloud deployment or migration occurred during this work. Voice/search remain
deferred.

Authored adversarial review: tests cover preserved literal quotations, business
printing instructions, tentative Draft status, decimal amounts, mixed factual clauses and supplied causal
language. The cleanup's scope and fallibility are explicit; no semantic correctness
or security guarantee is inferred from its patterns. Normal drafts are not exported.
Readability review: 3/4; current instructions and evidence limits are explicit,
with detailed build commands kept in the developer guide. Independent publication
review and exact-candidate CI remain required before release.
