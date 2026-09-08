import unittest

from beanfit.emit import launch_cmd, mlx_cmd, render_table
from beanfit.engine import evaluate
from tests.fixtures import M2_BASE_8, M5_MAX_128


def top_row(hw, use_case="chat"):
    return next(r for r in evaluate(hw, use_case) if r["fits"])


class LaunchCommands(unittest.TestCase):
    def test_ollama_launch(self):
        row = top_row(M5_MAX_128)
        self.assertEqual(launch_cmd(row), "ollama pull gemma3:27b && ollama run gemma3:27b")

    def test_mlx_repo_mapping(self):
        row = top_row(M5_MAX_128)
        self.assertEqual(
            mlx_cmd(row),
            "pip install mlx-lm && mlx_lm.generate --model mlx-community/gemma-3-27b-it-4bit",
        )

    def test_unpinned_model_gets_no_mlx_alt(self):
        self.assertEqual(mlx_cmd({"runtime_tag": "not-a-catalog-tag"}), "")


class TableGolden(unittest.TestCase):
    def test_full_render_matches_golden(self):
        hw = M5_MAX_128
        rows = evaluate(hw, "chat")
        golden = (
            "beanfit · Apple M5 Max · 128.0 GiB unified\n"
            "Metal working-set cap ~96.0 GiB → model budget 96.0 GiB "
            "(~600 GB/s ±40% est [BW estimate])\n"
            "\n"
            "MODEL                     QUANT      TOTAL   TOK/S  FIT    SCORE\n"
            "----------------------------------------------------------------\n"
            "Gemma 3 27B               q4_K_M     17.9G    28.5  yes    122.3\n"
            "Qwen3 30B-A3B (MoE)       q4_K_M     19.9G    25.6  yes    121.8\n"
            "Qwen3 8B                  q4_K_M      5.7G    90.3  yes    115.0\n"
            "gpt-oss 20b (MXFP4)       q4_K_M     14.7G    34.7  yes    111.2\n"
            "Mistral Small 3.1 24B     q4_K_M     15.8G    32.3  yes    110.8\n"
            "Llama 4 Scout 109B (16x17B MoE)q4_K_M     67.8G     7.5  yes    107.1\n"
            "Phi-4-reasoning 14B       q4_K_M     11.6G    44.0  yes    100.6\n"
            "DeepSeek Coder V2 16B     q4_K_M     10.7G    47.9  yes     77.2\n"
            "\n"
            "Pick: Gemma 3 27B (q4_K_M) — quality 9/10, ~28.5 tok/s est (±40%). "
            "Verify: ollama run --verbose.\n"
            "Run it:\n"
            "  $ ollama pull gemma3:27b && ollama run gemma3:27b\n"
            "MLX alternative (Apple Silicon, often faster decode):\n"
            "  $ pip install mlx-lm && mlx_lm.generate --model mlx-community/gemma-3-27b-it-4bit"
        )
        self.assertEqual(render_table(hw, rows, "chat"), golden)

    def test_no_fit_device_renders_without_pick(self):
        out = render_table(M2_BASE_8, evaluate(M2_BASE_8, "chat"), "chat")
        self.assertNotIn("Pick:", out)
        self.assertIn("NO", out)


if __name__ == "__main__":
    unittest.main()
