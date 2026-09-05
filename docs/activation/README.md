# BF-CER first-dollar activation package

2026-09-05 · Agency task **192** · based on Beanfit **v0.2.0**
(`4ec003e`; exact SHA in historical receipts). **Synthetic software release;
live activation NO-GO.** The v0.3.0 release integrates the reviewed local
candidate; Venture 06 financial records remain unchanged.

## What is ready to inspect

- `src/beanfit/activation.py`: SQLite order claims, immutable intent identity,
  append-only zero-cash test events, payment binding, event aliases, atomic
  report publication, authenticated local retrieval, retries, one correction,
  and refund reconciliation. Orders remain `TEST`; no live recognition method.
- `src/beanfit/stripe_test.py`: fixed USD 12 card Checkout Session, exact
  raw-body webhook signature verification, test-only reads/refunds and stable
  request keys. Live keys/events are rejected. A known pending refund is
  polled by ID; it is never declared refunded merely because a request returned.
- `src/beanfit/apify_fulfillment.py`: prepared private Actor bridge with durable
  run intents, one unresolved remote run at a time, unknown-start freeze,
  immutable build binding, restricted output checks and local artifact caching.
  It passes synthetic tests; actual preflight stops before starting a run. See
  [Apify bridge](APIFY-BRIDGE.md) for the unresolved provider fields.
- `scripts/activation_demo.py`: reproducible offline payment-to-report-to-
  correction-to-refund flow using a labeled Stripe fixture and the real local
  Actor/report engine. `offline-receipt.json` is evidence of that scope only.
- `scripts/activation_provider.py`: prepared, manual synthetic-only integration
  driver for runtime-injected Stripe test access. It never loads customer
  profiles or installs a public listener. It stores private local state outside
  the repo and prints no credentials, input text, payer details or bearer token.
- [Distribution](DISTRIBUTION.md): five anonymized prospective-buyer profiles; the named roster remains local, unsent
  copy, eligibility/permission checks, operator time budget, funnel and stop rules.
- [Economics](ECONOMICS.md): unchanged $12 offer, per-rail costs, acquisition
  break-even, refund losses and settlement/recognition limits.
- [Independent ledger QA](QA-REVIEW.md), central `qa-logs/`, and
  `provider-receipt.json`: what passed and what remains unproved.

## Intent and architecture decisions

**One payment rail per order.** Direct Stripe is the proposed shortest route;
keep the private Actor noncharging. The released Apify publication/PPE proposal
is retained unchanged and unapplied. A Stripe customer must never also emit a
$12 Apify billing event. This is a reviewed candidate direction, not an amendment
or activation of the frozen portfolio record.

**Prevalidate before collecting payment.** The report engine rejects unsupported
inputs before creating an order. Context above 16384 and nonempty constraints
remain `NEEDS_REVIEW`; they are not silently treated as fulfilled. The full
contract accepts a wider scope than automation supports. An authorized operator
must either prove the existing engine can satisfy a redacted review request or
decline before checkout; after payment, apply the original correction/refund
promise. Full-contract automated coverage is not claimed. No extra model
benchmarking, consultancy, subscription or new price is introduced.

**Hosted Checkout Sessions replace the old test Payment Link proposal in this
candidate.** A server-bound single order/session allows durable deduplication and
input gating. Fixed amount 1200 cents, USD, quantity one, card only, no promotion
codes, automatic tax, subscription, optional products or customer profile in
metadata. The earlier product/price/Payment Link proposal remains historical;
no provider object was created here. Future live tax/account decisions remain
with the account owner and cannot be inferred from a synthetic configuration.

**Separate operational state from money.** `PAID`, `READY`, `RETRY`, and
`REFUND_PENDING` are technical projections. Every canonical audit event retains
`payer_class=TEST`, zero real monetary deltas and exclusion notes. Stored audit
hashes detect mutation but do not replace independent backups or tamper-proof
external storage. SQLite triggers prohibit ordinary event edits/deletes.

**Private delivery.** Report bytes remain in a private SQLite artifact store.
Retrieval requires the original random bearer token; only its digest is stored.
No email, public link, arbitrary URL upload, raw input or card data enters the
ledger. An authenticated retrieval records delivery once, but it cannot prove
the recipient saved the bytes. Production needs an authenticated HTTPS delivery
surface, transport receipt, retention/deletion proof and authorization before
customer data. The local driver copies synthetic attachments to a private temp
directory only. Never expose this internal library directly as customer routes.

## Replay, correction and incident procedures

| Condition | Deterministic response |
|---|---|
| Same accepted intent after restart/date change | Same order; input/token conflict rejected. Token is never recovered or rotated by a retry. |
| Checkout POST times out | Preserve `CHECKOUT_UNKNOWN`; same key only within 23 hours. After that, reconcile through Stripe; never mint a new order/key to retry. |
| Duplicate or reordered payment event | Verify raw signature, retrieve session, require test mode/complete/paid/USD1200/exact metadata/session binding. Reserve event IDs and aliases; one paid effect. Unpaid/unknown orders cannot fulfill. |
| Local generation fails | Keep artifacts unpublished; one retry after 15 minutes. Second failure stops fulfillment and stays refundable. |
| Hash mismatch / missing Actor success marker | Fail closed, no report delivered. Never use partial artifacts. |
| Correction within seven calendar days | Same order and payment, revision 1, no extra checkout. One business day from complete corrected input; second correction rejected. |
| Refund request uncertain | `REFUND_PENDING` disables delivery; same request identity within 23 hours. Known refund ID uses GET status even after the request window. Unknown ID requires reconciliation, not another POST. |
| Refund pending/failed/action required | Remain frozen; successful provider result alone advances `REFUNDED`. Unknown/suspicious references fail closed. |
| SLA missed | Buyer chooses full refund or a newly agreed delivery time. This candidate has no running SLA scheduler or customer communications. |
| Dispute, privacy issue, unreconciled money | Stop new intake, route the runbook's V06-OPS/V06-FREEZE and owner-only account actions. No automatic live mutations exist here. |

One-business-day timing needs the operating calendar, a staffed operator queue,
and monitored dispatch after activation. UTC timestamps and the seven-day
correction check are implemented; a generic 24-hour timer is not represented as
a business-day SLA. No recurrence was installed.

## Reproduce local verification

From the isolated Beanfit worktree:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
python3 scripts/activation_demo.py
python3 scripts/check_activation_qa.py
```

The last command runs the actual central QA runner against this Beanfit candidate
and the canonical QA-kit registration under `~/beans/platform/qa-kit`. It
overrides only the target checkout path and writes fresh logs outside the
repository. The manifest registers the owned activation E2E. Override
`BF_CER_QA_ROOT` if the QA checkout moves. The demo prints its result by default;
use `--receipt /private/tmp/bfcer-synthetic-receipt.json` to save new evidence.

## Complete the provider test after authentication

1. Sign into the staged Stripe test Dashboard. No credential or verification
   code belongs in chat, repository, receipt, or command-line arguments. An API
   test key must be supplied through the existing runtime secret mechanism;
   the available vault currently has no matching Stripe key. Dashboard access
   by itself does not authorize creating a new credential.
2. For the prepared driver, inject `STRIPE_TEST_KEY` and a stable, random
   `BF_CER_TEST_DOWNLOAD_TOKEN` (at least 32 characters) into its process.
   Keep private state in a mode-0700 temporary directory outside this repo.
3. Run `activation_provider.py checkout --state-dir <private directory>` once;
   inspect the actual test Checkout Session, amount, mode and object references.
   Complete only Stripe's documented synthetic test payment flow. Never use
   a real card, live-mode session or customer email.
4. Obtain the actual signed test event through an approved test listener;
   pass raw bytes on stdin with runtime `BF_CER_WEBHOOK_SECRET` and
   `BF_CER_STRIPE_SIGNATURE` to the `event` action. The driver verifies the
   signature and retrieves Stripe's current session before crediting test state.
   Do not manufacture an event and call it provider proof.
5. Run `fulfill`, then `download`; verify both synthetic attachments and replay
   behavior. Execute `refund` and poll the same known refund until success;
   reconcile provider objects, signatures, costs and test classification.
6. Record only safe IDs/statuses/hashes in a new dated receipt. Retain the
   blocked historical receipt. Test success never proves live fees, payout,
   customer demand or unrelated revenue.

This is a concrete manual test procedure, not a deployed autonomous service.

## Shortest safe path to an unrelated paid transaction

1. Clear Stripe authentication/runtime test access and collect a genuine test
   checkout/payment/refund receipt through the prepared control path.
2. Resolve the Apify pricing/default-access schema proof before remote
   rehearsal; the prepared bridge currently stops before any run. The existing
   released private build remains unchanged. Then finish the customer boundary: authorized supported-input intake, authenticated
   private delivery and deletion, SLA dispatch/alert routes, catalog freshness,
   operator correction/decline path, and actual fee/refund/payout reconciliation.
   Record paid-order and unrelated-payer controls in a separately reviewed live
   implementation; this test-only module deliberately has no live switch.
3. Present one final, exact activation decision: **USD 12 direct Stripe, private
   noncharging Actor, the supported BF-CER contract path, bounded five-prospect
   permitted campaign, customer-spec intake, delivery/correction/refund scope,
   zero advertising spend and no recurring founder sales work.** Do not publish
   Apify or apply its PPE pricing as a side effect.
4. After explicit authorization, execute the finite opt-in distribution plan.
   Trace the first unrelated order through delivery, fees, available balance
   and payout evidence. Count recognition only once and subtract observed
   acquisition/fulfillment costs. One sale with negative fully loaded contribution
   does not pass C1; two other explicit purchase intents are also required.

The original preparation performed no live charge, customer input, prospect
contact, public Actor, paid pricing, spending, release, push or merge. Later
authority covers the Git release and test-only provider work, as recorded below;
live activation remains separate because provider/customer boundaries are unproven.

## Source and catalog evidence

All 17 public catalog registry requests returned HTTP 200 in the dated
`catalog-live-receipt.json`. This establishes link liveness at observation time,
not quantization, model quality, a measured benchmark or future availability.
`source-receipt.json` pins the released Beanfit base and the exact Venture 06
contract/runbook/setup documents used. The v0.3.0 runtime reports version `0.3.0`. Historical v0.2.0 receipts remain
unchanged. The demo identifies its executing Git HEAD and a source hash map,
with the original v0.2.0 baseline recorded separately; it needs no historical
tag in a shallow checkout.

The local activation modules are an overlay outside the existing remote build.
The inherited `.actor/build-manifest.json` and packaged private payloads describe
the earlier validated source, not this added controller code. Do not deploy this
worktree using the old manifest: any future Actor rebuild requires regenerating
and verifying its complete source manifest and a separate reviewed deployment.
The first-dollar design can retain immutable remote build 1.0.2 without uploading
the controller. Nothing in this package updates that build or its source.

## v0.3.0 Git release scope

The owner approved Git integration/publication and test-only provider actions.
This software release grants no customer, paid Actor, live payment or outreach
authority. The canonical GitHub repository is public, so exact prospect handles
and source links stay in the original local candidate `1418c2a`; the public
release integrates its reviewed implementation with an anonymized plan.

The manual provider driver is POSIX-only (macOS/Linux) because it relies on
POSIX private file modes and `O_NOFOLLOW`. It fails before opening state or
calling a provider on Windows. The core ledger and test transports remain
cross-platform and continue to run in the Windows CI matrix.

Release review fixed Windows platform handling, shallow-checkout provenance,
and test output destinations. Historical provider receipts in this directory
are explicitly dated and are not new provider evidence for v0.3.0.
