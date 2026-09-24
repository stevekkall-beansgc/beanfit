#!/usr/bin/env python3
"""Validate every beanfit catalog tag against its live registry.

Exit 0 = all tags resolve; exit 1 = at least one dead/unreachable tag.
Stdlib only. Run in CI weekly and manually before every release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from beanfit import __version__  # noqa: E402
from beanfit.catalog.validate import validate_catalog  # noqa: E402

UA = {"User-Agent": f"beanfit-catalog-validator/{__version__}"}
VALIDATOR_PATH = ROOT / "scripts" / "validate_catalog.py"
RECEIPT_SCHEMA_VERSION = 1
RECEIPT_KIND = "public_registry_GET_liveness_only"
RECEIPT_LIMITATION = (
    "Registry liveness is a point-in-time observation, not performance evidence; "
    "HTTP 200 does not prove quantization, model quality, hardware fit, or future "
    "tag availability."
)


def fetch_status(url: str) -> int:
    req = urllib.request.Request(url, headers=UA, method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read(64)
        return resp.status


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def source_revision() -> str:
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("cannot determine the exact source revision") from exc
    if not revision:
        raise RuntimeError("git returned an empty source revision")
    return revision


def source_tree_dirty() -> bool:
    try:
        output = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("cannot determine whether the source tree is clean") from exc
    return bool(output.strip())


def validator_sha256() -> str:
    return hashlib.sha256(VALIDATOR_PATH.read_bytes()).hexdigest()


def result_status(result: dict) -> str:
    if result["ok"]:
        return "PASS"
    return "FAIL" if result["blocking"] else "WARN"


def build_receipt(
    results: list[dict],
    source_revision: str,
    package_version: str,
    validated_at: str,
    source_dirty: bool = False,
    validation_started_at: str | None = None,
) -> dict:
    formatted_results = []
    for result in results:
        formatted = dict(result)
        formatted["result"] = result_status(result)
        formatted_results.append(formatted)

    counts = {
        "total": len(formatted_results),
        "pass": sum(result["result"] == "PASS" for result in formatted_results),
        "warn": sum(result["result"] == "WARN" for result in formatted_results),
        "fail": sum(result["result"] == "FAIL" for result in formatted_results),
    }
    status = (
        "FAIL"
        if counts["fail"]
        else ("WARN" if counts["warn"] or source_dirty else "PASS")
    )
    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "kind": RECEIPT_KIND,
        "status": status,
        "source_revision": source_revision,
        "source": {"revision": source_revision, "dirty": source_dirty},
        "package_version": package_version,
        "validator": {
            "entrypoint": "scripts/validate_catalog.py",
            "hash_algorithm": "sha256",
            "hash_scope": "scripts/validate_catalog.py bytes",
            "sha256": validator_sha256(),
        },
        "validated_at": validated_at,
        "summary": counts,
        "results": formatted_results,
        "limitations": RECEIPT_LIMITATION,
    }
    if validation_started_at is not None:
        receipt["validation_started_at"] = validation_started_at
    return receipt


def write_receipt(path: Path, receipt: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def print_results(results: list[dict]) -> None:
    width = max((len(r["id"]) for r in results), default=1) + 2
    for result in results:
        mark = result_status(result)
        note = "" if result["ok"] else f"  ({result['error']})"
        print(f"{mark}  {result['kind']:<13}{result['id']:<{width}}{note}")
    passes = sum(result["ok"] for result in results)
    warns = sum(not result["ok"] and not result["blocking"] for result in results)
    fails = sum(not result["ok"] and result["blocking"] for result in results)
    print(f"\n{passes}/{len(results)} live · {warns} warn · {fails} fail")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--receipt",
        type=Path,
        metavar="PATH",
        help="write a machine-readable release receipt to PATH",
    )
    ap.add_argument(
        "--allow-dirty",
        action="store_true",
        help="allow a receipt from a dirty checkout for local diagnosis",
    )
    args = ap.parse_args(argv)

    revision = ""
    dirty = False
    if args.receipt:
        try:
            revision = source_revision()
            dirty = source_tree_dirty()
        except RuntimeError as exc:
            print(f"catalog-validator: {exc}", file=sys.stderr)
            return 2
        if dirty and not args.allow_dirty:
            print(
                "catalog-validator: refusing a release receipt from a dirty checkout; "
                "commit or clean the checkout, or use --allow-dirty for diagnosis",
                file=sys.stderr,
            )
            return 2

    started_at = utc_timestamp()
    results = validate_catalog(fetch_status, sleep=time.sleep)
    blocking_failures = [r for r in results if not r["ok"] and r["blocking"]]

    if args.receipt:
        receipt = build_receipt(
            results,
            source_revision=revision,
            package_version=__version__,
            validated_at=utc_timestamp(),
            source_dirty=dirty,
            validation_started_at=started_at,
        )
        try:
            write_receipt(args.receipt, receipt)
        except OSError as exc:
            print(f"catalog-validator: could not write receipt: {exc}", file=sys.stderr)
            return 2

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results)
        if args.receipt:
            print(f"receipt: {args.receipt} ({receipt['status']})")

    return 1 if blocking_failures else 0


if __name__ == "__main__":
    sys.exit(main())
