from __future__ import annotations

from beanfit.catalog.models import CATALOG, mlx_repo_for

# Policy: pinned MLX repos and ollama tags must return HTTP 200 (401 counts
# as failure — gated mirrors would break emitted commands). Entries without a
# vetted MLX pin are checked against their ollama tag only; nothing guessed.


def ollama_url(tag: str) -> str:
    return f"https://ollama.com/library/{tag}"


def mlx_url(repo: str) -> str:
    return f"https://huggingface.co/api/models/{repo}"


def validate_catalog(fetch_status, sleep=lambda _s: None) -> list[dict]:
    """Check every catalog entry against its live registry.

    `fetch_status(url) -> int` is injectable for tests. Network errors are
    reported as failures, never raised.
    """
    results = []
    for name, tag, *_ in CATALOG:
        targets = [("ollama", tag, ollama_url(tag), True)]
        repo = mlx_repo_for(tag)
        if repo:
            targets.append(("hf-pinned", repo, mlx_url(repo), True))
        for kind, ident, url, blocking in targets:
            try:
                status = fetch_status(url)
                ok = status == 200
                error = None if ok else f"HTTP {status}"
            except Exception as exc:
                status, ok, error = None, False, str(exc)
            results.append({
                "model": name, "kind": kind, "id": ident,
                "url": url, "status": status, "ok": ok,
                "blocking": blocking, "error": error,
            })
            sleep(1)
    return results
