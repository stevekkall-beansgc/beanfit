from __future__ import annotations

# Illustrative 2026 subset (production build syncs Ollama/HF registries).
# sizes_gib = weights at that quant incl. activation slop;
# kv_gib_per_32k = KV cache cost for a 32k context window.
# Columns: name, ollama tag, params_B, mem q4/q8 GiB, kv@32k, quality c/r/chat
# Tags are reality-checked against ollama.com by scripts/validate_catalog.py;
# CI fails the release if any tag 404s.

CATALOG = [
    ["Qwen3.5 9B Instruct",      "qwen3.5:9b",            9,  6.2, 10.5, 0.9, 7, 7, 8],
    ["Phi-4-reasoning 14B",      "phi4-reasoning:14b",    14,  9.3, 15.8, 1.2, 7, 8, 7],
    ["gpt-oss 20b (MXFP4)",      "gpt-oss:20b",           21, 12.5, 20.0, 1.4, 9, 8, 8],
    ["Gemma 4 31B",              "gemma4:31b",            31, 19.5, 33.0, 1.8, 9, 8, 9],
    ["Qwen3.6 35B-A3B (MoE)",    "qwen3.6:35b-a3b",       35, 21.5, 36.0, 1.9, 9, 9, 9],
    ["Llama 4 Scout 17B",        "llama4:scout",          17, 11.0, 18.6, 1.5, 8, 7, 8],
    ["DeepSeek Coder V2 16B",    "deepseek-coder-v2:16b", 16, 10.5, 16.0, 1.3, 9, 6, 5],
    ["Mistral Small 3.2 24B",    "mistral-small3.2",      24, 15.0, 25.5, 1.6, 8, 7, 8],
    ["Kimi K2.6 A1B (MoE)",      "kimi-k2.6",           1000, 640, 700,  6.0, 10, 10, 9],
]

USE_CASES = ("chat", "coding", "reasoning")

# Verified HF MLX repos per ollama tag (resolved via registry search
# 2026-08-23). The old `tag.replace(':','-')-4bit` heuristic produced dead
# repos for most of these — always pin, never guess. Tags without an entry
# have no vetted MLX build; the launcher omits the MLX alternative for them.
MLX_REPOS = {
    "qwen3.5:9b": "mlx-community/Qwen3.5-9B-4bit",
    "phi4-reasoning:14b": "mlx-community/Phi-4-reasoning-4bit",
    "gpt-oss:20b": "mlx-community/gpt-oss-20b-MXFP4-Q4",
    "gemma4:31b": "mlx-community/gemma-4-31b-it-4bit",
    "qwen3.6:35b-a3b": "mlx-community/Qwen3.6-35B-A3B-4bit",
    "llama4:scout": "mlx-community/Llama-4-Scout-17B-16E-4bit",
    "deepseek-coder-v2:16b": "mlx-community/DeepSeek-Coder-V2-Lite-Instruct-4bit",
    "mistral-small3.2": "mlx-community/Mistral-Small-3.2-24B-Instruct-2506-4bit",
}


def mlx_repo_for(tag: str) -> str | None:
    return MLX_REPOS.get(tag)
