import unittest

from beanfit.emit import launch_cmd, mlx_cmd, render_table
from beanfit.engine import evaluate
from tests.fixtures import M2_BASE_8, M5_MAX_128


def top_row(hw, use_case="chat"):
    return next(r for r in evaluate(hw, use_case) if r["fits"])


class LaunchCommands(unittest.TestCase):
    def test_ollama_launch(self):
        row = top_row(M5_MAX_128)
        self.assertEqual(launch_cmd(row), "ollama pull gemma4:31b && ollama run gemma4:31b")

    def test_mlx_repo_mapping(self):
        row = top_row(M5_MAX_128)
        self.assertEqual(
            mlx_cmd(row),
            "pip install mlx-lm && mlx_lm.generate --model mlx-community/gemma-4-31b-it-4bit",
        )

    def test_unpinned_model_gets_no_mlx_alt(self):
        kimi = next(r for r in evaluate(M5_MAX_128, "chat")
                    if r["runtime_tag"] == "kimi-k2.6")
        self.assertEqual(mlx_cmd(kimi), "")


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
            "Gemma 4 31B               q4_K_M     20.4G    25.0  yes    121.8\n"
            "Qwen3.6 35B-A3B (MoE)     q4_K_M     22.4G    22.7  yes    121.4\n"
            "Qwen3.5 9B Instruct       q4_K_M      6.7G    76.7  yes    115.0\n"
            "Llama 4 Scout 17B         q4_K_M     11.8G    43.4  yes    112.5\n"
            "gpt-oss 20b (MXFP4)       q4_K_M     13.2G    38.6  yes    111.8\n"
            "Mistral Small 3.2 24B     q4_K_M     15.8G    32.3  yes    110.8\n"
            "Phi-4-reasoning 14B       q4_K_M      9.9G    51.5  yes    101.7\n"
            "DeepSeek Coder V2 16B     q4_K_M     11.2G    45.7  yes     76.9\n"
            "\n"
            "Pick: Gemma 4 31B (q4_K_M) — quality 9/10, ~25.0 tok/s est (±40%). "
            "Verify: ollama run --verbose.\n"
            "Run it:\n"
            "  $ ollama pull gemma4:31b && ollama run gemma4:31b\n"
            "MLX alternative (Apple Silicon, often faster decode):\n"
            "  $ pip install mlx-lm && mlx_lm.generate --model mlx-community/gemma-4-31b-it-4bit"
        )
        self.assertEqual(render_table(hw, rows, "chat"), golden)

    def test_no_fit_device_renders_without_pick(self):
        out = render_table(M2_BASE_8, evaluate(M2_BASE_8, "chat"), "chat")
        self.assertNotIn("Pick:", out)
        self.assertIn("NO", out)


if __name__ == "__main__":
    unittest.main()
