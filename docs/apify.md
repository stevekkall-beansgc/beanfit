# BF-CER-v1.0 private Apify Actor

This adapter delivers the existing $12 Beanfit Compatibility Evidence Report:
one Apple Silicon device, one use case, one revision. It uses Beanfit's existing
catalog and fit engine. Private synthetic validation only; no public listing,
paid activation, customer solicitation, or charge API is present in this build.

## Files and execution

`.actor/actor.json`, `input_schema.json`, and `Dockerfile` define the Actor.
The container uses Python 3.12 slim, no pip installation or third-party SDK.
The upstream base image tag is mutable; record the resolved image digest/build
ID in the deployment receipt before reproducing a platform build.

An operator-generated `.actor/build-manifest.json` is required before building:
`repository_revision` is the immutable base Beanfit revision; `source_sha256`
maps **every** `src/**/*.py` relative path to its SHA-256 digest. Runtime startup
verifies the complete map, including the adapter, report engine, and catalog.
The manifest distinguishes the reviewed base revision from this uncommitted
source overlay; it does not imply the overlay exists at that Git revision.

Run tests with `PYTHONPATH=src python3 -m unittest discover -s tests`.
The deterministic adapter tests inject memory-only storage, a clock, and a
generator; they never access Apify or require credentials.

Platform runs require the automatically injected `APIFY_TOKEN` and
`ACTOR_DEFAULT_KEY_VALUE_STORE_ID`, `ACTOR_MEMORY_MBYTES` (legacy `APIFY_`
prefixes also supported). Input key must be `INPUT`. No bootstrap token is
embedded in source, images, schema, logs, or run input. Use limited platform
permissions wherever available. Memory must be at most 1024 MiB; use 128 MiB
and a 60-second timeout for the initial private validation, concurrency one,
no retries, and a verified free-credit budget including build cost. The adapter
does not inspect account credit: the operator must pass that gate before any
remote build or run. No local hardware detection occurs inside the container.

## Storage, privacy, and failure semantics

The adapter uses only the exact HTTPS host `api.apify.com`, disables proxies
and redirects, limits reads to 32 KiB plus an overflow byte, restricts record
keys, and uses a 15-second timeout per request. Raw input is deleted immediately
after the read, before parsing, including on read failure, malformed JSON, or
report validation rejection. Failure to delete prevents report generation.
Schema UI checks are supplemented by the report engine's authoritative input
validation. Invalid values and unknown fields must not be silently coerced.

No raw input, credentials, API response bodies, exception details, or report
content are logged. A startup failure prints only a generic configuration
message. Configuration/provenance failures occurring before storage opens
cannot delete INPUT; the operator must delete that run's default store. A
platform interruption or storage outage can also prevent cleanup. Therefore
use only synthetic inputs until retention and deletion have been tested.

Successful runs write `REPORT.md`, `REPORT.json`, `METRICS`, then `OUTPUT`.
`OUTPUT.status == "SUCCEEDED"` is the sole completion marker. Do not deliver
partial reports if that marker is absent. Rejected/failed runs return a nonzero
exit code, clear report artifacts where possible, and emit only sanitized
status codes. A cleanup/storage outage fails closed but needs operator cleanup.
Outputs repeat accepted device/workload inputs and are sensitive artifacts:
keep the Actor/stores private, do not share hard-to-guess storage URLs, and
delete the default store after synthetic receipts are collected. Raw INPUT
deletion does not promise deletion from platform backups or audit systems;
confirm platform retention before accepting customer input.

## Idempotency and cost

All writes use fixed keys; rerunning with the same input re-supplied to the same
store overwrites the report rather than appending duplicates. With INPUT absent,
a retry verifies both report hashes against a previously successful OUTPUT and
returns success without rewriting artifacts, timestamps, or metrics. Corrupt
artifacts return failure and remain available for inspection; consumers must
verify hashes as well as the completion marker. Without a committed success,
missing INPUT fails and requires explicit resubmission. Automatic restart is
disabled for private validation. Timestamps change on a new invocation with
re-supplied input. This is
**not cross-run order deduplication**. Before paid activation, an external order
ledger must atomically claim the transaction/revision, identify corrections,
record delivery, and prevent duplicate billing across retries/new run IDs.

`METRICS` records elapsed adapter seconds, allocated MiB, and estimated CU:
`seconds / 3600 × MiB / 1024`. It excludes startup and final receipt writes,
and is not a billed amount. `billed_cost_usd` remains null. After the run, the
operator must retrieve platform usage/actual cost, capture build cost, and
reconcile remaining free credits. `billing_events_emitted` is always zero.

## Publication gate

The intended future charge is exactly one `report-generated` event at USD 12
per successfully delivered report. This build deliberately contains no charge
endpoint. It is not paid-ready merely by attaching pricing: activation requires
an authorized code/config change with transaction-level deduplication, correction
and refund handling, and a single post-delivery event. Keep the prepared pricing
configuration unapplied until explicit public publication and paid activation
authorization. No plan upgrade or cash spend is authorized by private testing.

## Current official references

- [Actor environment variables](https://docs.apify.com/actors/development/programming-interface/environment-variables)
- [Actor definition](https://docs.apify.com/actors/development/actor-definition/actor-json)
- [Key-value storage REST API](https://docs.apify.com/api/v2/storage-key-value-stores)

Reviewed 2026-09-04. Deployment receipts must record actual remote outcomes;
local tests do not establish that a private deployment or credit gate passed.

## Supported inputs and manual review

Required input example:

```json
{"device_chip":"Apple M4 Pro","memory_gib":48,"use_case":"coding","operating_system":"macOS 15.6 arm64"}
```

All three `latency_preference` values are accepted; quality and speed reorder
existing estimates deterministically, while balanced keeps original ranking.
Runtime versions are a small JSON object keyed by `ollama` and/or `mlx`, with
numeric version strings only. Automatic detection is not used in this cloud
adapter; an operator must normalize a redacted device profile before submission.

The frozen contract is broader than this automated path. Positive context above
16384 tokens and nonempty plain-language constraints return `NEEDS_REVIEW`
without producing or charging for a report. Wrong types, oversized constraints,
unknown fields and unsafe content are rejected. Raw inputs are deleted in either
case; no personal text is retained for a handoff. A reviewer must request a
redacted resubmission outside this Actor, evaluate whether existing Beanfit can
substantiate the requested condition, and either deliver under the original
contract or decline/refund as appropriate. No scheduler, external review task,
or customer contact is automatically created. This workflow is documented but
not deployed: full frozen-input fulfillment remains an activation blocker.
