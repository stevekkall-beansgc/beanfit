#!/usr/bin/env python3
"""Verify exact registry metadata without downloading or executing model weights."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def validate(doc):
    assert doc["schema"] == "beanfit.on-device.catalog.v1"
    devices = [d["id"] for d in doc["devices"]]
    assert len(devices) == len(set(devices)) and devices
    assert all(re.fullmatch(r"iPhone[0-9]+,[0-9]+", d) for d in devices)
    assert all(d["name"].strip() for d in doc["devices"])
    all_models = doc["models"] + doc.get("reference_models", [])
    ids = [m["id"] for m in all_models]
    assert len(ids) == len(set(ids))
    for model in all_models:
        assert model["qualification"] == "unqualified"
        assert model["runtime_status"] in ("native_text_candidate", "requires_integration")
        assert model["artifacts"]
        assert model["source_url"].startswith("https://huggingface.co/")
        if model["failed_experiences"]:
            assert (ROOT / model["failure_evidence_ref"]).is_file()
        for item in model["artifacts"] + ([model["q8_artifact"]] if model["q8_artifact"] else []):
            assert re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", item["repository"])
            assert re.fullmatch(r"[0-9a-f]{40}", item["revision"])
            assert re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
            assert type(item["bytes"]) is int and item["bytes"] > 0
            assert not item["filename"].startswith("/") and ".." not in item["filename"].split("/")
    for model in doc.get("reference_models", []):
        assert model["evaluation_scope"] == "mac_reference_only"
        assert model["runtime_status"] == "requires_integration"
    experiences = {task["id"] for task in doc["experiences"]}
    assert all(set(model["capabilities"]) <= experiences for model in all_models)
    for task in doc["experiences"]:
        expected = {m["id"] for m in doc["models"] if task["id"] in m["capabilities"]}
        assert set(task["trial_order"]) == expected
        assert len(task["trial_order"]) == len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    doc = json.loads((ROOT / "src/beanfit/catalog/on_device.json").read_text())
    validate(doc)
    groups = {}
    for model in doc["models"] + doc.get("reference_models", []):
        for item in model["artifacts"] + ([model["q8_artifact"]] if model["q8_artifact"] else []):
            groups.setdefault((item["repository"], item["revision"]), []).append(item)

    def check(pair):
        (repo, revision), artifacts = pair
        result = {"repository": repo, "revision": revision, "ok": False}
        try:
            with urlopen(f"https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true", timeout=30) as response:
                metadata = json.load(response)
            assert metadata["sha"] == revision, "revision mismatch"
            files = {f["rfilename"]: f for f in metadata["siblings"]}
            for item in artifacts:
                actual = files[item["filename"]]
                assert actual["size"] == item["bytes"], "size mismatch"
                if actual.get("lfs"):
                    assert actual["lfs"]["sha256"] == item["sha256"], "SHA-256 mismatch"
                else:
                    # Compiled Core ML packages include small ordinary Git files.
                    # Hash their exact pinned contents; never download large weights.
                    assert item["bytes"] <= 1024 * 1024, "non-LFS component exceeds verification bound"
                    with urlopen(f"https://huggingface.co/{repo}/resolve/{revision}/{item['filename']}", timeout=30) as response:
                        data = response.read(1024 * 1024 + 1)
                    assert len(data) == item["bytes"], "content size mismatch"
                    assert hashlib.sha256(data).hexdigest() == item["sha256"], "SHA-256 mismatch"
            result.update(ok=True, artifact_count=len(artifacts))
        except Exception as error:
            result["error"] = str(error)[:200]
        return result

    results = []
    if args.live:
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(check, groups.items()))
    receipt = {"schema": "beanfit.on-device.registry-check.v1",
               "checked_at": datetime.now(timezone.utc).isoformat(), "catalog_as_of": doc["as_of"],
               "scope": "registry metadata only; not runtime, task quality, memory fit or release proof",
               "live": args.live, "ok": all(r["ok"] for r in results), "results": results}
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, ValueError, OSError) as error:
        print(f"on-device catalog invalid: {error}", file=sys.stderr)
        raise SystemExit(1)
