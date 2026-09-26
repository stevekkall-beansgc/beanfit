import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('conversation_probe', Path(__file__).resolve().parents[1] / 'scripts/conversation_probe.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConversationProbeTests(unittest.TestCase):
    def test_followup_preserves_actual_assistant_reply(self):
        messages = [{'role':'system','content':'Rules'}, {'role':'user','content':'First'},
                    {'role':'assistant','content':'Actual wrong reply'}, {'role':'user','content':'Correction'}]
        prompt = module.prompt_for(messages, 'qwen3-no-thinking')
        self.assertIn('<|im_start|>assistant\nActual wrong reply<|im_end|>\n<|im_start|>user\nCorrection', prompt)
        self.assertTrue(prompt.endswith('<think>\n\n</think>\n\n'))
        self.assertEqual(module.answer_from((prompt+'New answer').encode(),prompt,'qwen3-no-thinking'),'New answer')

    def test_liquid_bos_echo_and_invalid_encoding(self):
        prompt = module.prompt_for([{'role':'user','content':'amber'}], 'lfm2')
        self.assertEqual(module.answer_from(('<|startoftext|>'+prompt+'violet').encode(),prompt,'lfm2'),'violet')
        for raw in [b'wrong prefix', ('<|startoftext|>'+prompt).encode()+b'\xff']:
            with self.assertRaises(ValueError):
                module.answer_from(raw,prompt,'lfm2')
