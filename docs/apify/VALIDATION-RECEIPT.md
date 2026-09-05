# BF-CER-v1.0 Apify validation receipt — 2026-09-04

**PRIVATE VALIDATION PASS / PUBLIC AND PAID ACTIVATION NO-GO.**

Machine source of truth: [provider-receipt.json](provider-receipt.json).
This document reconciles the completed originating-task validation; no external
calls or code changes were made to prepare this update. Earlier approval blocks
and the initial build failure are preserved in
[VALIDATION-HISTORY.md](VALIDATION-HISTORY.md), not active blockers.

## Ownership, source, and scope

- Agency task **190**, registered Beanfit repo, gated and last recorded queued.
  No claim is made that the Hub task was marked done.
- Private Actor **X457S8llVBn25IEYB**, `isPublic=false`, pricing not activated.
  The originating task reports the pricing field null.
- Version **1.0** exactly matched the **27** validated source files, as reported
  by the originating task. All **21** Python-source manifest hashes were
  previously verified locally and were unchanged by the schema correction.
- Candidate: `/Users/stephenkall/beans/worktrees/beanfit-bf-cer-apify`, branch
  `codex/bf-cer-apify`, based on `e8ec4507b89b3b0471894515e1f80794eb92664f`.
  The original Beanfit estimator/catalog and primary checkout were preserved.
- One private Actor, two builds, three synthetic runs. `EXCLUDED_TEST` throughout.
  Cash spend initiated **$0**; billing events **0**; no pricing, publication,
  customer activity, plan upgrade, push, merge, tag or release.

## Build evidence

| Build | ID | Result | Observed usage |
|---|---|---|---:|
| 1.0.1 | `czIituktgMxxpVkAx` | FAILED before container execution: missing `use_case.description` | $0.00022222222222222223 |
| 1.0.2 | `GQ41FN91r9DraYJiC` | SUCCEEDED; 0.0232 CU | $0.00464 |

The correction added schema metadata only. See
[SCHEMA-CORRECTION.md](SCHEMA-CORRECTION.md). Replacement build **1.0.2** clears
the formerly pending provider schema/build check.

## Private run evidence

All runs used build **1.0.2**. Every run deleted raw INPUT and emitted zero
billing events. Both successful runs validated reports and hashes; the second
also matched the first run's stable evidence.

| Run | ID | Outcome | Observed usage |
|---|---|---|---:|
| 1 | `ggaGTBeaz3zGUoqO3` | SUCCEEDED; report hashes verified | $0.0005246888679729567 |
| 2 | `DoY2OWQcJBsYFr1mo` | SUCCEEDED; report hashes verified; stable evidence equals run 1 | $0.0005257844238347478 |
| 3 | `CNXdhRtsWIXak8F8p` | Expected platform failure, exit 1; OUTPUT NEEDS_REVIEW; no report artifacts | $0.0005707610443499354 |

The third run is a **passing negative-control test**, not a successful report:
the platform failed with exit 1 as expected while OUTPUT said `NEEDS_REVIEW`.
Both raw INPUT and report artifacts were absent. This validates refusal to
fulfill an unsupported context request; it does not implement manual fulfillment
or paid cross-run deduplication.

## Costs and final account meter

- Final read at **2026-09-04T23:07:07Z**: FREE, non-paying; monthly credits and
  usage ceiling **$5** each.
- Account usage meter: **$0.005870139998886321**.
- Remaining free credits: **$4.994129860001114**.
- Sum of observed operation usage, including both builds and all three runs:
  **$0.006483456558379863**.

The operation sum and account meter differ. Preserve both observations: they
are different provider readings and do not establish final invoice or settlement
reconciliation. Do not replace one with the other, invent an adjustment, or
claim the difference has been explained. All observed use consumed free
credits; it is not cash spend or revenue. These figures are a timestamped
snapshot taken before the separately authorized cleanup below.

## Synthetic-resource cleanup

At **2026-09-04T23:14:58Z**, after explicit owner authorization, the **3 key-value
stores, 3 datasets, and 3 request queues** belonging to the three synthetic runs
were deleted. All nine resources were then verified to return not found. The
private Actor, successful build, all three historical run records, and local
receipts were separately verified retained. This cleanup is irreversible; the
synthetic output copies formerly held by Apify storage are not recoverable from
those deleted resources.

## Local validation and remaining work

Local schema correction: **72 deterministic tests PASS**, central isolated QA
**2/2 PASS**. Earlier local container checks **4/4 PASS**, with networking
disabled and 128 MB memory. Source manifest and metadata regressions passed.
These checks were not rerun for this documentation-only reconciliation.

Remaining gates:

1. Manual fulfillment for nonempty constraints and context above 16384 tokens;
   the automatic subset must not be described as full frozen-contract coverage.
2. Timestamped live catalog validation before customer delivery; estimates and
   catalog tags do not establish a measured benchmark or current tag liveness.
3. Charging implementation, durable cross-run/order/correction deduplication,
   unknown-charge reconciliation, reimbursement and payout controls. None was
   validated by the zero-billing synthetic runs.
4. Explicit authorization for public publication and the single proposed
   `report-generated` **USD 12** event. Current pricing remains inactive.
5. Dedicated central E2E manifest registration before any future merge; current
   E2E tests are discovered by the registered unit command. No merge occurred.

[DEPLOYMENT-GATE.md](DEPLOYMENT-GATE.md) records completed and remaining gates.
