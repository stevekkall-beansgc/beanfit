# BF-CER-v1.0 deployment and activation gates

**Private validation complete. Public publication and paid activation remain
NO-GO.** The bounded private procedure is finished; this document grants no
additional build/run, cleanup, publication, pricing or spending authority.

Source of truth: [provider-receipt.json](provider-receipt.json).
Full results/costs: [VALIDATION-RECEIPT.md](VALIDATION-RECEIPT.md).
Earlier authorization failures and the original procedure are retained in
[VALIDATION-HISTORY.md](VALIDATION-HISTORY.md) as history only.

## Completed private controls

- Agency task **190** verified; last recorded queued and gated.
- Actor **X457S8llVBn25IEYB** created privately, `isPublic=false`; pricing inactive
  (null according to the originating task).
- Corrected version **1.0** matched the 27 validated source files. Build
  **GQ41FN91r9DraYJiC / 1.0.2 SUCCEEDED** after the recorded initial schema failure.
- Three bounded synthetic runs completed: two successful report/hash checks,
  stable evidence equal across those runs, and expected exit-1 `NEEDS_REVIEW`
  rejection with no report artifacts. INPUT was deleted in all three; zero
  billing events. Classification **EXCLUDED_TEST**.
- Final FREE/non-paying account snapshot: $5 credit cap, meter
  **$0.005870139998886321**, remaining credits **$4.994129860001114**.
  Observed operation sum including failed build: **$0.006483456558379863**.
  These unequal readings remain separately recorded, not falsely reconciled.
- No cash spend, public publication, paid activation, plan upgrade or customer
  activity. No push, merge, tag or release.

## Cleanup complete

After separate explicit owner authorization, the **3 key-value stores, 3
datasets and 3 request queues** belonging to the synthetic runs were deleted at
**2026-09-04T23:14:58Z**. All nine were verified not found afterward. The private
Actor, successful build, three historical run records and local receipts were
verified retained. The deleted Apify storage artifacts are not recoverable.

## Remaining customer and paid-activation gates

- Complete the manual-review fulfillment path for contract-valid constraints
  and longer context requests; `NEEDS_REVIEW` is not fulfilled delivery.
- Verify live catalog tags before customer delivery and retain timestamped
  evidence. Existing estimates and generic runtime tags retain their disclosed
  limitations; synthetic report generation does not benchmark a model.
- Implement and validate one post-delivery charge with durable transaction and
  correction deduplication across new run IDs, plus ambiguous-charge recovery.
  Same-run artifact replay and equal report evidence across runs do not prove
  billing idempotency. Current build contains no charging endpoint.
- Confirm provider reimbursement, fees and payout controls; the account meter
  and per-operation usage sum are snapshots, not a settled invoice.
- Obtain explicit owner authorization for public publication and paid
  activation. Any required plan upgrade or cash spend requires separate authority.

## Exact go-live action, after those gates

Deploy a reviewed charging implementation; apply exactly one **PAY_PER_EVENT**
`report-generated` event at **USD 12**, primary and one-time per run; then publish
this same Actor publicly. No start fee, per-item charge, additional offer,
subscription or tiered price. The proposal in `pricing-proposal.json` remains
unapplied; it is not a directly executable API payload. One-time-per-run pricing
alone cannot prevent a new run or correction from charging a second time.

The current evidence supports private technical validation only. Owner tests
are EXCLUDED_TEST and cannot establish unrelated demand or recognized revenue.

Official references used in the earlier implementation review (2026-09-04):
- [Actor creation](https://docs.apify.com/api/v2/actors-post)
- [Build controls](https://docs.apify.com/api/v2/actors-builds-post)
- [Run controls](https://docs.apify.com/api/v2/actors-runs-post)
- [Pricing schema](https://docs.apify.com/api/v2/actor-put)

No external references were fetched for this documentation reconciliation.
