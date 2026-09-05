# Prepared synthetic Apify fulfillment bridge

Status: **prepared and fake-provider tested; real provider gate blocked**.
No run was started by this activation work. Read-only findings below were
reported by the root task on 2026-09-05. They are observations, not a successful
fulfillment rehearsal or permission to change account settings.

The bridge in `src/beanfit/apify_fulfillment.py` exposes
`step(ledger, order_id, profile, client)` and `ApifyTestClient(token)`.
It accepts synthetic ledger orders only. The only prepared write is a bounded
run start for private Actor `X457S8llVBn25IEYB`, build number `1.0.2`, whose
returned build ID must equal `GQ41FN91r9DraYJiC`. No build, publication, pricing,
access-setting, cleanup, restart, or live-payment method is exposed.

## Provider evidence and unresolved fields

| Evidence | Required by bridge | Read-only finding / disposition |
| --- | --- | --- |
| Actor pricing | Explicit `pricingInfos` empty/null and no active `pricingInfo` | Both fields absent in current owned private Actor response. Gate returns `APIFY_PRIVATE_UNPRICED_REQUIRED`; absence is not proof of inactive pricing. |
| Run access | `generalAccess == RESTRICTED` | Historical run reports `FOLLOW_USER_SETTING`. Inherited access has not been resolved. |
| Storage access | Matching store ID/owner and explicit `generalAccess == RESTRICTED` | Ownership alone does not establish access policy. Missing, public, and inherited values fail closed. |
| User default access | An authoritative explanation/evidence is needed to interpret inherited access | User GET exposed no readable default-access field. No safe inference is made. |
| Run options | Memory 128 MiB, timeout 60 seconds, build `1.0.2`, `restartOnError=false`, `forcePermissionLevel=LIMITED_PERMISSIONS`, positive `maxTotalChargeUsd <= 0.25` | Historical options match these boundaries, with cost cap `0.01`. This does not resolve pricing or access. |
| Historical run billing | No `pricingInfo` or charged events | Both were null. This describes that run, not necessarily current Actor pricing. |

## Shortest read-only follow-up

1. Inspect the owned Actor's current monetization page in Apify Console without
   saving or activating anything. Capture a redacted, timestamped indication
   of whether pricing is inactive. Compare it with the current Actor GET
   response and official API documentation or Apify support clarification for
   omitted optional pricing fields. Until there is explicit authoritative
   evidence, retain the current failed gate.
2. Inspect account sharing defaults and the historical run/storage sharing
   views without changing them. Establish what `FOLLOW_USER_SETTING` resolves
   to and whether run and default key-value storage metadata expose effective
   access. Record exact fields and redacted UI evidence; do not equate ownership
   or an unguessable URL with private access.
3. Review that evidence before proposing a narrowly scoped adapter change.
   If effective privacy cannot be established through read-only evidence,
   identify the exact setting change that would be required and seek specific
   authorization. Do not silently accept inherited access or missing pricing.
4. Once those evidence gaps are resolved and the bridge is reviewed, perform
   one authorized synthetic rehearsal using current free credits and fresh
   credit/privacy checks. Bind the exact returned Actor/build/run/store IDs,
   verify `INPUT` is absent, and verify the committed report hashes before
   delivery. Follow the existing cleanup authorization/runbook separately.

## Durable execution and local tests

A SQLite claim keyed by order/revision/attempt commits before starting a run.
A single unresolved slot enforces workstream concurrency one within that ledger.
A timeout or invalid start response becomes `UNKNOWN` and blocks further starts;
there is no blind retry or automatic mechanism to clear that state. Do not use
independent ledgers for concurrent runs of this workstream.

Polling checks identity, run limits, explicit restricted access, zero billing,
and input deletion. Successful artifacts are cached before local ledger
fulfillment, with remote-call-free consumption in the ledger transaction.
Verified terminal failure consumes a bounded attempt; the existing ledger
allows one retry after 15 minutes. A privacy or identity failure freezes delivery.

Run the synthetic suite with
`PYTHONPATH=src python3 -m unittest tests.test_apify_fulfillment`.
The tests use fake transport and actual local Actor/report generation. They
verify claims, concurrent starts, timeout freezes, credit/privacy gates,
identity and hash failures, bounded retries, and recovery from cached output.
They do not establish provider permissions, field availability, or a remote run.

Official references reviewed for implementation:
[run parameters](https://docs.apify.com/api/v2/actors-runs-post),
[Actor metadata](https://docs.apify.com/api/v2/actor-get),
[run metadata](https://docs.apify.com/api/v2/actor-run-get),
[private user data](https://docs.apify.com/api/v2/users-me-get), and
[account limits](https://docs.apify.com/api/v2/users-me-limits-get).

Root follow-up: a read-only Console visit on 2026-09-05 to the exact owned
Actor page redirected to `https://console.apify.com/sign-in`. The browser is
not authenticated, so pricing/sharing UI evidence could not be collected.
The staged sign-in tab is retained; no login credential or account setting was
entered or changed. API token access still works for the scoped read-only
checks. See `provider-receipt.json`.
