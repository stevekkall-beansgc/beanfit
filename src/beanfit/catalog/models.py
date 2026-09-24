from __future__ import annotations

from typing import NamedTuple

# Illustrative 2026 subset (production build syncs Ollama/HF registries).
# sizes_gib = weights at that quant incl. activation slop;
# kv32k_gib = KV cache cost for a 32k context window.
# quality c/r/chat = coding / reasoning / chat, each 0-10.
# Tags can be checked against live registries by scripts/validate_catalog.py;
# release operators can manually retain a receipt from a clean checkout.


class ModelEntry(NamedTuple):
    name: str
    runtime_tag: str
    params_b: int
    mem_q4_gib: float
    mem_q8_gib: float
    kv32k_gib: float
    qual_coding: int
    qual_reasoning: int
    qual_chat: int


CATALOG: list[ModelEntry] = [
    ModelEntry(
        name="Qwen3 8B", runtime_tag="qwen3:8b", params_b=8,
        mem_q4_gib=5.2, mem_q8_gib=8.9, kv32k_gib=0.9,
        qual_coding=7, qual_reasoning=7, qual_chat=8,
    ),
    ModelEntry(
        name="Phi-4-reasoning 14B", runtime_tag="phi4-reasoning:14b", params_b=14,
        mem_q4_gib=11.0, mem_q8_gib=17.0, kv32k_gib=1.2,
        qual_coding=7, qual_reasoning=8, qual_chat=7,
    ),
    ModelEntry(
        name="gpt-oss 20b (MXFP4)", runtime_tag="gpt-oss:20b", params_b=21,
        mem_q4_gib=14.0, mem_q8_gib=14.0, kv32k_gib=1.4,
        qual_coding=9, qual_reasoning=8, qual_chat=8,
    ),
    ModelEntry(
        name="Gemma 3 27B", runtime_tag="gemma3:27b", params_b=27,
        mem_q4_gib=17.0, mem_q8_gib=30.0, kv32k_gib=1.8,
        qual_coding=9, qual_reasoning=8, qual_chat=9,
    ),
    ModelEntry(
        name="Qwen3 30B-A3B (MoE)", runtime_tag="qwen3:30b-a3b", params_b=30,
        mem_q4_gib=19.0, mem_q8_gib=32.0, kv32k_gib=1.9,
        qual_coding=9, qual_reasoning=9, qual_chat=9,
    ),
    ModelEntry(
        name="Llama 4 Scout 109B (16x17B MoE)", runtime_tag="llama4:scout", params_b=109,
        mem_q4_gib=67.0, mem_q8_gib=117.0, kv32k_gib=1.5,
        qual_coding=8, qual_reasoning=7, qual_chat=8,
    ),
    ModelEntry(
        name="DeepSeek Coder V2 16B", runtime_tag="deepseek-coder-v2:16b", params_b=16,
        mem_q4_gib=10.0, mem_q8_gib=17.0, kv32k_gib=1.3,
        qual_coding=9, qual_reasoning=6, qual_chat=5,
    ),
    ModelEntry(
        name="Mistral Small 3.1 24B", runtime_tag="mistral-small3.1:24b", params_b=24,
        mem_q4_gib=15.0, mem_q8_gib=26.0, kv32k_gib=1.6,
        qual_coding=8, qual_reasoning=7, qual_chat=8,
    ),
]

USE_CASES = ("chat", "coding", "reasoning")

# Verified HF MLX repos per ollama tag (resolved via registry search
# 2026-08-23). The old `tag.replace(':','-')-4bit` heuristic produced dead
# repos for most of these — always pin, never guess. Tags without an entry
# have no vetted MLX build; the launcher omits the MLX alternative for them.
MLX_REPOS = {
    "qwen3:8b": "mlx-community/Qwen3-8B-4bit",
    "phi4-reasoning:14b": "mlx-community/Phi-4-reasoning-4bit",
    "gpt-oss:20b": "mlx-community/gpt-oss-20b-MXFP4-Q4",
    "gemma3:27b": "mlx-community/gemma-3-27b-it-4bit",
    "qwen3:30b-a3b": "mlx-community/Qwen3-30B-A3B-4bit",
    "llama4:scout": "mlx-community/Llama-4-Scout-17B-16E-4bit",
    "deepseek-coder-v2:16b": "mlx-community/DeepSeek-Coder-V2-Lite-Instruct-4bit",
    "mistral-small3.1:24b": "mlx-community/Mistral-Small-3.1-24B-Instruct-2503-4bit",
}


def mlx_repo_for(tag: str) -> str | None:
    return MLX_REPOS.get(tag)
