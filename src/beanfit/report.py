"""Deterministic, offline BF-CER-v1.0 report; no buyer text reaches commands."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from beanfit import __version__
from beanfit.catalog.models import CATALOG, MLX_REPOS
from beanfit.engine.evaluate import evaluate
from beanfit.engine.estimate import assumptions, decode_tok_s
from beanfit.emit.launch import launch_cmd, mlx_cmd
from beanfit.hw.bandwidth import lookup
from beanfit.hw.macos import DEFAULT_WIRED_RATIO
from beanfit.profile import MODEL_BUDGET_FLOOR_GIB, OS_HEADROOM_GIB

CONTRACT_VERSION = "BF-CER-v1.0"
DEFAULT_CONTEXT_TOKENS = 16384
REQUIRED = {"device_chip", "memory_gib", "use_case", "operating_system"}
OPTIONAL = {"preferred_runtime", "minimum_context_tokens", "latency_preference", "installed_runtime_versions", "constraints"}
POLICY = [
    "USD $12 covers one device, one use case, and one report revision; delivery within one business day after complete input is accepted.",
    "If delivery misses the SLA, the buyer may choose a full refund or a new agreed delivery time.",
    "An operator-caused defect reported within seven calendar days receives one corrected report within one business day at no charge; if it cannot be corrected, issue a full refund.",
    "For an incorrect or incomplete buyer-supplied device profile, one corrected run is included if requested within seven days; the SLA restarts on receipt of complete inputs.",
    "A runtime/catalog change after the timestamp is not a defect and requires a new order, unless the cited tag was already invalid at delivery.",
    "Support is limited to one clarification thread and one correction. No remote access, ongoing tuning, production incident support, installation, custom benchmarking, production deployment, unrelated troubleshooting, or unsupported configuration generation is included.",
    "Preference disagreement is not a defect. A wrong accepted input, dead catalog tag, arithmetic error, missing required section, or command not matching the cited catalog is a defect.",
    "Refunds and reversals are separate state events against the original transaction ID; they reduce promotion-eligible revenue and never overwrite earlier ledger entries.",
]
LIMITATIONS = [
    "This is technical compatibility information, not a measured benchmark. No model is downloaded or executed to create this report.",
    "Actual performance may fall outside the uncertainty band with thermals, OS pressure, context, prompt shape, runtime version, and model implementation.",
    "The catalog budgets half of a 32k-token KV cache (16384 tokens). A requested context at or below that assumption does not guarantee a model's native context capacity; verify the model and runtime locally. Launch commands do not configure context.",
    "Balanced ordering uses the original Beanfit score; quality ordering sorts by catalog quality then original score; speed ordering sorts by estimated decode speed then original score. These are deterministic adapter orderings, not new benchmarks. Nonempty workload constraints require manual review because arbitrary prose and personal-data content cannot be reliably interpreted or screened by this automated path.",
    "The GPU working-set cap is a 75% RAM fallback, not measured on the buyer's device. Bandwidth is a versioned table lookup or explicitly labeled fallback.",
    "Catalog quality scores and memory values are illustrative estimates. Fit does not prove output quality, model license suitability, privacy policy, or production reliability.",
    "Catalog membership is checked offline; live registry tag availability and exact installed quantization are not verified. Generic runtime tags may resolve to a different quantization; verify the downloaded artifact before relying on memory estimates.",
    "GB/s and GiB retain the original Beanfit estimator convention; this is an engineering approximation, not a precision physical model.",
    "No investment advice, managed execution, performance or income promises, customer-fund custody, or trading/brokerage action is included.",
]


class InputRejected(ValueError):
    """Safe rejection messages never include submitted values."""

    code = "INVALID_INPUT"


class NeedsReview(InputRejected):
    """Valid contract input outside automated coverage; never fulfilled or retained.

    This is an explicit manual handoff outcome, not evidence that a reviewer
    received the submission. Callers must discard buyer prose and only emit the
    safe status; the operator needs a separate redacted resubmission workflow.
    """

    code = "NEEDS_REVIEW"


def _reject(reason):
    raise InputRejected(reason)


def validate_input(input_dict: dict) -> dict:
    """Strict frozen fields; fail closed on free text and unsupported policies."""
    if type(input_dict) is not dict:
        _reject("Input must be an object; submit only the documented device fields.")
    if not REQUIRED <= input_dict.keys() or input_dict.keys() - REQUIRED - OPTIONAL:
        _reject("Missing required or unrecognized fields; redact and resubmit documented fields only.")
    value = dict(input_dict)
    chip = value["device_chip"]
    if not isinstance(chip, str) or not re.fullmatch(r"Apple M[1-9][0-9]?(?: (?:Pro|Max|Ultra))?", chip):
        _reject("An exact Apple Silicon chip label is required.")
    if type(value["memory_gib"]) is not int or not 8 <= value["memory_gib"] <= 4096:
        _reject("Supported Apple Silicon profiles require whole-number memory from 8 through 4096 GiB; smaller profiles cannot satisfy the OS reserve and model-budget floor safely.")
    if not isinstance(value["use_case"], str) or value["use_case"] not in ("chat", "coding", "reasoning"):
        _reject("Use case must be chat, coding, or reasoning.")
    os_value = value["operating_system"]
    if not isinstance(os_value, str) or not re.fullmatch(r"macOS [0-9]{1,2}(?:\.[0-9]{1,3}){0,2} (?:arm64|Apple Silicon)", os_value):
        _reject("OS must specify macOS version and Apple Silicon architecture, for example macOS 15.6 arm64.")
    for field, default, allowed in (("preferred_runtime", "no preference", ("ollama", "mlx", "no preference")), ("latency_preference", "balanced", ("quality", "balanced", "speed"))):
        value.setdefault(field, default)
        if not isinstance(value[field], str) or value[field] not in allowed:
            _reject("Unsupported runtime or latency policy; use the documented choices.")
    value.setdefault("minimum_context_tokens", DEFAULT_CONTEXT_TOKENS)
    if type(value["minimum_context_tokens"]) is not int or value["minimum_context_tokens"] < 1:
        _reject("Minimum context must be a positive whole number.")
    value.setdefault("installed_runtime_versions", {})
    versions = value["installed_runtime_versions"]
    if type(versions) is not dict or versions.keys() - {"ollama", "mlx"} or any(not isinstance(v, str) or not re.fullmatch(r"[0-9]{1,4}(?:\.[0-9]{1,4}){1,3}(?:-(?:alpha|beta|rc)[0-9]{0,3})?", v) for v in versions.values()):
        _reject("Runtime versions must contain only ollama/mlx numeric version strings; no credentials or logs.")
    value.setdefault("constraints", "")
    constraints = value["constraints"]
    if not isinstance(constraints, str) or len(constraints.split()) > 500:
        _reject("Constraints must be plain language with at most 500 words.")
    # Recognizable patterns only: this is not a general personal-data detector.
    # Every other nonempty submission is discarded with NEEDS_REVIEW as well.
    sensitive = re.compile(
        r"(?:private[ _-]?key|password|credential|secret|bearer|api[ _-]?key|"
        r"access[ _-]?token|apify_api_|sk-[A-Za-z0-9]|gh[pousr]_|"
        r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"
        r"\b\d{3}-\d{2}-\d{4}\b|\b(?:ssn|social security)\b|"
        r"\b(?:\d[ -]?){13,19}\b)", re.IGNORECASE)
    if sensitive.search(constraints) or any(ord(c) < 32 and c not in "\n\r\t" for c in constraints):
        _reject("Sensitive or non-plain-language input detected; remove credentials, personal customer data, and logs before resubmission.")
    if value["minimum_context_tokens"] > DEFAULT_CONTEXT_TOKENS or constraints:
        raise NeedsReview("Manual review required for context beyond the catalog assumption or workload constraints. No report was generated or submission forwarded; arrange a redacted resubmission with the operator.")
    return value


def generate_report(input_dict: dict, *, generated_at: str, repository_revision: str) -> dict:
    accepted = validate_input(input_dict)
    if not isinstance(repository_revision, str) or not re.fullmatch(r"[0-9a-f]{40}", repository_revision):
        _reject("An immutable 40-character repository revision is required.")
    try:
        timestamp = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        _reject("Generation timestamp must be ISO-8601 with timezone.")
    family_variant = accepted["device_chip"][6:].split(" ", 1)
    family, variant = family_variant[0], family_variant[1] if len(family_variant) > 1 else ""
    bw, source = lookup(family, variant)
    ram = accepted["memory_gib"]
    cap = round(ram * DEFAULT_WIRED_RATIO, 1)
    # Keep the original detector budget math, including its documented floor.
    budget = max(MODEL_BUDGET_FLOOR_GIB, min(cap, ram - OS_HEADROOM_GIB))
    hw = dict(os="macos", arch="apple_silicon", backend="unified", chip=accepted["device_chip"], family=family, variant=variant, ram_gib=ram, metal_cap_gib=cap, model_budget_gib=budget, mem_bandwidth_gbs=bw, bw_source=source)
    rows = []
    catalog_by_tag = {entry.runtime_tag: entry for entry in CATALOG}
    candidates = evaluate(hw, accepted["use_case"])
    preference = accepted["latency_preference"]
    if preference == "quality":
        candidates.sort(key=lambda row: (row["quality"], row["score"]), reverse=True)
    elif preference == "speed":
        candidates.sort(key=lambda row: (row.get("est_tok_s", 0), row["score"]), reverse=True)
    for candidate in candidates:
        if not candidate["fits"]:
            continue
        if accepted["preferred_runtime"] == "mlx" and candidate["runtime_tag"] not in MLX_REPOS:
            continue
        entry = catalog_by_tag[candidate["runtime_tag"]]
        total = candidate["weights_gib"] + entry.kv32k_gib * 0.5
        estimate = decode_tok_s(bw, total, candidate["quant"])
        band = candidate["est_uncertainty_pct"] / 100
        rows.append(dict(candidate, rank=len(rows) + 1, full_32k_kv_gib=entry.kv32k_gib, included_kv_gib=entry.kv32k_gib * 0.5, calculation_total_gib=total, headroom_gib=budget-total, budget_used_pct=total / budget * 100, estimate_unrounded_tok_s=estimate, estimate_band_tok_s=[estimate*(1-band), estimate*(1+band)]))
    commands = []
    if rows:
        top = rows[0]
        ollama = dict(runtime="ollama", catalog_tag=top["runtime_tag"], command=launch_cmd(top))
        mlx = dict(runtime="mlx", catalog_tag=MLX_REPOS.get(top["runtime_tag"]), command=mlx_cmd(top))
        commands = [item for item in ([mlx, ollama] if accepted["preferred_runtime"] == "mlx" else [ollama, mlx]) if item["command"]]
    catalog_hash = hashlib.sha256(Path(__file__).with_name("catalog").joinpath("models.py").read_bytes()).hexdigest()
    versions = dict(beanfit=__version__, repository_revision=repository_revision, catalog_sha256=catalog_hash, catalog_hash_scope="src/beanfit/catalog/models.py bytes", report_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    provenance = {key: ("buyer-supplied" if key in input_dict else "documented fallback") for key in accepted}
    report = dict(contract_version=CONTRACT_VERSION, generated_at=generated_at, accepted_inputs=accepted, provenance=provenance, versions=versions, device_profile=hw, assumptions=assumptions(), ranked_options=rows, commands=commands, limitations=LIMITATIONS[:], policy=POLICY[:], catalog_live_validation="not performed; offline catalog membership only", ranking_policy={"preference": preference, "balanced": "original Beanfit score descending", "quality": "catalog quality then original score descending", "speed": "estimated decode speed then original score descending", "source": "deterministic adapter ordering; estimator values unchanged"})
    lines = ["# Beanfit Compatibility Evidence Report", "", f"Contract: {CONTRACT_VERSION} · Generated: {generated_at}", "", "## Accepted inputs", ""]
    for key, val in accepted.items():
        lines.append(f"- {key}: {json.dumps(val, sort_keys=True)} ({provenance[key]})")
    lines += ["", "## Versioned evidence", "", *[f"- {key}: `{val}`" for key, val in versions.items()], f"- Bandwidth: {bw:g} GB/s; source: {source}.", "- Live registry validation: not performed; offline catalog membership only.", "", "## Fit and memory math", "", f"Buyer-supplied RAM: {ram} GiB. Fallback Metal cap: {cap:g} GiB (75% RAM). Model budget: {budget:g} GiB = max({MODEL_BUDGET_FLOOR_GIB:g}, min({cap:g}, {ram} - {OS_HEADROOM_GIB:g})).", "", "Assumptions:", "```json", json.dumps(assumptions(), indent=2, sort_keys=True), "```", "", "## Ranked compatible options", "", "| Rank | Model | Quant | Total GiB | Estimated tok/s | Estimated band tok/s |", "|---:|---|---|---:|---:|---| "]
    for row in rows:
        lo, hi = row["estimate_band_tok_s"]
        lines.append(f'| {row["rank"]} | {row["name"]} | {row["quant"]} | {row["calculation_total_gib"]:.8g} | {row["est_tok_s"]:.1f} | {lo:.2f}–{hi:.2f} (±{row["est_uncertainty_pct"]}%) |')
    if len(rows) < 3:
        lines += ["", f"Fewer than three compatible options fit the memory budget and requested runtime: {len(rows)} found."]
    if rows:
        top = rows[0]
        lines += ["", f'Top choice: {top["name"]}. Unrounded memory calculation: {top["weights_gib"]} + {top["full_32k_kv_gib"]} / 2 = {top["calculation_total_gib"]:.12g} GiB <= {budget:g} GiB budget; headroom {top["headroom_gib"]:.12g} GiB; budget use {top["budget_used_pct"]:.6g}%.', "Estimated decode uses bandwidth / unrounded total × 0.85 × quant speedup; the table includes its uncertainty band."]
    lines += ["", "## Catalog-pinned commands", ""]
    for index, command in enumerate(commands):
        lines += [f'{"Primary" if index == 0 else "Alternate"} {command["runtime"]} path:', "```sh", command["command"], "```"]
    if not commands:
        lines.append("No compatible catalog command can be recommended for these inputs.")
    elif len(commands) < 2:
        lines.append("No alternate runtime command is available for the top choice in this catalog.")
    lines += ["", "## Local verification checklist", "", "- Check the cited runtime tag/repository still exists and confirm downloaded quantization and native context capacity.", "- Record installed runtime versions; run the chosen catalog command locally using a non-sensitive test prompt.", "- For Ollama use its --verbose option locally; compare measured throughput and memory pressure with the estimated band. This report does not claim a measured benchmark.", "- Stop if memory pressure is excessive. Retain the report and local measurements; never send secrets or private prompts to support.", "", "## Uncertainty and limitations", "", *[f"- {item}" for item in LIMITATIONS], "", "## Correction, refund, and support policy", "", *[f"- {item}" for item in POLICY]]
    report["markdown"] = "\n".join(lines) + "\n"
    return report
