#!/usr/bin/env python3
"""beanfit — what local AI actually fits and runs well on THIS device (prototype).

Differentiator vs existing fit-checkers (llmfit, paddock, ModelFit): beanfit
sizes the whole stack decision — runtime choice (MLX vs GGUF), context budget,
and emits ready-to-run launch config — tuned for Apple Silicon first, where
unified memory + the Metal working-set cap decide everything.

Stdlib only.   Usage:
    python3 beanfit.py                       # ranked table, chat use case
    python3 beanfit.py --use-case coding     # or reasoning|chat
    python3 beanfit.py --json                # machine-readable output
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys

# ------------------------------------------------------------- hardware ----


def sh(*args: str) -> str:
    try:
        return subprocess.check_output(args, text=True).strip()
    except Exception:
        return ""


def detect() -> dict:
    chip = sh("sysctl", "-n", "machdep.cpu.brand_string") or platform.machine()
    ram_bytes = int(sh("sysctl", "-n", "hw.memsize") or 0)
    wired = int(sh("sysctl", "-n", "iogpu.wired_limit_mb") or 0)  # 0 => default

    ram_gib = ram_bytes / 2**30 if ram_bytes else 8.0
    # macOS caps GPU-wired memory at ~75% of RAM by default.
    metal_cap_gib = (wired / 1024) if wired > 0 else round(ram_gib * 0.75, 1)
    # keep headroom for OS + apps regardless of cap
    budget_gib = max(4.0, min(metal_cap_gib, ram_gib - 4))

    m = re.search(r"Apple (M\d+)(?:\s*(Pro|Max|Ultra))?", chip)
    fam, var = (m.group(1), m.group(2) or "") if m else ("", "")
    bw = BANDWIDTH.get((fam, var), BANDWIDTH.get((fam, ""), 60.0))
    return {
        "chip": chip, "family": fam, "variant": var,
        "ram_gib": round(ram_gib, 1),
        "metal_cap_gib": metal_cap_gib,
        "model_budget_gib": round(budget_gib, 1),
        "mem_bandwidth_gbs": bw,          # ESTIMATE from family tables
        "arch": "apple_silicon" if fam.startswith("M") else "other",
    }


BANDWIDTH = {  # public spec sheets; unknown variants fall back conservatively
    ("M1", ""): 68, ("M1", "Pro"): 200, ("M1", "Max"): 400, ("M1", "Ultra"): 800,
    ("M2", ""): 100, ("M2", "Pro"): 200, ("M2", "Max"): 400, ("M2", "Ultra"): 800,
    ("M3", ""): 100, ("M3", "Pro"): 150, ("M3", "Max"): 400, ("M3", "Ultra"): 800,
    ("M4", ""): 120, ("M4", "Pro"): 273, ("M4", "Max"): 546,
    ("M5", ""): 150, ("M5", "Pro"): 330, ("M5", "Max"): 600,   # ESTIMATED
}

# --------------------------------------------------------------- catalog ---
# Illustrative 2026 subset (a production build would sync Ollama/HF registries
# like paddock does). sizes_gib = weights at that quant incl. activation slop;
# kv_gib_per_32k = KV cache cost for a 32k context window.

CATALOG = [
    # name, ollama tag / mlx repo, params_B, mem q4/q8 GiB, kv@32k, quality c/r/chat
    # tag reality-checked against ollama.com/library 2026-08-23 (agent audit)
    ["Qwen3.5 9B Instruct",      "qwen3.5:9b",        9,  6.2, 10.5, 0.9, 7, 7, 8],
    ["Phi-4-reasoning 14B",      "phi4-reasoning:14b",14,  9.3, 15.8, 1.2, 7, 8, 7],
    ["gpt-oss 20b (MXFP4)",      "gpt-oss:20b",      21, 12.5, 20.0, 1.4, 9, 8, 8],
    ["Gemma 4 31B",              "gemma4:31b",       31, 19.5, 33.0, 1.8, 9, 8, 9],
    ["Qwen3.6 35B-A3B (MoE)",    "qwen3.6:35b-a3b",  35, 21.5, 36.0, 1.9, 9, 9, 9],
    ["Llama 4 Scout 17B",        "llama4:scout",     17, 11.0, 18.6, 1.5, 8, 7, 8],
    ["DeepSeek Coder V2 16B",    "deepseek-coder-v2:16b", 16, 10.5, 16.0, 1.3, 9, 6, 5],
    ["Mistral Small 3.2 24B",    "mistral-small3.2", 24, 15.0, 25.5, 1.6, 8, 7, 8],
    ["Kimi K2.6 A1B (MoE)",      "kimi-k2.6",       1000, 640, 700,  6.0, 10, 10, 9],
]

QUANT_SPEEDUP = {"q4": 1.00, "q8": 0.62}  # decode efficiency vs bandwidth math


def evaluate(hw: dict, use_case: str) -> list[dict]:
    rows = []
    qi = {"chat": 8, "coding": 7, "reasoning": 6}[use_case] - 1
    for name, tag, params, q4, q8, kv32k, code, reason, chat in CATALOG:
        qual = {"chat": chat, "coding": code, "reasoning": reason}[use_case]
        best = None
        for quant, mem in (("q4_K_M", q4), ("q8_0", q8)):
            total = mem + kv32k * 0.5          # half-32k context assumption
            if total <= hw["model_budget_gib"]:
                # decode tok/s ≈ memory bandwidth / bytes-per-token-pass
                tok_s = hw["mem_bandwidth_gbs"] / total * 0.85 \
                    * QUANT_SPEEDUP[quant.split("_")[0]]
                best = {"quant": quant, "weights_gib": mem, "total_gib": round(total, 1),
                        "est_tok_s": round(tok_s, 1)}
                break                          # highest-quality quant that fits first
        fits = bool(best)
        speed = best["est_tok_s"] if best else 0
        # score: quality dominates, usable speed breaks ties, no-fit disqualifies
        s = qual * 12 + min(speed, 60) * 0.15 + (10 if fits else -40)
        rows.append({"name": name, "runtime_tag": tag, "quality": qual,
                     "fits": fits, **(best or {}), "score": round(s, 1)})
    return sorted(rows, key=lambda r: r["score"], reverse=True)


def launch_cmd(row: dict, ctx_tokens: int) -> str:
    tag = row["runtime_tag"]
    return f"ollama pull {tag} && ollama run {tag}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--use-case", choices=["chat", "coding", "reasoning"],
                    default="chat")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    hw = detect()
    rows = evaluate(hw, args.use_case)

    if args.json:
        print(json.dumps({"hardware": hw, "use_case": args.use_case,
                          "ranked": rows}, indent=2))
        return 0

    arch_note = "" if hw["arch"] == "apple_silicon" else \
        "  [non-Apple-Silicon: estimates unreliable]"
    print(f"beanfit · {hw['chip']} · {hw['ram_gib']} GiB unified")
    print(f"Metal working-set cap ~{hw['metal_cap_gib']} GiB → "
          f"model budget {hw['model_budget_gib']} GiB "
          f"({hw['mem_bandwidth_gbs']} GB/s est BW){arch_note}\n")

    hdr = f"{'MODEL':<26}{'QUANT':<9}{'TOTAL':>7}{'TOK/S':>8}  {'FIT':<6}{'SCORE':>6}"
    print(hdr); print("-" * len(hdr))
    for r in rows[:8]:
        if r["fits"]:
            print(f"{r['name']:<26}{r['quant']:<9}{r['total_gib']:>6.1f}G"
                  f"{r['est_tok_s']:>8.1f}  {'yes':<6}{r['score']:>6}")
        else:
            print(f"{r['name']:<26}{'—':<9}{'—':>7}{'—':>8}  {'NO':<6}{r['score']:>6}")

    top = next((r for r in rows if r["fits"]), None)
    if top:
        print(f"\nPick: {top['name']} ({top['quant']}) — quality {top['quality']}/10, "
              f"~{top['est_tok_s']} tok/s est.")
        print(f"Run it:\n  $ {launch_cmd(top, 32768)}")
        print("MLX alternative (Apple Silicon, often faster decode):\n"
              f"  $ pip install mlx-lm && mlx_lm.generate --model "
              f"mlx-community/{top['runtime_tag'].replace(':', '-')}-4bit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
