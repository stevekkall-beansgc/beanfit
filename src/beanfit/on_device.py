"""Pinned on-device candidates and conservative, task-specific trial suggestions.

Catalog metadata cannot qualify a model. Use reviewed physical receipts through
``beanfit mobile`` to select the smallest passing complete configuration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


CATALOG_PATH = Path(__file__).with_name("catalog") / "on_device.json"


def catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def target_device(device):
    """Known iPhone hardware identifiers only; marketing names are not probes."""
    return any(row["id"] == device for row in catalog()["devices"])


def suggest(*, experience="text_assistant", device="unknown", os_major=None,
            memory_budget_bytes=None, context_tokens=2048, preference="balanced"):
    doc = catalog()
    experiences = {e["id"]: e for e in doc["experiences"]}
    if not isinstance(experience, str) or experience not in experiences:
        raise ValueError("unknown experience")
    if not isinstance(device, str) or not 1 <= len(device) <= 80:
        raise ValueError("device must be a bounded hardware identifier")
    if os_major is not None and (type(os_major) is not int or not 1 <= os_major <= 100):
        raise ValueError("os_major must be an integer")
    if memory_budget_bytes is not None and (type(memory_budget_bytes) is not int
                                            or not 1 <= memory_budget_bytes <= 2**50):
        raise ValueError("memory_budget_bytes must be a positive integer")
    if type(context_tokens) is not int or not 1 <= context_tokens <= doc["native_context_tokens"]:
        raise ValueError("context exceeds the current embedded runtime limit")
    if preference not in ("balanced", "smallest_download"):
        raise ValueError("preference must be balanced or smallest_download")
    task = experiences[experience]
    known_device = target_device(device)
    priority = {cid: i for i, cid in enumerate(task["trial_order"])}
    rows = []
    for model in doc["models"]:
        if experience not in model["capabilities"]:
            continue
        size = sum(a["bytes"] for a in model["artifacts"])
        if model["runtime_status"] != "native_text_candidate":
            status = "requires_runtime_integration"
        elif experience in model["failed_experiences"]:
            status = "known_task_failure"
        elif not known_device:
            status = "unsupported_or_unknown_device"
        elif os_major is None or os_major < doc["minimum_ios"]:
            status = "unsupported_or_unknown_os"
        elif memory_budget_bytes is not None and size >= memory_budget_bytes:
            # Conservative pre-trial file-size screen, not a RAM measurement.
            # Memory mapping means file size is not a strict resident-memory
            # bound; reviewed whole-stack measurements own actual selection.
            status = "weights_exceed_memory_budget"
        else:
            status = "needs_device_evidence"
        rows.append({"id": model["id"], "name": model["name"], "status": status,
                     "eligible_for_trial": status == "needs_device_evidence",
                     "download_bytes": size, "memory_fit": "unknown",
                     "qualified": False, "summary": model["summary"],
                     "source_url": model["source_url"], "artifacts": model["artifacts"]})
    if preference == "smallest_download":
        rows.sort(key=lambda r: (r["download_bytes"], r["id"]))
    else:
        rows.sort(key=lambda r: (priority[r["id"]], r["id"]))
    return {"schema": "beanfit.on-device.suggestions.v1", "catalog_as_of": doc["as_of"],
            "experience": experience, "device": device, "os_major": os_major,
            "context_tokens": context_tokens, "memory_budget_bytes": memory_budget_bytes,
            "preference": preference, "status": "needs_device_evidence", "selection": None,
            "trial_order": [r["id"] for r in rows if r["eligible_for_trial"]],
            "fallback": task["fallback"], "candidates": rows,
            "limits": [doc["trial_order_basis"], doc["artifact_scope"],
                       "A budget is the application's incremental memory allocation, not nominal phone RAM.",
                       "No candidate is production-qualified by this catalog or trial ordering.",
                       "Use beanfit mobile with reviewed, comparable physical whole-stack receipts for a selection."]}


def select_catalog(profile, receipts, *, experience="text_assistant"):
    """Bind reviewed mobile trials to exact catalog artifacts before selection.

    This remains a self-reported evidence evaluation, not device attestation.
    """
    from beanfit.mobile import MATCH_FIELDS, select, validate_profile

    validate_profile(profile)
    if profile.get("catalog_experience") != experience:
        raise ValueError("profile must pin catalog_experience to the requested experience")
    if type(profile.get("ios_major")) is not int:
        raise ValueError("profile must specify ios_major in addition to the exact os_build")
    if not isinstance(receipts, list) or len(receipts) > 500:
        raise ValueError("receipts must be a list of at most 500 candidates")
    if profile["output_limit_tokens"] > catalog()["native_output_tokens"]:
        raise ValueError("output limit exceeds the embedded runtime contract")
    screened = suggest(experience=experience, device=profile["device"], os_major=profile["ios_major"],
                       context_tokens=profile["context_tokens"])
    eligible = {row["id"]: row for row in screened["candidates"] if row["eligible_for_trial"]}
    accepted, rejected = [], []
    for index, receipt in enumerate(receipts):
        candidate = receipt.get("candidate", {}) if isinstance(receipt, dict) else {}
        if not isinstance(candidate, dict):
            candidate = {}
        cid = candidate.get("id")
        row = eligible.get(cid) if isinstance(cid, str) else None
        artifact = row["artifacts"][0] if row else None
        identity_ok = artifact is not None and all((
            candidate.get("runtime") == "llama.cpp",
            candidate.get("runtime_revision") == catalog()["runtime_revision"],
            candidate.get("model_revision") == artifact["revision"],
            candidate.get("artifact_sha256") == artifact["sha256"],
            candidate.get("repository") == artifact["repository"],
            type(candidate.get("weights_bytes")) is int and candidate["weights_bytes"] == artifact["bytes"],
            all(type(receipt.get(k)) is type(profile[k]) and receipt.get(k) == profile[k] for k in MATCH_FIELDS),
        ))
        if not identity_ok:
            rejected.append({"receipt_index": index, "candidate_id": cid,
                             "reason": "unsupported candidate, failed task gate, or pinned identity/profile mismatch"})
        else:
            accepted.append(receipt)
    result = select(profile, accepted)
    result["catalog_as_of"] = catalog()["as_of"]
    result["catalog_experience"] = experience
    result["catalog_rejections"] = rejected
    return result


def suggest_main(argv=None):
    parser = argparse.ArgumentParser(prog="beanfit suggest", description=__doc__)
    parser.add_argument("--experience", default="text_assistant")
    parser.add_argument("--device", default="unknown", help="hardware identifier, for example iPhone15,3")
    parser.add_argument("--ios", type=int, dest="os_major")
    parser.add_argument("--memory-budget-mib", type=int)
    parser.add_argument("--context-tokens", type=int, default=2048)
    parser.add_argument("--preference", default="balanced", choices=["balanced", "smallest_download"])
    parser.add_argument("--catalog", action="store_true", help="export all pinned on-device candidates")
    parser.add_argument("--profile", type=Path, help="qualification profile with catalog_experience and ios_major")
    parser.add_argument("--receipts", type=Path, help="reviewed physical trials with exact catalog identity")
    args = parser.parse_args(argv)
    try:
        if bool(args.profile) != bool(args.receipts) or (args.catalog and args.profile):
            raise ValueError("provide both --profile and --receipts; do not combine them with --catalog")
        if args.profile:
            def read(path):
                if path.stat().st_size > 16 * 1024 * 1024:
                    raise ValueError("input exceeds 16 MiB")
                return json.loads(path.read_text())
            result = select_catalog(read(args.profile), read(args.receipts), experience=args.experience)
        else:
            result = catalog() if args.catalog else suggest(
            experience=args.experience, device=args.device, os_major=args.os_major,
            memory_budget_bytes=None if args.memory_budget_mib is None else args.memory_budget_mib * 1024**2,
            context_tokens=args.context_tokens, preference=args.preference)
    except (OSError, ValueError) as error:
        print(f"beanfit suggest: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0
