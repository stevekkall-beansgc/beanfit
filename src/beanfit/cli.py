from __future__ import annotations

import argparse
import sys

from beanfit import __version__
from beanfit.catalog.models import USE_CASES
from beanfit.engine import evaluate
from beanfit.emit import render_json, render_table
from beanfit.hw import UnsupportedPlatform, detect


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="beanfit",
        description="What local AI actually fits — and runs well — on THIS device.",
    )
    ap.add_argument("--use-case", choices=list(USE_CASES), default="chat")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--version", action="version", version=f"beanfit {__version__}")
    args = ap.parse_args(argv)

    try:
        hw = detect()
    except UnsupportedPlatform as exc:
        print(f"beanfit: {exc}", file=sys.stderr)
        return 2

    rows = evaluate(hw, args.use_case)
    if args.json:
        print(render_json(hw, rows, args.use_case, __version__))
    else:
        print(render_table(hw, rows, args.use_case))
    return 0


if __name__ == "__main__":
    sys.exit(main())
