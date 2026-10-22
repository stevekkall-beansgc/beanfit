import unittest

from beanfit.on_device import catalog, suggest


class OnDeviceSuggestions(unittest.TestCase):
    def test_current_text_models_have_pinned_artifacts(self):
        models = catalog()["models"]
        self.assertTrue({"liquid230", "liquid350", "liquid12", "liquid26", "qwen08", "qwen2"} <= {m["id"] for m in models})
        for model in models:
            for artifact in model["artifacts"]:
                self.assertRegex(artifact["revision"], r"^[0-9a-f]{40}$")
                self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")
                self.assertGreater(artifact["bytes"], 0)

    def test_catalog_is_not_phone_qualification(self):
        result = suggest(experience="text_assistant", device="iPhone15,3", os_major=26)
        self.assertIsNone(result["selection"])
        self.assertEqual(result["status"], "needs_device_evidence")
        self.assertEqual(result["trial_order"][0], "liquid12")
        self.assertTrue(all(row["memory_fit"] == "unknown" for row in result["candidates"]))

    def test_failed_shopping_models_do_not_return_as_suggestions(self):
        result = suggest(experience="shopping_filters", device="iPhone15,3", os_major=26)
        self.assertNotIn("liquid350", result["trial_order"])
        self.assertNotIn("qwen08", result["trial_order"])
        self.assertEqual(result["fallback"], "reviewed_manual_filters_or_bounded_parser")

    def test_download_sizes_cannot_prove_memory_fit(self):
        result = suggest(experience="text_assistant", device="iPhone15,3", os_major=26, memory_budget_bytes=200_000_000)
        self.assertEqual(result["trial_order"], ["liquid230"])
        self.assertIsNone(result["selection"])
        self.assertEqual(next(r for r in result["candidates"] if r["id"] == "liquid12")["status"], "weights_exceed_memory_budget")

    def test_other_modalities_need_their_runtime_components(self):
        for experience in ("image_description", "transcription", "speech_output", "semantic_search", "decision_classification"):
            result = suggest(experience=experience, device="iPhone15,3", os_major=26)
            self.assertEqual(result["trial_order"], [])
            self.assertTrue(result["candidates"])
            self.assertTrue(all(r["status"] == "requires_runtime_integration" for r in result["candidates"]))

    def test_voice_notes_search_and_decisions_have_complete_components(self):
        voice = suggest(experience="transcription", device="iPhone15,3", os_major=26)
        first = voice["candidates"][0]
        self.assertEqual(first["id"], "fluid_speech_mini")
        names = {a["filename"] for a in first["artifacts"]}
        for component in ("Encoder", "Decoder", "JointDecision", "Preprocessor"):
            self.assertIn(f"{component}.mlmodelc/model.mil", names)
            self.assertIn(f"{component}.mlmodelc/weights/weight.bin", names)
        self.assertIn("parakeet_v3_vocab.json", names)
        self.assertIn("NOTICE", names)
        search = suggest(experience="semantic_search", device="iPhone15,3", os_major=26)
        self.assertEqual(search["candidates"][0]["id"], "embeddinggemma300")
        self.assertEqual(search["candidates"][0]["download_bytes"], 333590944)
        self.assertEqual(search["fallback"], "keyword_search_or_manual_browsing")
        decision = suggest(experience="decision_classification", device="iPhone15,3", os_major=26)
        self.assertEqual(decision["candidates"][0]["download_bytes"], 669998816)

    def test_mac_references_never_enter_phone_suggestions(self):
        doc = catalog()
        reference_ids = {m["id"] for m in doc["reference_models"]}
        self.assertEqual(len(reference_ids), 3)
        for task in doc["experiences"]:
            result = suggest(experience=task["id"], device="iPhone15,3", os_major=26)
            self.assertTrue(reference_ids.isdisjoint(row["id"] for row in result["candidates"]))

    def test_unknown_or_older_devices_never_receive_an_automatic_trial(self):
        for device, os_major in (("iPhone", 26), ("iPhone14,5", 26), ("iPhone15,3", 25)):
            result = suggest(experience="text_assistant", device=device, os_major=os_major)
            self.assertEqual(result["trial_order"], [])
            self.assertIsNone(result["selection"])

    def test_input_validation(self):
        for kwargs in ({"experience":"bogus"}, {"memory_budget_bytes":True}, {"memory_budget_bytes":0}, {"os_major":True}, {"context_tokens":2049}):
            with self.assertRaises(ValueError): suggest(**kwargs)


class CatalogQualification(unittest.TestCase):
    def inputs(self, cid, peak=900_000_000):
        from tests.test_mobile import profile, receipt
        from beanfit.mobile import MATCH_FIELDS
        p = {**profile(), "device": "iPhone15,3", "catalog_experience": "text_assistant", "ios_major": 26,
             "memory_budget_bytes": 2_000_000_000}
        r = receipt(cid, peak)
        r.update({key: p[key] for key in MATCH_FIELDS})
        m = next(m for m in catalog()["models"] if m["id"] == cid)
        a = m["artifacts"][0]
        r["candidate"] = {"id": cid, "runtime": "llama.cpp", "runtime_revision": catalog()["runtime_revision"],
                          "model_revision": a["revision"], "artifact_sha256": a["sha256"],
                          "repository": a["repository"], "weights_bytes": a["bytes"]}
        return p, r

    def test_reviewed_peak_memory_selects_winner_not_download_size(self):
        from beanfit.on_device import select_catalog
        p, tiny = self.inputs("liquid230", 950_000_000)
        _, larger = self.inputs("liquid12", 900_000_000)
        result = select_catalog(p, [tiny, larger])
        self.assertEqual(result["selection"]["id"], "liquid12")
        self.assertEqual(result["catalog_rejections"], [])

    def test_wrong_artifact_and_simulator_cannot_qualify(self):
        from beanfit.on_device import select_catalog
        p, row = self.inputs("liquid12")
        row["candidate"]["artifact_sha256"] = "0" * 64
        self.assertIsNone(select_catalog(p, [row])["selection"])
        p, row = self.inputs("liquid12")
        row["evidence_kind"] = "simulator"
        self.assertIsNone(select_catalog(p, [row])["selection"])

    def test_reviewed_memory_is_not_overridden_by_file_size_screen(self):
        from beanfit.on_device import select_catalog
        p, row = self.inputs("liquid12", 300_000_000)
        p["memory_budget_bytes"] = 500_000_000
        # Synthetic selector fixture: mapped files and resident memory differ.
        self.assertEqual(select_catalog(p, [row])["selection"]["id"], "liquid12")

    def test_quality_failure_outweighs_low_memory(self):
        from beanfit.on_device import select_catalog
        p, small = self.inputs("liquid230", 200_000_000)
        _, large = self.inputs("liquid12")
        small["trials"][2]["quality_pass"] = False
        self.assertEqual(select_catalog(p, [small, large])["selection"]["id"], "liquid12")

    def test_experience_binding_and_existing_task_failure(self):
        from beanfit.on_device import select_catalog
        p, row = self.inputs("liquid350")
        with self.assertRaises(ValueError): select_catalog(p, [row], experience="shopping_filters")
        p["catalog_experience"] = "shopping_filters"
        result = select_catalog(p, [row], experience="shopping_filters")
        self.assertIsNone(result["selection"])
        self.assertEqual(len(result["catalog_rejections"]), 1)

    def test_generated_native_snapshot_is_current(self):
        from pathlib import Path
        import subprocess
        import sys
        subprocess.run([sys.executable, "scripts/sync_on_device_catalog.py", "--check"],
                       cwd=Path(__file__).resolve().parents[1], check=True)


if __name__ == "__main__":
    unittest.main()
