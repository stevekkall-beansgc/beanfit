import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("simulator_eval", Path(__file__).resolve().parents[1] / "scripts/simulator_eval.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SimulatorEvaluatorTests(unittest.TestCase):
    def test_bos_echo_is_removed_without_grading_prompt(self):
        for template, bos in [("lfm2", "<|startoftext|>"), ("gemma3", "<bos>"),
                              ("chatml", ""), ("qwen3-no-thinking", "")]:
            prompt = module.prompt_for("Return amber", template)
            self.assertEqual(module.extract_answer(bos + prompt + "violet\n", prompt, template), "violet")
            with self.assertRaises(ValueError):
                module.extract_answer("unexpected prefix" + bos + prompt + "amber", prompt, template)

    def test_gemma_template_preserves_instructions_in_user_turn(self):
        prompt = module.prompt_for("Return amber", "gemma3")
        self.assertTrue(prompt.startswith("<start_of_turn>user\n"))
        self.assertIn("Never invent missing information.\n\nReturn amber", prompt)
        self.assertTrue(prompt.endswith("<end_of_turn>\n<start_of_turn>model\n"))
        self.assertNotIn("<bos>", prompt)  # added by llama-simple, once

    def test_bytes_capture_rejects_invalid_answer_encoding(self):
        prompt = module.prompt_for("Return amber", "chatml")
        self.assertEqual(module.extract_answer((prompt + "amber").encode(), prompt, "chatml"), "amber")
        with self.assertRaises(ValueError):
            module.extract_answer(prompt.encode() + b"\xc4", prompt, "chatml")

    def test_supplemental_system_prompt_is_explicit(self):
        prompt = module.prompt_for("Bluebird is paused", "lfm2", "Return JSON with a status key.")
        self.assertTrue(prompt.startswith("<|im_start|>system\nReturn JSON with a status key.<|im_end|>"))
        self.assertNotIn("You are a helpful assistant", prompt)

    def test_exact_output_not_substring(self):
        case = {"expected": "amber"}
        self.assertTrue(module.grade(case, " Amber. "))
        self.assertFalse(module.grade(case, "amber or violet"))
        self.assertFalse(module.grade(case, "The prompt says amber"))

    def test_json_shape_and_duplicate_keys(self):
        case = {"expected_json": {"project": "Bluebird"}}
        self.assertTrue(module.grade(case, '{"project":"Bluebird"}'))
        self.assertFalse(module.grade(case, '{"project":"Orchard","project":"Bluebird"}'))
        self.assertFalse(module.grade(case, '```json\n{"project":"Bluebird"}\n```'))

    def test_critical_failure_and_simulator_boundary(self):
        workload = {"cases": [{"id": "critical", "critical": True}], "repeats": 1, "quality_floor": .9}
        good = [{"case_id": "critical", "quality_pass": True, "outcome": "completed"}]
        result = module.summarize(good, workload)
        self.assertTrue(result["simulator_quality_screen_pass"])
        self.assertFalse(result["physical_device_qualified"])
        self.assertIsNone(result["peak_stack_bytes"])
        good[0]["quality_pass"] = False
        self.assertFalse(module.summarize(good, workload)["simulator_quality_screen_pass"])

    def test_noncompletion_disqualifies(self):
        workload = {"cases": [{"id": "a"}], "repeats": 1, "quality_floor": 0}
        self.assertFalse(module.summarize([], workload)["simulator_quality_screen_pass"])
        self.assertFalse(module.summarize([{"case_id":"a", "quality_pass":False, "outcome":"timeout"}], workload)["simulator_quality_screen_pass"])

    def test_duplicate_case_cannot_replace_missing_case(self):
        workload = {"cases": [{"id": "a"}, {"id": "b", "critical": True}], "repeats": 1, "quality_floor": .9}
        rows = [{"case_id": "a", "quality_pass": True, "outcome": "completed"}] * 2
        self.assertFalse(module.summarize(rows, workload)["simulator_quality_screen_pass"])
