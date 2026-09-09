# Launch readiness preparation — 2026-09-09

**Live launch remains NO-GO. Version remains 0.3.0.** This local preparation
addresses the evidence gaps in the v0.3.0 RESULT dated September 5. No new
account observations, payment receipts, Apify runs, customer data, or payout
proof are claimed. Historical receipts and the pinned Actor build are unchanged.

## Safe local commands

From this worktree, run the supported-input preview with synthetic data:

```sh
python3 scripts/launch_preflight.py intake <<'JSON'
{"device_chip":"Apple M4 Pro","memory_gib":48,"use_case":"coding","operating_system":"macOS 15.6 arm64"}
JSON
python3 scripts/launch_preflight.py review <<'JSON'
{}
JSON
```

The preview uses the same authoritative validator as the report engine. It
returns `SUPPORTED`, `NEEDS_REVIEW`, or `INVALID_INPUT`, with no order, Checkout,
storage, or review dispatch. Context above 16384 and nonempty constraints require
review. Do not pipe customer submissions into this preparation tool.

`review` inventories the missing evidence. It accepts a bounded JSON object on
stdin, rejects duplicate keys, nonfinite numbers and input over 256 KiB, and
outputs only fixed diagnostic codes. It neither reads environment credentials
nor opens provider connections. Redirects and provider requests are absent.
Exit codes: **0** supported intake preview, **1** malformed input, **2** blocked
intake or launch NO-GO. A review always exits 2, even with `snapshot_checks=PASS`.

## Snapshot contract

A local snapshot is an **unverified assertion**, never a provider receipt or
authorization. For review, use this structure with minimized, authorized
observations; values below are placeholders, not evidence:

```json
{
  "schema_version": 1,
  "apify": {
    "observed_at": "ISO-8601 timestamp with timezone",
    "expected_owner_id": "expected Apify owner ID",
    "actor": {},
    "run": {},
    "store": {}
  },
  "stripe": {
    "observed_at": "ISO-8601 timestamp with timezone",
    "expected_account_id": "expected Stripe account ID",
    "account": {}
  }
}
```

Apify objects are the `data` objects from Actor GET, run GET, and store GET.
Stripe `account` is the Accounts v1 object, without a `data` wrapper. Include
only the fields listed below. Keep source observations private and outside Git;
never export raw account responses, bank details, addresses, email, secret keys,
proxy credentials, report contents, or request headers into a receipt. Unknown
input fields are discarded by the summary; this is not a raw-response sanitizer
for storing or sharing the original input. Shell redirection to a private local
file is optional; the tool writes no files itself.

Each provider has its own observation timestamp. Older than one hour, future,
missing or timezone-free timestamps block the snapshot checks. The runtime bridge
still requires its own fresh preflight within 60 seconds of the start attempt.
The snapshot cannot be supplied as a bridge proof. No CLI option bypasses gates.

## Apify evidence surfaces

| Surface | Local rule | Remaining provider action |
| --- | --- | --- |
| Actor pricing | Distinguish missing, null, empty, nonempty and invalid `pricingInfos`; a non-null `pricingInfo` blocks. Only explicit null/empty list with absent/null current pricing passes the existing predicate. | Read owned Actor monetization state and reconcile current API fields with authoritative semantics. Missing fields remain unknown. |
| Pricing records | Any nonempty list blocks, including `pricingModel=FREE` or future records. | A narrowly reviewed adapter change needs documented effective-date/model semantics; this preparation does not interpret them. |
| Actor ownership | Exact Actor `X457S8llVBn25IEYB`, expected owner and `isPublic=false`. | Collect current owned Actor observation. |
| Run and store | Exact run Actor, owner, build ID `GQ41FN91r9DraYJiC`, build number `1.0.2`; run's `defaultKeyValueStoreId` equals store ID and owner. | Retrieve the same historical run/store pair using read-only access. |
| General access | Explicit `RESTRICTED` only. Missing, null, unknown, public, and `FOLLOW_USER_SETTING` block. | Establish effective default access and privacy before any new run; history does not establish future defaults. |
| Credit/build/run safety | Always remains an external gate in snapshot review. | Re-run original enabled FREE/nonpaying, credit/cap/usage, zero-active-jobs and successful immutable build gates immediately before separately authorized rehearsal. |

`ApifyTestClient.preflight(include_evidence=True)` now adds minimized pricing
field diagnostics to its four existing authenticated GETs. It starts no run.
Default bridge calls preserve the prior proof shape and pricing predicate.
Malformed nested plan/limit containers now yield missing proof and a controlled
gate failure. This session did not invoke an authenticated preflight.

## Stripe intake and payout evidence

Use the correct account's Accounts v1 object. Review checks exact expected
account identity, `object=account`, and strict boolean `charges_enabled`,
`payouts_enabled`, and `details_submitted`. Integers or string booleans are unknown.
For both `requirements` and `future_requirements`, include `currently_due`,
`past_due`, `pending_verification`, `errors`, `eventually_due`, and
`disabled_reason`. Missing containers/fields are unknown. Only explicit empty
arrays and a null disabled reason clear this conservative local review.
Future/eventual requirements trigger owner review even if Stripe presently
permits charges. This is Beanfit's launch review policy, not a claim that Stripe
has disabled that account. Do not invent hidden or unavailable fields.

The result shows only enabled/disabled/unknown and empty/present/unknown states;
it does not echo requirement names or account identifiers. Accounts v1 evidence
here establishes neither live mode nor receipt of money. There is no live-key
reader, account updater, payout creator, Checkout creator or credential loader
in this tool. Test account configuration and successful test payments cannot
substitute for live account, fees, balance or bank evidence.

## Concrete launch sequence and stop conditions

1. **Review local preparation.** Run the tests below, inspect the committed diff,
   and retain NO-GO output. Propose the exact branch integration/push/release
   action separately. Do not rebuild the Actor using its old source manifest.
2. **Resolve read-only provider access.** Obtain existing authorized Stripe test
   runtime access and Apify monetization/default-sharing evidence. Bind the
   correct account, Actor, historical run and store. Resolve missing/inherited
   fields through authoritative provider evidence; stop if proof is unavailable.
3. **Authorize a bounded provider rehearsal separately.** After fresh original
   gates pass, use the prepared synthetic driver for one USD 12 test Checkout,
   actual signed test event, private synthetic fulfillment, authenticated
   download, correction and full refund. Reconcile unknown starts/refunds
   without retrying new identities. Check input deletion, output hashes, store
   cleanup, build/run usage and remaining credit. Record genuine safe receipts.
   No test payment or remote run is authorized by this preparation report.
4. **Implement and verify the customer boundary.** Supported-input HTTPS intake
   must validate before Checkout; unsupported requests need a staffed redacted
   decline/review path. Prove authenticated delivery, deletion/retention, replay
   resistance, one-business-day dispatch, alerts, correction and refund handling.
   Review a separate live ledger/payment implementation; the test ledger has
   no live switch. Confirm catalog freshness and the exact frozen offer terms.
5. **Owner reviews live account and payout readiness.** Confirm account identity,
   mode, requirements, charge/payout availability, payout destination/currency
   and schedule in authorized private account surfaces. Decide tax treatment,
   receipt/support settings, observed fee/refund economics and a refund reserve.
   Destination details stay outside Git. Flags alone are insufficient evidence.
6. **Present the exact launch decision.** USD 12 direct Stripe; private
   noncharging Actor; supported contract scope; bounded five-prospect permitted
   campaign; zero ad spend; delivery/correction/refund coverage and stop rules.
   Obtain explicit live intake and outreach authorization before executing it.
7. **Reconcile the first authorized unrelated sale.** Bind the order to payment,
   report/delivery, charge and balance-transaction IDs; record gross, actual fee,
   refunds/disputes, currency, net and available date. Follow settlement into
   the payout and bank receipt; stop recognition on mismatch or unknown status.
   Do not initiate payouts as a verification shortcut. Deduplicate recognition,
   subtract observed acquisition/fulfillment costs, and apply the original C1
   requirement including two other explicit purchase intents. Test revenue is zero.

## Verification

```sh
PYTHONPATH=src python3 -m unittest tests.test_launch_readiness tests.test_apify_fulfillment
PYTHONPATH=src python3 -m unittest discover -s tests
python3 scripts/activation_demo.py
python3 scripts/check_activation_qa.py
```

The existing centrally registered activation demo now exercises the real preview
CLI for supported intake, manual review, and launch NO-GO before its offline
payment/report/correction/refund flow. This extends the existing QA entrypoint;
no other repository's manifest needs editing. Set `TMPDIR` to a private directory
inside this worktree and `PYTHONDONTWRITEBYTECODE=1` when QA must keep all writes
inside it. Fresh receipts belong in ignored `.launch-qa/`, not historical files.

## Official schema references checked 2026-09-09

- [Apify Actor metadata](https://docs.apify.com/api/v2/actor-get) describes optional
  pricing records. The reviewed schema does not establish that omission means
  inactive pricing; retain the conservative existing rule.
- [Apify run metadata](https://docs.apify.com/api/v2/actor-run-get) and
  [store metadata](https://docs.apify.com/api/v2/key-value-store-get) expose general
  access. Inherited access remains unresolved without effective-default evidence.
- [Stripe Accounts v1](https://docs.stripe.com/api/accounts/object) documents
  charge/payout flags and current/future requirements. These are configuration
  observations, not settlement receipts.
