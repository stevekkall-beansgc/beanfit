# BF-CER activation: independent synthetic QA

Reviewed 2026-09-05 in the isolated `beanfit-first-dollar` worktree. Scope is
`src/beanfit/activation.py`, exercised by `tests/test_activation.py`. No provider
calls, account changes, customer inputs, or charges were made during this review.

## Result

**26 tests passed** with:

```sh
PYTHONPATH=src python3 -m unittest tests.test_activation -v
```

This is local integration evidence, not a Stripe sandbox payment receipt or
production readiness approval. The fake provider deliberately models stable
idempotency so tests can distinguish repeated transport calls from duplicate
provider objects. Report production uses the real `apify_actor.run` and
`generate_report` in an in-memory store, including the Actor's own output hashes
and deletion of the synthetic `INPUT` record.

## Findings and corrections verified

The initial ledger serialized a report object with compact JSON before checking
its digest, while the Actor hashes sorted JSON with default separators. An actual
Actor-generated object therefore failed fulfillment despite an intact report.
The implementation now verifies the Actor digest over parsed JSON, then stores
canonical bytes with a separate local manifest. The real-Actor delivery test
protects this integration boundary.

During review, the implementation also added persisted intent identity across
dates, payment event alias tracking, bounded retry state, and persisted refund
identity with read-only status reconciliation. Tests cover these final behaviors.

## Coverage

| Boundary | Verified behavior |
| --- | --- |
| Intake | Only explicit synthetic intent; unsupported fields, Intel profiles, oversized context and free-text constraints fail before an order or checkout exists. |
| Identity | Stable acceptance across restart and UTC date change; conflicting input or bearer token fails; raw bearer token is absent from the order row. |
| Checkout | Ambiguous outcome survives restart; same order identity retries within the provider key window; unknown outcomes at 23 hours block a new request. Two simultaneous calls produce one modeled provider session and one checkout ledger event. |
| Payment | Fresh session read binds mode, completion, paid state, amount, currency, offer metadata, order, and payment intent. Live events and unbound sessions fail. Duplicate event IDs and distinct aliases cause one paid effect; an alias cannot be reused for another order. Untrusted event customer text is not retained. |
| Production | Real Actor output succeeds. Tampered Markdown, structured report, accepted input, or success marker never publishes. Wrong fulfillment profile never reaches production. Failure after artifact insertion rolls back both artifact and ready state. |
| Delivery | Wrong or missing bearer token fails without marking delivery. Artifact integrity is checked again on download. Repeat download after process restart returns the same artifact without a second delivery event. |
| Retry | One retry is allowed after 15 minutes, including restart; early retry does not invoke production. A second failure freezes fulfillment and remains refundable. Exception detail is absent from the audit. |
| Correction | One correction is included through exactly seven days after delivery; later or backward-clock requests fail. Correction temporarily blocks download, creates revision 1, resets its production attempt allowance, and creates no new checkout or paid effect. |
| Refund | Ambiguous and pending outcomes disable delivery. Known refund IDs use status reads even after 23 hours. Unknown refund IDs stop new refund requests after 23 hours. Failed/canceled/action-required results stay frozen. Successful repeat refund calls create no new request. A mismatched payment intent fails. |
| Concurrency | Separate SQLite connections simultaneously process payment, generation and download; one paid effect, one generation, one artifact and one delivery event result. |
| Audit | Ledger event updates and deletes are rejected. The hash chain verifies through delivery/refund; every economic delta and all recognized/eligible revenue remain zero with `EXCLUDED_TEST` classification. |

## Limits and release judgment

The harness has no deployed customer intake, public delivery endpoint, remote
Actor execution, scheduler, or customer authorization layer. `payment` requires
its caller to verify the Stripe webhook signature; signature transport tests
belong to `tests/test_stripe_test.py`. Correction and refund methods are internal
trusted operations and must not become unauthenticated public routes.

The injected producer is expressly local and deterministic. SQLite rollback can
recover local generation; it does not prove exactly-once remote Actor runs. A
remote adapter needs persisted run intent, reconciliation of unknown outcomes,
and cost limits before activation. Tests also do not prove real Stripe
idempotency, asynchronous settlement, provider refund behavior, hosted checkout,
or fulfillment SLA scheduling. Provider receipts and the operating runbook must
establish those claims separately.

The tests are a **pass for the stated synthetic-only ledger scope**. They are not
authorization to publish the Actor, enable paid pricing, accept customer data,
contact prospects, or create live charges. The integrating owner must run the
repository's complete required QA gate after all workstream changes are combined.

## Provider CLI boundary follow-up

Added 10 tests in `tests/test_activation_provider.py`. Together with the 26
activation and 15 Stripe transport tests, **51 tests passed**:

```sh
PYTHONPATH=src python3 -m unittest tests.test_activation tests.test_activation_provider tests.test_stripe_test -v
```

Two additional defects were identified and corrected by the integrating owner:

1. The CLI accepted any valid signed event for a bound order in its ledger, then
   printed the fixed provider-test order's status. It now passes that expected
   order into payment processing, and the fresh provider binding is checked
   before any payment mutation. A valid signed event belonging to another bound
   order is rejected without changing that order.
2. A private state directory did not make preexisting files private or prevent
   report symlink writes. The CLI now rejects symlinks, hard links, nonregular
   files and broad file permissions for its database, sidecars and reports. The
   report writer opens without following symlinks and checks the actual file
   descriptor before truncating. Tests preserve an external synthetic target
   unchanged under symlink, hardlink and broad-permission cases.

The fixes landed before the first executable reproducer finished. To avoid
misstating that chronology, `qa-logs/provider-boundary-regression-receipt.json`
records a separate mutation check: restoring the two exact unsafe behaviors in
memory causes both regression tests to fail. No runtime source was changed for
that proof, and it is explicitly not a historical checkout test run.

Additional checks establish that missing tokens, missing/test-invalid API keys,
missing or invalid webhook authentication, altered signed bytes, signed live
events and oversized webhook payloads all fail before provider calls. Repository
state paths are rejected. Ledger connections close on token and acceptance
failures. A complete CLI path uses the real Stripe transport with an in-memory
HTTP opener, authenticates raw webhook bytes, processes one payment effect,
generates actual reports, writes mode-0600 files in a mode-0700 directory, then
reconciles a pending refund using GET without another refund POST. Audit output
contains no supplied credential and recognizes zero revenue.

Ledger tests now also check the explicit checkout/refund intent events and
continuity between each event's prior state and its predecessor's resulting
state. These changes add evidence for ambiguous outbound requests without
changing the exclusion of synthetic activity from economic results.
