import unittest

from beanfit.catalog.validate import (
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
        self.assertEqual(len(results), 17)  # 9 ollama + 8 pinned, nothing guessed

    def test_unpinned_entry_gets_ollama_target_only(self):
        results = validate_catalog(lambda _u: 200)
        kinds_by_model = {}
        for r in results:
            kinds_by_model.setdefault(r["model"], set()).add(r["kind"])
        kimi_kinds = kinds_by_model["Kimi K2.6 A1B (MoE)"]
        self.assertEqual(kimi_kinds, {"ollama"})
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
        self.assertEqual(ollama_url("gemma4:31b"), "https://ollama.com/library/gemma4:31b")


if __name__ == "__main__":
    unittest.main()
