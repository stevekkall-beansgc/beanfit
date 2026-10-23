# Historical text evidence included with the catalog release

These October 22 synthetic pilot receipts support a conservative catalog update,
not a production qualification or a mobile runtime release. The generation code
that produced them remains on the separate native review branch. Source hashes
identify those pilot configurations; this release does not claim to reproduce or
ship their executables. The local source path is omitted from the resource build
manifest, with its original local file hash recorded. Other included receipts
are copied unchanged from the retained pilot evidence.

The frozen 36-case packet and criteria are in `../../Tests/`. Its SHA256 is
47f1797303c82d58180f913e697d30c590a69097afed98141d164862bd0d70c5.
`pocket-liquid12-initial-quality.json` retains the LFM1.2B phone run and
`pocket-liquid12-initial-authored-review.json` records 29/36 factual/clarity passes
and critical failures r09, s07 and w03. The review is by the implementing agent,
not independent users. This specific configuration failed; revised configuration
review is required before removing its hold for text. Other tasks require their
own evidence.

`pocket-qwen2-formatter-resource.json` contains preliminary Pocket resource/stop
checks for Qwen2 with the separate reply formatter. Resident mapped peak and
footprint plus full model weights stayed below the frozen 1536MiB limit in that
packet; five load cycles met the growth bound. This is app-process sampling,
not whole-system RAM, sustained heat, final-build quality, or other-device proof.
Injected warnings are handler checks, not real OS pressure. The following phone
quality attempt was incomplete and is not used to claim acceptance.

All models remain unqualified, memory fit unknown and automatic selection empty.
Full quality, memory/load-cycle, five-minute heat, real UI and Instruments checks
on the final native candidates remain open in the separate phone task. This
release includes catalog metadata/mirrors and static evidence only; no new model
weights, generation adapter or app binary is shipped.
