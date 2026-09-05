# Local correction for private build 1.0.1

**Completed:** the originating task applied the correction and replacement build
`GQ41FN91r9DraYJiC / 1.0.2` SUCCEEDED. The text below records the historical
local-only correction stage; its then-pending rebuild is now complete. See
[VALIDATION-RECEIPT.md](VALIDATION-RECEIPT.md) for current status.

Originating-task receipt: private Actor `X457S8llVBn25IEYB`, `isPublic=false`;
build `czIituktgMxxpVkAx` / `1.0.1` failed before container execution:
`Input schema is not valid (Field schema.properties.use_case.description is required)`.
Reported build credit usage: **$0.00022222222222222223**. This is failed-build
usage, not report-run cost. These facts were relayed by the originating task;
this correction made no API request to independently reread them.

## Exact minimal remote source change

In existing Actor version **1.0**, replace only `.actor/input_schema.json`:

- Add descriptions to `use_case`, `preferred_runtime`, `latency_preference`.
- Add title, description, and textfield editor metadata to nested runtime
  version properties `installed_runtime_versions.ollama` and `.mlx`.

No input names, required fields, types, enum values, constraints or report logic
changed. All 21 Python hashes and the Python-source build manifest are unchanged.
The regenerated package differs from the previous package in **exactly one of
27 source files**; the remaining 26 file records are byte-for-byte identical.

The local `private-version-update-payload.json` contains the complete
`sourceFiles` array for a future version update. Do not create another Actor.
Before applying it, the originating task should read version 1.0, preserve its
other configuration and verify that the 26 unchanged file records still match.
Then replace only the matching schema record in that source array. Do not send
only a one-file array: a replacement array could discard the other files.
If remote source differs unexpectedly, stop and reconcile before updating.

No upload, build, run, pricing, publication, plan change, or external usage was
performed for this correction. An updated source upload and another build
require revised authorization in the originating task.

## Local validation

- Recursive metadata/structural guard: PASS for all 9 top-level and 2 nested
  properties, including nonempty title/description and compatible editor.
- Regression recreating the exact missing-use-case-description error: PASS.
- Removal of each field's metadata is rejected by the guard: PASS.
- Frozen fields and all three enum choice sets checked unchanged: PASS.
- Full deterministic suite: **72 tests PASS**.
- Isolated central QA: **2/2 PASS**.
- Source manifest: all **21** hashes verified; unchanged.
- `git diff --check`: PASS.

The local guard covers known requirements and these field types, and now runs
inside the package builder. No provider validator was available locally;
therefore this is not a claim that Apify's complete schema validation has passed.
The revised remote build remains the final platform compatibility check.

Hashes and machine-readable evidence: `schema-correction-receipt.json`.
