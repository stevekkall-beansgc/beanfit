import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('extraction_eval', Path(__file__).resolve().parents[1] / 'scripts/extraction_eval.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExtractionTests(unittest.TestCase):
    def test_normalization_does_not_repair_values(self):
        obj = module.parse('```json\n{"project":" Atlas ","status":"Active","owner":null,"budget":9}\n```', True)
        self.assertEqual(obj, {'project':'Atlas','status':'active','owner':None,'budget':9})
        for answer in ['{"abstain":1}', '{"abstain":true,"extra":0}',
                       '{"project":"A","status":null,"owner":null,"budget":true}',
                       '{"project":"A","status":null,"owner":null,"budget":"9"}',
                       '{"project":"A","status":null,"owner":null,"budget":NaN}',
                       '{"abstain":true,"abstain":false}']:
            with self.assertRaises(ValueError):
                module.parse(answer, True)

    def test_rejecting_everything_cannot_pass(self):
        workload = {'cases':[{'id':'a','expected_json':{'project':'A','status':None,'owner':None,'budget':None},'critical':True}],
                    'repeats':1,'acceptance':{'min_answerable_coverage':.8,'min_accepted_accuracy':1}}
        trials = [{'id':'a-0','case_id':'a','answer':'{"abstain":true}','outcome':'completed'}]
        result = module.evaluate(workload,trials)
        self.assertFalse(result['experimental_contract_pass'])
        trials[0]['answer'] = '{"project":"A","status":null,"owner":null,"budget":9}'
        result = module.evaluate(workload,trials)
        self.assertEqual(result['critical_accepted_errors'], ['a-0'])
        self.assertFalse(result['experimental_contract_pass'])
        trials[0]['answer'] = '{"project":"A","status":null,"owner":null,"budget":null}'
        self.assertTrue(module.evaluate(workload,trials)['experimental_contract_pass'])
        self.assertFalse(module.evaluate(workload,trials*2)['experimental_contract_pass'])

    def test_baseline_only_accepts_complete_literal_record(self):
        self.assertEqual(module.baseline({'target':'A','document':'A is active.'}), {'abstain':True})
        self.assertEqual(module.baseline({'target':'A','document':'Project: B\nStatus: active\nOwner: X\nBudget: 3'}), {'abstain':True})
        self.assertEqual(module.baseline({'target':'A','document':'Project: A\nStatus: active\nOwner: X\nBudget: 3'})['budget'], 3)
