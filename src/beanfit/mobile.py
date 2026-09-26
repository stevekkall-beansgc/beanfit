"""Offline, memory-first qualification of externally collected iPhone trials.

No detection, inference, downloads, network calls or fabricated mobile estimates.
Receipts are self-reported observations, not authenticated device attestations.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys


# Version of the public mobile profile/receipt/selection contracts.
CONTRACT_VERSION = "v1"


class EvidenceError(ValueError):
    pass


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise EvidenceError(f"{name} must be a nonempty string of at most 512 characters")
    return value


def _number(value, name, low, high):
    if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
        raise EvidenceError(f"{name} must be a finite number in [{low}, {high}]")
    return value


def _integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise EvidenceError(f"{name} must be an integer in [{low}, {high}]")
    return value


def _case_list(value, name, *, empty=False):
    if not isinstance(value, list) or len(value) > 500 or (not value and not empty):
        raise EvidenceError(f"{name} must be a bounded list of case IDs")
    for item in value:
        _text(item, name)
    if len(set(value)) != len(value):
        raise EvidenceError(f"{name} contains duplicate case IDs")
    return value


MATCH_FIELDS = ("device", "os_build", "workload_sha256", "context_tokens",
                "output_limit_tokens", "stack_id", "memory_method")


def validate_profile(profile):
    if not isinstance(profile, dict) or profile.get("schema") != "beanfit.mobile.profile.v1":
        raise EvidenceError("unsupported product profile schema")
    for name in ("product", "device", "os_build", "stack_id", "memory_method"):
        _text(profile.get(name), name)
    if not re.fullmatch(r"[0-9a-f]{64}", str(profile.get("workload_sha256", ""))):
        raise EvidenceError("workload_sha256 must pin the product's evaluation dataset")
    for name in ("context_tokens", "output_limit_tokens"):
        _integer(profile.get(name), name, 1, 1_000_000)
    _integer(profile.get("memory_budget_bytes"), "memory_budget_bytes", 1, 2**50)
    _number(profile.get("headroom_fraction"), "headroom_fraction", 0, 1)
    _number(profile.get("min_quality"), "min_quality", 0, 1)
    _number(profile.get("max_p95_latency_ms"), "max_p95_latency_ms", 1, 86_400_000)
    _integer(profile.get("min_repeats"), "min_repeats", 1, 100)
    cases = _case_list(profile.get("case_ids"), "case_ids")
    critical = _case_list(profile.get("critical_case_ids"), "critical_case_ids", empty=True)
    if not set(critical) <= set(cases):
        raise EvidenceError("critical cases must belong to the pinned evaluation dataset")


def _evaluate(profile, receipt):
    if not isinstance(receipt, dict) or receipt.get("schema") != "beanfit.mobile.receipt.v1":
        raise EvidenceError("unsupported receipt schema")
    candidate = receipt.get("candidate")
    if not isinstance(candidate, dict):
        raise EvidenceError("candidate identity is required")
    for name in ("id", "runtime", "runtime_revision", "model_revision"):
        _text(candidate.get(name), name)
    kind = receipt.get("evidence_kind")
    if kind not in {"physical_device", "simulator", "synthetic"}:
        raise EvidenceError("explicit evidence_kind required")
    _text(receipt.get("recorded_at"), "recorded_at")
    _text(receipt.get("evidence_ref"), "evidence_ref")
    if receipt.get("memory_scope") != "whole_stack_incremental_peak":
        raise EvidenceError("whole-stack incremental peak memory required; weights/app RSS alone are insufficient")
    for name in MATCH_FIELDS:
        value = receipt.get(name)
        # bool/int equality and omitted metadata must not create a match.
        if type(value) is not type(profile[name]) or value != profile[name]:
            raise EvidenceError(f"incomparable receipt: {name} differs from product profile")
    if receipt.get("inference_location") != "on_device" or receipt.get("offline_verified") is not True:
        raise EvidenceError("on-device execution and offline verification required")
    weights = candidate.get("weights_bytes")
    if weights is not None:
        _integer(weights, "weights_bytes", 1, 2**50)
    trials = receipt.get("trials")
    if not isinstance(trials, list) or not 1 <= len(trials) <= 50_000:
        raise EvidenceError("nonempty bounded trials required")
    ids, coverage, peaks, latencies = set(), {}, [], []
    passed = 0
    failed = 0
    critical_failed = False
    expected = set(profile["case_ids"])
    for trial in trials:
        if not isinstance(trial, dict):
            raise EvidenceError("trial must be an object")
        tid = _text(trial.get("id"), "trial.id")
        if tid in ids:
            raise EvidenceError("duplicate trial ID")
        ids.add(tid)
        case = _text(trial.get("case_id"), "trial.case_id")
        if case not in expected:
            raise EvidenceError("trial case is not in the evaluation dataset")
        coverage[case] = coverage.get(case, 0) + 1
        if type(trial.get("quality_pass")) is not bool:
            raise EvidenceError("every trial needs an explicit quality verdict")
        outcome = trial.get("outcome")
        if outcome not in {"completed", "failed", "timeout", "cancelled"}:
            raise EvidenceError("trial outcome required")
        if outcome != "completed":
            failed += 1
            if trial["quality_pass"]:
                raise EvidenceError("failed trials cannot claim quality success")
        else:
            peaks.append(_integer(trial.get("peak_stack_bytes"), "peak_stack_bytes", 1, 2**50))
            latencies.append(_number(trial.get("latency_ms"), "latency_ms", 0, 86_400_000))
            passed += int(trial["quality_pass"])
        if case in profile["critical_case_ids"] and not trial["quality_pass"]:
            critical_failed = True
    # Equal repeats prevent weighting the easiest cases more heavily.
    counts = [coverage.get(case, 0) for case in profile["case_ids"]]
    if min(counts) < profile["min_repeats"] or len(set(counts)) != 1:
        raise EvidenceError("each evaluation case needs the same number of repeats, meeting min_repeats")
    peak = max(peaks) if peaks else None
    required = math.ceil(peak * (1 + profile["headroom_fraction"])) if peak else None
    p95 = sorted(latencies)[math.ceil(len(latencies) * .95) - 1] if latencies else None
    quality = passed / len(trials)
    reasons = []
    if failed:
        reasons.append("not_all_trials_completed")
    if quality < profile["min_quality"]:
        reasons.append("quality_below_floor")
    if critical_failed:
        reasons.append("critical_case_failed")
    if required is None or required > profile["memory_budget_bytes"]:
        reasons.append("memory_budget_exceeded_or_unknown")
    if p95 is None or p95 > profile["max_p95_latency_ms"]:
        reasons.append("latency_limit_exceeded_or_unknown")
    return {
        "candidate": candidate, "evidence_kind": kind,
        "qualified_for_tested_profile": not reasons and kind == "physical_device",
        "passes_demo_gates": not reasons and kind != "physical_device",
        "reasons": reasons + ([] if kind == "physical_device" else ["not_physical_device_evidence"]),
        "quality": quality, "trials": len(trials), "failed_trials": failed,
        "peak_stack_bytes": peak, "required_with_headroom_bytes": required,
        "p95_latency_ms": p95, "evidence_ref": receipt["evidence_ref"],
    }


def select(profile, receipts):
    """Select minimum measured memory among qualified, comparable observations."""
    validate_profile(profile)
    if not isinstance(receipts, list) or len(receipts) > 500:
        raise EvidenceError("receipts must be a list of at most 500 candidates")
    rows = []
    seen = set()
    for receipt in receipts:
        candidate = receipt.get("candidate") if isinstance(receipt, dict) else None
        cid = candidate.get("id") if isinstance(candidate, dict) else None
        if isinstance(cid, str):
            if cid in seen:
                raise EvidenceError("duplicate candidate ID; combine its trials in one receipt")
            seen.add(cid)
        try:
            row = _evaluate(profile, receipt)
        except EvidenceError as error:
            rows.append({"qualified_for_tested_profile": False, "reasons": [str(error)],
                         "receipt_index": len(rows)})
            continue
        rows.append(row)
    qualified = sorted((r for r in rows if r["qualified_for_tested_profile"]),
                       key=lambda r: (r["peak_stack_bytes"], r["p95_latency_ms"], r["candidate"]["id"]))
    return {
        "schema": "beanfit.mobile.selection.v1", "product": profile["product"],
        "status": "smallest_qualified_observed" if qualified else "needs_device_evidence",
        "selection": qualified[0]["candidate"] if qualified else None,
        "ranking": [r["candidate"]["id"] for r in qualified], "candidates": rows,
        "policy": "quality and reliability gates first; minimum measured whole-stack peak memory; latency breaks ties",
        "limits": ["Only supplied candidates and the exact tested profile are compared.",
                   "Receipts and offline/quality claims are self-reported, not device attestation.",
                   "No iPhone inference, download, or installation is performed by this command.",
                   "System-managed memory must be included; absent comparable accounting means unknown."],
    }


def mobile_main(argv=None):
    parser = argparse.ArgumentParser(prog="beanfit mobile", description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--receipts", required=True, type=Path, help="JSON array of candidate receipts")
    args = parser.parse_args(argv)
    try:
        def read(path):
            if path.stat().st_size > 16 * 1024 * 1024:
                raise EvidenceError("input exceeds 16 MiB")
            return json.loads(path.read_text())
        result = select(read(args.profile), read(args.receipts))
    except (OSError, ValueError) as error:
        print(f"beanfit mobile: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0
