from __future__ import annotations

# decode tok/s ≈ memory bandwidth / bytes-per-token-pass, damped 15% for
# scheduler/activation overhead; q8 decodes slower than q4 at the same BW.
QUANT_SPEEDUP = {"q4": 1.00, "q8": 0.62}

# Honesty bands by bandwidth source (±%, applied to every speed number shown).
# spec_sheet: published figure, real variance from thermals/OS pressure.
# estimate:   pre-release figure on top of that.
# unknown_fallback: chip not in tables at all.
UNCERTAINTY_PCT = {
    "spec_sheet": 25,
    "estimate": 40,
    "unknown_fallback": 50,
}
DEFAULT_UNCERTAINTY_PCT = 50


def decode_tok_s(bandwidth_gbs: float, total_mem_gib: float, quant: str) -> float:
    return bandwidth_gbs / total_mem_gib * 0.85 * QUANT_SPEEDUP[quant.split("_")[0]]


def band_for(bw_source: str) -> int:
    return UNCERTAINTY_PCT.get(bw_source, DEFAULT_UNCERTAINTY_PCT)


def assumptions() -> dict:
    """The full estimation model, shipped with every --json output."""
    return {
        "formula": "tok/s ≈ mem_bandwidth_GBs / total_weights_gib * 0.85 * quant_speedup",
        "quant_speedup": QUANT_SPEEDUP,
        "context_assumption": "half of a 32k-token KV cache included in total GiB",
        "budget_rule": "min(unified-memory cap, RAM - 4 GiB OS headroom), floor 4 GiB",
        "uncertainty_pct_by_bw_source": UNCERTAINTY_PCT,
    }
