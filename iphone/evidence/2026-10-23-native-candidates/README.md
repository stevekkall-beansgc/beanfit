# Native candidates prepared on October 23

Pocket 0.1.0/build 2 and beanSprout 0.2.0/build 1317 are local developer candidates
for the next phone session. Generic iPhone builds/signatures and both actual
simulator hosts pass. They include released BeanFit v0.8.1 catalog metadata;
Qwen2 remains an unqualified comparison candidate and replies use the separate
own-facts formatter. No phone was used, no app was installed on physical hardware, and no native
release was published.

The source/executable identities bind local files, not reproducible builds or
store-ready distribution. Paths in build-identity.json are relative to the local
beans output directory `outputs/beanfit-native-candidates-20261023`. Both finalized
simulator suites have2 passes, 0 failures/skips and removed their own simulators.
Their lifecycle receipts include the actual app build/version. Messages and App
Clip retain matching versions and have no added text runtime/model assets.

The six prompt/inference/runtime files listed in scope-review.json match the
previous05b3235 candidate, and the frozen36-case packet is unchanged. Existing
Mac quality reviews remain historical corroboration; they were not rerun or
relabeled as new physical acceptance. The shared view changed only report build
metadata in this round. All 9 shared sources match the prepared actual UIKit host.

Authored structural/adversarial review with automated corroboration is recorded
in candidate-review.json; it is not independent sign-off. Core QA 3/3 (256 unit
checks), host QA 2/2 (870 product assertions), Swift contracts and pinned static
checks pass. The older native package passes 181 XCTest cases in Debug and Release,
plus14/12 Swift Testing cases and its release synthetic-creation compile gate.
Passing these checks does not approve the older native baseline for publication.

The phone packet runner now checks exact local and returned build identity and
owns a bounded console launch. Its local child-process cleanup test passes.
Actual devicectl signal forwarding/app exit is explicitly unverified until the
phone returns. Full36-case quality, memory/load cycles, 20-request/five-minute heat,
actual UI/lifecycle and Instruments remain open for each app. The earlier
four-case Pocket interruption is unresolved. The older 108-file beanSprout native
baseline still needs separate publication review; never ship the full branch as
a text-only change. Voice notes/search stay deferred.

The first generic Pocket build used a missing auto-created scheme and failed
before compilation. Its log is retained locally. Corrected commands use the
checked-in shared scheme; all 4 final builds pass. The build wrapper now uses that
scheme and supports an explicit BF_BUILD_NUMBER. Its shell syntax and equivalent
Xcode invocation pass; the full wrapper's CMake rebuild was not repeated.
