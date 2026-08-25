from __future__ import annotations

from beanfit.catalog.models import CATALOG
from beanfit.engine.estimate import band_for, decode_tok_s
from beanfit.profile import DeviceProfile

SCORE_QUALITY_WEIGHT = 12
SPEED_CAP_TOK_S = 60
SPEED_TIEBREAK = 0.15
FIT_BONUS = 10
NO_FIT_PENALTY = -40


def evaluate(hw: DeviceProfile, use_case: str) -> list[dict]:
    rows = []
    band = band_for(hw["bw_source"])
    for name, tag, params, q4, q8, kv32k, code, reason, chat in CATALOG:
        qual = {"chat": chat, "coding": code, "reasoning": reason}[use_case]
        best = None
        for quant, mem in (("q4_K_M", q4), ("q8_0", q8)):
            total = mem + kv32k * 0.5          # half-32k context assumption
            if total <= hw["model_budget_gib"]:
                tok_s = decode_tok_s(hw["mem_bandwidth_gbs"], total, quant)
                best = {
                    "quant": quant,
                    "weights_gib": mem,
                    "total_gib": round(total, 1),
                    "est_tok_s": round(tok_s, 1),
                    "est_uncertainty_pct": band,
                }
                break                          # highest-quality quant that fits first
        fits = bool(best)
        speed = best["est_tok_s"] if best else 0
        # score: quality dominates, usable speed breaks ties, no-fit disqualifies
        s = (qual * SCORE_QUALITY_WEIGHT
             + min(speed, SPEED_CAP_TOK_S) * SPEED_TIEBREAK
             + (FIT_BONUS if fits else NO_FIT_PENALTY))
        rows.append({"name": name, "runtime_tag": tag, "quality": qual,
                     "fits": fits, **(best or {}), "score": round(s, 1)})
    return sorted(rows, key=lambda r: r["score"], reverse=True)
