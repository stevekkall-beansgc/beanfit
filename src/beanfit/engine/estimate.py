from __future__ import annotations

# decode tok/s ≈ memory bandwidth / bytes-per-token-pass, damped 15% for
# scheduler/activation overhead; q8 decodes slower than q4 at the same BW.
# Keys are the exact quant labels engine/evaluate.py emits.
QUANT_SPEEDUP = {"q4_K_M": 1.00, "q8_0": 0.62}

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
    return bandwidth_gbs / total_mem_gib * 0.85 * QUANT_SPEEDUP[quant]


def band_for(bw_source: str) -> int:
    return UNCERTAINTY_PCT.get(bw_source, DEFAULT_UNCERTAINTY_PCT)


def assumptions() -> dict:
    """The full estimation model, shipped with every --json output."""
    # Late imports: beanfit.engine.evaluate imports this module at load time.
    from beanfit.engine.evaluate import (
        FIT_BONUS,
        NO_FIT_PENALTY,
        SCORE_QUALITY_WEIGHT,
        SPEED_CAP_TOK_S,
        SPEED_TIEBREAK,
    )
    from beanfit.profile import MODEL_BUDGET_FLOOR_GIB, OS_HEADROOM_GIB

    return {
        "formula": "tok/s ≈ mem_bandwidth_GBs / total_weights_gib * 0.85 * quant_speedup",
        "quant_speedup": QUANT_SPEEDUP,
        "context_assumption": "half of a 32k-token KV cache included in total GiB",
        "budget_rule": (
            f"min(unified-memory cap, RAM - {OS_HEADROOM_GIB:g} GiB OS headroom), "
            f"floor {MODEL_BUDGET_FLOOR_GIB:g} GiB"
        ),
        "uncertainty_pct_by_bw_source": UNCERTAINTY_PCT,
        "score_weights": {
            "quality_weight": SCORE_QUALITY_WEIGHT,
            "speed_cap_tok_s": SPEED_CAP_TOK_S,
            "speed_tiebreak": SPEED_TIEBREAK,
            "fit_bonus": FIT_BONUS,
            "no_fit_penalty": NO_FIT_PENALTY,
        },
    }
