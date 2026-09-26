"""Offline validation of one text probe; never certifies voice or device fit.

Receipts are self-reported evidence, not authenticated device attestations.
No inference, network, model download, or change to BeanFit's Mac ranking.
"""
import argparse
import json
import math
from pathlib import Path


def summarize(receipt):
    if not isinstance(receipt, dict) or receipt.get("schema") != "beanfit.iphone.text.v1":
        raise ValueError("unsupported receipt schema")
    kind = receipt.get("evidence_kind")
    if kind not in {"physical_device", "simulator", "synthetic"}:
        raise ValueError("explicit evidence_kind required")
    for field in ("device", "os_build", "runtime", "model", "recorded_at", "case_id"):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            raise ValueError(f"nonempty {field} required")
    if receipt.get("scope") != "text_only" or receipt.get("inference_location") != "on_device":
        raise ValueError("only on-device text receipts supported")
    if receipt.get("offline_verified") is not False:
        raise ValueError("this probe cannot attest network isolation")
    outcome = receipt.get("outcome")
    if outcome not in {"completed", "unavailable", "failed", "cancelled", "not_run"}:
        raise ValueError("explicit outcome required")
    first, total = receipt.get("first_text_ms"), receipt.get("total_ms")
    for field, value in (("first_text_ms", first), ("total_ms", total)):
        if value is not None and (type(value) not in (int, float) or
                                  not 0 <= value <= 86_400_000 or not math.isfinite(value)):
            raise ValueError(f"{field} must be milliseconds within one day or null")
    if first is not None and (total is None or first > total):
        raise ValueError("first text must precede completion")
    if outcome == "completed" and (first is None or total is None):
        raise ValueError("completed requires both measured timings")
    if outcome in {"not_run", "unavailable"} and (first is not None or total is not None):
        raise ValueError("unexecuted inference must not contain timings")
    observed = kind == "physical_device" and outcome == "completed"
    return {
        "evidence_kind": kind,
        "outcome": outcome,
        "status": "physical_text_observation" if observed else "not_device_performance_evidence",
        "first_text_ms": first,
        "total_ms": total,
        "iphone_voice_ready": False,
        "fit": "unknown",
        "tokens_per_second": None,
        "limits": ["self-reported receipt; not attestation", "one text trial, not a voice benchmark",
                   "memory, battery, speech, quality and offline behavior unverified"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    try:
        result = summarize(json.loads(args.receipt.read_text()))
    except (ValueError, OSError) as error:
        parser.exit(2, f"Invalid receipt: {error}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
