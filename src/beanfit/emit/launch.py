from __future__ import annotations

from beanfit.catalog.models import mlx_repo_for


def launch_cmd(row: dict) -> str:
    tag = row["runtime_tag"]
    return f"ollama pull {tag} && ollama run {tag}"


def mlx_cmd(row: dict) -> str:
    repo = mlx_repo_for(row["runtime_tag"])
    if repo is None:
        return ""  # no vetted MLX build — omit rather than emit a dead command
    return f"pip install mlx-lm && mlx_lm.generate --model {repo}"
