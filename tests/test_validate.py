import unittest

from beanfit.catalog.validate import (
    heuristic_mlx_repo,
    ollama_url,
    validate_catalog,
)


def fake_fetch(url):
    if "dead" in url:
        return 404
    if "boom" in url:
        raise ConnectionError("network down")
    return 200


class ValidateCatalog(unittest.TestCase):
    def test_all_ok(self):
        results = validate_catalog(lambda _u: 200)
        self.assertTrue(all(r["ok"] for r in results))
        self.assertEqual(len(results), 18)  # 9 ollama + 8 pinned + 1 heuristic

    def test_heuristic_only_entry_is_non_blocking(self):
        def dead_heuristics(url):
            return 404 if "4bit" in url else 200
        results = validate_catalog(dead_heuristics)
        heuristics = [r for r in results if r["kind"] == "hf-heuristic"]
        self.assertTrue(heuristics and not any(r["ok"] for r in heuristics))
        self.assertFalse(any(r["blocking"] for r in heuristics))

    def test_pinned_401_counts_as_failure(self):
        results = validate_catalog(lambda _u: 401)
        pinned = [r for r in results if r["kind"] == "hf-pinned"]
        self.assertEqual(len(pinned), 8)
        self.assertTrue(all((not r["ok"]) and r["blocking"] for r in pinned))

    def test_failures_reported_not_raised(self):
        def flaky(_u):
            raise ConnectionError("down")
        results = validate_catalog(flaky)
        self.assertFalse(any(r["ok"] for r in results))
        self.assertIn("down", results[0]["error"])

    def test_urls_follow_emitter_conventions(self):
        self.assertEqual(ollama_url("gemma4:31b"), "https://ollama.com/library/gemma4:31b")
        self.assertEqual(heuristic_mlx_repo("gemma4:31b"), "mlx-community/gemma4-31b-4bit")


if __name__ == "__main__":
    unittest.main()
