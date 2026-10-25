#!/usr/bin/env python3
"""Snapshot and run the real Swift text adapter with a supplied local native library.

Mac functional evidence only: never connects to a phone, downloads weights,
calls an AI provider, or measures iPhone memory/heat. The library's provenance
must be reviewed separately; its hash is recorded, not treated as attestation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-library", type=Path, required=True)
    parser.add_argument("--model-id", default="qwen2")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="New evidence directory; existing results are never overwritten")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("This harness requires macOS and Xcode")
    library = args.native_library.resolve(strict=True)
    model = args.model.resolve(strict=True)
    packet = args.packet.resolve(strict=True)
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output / "source"
    snapshot.mkdir()
    names = ["RuntimeContracts.swift", "Models.swift", "ModelCatalog.generated.swift",
             "ModelSuggestions.swift", "TextDraft.swift"]
    for name in [*names, "Native.h", "Native.cpp"]:
        shutil.copy2(root / "BeanFitRuntime" / name, snapshot / name)
    shutil.copy2(root / "Tests/NativeTextPreflight.swift", snapshot / "NativeTextPreflight.swift")
    shutil.copy2(packet, output / "packet.json")
    identity = {"source_sha256": {p.name: digest(p) for p in snapshot.iterdir()},
                "packet_sha256": digest(output / "packet.json"),
                "native_library_sha256": digest(library),
                "native_library_provenance": "Supplied local library; not attested by this harness",
                "evidence_kind": "mac-native-preflight-not-phone", "qualified": False}
    (output / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    command = ["xcrun", "swiftc", "-parse-as-library", "-import-objc-header",
               str(snapshot / "Native.h"), str(library), "-Xlinker", "-rpath",
               "-Xlinker", str(library.parent)]
    command += [str(snapshot / name) for name in names]
    command += [str(snapshot / "NativeTextPreflight.swift"), "-o", str(output / "preflight")]
    with (output / "compile.log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    command = [str(output / "preflight"), args.model_id, str(model),
               str(output / "packet.json"), str(output / "report.json"), "0"]
    with (output / "native.log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    report = json.loads((output / "report.json").read_text())
    assert report["evidence_kind"] == identity["evidence_kind"] and not report["qualified"]
    records = report["records"]
    print(json.dumps({"completed": report["completed"], "cases": len(records),
                      "pipeline_phrase_passes": sum(row["passed"] for row in records),
                      "qualified": False, "evidence_kind": report["evidence_kind"]}))


if __name__ == "__main__":
    main()
