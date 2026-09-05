# BF-CER economics and first-dollar decision

2026-09-05. USD throughout. Planning assumptions; no live fee, payout, buyer,
or revenue has been observed. Existing free credits are an execution allowance,
not a reason to erase economic cost. No cash spend is initiated by this package.

| Per delivered order | Frozen contract | Direct domestic-card illustration | Apify PPE illustration |
|---|---:|---:|---:|
| Price | 12.00 | 12.00 | 12.00 |
| Payment/platform share | 0.72 reserve | 0.65 rounded | 2.40 |
| Agent/runtime | 0.40 | 0.40 | 0.40 |
| Electricity | 0.05 | 0.05 | 0.05 |
| Support/refund reserve | 1.20 | 1.20 | 1.20 |
| Catalog maintenance | 0.75 | 0.75 | 0.75 |
| Depreciation | 0.15 | 0.15 | 0.15 |
| Operator exceptions (8 min × $15/h) | 2.00 | 2.00 | 2.00 |
| Founder exceptions (about 2 min × $50/h) | 1.67 | 1.67 | 1.67 |
| Fully loaded cost before acquisition | **6.94** | **6.87** | **8.62** |
| Economic contribution before acquisition | **5.06** | **5.13** | **3.38** |

Stripe publishes 2.9% + $0.30 for standard US domestic-card processing;
`12 × .029 + .30 = .648`, about $0.65. Account rates and actual balance
transaction control. Payment Links/Checkout included with standard Payments;
other methods, international cards, currency conversion, disputes and optional
products can add costs. [Stripe pricing](https://stripe.com/us/pricing)

Apify PPE documents `0.8 × revenue − platform costs`. Its 20% share replaces the
payment reserve; do not combine Stripe and Apify customer charges for one order.
The runtime budget above must be reconciled against actual compute/storage
charges: add any platform amount outside it, never count one compute bill twice.
Apify free-plan buyer activity does not establish paid-plan developer profit.
[Apify PPE](https://docs.apify.com/actors/publishing/monetize/pay-per-event)

The released successful runs used about $0.000525 each; build usage was about
$0.00464 after an earlier $0.000222 failed build. Those are historical snapshots,
not a production price or an all-in report cost. The 2026-09-05 free account
meter is $0.005954244946632121 against a $5 cap; arithmetic remaining credit is
$4.994045755053368. No new run/build was needed for this local activation test.
The prior operation sum and account meter were unequal; no invented settlement
adjustment is made. See the existing `docs/apify/provider-receipt.json` and this
package's `provider-receipt.json`.

## Acquisition changes the first-sale result

The finite five-prospect campaign budgets at most 45 operator minutes:
20 for fresh eligibility/permission checks, 15 for five short authorized
invitations, 10 for measurement. These are **incremental acquisition minutes**;
the per-order eight-minute reserve above is fulfillment exception time.
At $15/hour the campaign costs $11.25 economically, even if cash spend is zero.

| Paid orders from five verified exposures | Acquisition per order | Contract contribution after acquisition |
|---:|---:|---:|
| 1 | 11.25 | **−6.19** |
| 2 | 5.625 | **−0.565** |
| 3 | 3.75 | **1.31** |
| 5 | 2.25 | **2.81** |

These are scenarios, not assumed conversion rates. A lone unrelated sale can
prove someone paid but may fail C1's nonnegative fully loaded contribution gate.
Do not conceal research, messaging or founder time to pass it. For one order to
cover the frozen $5.06 contribution, incremental acquisition must stay at or
below about **20.24 operator minutes** (and lower if other costs rise). Prefer
an authorized opt-in placement and self-service purchase, then measure actual
attention. Zero continuing founder labor is a design target, not observed proof.
No founder sales calls or routine bespoke report writing is in the plan.

A full refund leaves gross revenue zero; original Stripe processing fees are
generally retained. As an illustration, replacing the $1.20 expected
support/refund reserve with the actual full reversal leaves $5.67 of other
sunk costs per refunded order under the standard-card assumptions, before extra
refund handling or acquisition. Failed/pending refunds are not successful
reversals. Refund status and cash reconciliation must remain separate.
[Stripe refunds](https://docs.stripe.com/refunds)

## Recognition and controls

- Every local/provider test remains `TEST` / `EXCLUDED_TEST`, all real monetary
  deltas zero. Nominal 1200-cent API fields are test assertions, not cash.
- Live checkout authorization does not establish `UNRELATED`. Require an
  auditable privacy-safe payer reference and the runbook's relationship check;
  insufficient evidence stays `AMBIGUOUS`.
- A future paid event is pipeline only until actual available balance or
  receiving-account evidence reconciles. Recognize the first WITHDRAWABLE or
  WITHDRAWN event once. This synthetic-only ledger cannot recognize live money.
- Apify's $20 PayPal/Wise / $100 other minimum payout means one $12 sale cannot
  alone be withdrawable there. Direct Stripe is therefore the proposed first
  sale rail. Account-specific timing/eligibility remains unverified.
  [Apify payouts](https://docs.apify.com/actors/publishing/monetize/monthly-payouts)
- Pause after two negative fully loaded orders. C1 also needs two **other**
  explicit purchase-intent confirmations. C2 needs three unrelated sales,
  including a repeat payer and at least $20 eligible net. Tests satisfy none.
