#!/usr/bin/env python3
"""Offline launch snapshot review or synthetic intake preview. JSON on stdin only.

No credentials, provider calls, persistent state, or launch authorization.
Exit 0: supported intake preview; 2: blocked/NO_GO; 1: invalid JSON.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from beanfit.launch_readiness import intake_preview, review_snapshot
from beanfit.stripe_test import StripeTestError, _json_object

MAX_INPUT_BYTES = 262144


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('review', 'intake'))
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError()
        value = _json_object(raw)
    except (ValueError, StripeTestError):
        print(json.dumps(dict(status='INVALID_JSON', provider_calls=0, launch_authorized=False)))
        return 1
    if args.action == 'intake':
        result = intake_preview(value)
        code = 0 if result['status'] == 'SUPPORTED' else 2
    else:
        result = review_snapshot(value, now=datetime.now(timezone.utc))
        code = 2  # A snapshot can never clear the external launch gates.
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
