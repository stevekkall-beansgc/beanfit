import unittest

from beanfit.catalog.validate import (
    ollama_url,
    validate_catalog,
)
from beanfit.catalog.models import CATALOG


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
        self.assertEqual(len(results), 16)  # 8 ollama + 8 pinned, nothing guessed

    def test_every_catalog_entry_has_ollama_and_pinned_mlx_targets(self):
        results = validate_catalog(lambda _u: 200)
        kinds_by_model = {}
        for r in results:
            kinds_by_model.setdefault(r["model"], set()).add(r["kind"])
        self.assertEqual(set(kinds_by_model), {entry.name for entry in CATALOG})
        self.assertTrue(all(kinds == {"ollama", "hf-pinned"}
                            for kinds in kinds_by_model.values()))
        self.assertTrue(all(r["blocking"] for r in results))

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
        self.assertEqual(ollama_url("gemma3:27b"), "https://ollama.com/library/gemma3:27b")


if __name__ == "__main__":
    unittest.main()
