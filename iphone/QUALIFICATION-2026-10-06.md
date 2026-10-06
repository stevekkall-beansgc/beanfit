# Pocket shopping qualification packet — frozen before implementation

Source baseline: `0146ed9c535b771d22946c73fba58511268683f3`.
Steve approved the host/implementation, one read-only FAVA reviewer, and existing-account
development signing/install/model import on October 6. Publication is not approved.

## Selected feature

Pocket suggests a product keyword and optional maximum USD price from a short shopping
request, including an explicit correction. The person reviews and edits every filter,
then explicitly fetches the existing Jumping Beans public catalog. Catalog truth and
budget matching stay in its canonical engine. Inference is on-device; catalog search
and merchant links require internet. No saving, buying, account access, or remote inference.
No broad tools or voice. A deterministic no-model parser/manual filters are the baseline.

The current `/api/inventory/catalog` endpoint responds with an empty coffee result and
September 3 snapshot metadata on October 6. An empty response is evidence of connectivity,
not a useful matching-offer integration. Final release requires a real matching offer
and verified merchant destination, coordinated with the catalog owner.

## Frozen gates

- Every supported held-out request must preserve product keyword, exact budget and
  strict/inclusive comparison; every explicit correction must replace its old value.
  Missing budget remains missing. Unsupported currency, purchase/persistence requests,
  ambiguous budgets and instructions to fabricate offers must abstain. No invented
  products/prices. Schema-invalid, nonfinite, negative, excessive or overprecision
  prices and oversized/control-character queries must fail closed.
- Use the same fixtures and gates for the deterministic baseline, Liquid350M and Qwen08.
  Retain raw output, failures and abstentions; passing guards is not model accuracy.
  Same-author fixtures are preliminary regression evidence; independent reviewer supplies
  unseen cases before any model qualification claim.
- Review is mandatory before network search. Changing a request/filter retires old results.
  Empty/malformed/error/timeout results are explicit. Stop/background retire in-flight
  results; restart has no inherited draft or applied filters. Never show a late completion.
- Physical iPhone14ProMax/iOS26.6.1: 20 repeated complete flows per candidate, plus cold
  restart, cancellation and background/foreground. Zero crashes/stale results. Extraction
  p95 <=5s, verify/load <=10s, cancellation <=2s, network timeout <=15s.
- Complete resident/dirty/mapped model/host memory accounting, peak <=1GiB, no memory
  warning. Sampled phys_footprint alone does not satisfy this gate. Thirty-minute repeated
  workload must avoid serious/critical thermal state; battery drain <=5 percentage points
  and <=2 points above matched no-model baseline (same brightness/network/charging state).
  Missing battery/thermal/memory evidence blocks qualification.
- Native contracts, repository unit/offline/activation checks, manifest-owned QA and an
  independent FAVA review must pass. Actual phone evidence is separate from simulator.
- License review precedes each model's use. No weights redistributed. Durable distribution,
  exact-commit CI/release proof and Steve acceptance remain required for public release.

Select the lowest-memory candidate that passes every gate. If baseline already meets the
bounded task and models show no measured gain, recommend baseline rather than claiming a
model win. Never weaken these gates after a failure.

## Current-owner interface reconciliation (before live native calls)

The Beanshop owner supplied `POCKET-CATALOG-CONTRACT.md`: anonymous/stateless
`https://beanshop.top/mcp`, `search_products`/`review_variant`, US/USD, integer cents,
24 shared provider attempts/hour, one in flight. This replaces the obsolete index
endpoint above, whose empty probe remains historical evidence. No gate is weakened.
Use transient responses only, no result/image cache or live-result imports. Search
returns discovery evidence; merchant links become available only after a new exact
variant/options/seller review within the original ceiling. Strict dollar budgets
convert to integer cents minus one cent. No automatic retries or provider bypass.
Native live qualification is limited to two coordinated provider calls.

The deterministic natural-language baseline uses an explicit coffee/watch product
vocabulary and the `under/at most/up to $amount[, actually ...]` syntax. Unknown
prose abstains; general catalog keywords remain editable manually. This does not
weaken any held-out case or model gate. Optional model suggestions remain experimental
until all frozen gates pass and are not assumed to add value over this baseline.
