#!/usr/bin/env python3
"""Validate every beanfit catalog tag against its live registry.

Exit 0 = all tags resolve; exit 1 = at least one dead/unreachable tag.
Stdlib only. Run in CI weekly and before every release.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

sys.path.insert(0, "src")

from beanfit import __version__  # noqa: E402
from beanfit.catalog.validate import validate_catalog  # noqa: E402

UA = {"User-Agent": f"beanfit-catalog-validator/{__version__}"}


def fetch_status(url: str) -> int:
    req = urllib.request.Request(url, headers=UA, method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read(64)
        return resp.status


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    results = validate_catalog(fetch_status, sleep=time.sleep)
    blocking_failures = [r for r in results if not r["ok"] and r["blocking"]]
    warns = [r for r in results if not r["ok"] and not r["blocking"]]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        width = max(len(r["id"]) for r in results) + 2
        for r in results:
            mark = "PASS" if r["ok"] else ("WARN" if not r["blocking"] else "FAIL")
            note = "" if r["ok"] else f"  ({r['error']})"
            print(f"{mark}  {r['kind']:<13}{r['id']:<{width}}{note}")
        print(f"\n{len(results) - len(blocking_failures) - len(warns)}/{len(results)} live"
              f" · {len(warns)} warn · {len(blocking_failures)} fail")

    return 1 if blocking_failures else 0


if __name__ == "__main__":
    sys.exit(main())
