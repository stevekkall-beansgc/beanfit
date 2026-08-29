"""beanfit register — pair THIS machine with your beanfit account.

Detection and recommendation math run locally; only the resulting profile
(the same fields shown at approval time) is sent to the server.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
import urllib.error
import urllib.request

from beanfit import __version__
from beanfit.catalog.models import USE_CASES
from beanfit.engine import evaluate
from beanfit.hw import UnsupportedPlatform, detect
from beanfit.profile import DeviceProfile


def _ci_profile() -> DeviceProfile:
    """Return a conservative profile for deterministic hosted E2E runs."""
    return {
        "os": platform.system().lower() or "unknown",
        "arch": "other",
        "backend": "unknown",
        "chip": f"{platform.system() or 'unknown'} CI runner",
        "family": "",
        "variant": "",
        "ram_gib": 8.0,
        "metal_cap_gib": 4.0,
        "model_budget_gib": 4.0,
        "mem_bandwidth_gbs": 60.0,
        "bw_source": "unknown_fallback",
    }


def _detect_for_register() -> DeviceProfile:
    try:
        return detect()
    except UnsupportedPlatform:
        if os.environ.get("BEANFIT_ALLOW_UNSUPPORTED_PLATFORM") != "1":
            raise
        return _ci_profile()


def build_pair_payload(hw: dict, use_case: str, label: str | None) -> dict:
    return {
        "label": label or f"{hw['chip']} · {hw['ram_gib']:.0f} GiB",
        "profile": {"hardware": hw},
        "recommendations": {
            "use_case": use_case,
            "engine_version": __version__,
            "ranked": evaluate(hw, use_case),
        },
    }


def _request(url: str, data: dict | None = None, timeout: int = 20) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"content-type": "application/json",
                 "user-agent": f"beanfit-cli/{__version__}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            return resp.status, (json.loads(body) if body.strip() else {})
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode())
        except Exception:
            return exc.code, {}


def save_device_credential(path: str, doc: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(doc, fh, indent=2)


def credential_path() -> str:
    base = os.environ.get("APPDATA") if sys.platform == "win32" else \
        os.path.expanduser("~/.config")
    return os.path.join(base, "beanfit", "device.json")


def register_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="beanfit register")
    ap.add_argument("--server", default=os.environ.get("BEANFIT_SERVER", ""),
                    help="e.g. https://beanfit-app.example.workers.dev")
    ap.add_argument("--use-case", choices=list(USE_CASES), default="chat")
    ap.add_argument("--label", default=None)
    ap.add_argument("--poll-secs", type=int, default=3)
    args = ap.parse_args(argv)

    if not args.server:
        print("Provide --server https://… or set BEANFIT_SERVER.", file=sys.stderr)
        return 2
    server = args.server.rstrip("/")

    try:
        hw = _detect_for_register()
    except UnsupportedPlatform as exc:
        print(f"beanfit: {exc}", file=sys.stderr)
        return 2
    print(f"beanfit · detected {hw['chip']} · {hw['ram_gib']} GiB")

    status, body = _request(f"{server}/api/pair/start",
                            build_pair_payload(hw, args.use_case, args.label))
    if status != 201:
        print(f"Pairing failed ({status}): {body.get('error', 'unknown')}", file=sys.stderr)
        return 1

    code, pair_id = body["code"], body["pair_id"]
    print(f"\nApprove this device in your browser:\n\n  {server}/pair\n\n"
          f"Pairing code: {code}\n\nWaiting for approval", end="", flush=True)

    deadline = time.monotonic() + int(body.get("expires_in", 900))
    while time.monotonic() < deadline:
        time.sleep(args.poll_secs)
        status, body = _request(f"{server}/api/pair/status/{pair_id}")
        state = body.get("status", "?")
        if state == "approved":
            cred = {"server": server, "device_id": body["device_id"],
                    "device_token": body["device_token"], "registered_at": __version__}
            path = credential_path()
            save_device_credential(path, cred)
            print(f"\n\nApproved! Device registered.")
            print(f"Credentials saved to {path} (keep private; revoke anytime "
                  f"from your account page).")
            return 0
        if state in ("denied", "expired"):
            print(f"\nPairing {state}. Run `beanfit register` again.")
            return 1
        print(".", end="", flush=True)

    print("\nTimed out waiting for approval.")
    return 1


if __name__ == "__main__":
    sys.exit(register_main())
