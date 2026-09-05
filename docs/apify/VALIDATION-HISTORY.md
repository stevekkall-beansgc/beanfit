# Historical private-validation stages

Superseded by VALIDATION-RECEIPT.md and DEPLOYMENT-GATE.md. These dated stages
retain earlier approval blocks and first-build failure; they are not current
authorization requests or current deployment status.

# BF-CER-v1.0 Apify candidate receipt — 2026-09-04

Current disposition: PRIVATE ACTOR CREATED; FIRST BUILD FAILED; LOCAL SCHEMA CORRECTION READY. Public and paid NO-GO. See latest appended receipt.

## Ownership and changes

Registry: `/Users/stephenkall/beans/platform/agency/repos.json` → Beanfit at
`~/beans/products/beanfit`. Isolated candidate:
`~/beans/worktrees/beanfit-bf-cer-apify`, branch `codex/bf-cer-apify`, base
`e8ec4507b89b3b0471894515e1f80794eb92664f`. Primary Beanfit was clean and is
unchanged. Original engine/catalog/hardware/emission files are unchanged.
No commit, push, merge, tag, release, publication, schedule or monetization.

Added:
- `src/beanfit/report.py`: validated inputs, report JSON/Markdown, versioned
  evidence, original fit/estimate reuse, latency ordering, catalog commands,
  policy and explicit NEEDS_REVIEW for unsupported but valid requests.
- `src/beanfit/apify_actor.py`: restricted storage adapter, deleted raw input,
  bounded reads, safe rejection, duplicate-key rejection, checked source
  manifest, fixed output keys and hash-verified same-run replay, cost metrics.
- `tests/test_report.py`, `tests/test_apify_actor.py`, `tests/test_apify_e2e.py`.
- `.actor/`, `.dockerignore`: secret-free build, input schema and source manifest.
- `scripts/apify_package.py`, `apify_preflight.py`, `apify_container_smoke.py`,
  `check_apify_qa.py`: preparation and validation only; no deployment script.
- `docs/apify.md`, `docs/apify/`: sample artifacts, proposed pricing, prepared
  private create payload, deployment gate, this receipt, and QA logs.

## Validation observed

- Complete deterministic unittest discovery: **68 tests PASS**.
- Central QA original Beanfit baseline: docs/unit **2/2 PASS**.
- Same central QA runner with only Beanfit's path redirected to isolated
  candidate: docs/unit **2/2 PASS**; logs under `docs/apify/qa-logs/`.
- Local Docker image built from already-cached Python 3.12 slim with build
  networking disabled: **PASS**, image short ID `6fe0ab6147fd`.
- Real container entrypoint: **4/4 PASS** (success, identical retry, manual
  review, duplicate-key rejection); runtime networking disabled, read-only
  filesystem, 128 MB, 0.5 CPU. Storage was synthetic in-memory transport.
- Exact source manifest verified both locally and in the container.
- `git diff --check`: PASS. Original unit suite emits a pre-existing unclosed
  fixture-file ResourceWarning in `tests/test_register.py`; tests still pass.
- Synthetic sample reproduces DeepSeek Coder V2 16B top coding choice on M4 Pro
  48 GiB, 36 GiB budget, 11.15 GiB calculation total, 20.8 estimated tok/s with
  ±25% band. No measured model benchmark or live catalog availability claim.

Independent review identified duplicate-key overwrite and ambiguous handling
of contract-valid unsupported requests. Both were fixed with regression tests:
all duplicate keys reject, and unsupported context/workload constraints have
an explicit NEEDS_REVIEW outcome. Final independent re-review confirmed both dispositions, 68 passing tests, all 21 source manifest hashes, and sample Markdown/JSON consistency. Full contract fulfillment remains gated rather than falsely claimed complete.

## Apify and cost observations

BeanLaunch retrieved the existing bootstrap token in memory for **GET only**:
account, limits, current monthly usage. Token and raw response bodies were not
retained. Plan FREE/enabled, account not paying, free monthly credits $5,
monthly usage limit $5, current usage $0.000004458986222743988. This existing
platform usage is not this Actor's run cost.

Actor create/build/run calls: **0**. Public/payout/plan writes: **0**.
Private Actor ID/build ID/run ID: **none**. Observed Apify per-run cost: **not
available**. Cash spend initiated: **$0**. Billing events: **0**. Revenue: **$0**.
Local CU instrumentation is an estimate and billed cost remains null.

Automatic approval review rejected gated Agency task registration, including
a retry supported by a read of the source task. Its reason was that delegated
history/source-task output did not establish trusted direct-user authorization
for a persistent task write. No Hub task was created; private deployment was
not attempted because the required control remained uncleared. This is an
approval-control blocker, not a failed Apify credential or exhausted credit.

## Remaining gates

1. Direct owner authorization to register the gated Agency task and resume the
   exact private procedure in DEPLOYMENT-GATE.md. No workaround transport.
2. Actual private build, restricted storage/deletion, rejection and repeat-run
   receipts; observed platform cost and budget reconciliation.
3. Full-contract manual-review fulfillment path for nonempty constraints and
   contexts above 16384; the automatic subset must not be represented as full
   frozen-input support. Memory below 8 or above 4096 GiB rejects explicitly.
4. Current catalog-tag validation before first customer delivery; inherited
   illustrative memory/quality assumptions and unpinned generic tag quantization
   remain disclosed. Never claim model benchmarking or tag liveness from these
   local tests.
5. Paid event implementation, durable cross-run order/correction deduplication,
   ambiguous-charge reconciliation, and provider reimbursement/payout evidence.
   The current build contains no charge endpoint; pricing is prepared only.
6. Explicit final authorization to publish this single Actor and activate one
   `report-generated` event at exactly **USD 12**, once per successful report,
   no start/per-item/additional charge. Any required paid plan or cash spend
   needs separate authority. Proposed JSON is not applied.

New-flow E2E is currently discovered by the registered unit command. A dedicated
central E2E manifest registration remains an integration requirement before a
future merge; no unrelated QA registry was modified in this candidate.

## Resumed authorization check — 2026-09-04T22:42:47.167052+00:00

The originating task relayed explicit owner authorization to register exactly
one gated Agency task and run bounded private tests using existing free credits.
One registration attempt was made. Automatic approval review again rejected it
because delegated/tool-output authorization was not a direct trusted user
message in this task. No alternate transport or deployment was attempted.

Fresh GET-only Apify proof: FREE/enabled, not paying, $5 monthly credits and
$5 usage cap; current platform usage $0.000006524287164211274. All 21 source
files still match the prepared manifest. No source change or test rerun was
needed. Actor create/build/run calls remain zero; per-run cost unobserved.

Required unblock: the owner must place the authorization directly in this
Codex task, rather than relay it through another task. Suggested exact text:
“Register one gated Agency task for BF-CER and run the prepared bounded private
Apify tests using existing free credits only; no public publication or paid
activation.” The approval system remains authoritative; this records the
request, not a bypass or guarantee of approval.

## Governance verified; upload approval blocked — 2026-09-04T22:45:40.469065+00:00

- Agency task 190 was independently read and verified: registered repo beanfit,
  branch codex/bf-cer-apify, queued, requires_approval=true, exact private/free-
  credit scope. The earlier task-registration blocker is cleared. No runner
  was dispatched or second Agency task created.
- Fresh authenticated GET-only preflight: FREE/enabled, not paying, $5 monthly
  credits, $5 usage limit, current platform usage $0.000008590333163738252.
  Exhaustive Actor-list check found no existing BF-CER Actor.
- Prepared create request was rejected by automatic approval review before
  execution. Reason: Actor creation would upload private Beanfit source to
  Apify and create a persistent resource, and the reviewer did not recognize
  trusted authorization for that source upload/destination.
- Source uploaded: no. Actor create/build/run calls: zero. No private Actor
  exists; observed per-run cost remains unavailable. No paid activation, public
  publication, cash spend, upgrade or cleanup was needed.
- Required authorization is now specifically the source upload and creation:
  “Upload the prepared BF-CER source package to my Apify account, create the
  private Actor, and run the bounded tests using existing free credits only;
  no public publication, paid activation or cash spend.” The approval system
  must accept this directly in the executing task; no workaround is authorized.
- Non-secret machine receipt: docs/apify/provider-receipt.json. The helper
  scripts/apify_private_validation.py implements only inspection and guarded
  creation; the create stage did not execute.

## Local schema correction — 2026-09-04T22:56:52.663242+00:00

The originating task reports private Actor X457S8llVBn25IEYB created and
verified isPublic=false. Build czIituktgMxxpVkAx (1.0.1) failed schema validation
before container execution: missing use_case.description. Reported free-credit
build cost was $0.00022222222222222223; no report-run cost exists. This
supersedes the earlier no-Actor state; this correction made no provider calls.

Added missing descriptions and nested runtime-property metadata locally.
Exactly one packaged source file changes: .actor/input_schema.json; 26 other
file records and all 21 Python-source manifest hashes are unchanged. Full suite
72 PASS; isolated QA 2/2 PASS; metadata regressions and manifest verification
PASS. Prepared docs/apify/private-version-update-payload.json for existing
version1.0; preserve and verify all remote files before replacing only the schema.
No source upload/rebuild/run/price/publication action occurred here. Revised
authorization and remote validation remain with the originating task.
Detailed local receipt: docs/apify/SCHEMA-CORRECTION.md.


# Historical deployment procedure and gates

# BF-CER-v1.0 private deployment gate

Current status: private Actor created by originating task; first build failed input-schema validation. Local correction prepared; revised build authorization pending. No public or paid activation. Earlier entries below are historical.

The canonical registry resolves Beanfit to `~/beans/products/beanfit`.
Implementation is isolated in `~/beans/worktrees/beanfit-bf-cer-apify`, branch
`codex/bf-cer-apify`, based on `e8ec4507b89b3b0471894515e1f80794eb92664f`.
The report uses that existing estimator/catalog, with the new adapter identified
separately by a verified source-file manifest. No new offer is introduced.

## Control evidence

2026-09-04 read-only BeanLaunch/Apify check: plan FREE, plan enabled,
`isPaying=false`, monthly credits USD 5, monthly usage limit USD 5,
current platform usage USD 0.000004458986222743988. Account response and token
were discarded. This is usage credit consumption, not a cash balance.
Payout readiness remains owner-attested in the portfolio's onboarding record.
Token expiry and long-term least-privilege scope are not independently attested.

Agency registration was attempted but automatic approval review rejected the
persistent task write because it did not accept delegated/source-task history
as direct user authorization. Source-task verification did not clear that
review. No Hub task was created; do not bypass the rejection with another
transport. The repository requires a gated Hub task, so private deployment is
held at that control. Direct owner authorization to register the task and resume
the bounded private build/test procedure is needed.

## Exact private procedure after the control clears

1. Run the owning repository unit suite and isolated QA entrypoint, inspect
   independent review findings, generate `.actor/build-manifest.json`, and
   prepare the source payload. Never send `.git`, local storage, environment
   files, credentials, unrelated repo content, or personal data.
2. Use `scripts/apify_preflight.py` for fresh GET-only controls. Stop unless
   FREE, not paying, enabled, the usage limit is at most free credits, and at
   least USD 0.25 of existing credits remains. Do not modify plan or caps.
3. Inspect the Actor list for the exact proposed name
   `beanfit-compatibility-evidence-report`. Stop on an existing name until its
   ownership/content is reconciled; never overwrite another Actor blindly.
4. Create a private Actor through `POST /v2/actors`: `isPublic=false`, one
   `SOURCE_FILES` version `1.0`, build tag `private-test`, timeout 60 seconds,
   memory 128 MB, restart-on-error false, limited permissions, standby off.
   Do not set pricing, public categories/distribution, schedules, or webhooks.
   Do not put the bootstrap token into source or Actor environment variables.
   Apify supplies its own scoped runtime token for the run's storage access.
5. Read the created Actor back and require `isPublic=false`. Build version
   `1.0` once, record build ID/status and usage, and abort if still running at
   120 seconds. Poll at bounded intervals. Do not retry a create/build POST
   with an unknown outcome; reconcile its identity first.
6. Recheck free-credit controls. At most three sequential synthetic runs:
   normal Apple M4 Pro/48 GiB coding input, the identical input again to compare
   stable evidence fields, and an unsupported context request (>16384) to prove
   rejection (if schema accepts it; schema rejection itself incurs no run).
   Pin the successful build number. Each run uses `memory=128`, `timeout=60`,
   `restartOnError=false`, `maxTotalChargeUsd=0.01`. No customer inputs or real
   credentials in fixtures. No charge events. Abort on any unexpected public
   state, fee model, costs, or missing privacy control.
7. Fetch terminal run state and `usageTotalUsd`, `usageUsd`, and
   `stats.computeUnits`; validate OUTPUT, REPORT.json and REPORT.md,
   verify INPUT is absent, and verify storage access is restricted. Preserve
   only synthetic outputs and non-secret IDs/cost receipts. Stop after the
   planned runs even if credits remain. Do not call a failed test successful.
8. Reconcile account usage after runs; distinguish build cost, run cost,
   storage costs and provisional platform usage. Keep all tests EXCLUDED_TEST
   with zero promotion-eligible revenue. No catalog downloads or model runs
   are part of this test. Current catalog validation needs its own bounded
   public registry check before a delivered customer report can be certified.

The account free-credit ceiling is the cash-spend safeguard. The run charge
limit is an additional provider cap; it does not cap build costs or establish
atomic billing. The 120-second build abort and finite run count bound this test;
network loss during an abort is a control failure requiring reconciliation.

## Paid configuration and final go-live action

`pricing-proposal.json` defines exactly one `report-generated` event at USD 12,
primary and one-time per run. No start fee, per-item charge, subscription,
additional offer, or tiered price. This file is a proposal, not an API payload:
Apify supplies pricing dates and margin fields when applying the Console's
Publishing configuration. Never send the proposal's metadata to the API.

After all private tests, payment/reimbursement controls, cross-run transaction
idempotency and authorization pass, the exact go-live action is: deploy a
reviewed charging implementation which emits one `report-generated` event only
after successful report delivery, apply this single USD 12 pay-per-event price,
and publish this Actor publicly. A platform one-time event caps each run only;
it cannot stop a retry/new-run or correction from charging again. Therefore
paid activation additionally needs durable transaction/correction deduplication
and unknown-charge reconciliation. The current build has no charging endpoint.
It cannot be monetized merely by flipping a setting.

Any required Creator/paid-plan upgrade or cash charge needs separate explicit
authorization; do not upgrade as part of publication. Owner self-tests never
prove paid demand. Portfolio correction/refund SLA and support promises remain
those in OFFER-CONTRACT.md.

Official references reviewed 2026-09-04:
- [Actor creation](https://docs.apify.com/api/v2/actors-post)
- [Build endpoint](https://docs.apify.com/api/v2/actors-builds-post)
- [Run controls](https://docs.apify.com/api/v2/actors-runs-post)
- [Pricing event schema](https://docs.apify.com/api/v2/actor-put)
- [Monetization](https://docs.apify.com/actors/publishing/monetize)

## Resumed authorization check — 2026-09-04T22:42:47.167052+00:00

The originating task relayed explicit owner authorization to register exactly
one gated Agency task and run bounded private tests using existing free credits.
One registration attempt was made. Automatic approval review again rejected it
because delegated/tool-output authorization was not a direct trusted user
message in this task. No alternate transport or deployment was attempted.

Fresh GET-only Apify proof: FREE/enabled, not paying, $5 monthly credits and
$5 usage cap; current platform usage $0.000006524287164211274. All 21 source
files still match the prepared manifest. No source change or test rerun was
needed. Actor create/build/run calls remain zero; per-run cost unobserved.

Required unblock: the owner must place the authorization directly in this
Codex task, rather than relay it through another task. Suggested exact text:
“Register one gated Agency task for BF-CER and run the prepared bounded private
Apify tests using existing free credits only; no public publication or paid
activation.” The approval system remains authoritative; this records the
request, not a bypass or guarantee of approval.

## Governance verified; upload approval blocked — 2026-09-04T22:45:40.469065+00:00

- Agency task 190 was independently read and verified: registered repo beanfit,
  branch codex/bf-cer-apify, queued, requires_approval=true, exact private/free-
  credit scope. The earlier task-registration blocker is cleared. No runner
  was dispatched or second Agency task created.
- Fresh authenticated GET-only preflight: FREE/enabled, not paying, $5 monthly
  credits, $5 usage limit, current platform usage $0.000008590333163738252.
  Exhaustive Actor-list check found no existing BF-CER Actor.
- Prepared create request was rejected by automatic approval review before
  execution. Reason: Actor creation would upload private Beanfit source to
  Apify and create a persistent resource, and the reviewer did not recognize
  trusted authorization for that source upload/destination.
- Source uploaded: no. Actor create/build/run calls: zero. No private Actor
  exists; observed per-run cost remains unavailable. No paid activation, public
  publication, cash spend, upgrade or cleanup was needed.
- Required authorization is now specifically the source upload and creation:
  “Upload the prepared BF-CER source package to my Apify account, create the
  private Actor, and run the bounded tests using existing free credits only;
  no public publication, paid activation or cash spend.” The approval system
  must accept this directly in the executing task; no workaround is authorized.
- Non-secret machine receipt: docs/apify/provider-receipt.json. The helper
  scripts/apify_private_validation.py implements only inspection and guarded
  creation; the create stage did not execute.

## Local schema correction — 2026-09-04T22:56:52.663242+00:00

The originating task reports private Actor X457S8llVBn25IEYB created and
verified isPublic=false. Build czIituktgMxxpVkAx (1.0.1) failed schema validation
before container execution: missing use_case.description. Reported free-credit
build cost was $0.00022222222222222223; no report-run cost exists. This
supersedes the earlier no-Actor state; this correction made no provider calls.

Added missing descriptions and nested runtime-property metadata locally.
Exactly one packaged source file changes: .actor/input_schema.json; 26 other
file records and all 21 Python-source manifest hashes are unchanged. Full suite
72 PASS; isolated QA 2/2 PASS; metadata regressions and manifest verification
PASS. Prepared docs/apify/private-version-update-payload.json for existing
version1.0; preserve and verify all remote files before replacing only the schema.
No source upload/rebuild/run/price/publication action occurred here. Revised
authorization and remote validation remain with the originating task.
Detailed local receipt: docs/apify/SCHEMA-CORRECTION.md.
