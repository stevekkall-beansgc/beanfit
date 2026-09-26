import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("simulator_eval", Path(__file__).resolve().parents[1] / "scripts/simulator_eval.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SimulatorEvaluatorTests(unittest.TestCase):
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
