from __future__ import annotations

from beanfit.emit.launch import launch_cmd, mlx_cmd


def render_table(hw: dict, rows: list[dict], use_case: str) -> str:
    out = []
    arch_note = "" if hw["arch"] == "apple_silicon" else \
        "  [non-Apple-Silicon: estimates unreliable]"
    bw_flag = "" if hw["bw_source"] == "spec_sheet" else \
        f" [BW {hw['bw_source'].replace('_', ' ')}]"
    out.append(f"beanfit · {hw['chip']} · {hw['ram_gib']} GiB unified")
    out.append(
        f"Metal working-set cap ~{hw['metal_cap_gib']} GiB → "
        f"model budget {hw['model_budget_gib']} GiB "
        f"(~{hw['mem_bandwidth_gbs']:.0f} GB/s ±"
        f"{_band(rows)}% est{bw_flag}){arch_note}\n"
    )

    hdr = f"{'MODEL':<26}{'QUANT':<9}{'TOTAL':>7}{'TOK/S':>8}  {'FIT':<6}{'SCORE':>6}"
    out.append(hdr)
    out.append("-" * len(hdr))
    for r in rows[:8]:
        if r["fits"]:
            out.append(f"{r['name']:<26}{r['quant']:<9}{r['total_gib']:>6.1f}G"
                       f"{r['est_tok_s']:>8.1f}  {'yes':<6}{r['score']:>6}")
        else:
            out.append(f"{r['name']:<26}{'—':<9}{'—':>7}{'—':>8}  {'NO':<6}{r['score']:>6}")

    top = next((r for r in rows if r["fits"]), None)
    if top:
        band = top.get("est_uncertainty_pct", 50)
        out.append(
            f"\nPick: {top['name']} ({top['quant']}) — quality {top['quality']}/10, "
            f"~{top['est_tok_s']} tok/s est (±{band}%). Verify: ollama run --verbose."
        )
        out.append(f"Run it:\n  $ {launch_cmd(top)}")
        mlx = mlx_cmd(top)
        if mlx:
            out.append("MLX alternative (Apple Silicon, often faster decode):\n"
                       f"  $ {mlx}")
    return "\n".join(out)


def _band(rows: list[dict]) -> int:
    for r in rows:
        if r.get("fits"):
            return r.get("est_uncertainty_pct", 50)
    return 50
