# First physical iPhone execution — 2026-09-26

BeanFit Pocket was development-signed, installed, trusted by the user, and run on
an iPhone 14 Pro Max (iPhone15,3), iOS 26.6.1. The app performed local inference;
there was no remote inference endpoint. The initial trust and locked-screen
launch failures were resolved before the successful runs below.

| Pinned model | App checks | Verify/load | Simple generation | Shopping extraction |
| --- | --- | --- | --- | --- |
| Liquid 350M QAD Q4_0 | 10/10 | 0.42 s | 0.34 s | 1.10 s |
| Qwen3.5 0.8B Q4_K_M | 10/10 | 1.20 s | 0.67 s | 3.22 s |

These are one run per model, two short generations each, four CPU threads,
2048-token context, and grammar-constrained shopping output. They demonstrate
native runtime and adapter execution, not robust model quality. Seven checks are
contract/lifecycle checks; only the simple reply and preference extraction probe
model behavior, with catalog matching checking their downstream use.

The smaller model is a candidate for the next product-specific qualification;
there is no production winner. No 2B phone run, voice stack, Bean Mind connection,
live Jumping Beans integration, purchase, or saved preference is claimed.

The accompanying JSON files are copied from the device app's Documents directory.
They explicitly retain `phoneQualified: false` / `qualified: false`. Observed
physical-footprint peaks were approximately 85 MiB and 201 MiB respectively, but
clean file-backed model pages may not be charged to this metric. **Do not treat
these numbers as total resident RAM, whole-product memory, or model fit budgets.**

The same final sources built successfully for both simulator and device. The
simulator's owned E2E passed 10/10 checks; repository QA passed docs, 225 unit
tests (including native Swift contracts), and offline plus native E2Es.

During review, model verification retained temporary Foundation buffers until
load returned. Draining those buffers per hash chunk reduced the simulator's
observed verify/load peak from about 1086 MiB to 582 MiB. An E2E regression guard
rejects a second model-sized accumulation. This simulator comparison is not a
phone performance estimate.

Review was performed by the implementing agent. Remaining release gates:
representative product quality, complete memory accounting, repeated device
reliability/thermal/latency testing, live host integration, model license review,
and durable distribution. The development profile used for this installation
expires on 2026-10-03; it can be refreshed with the configured development team.
