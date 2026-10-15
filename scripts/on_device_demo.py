#!/usr/bin/env python3
"""Owned offline E2E for current-model suggestions; no fabricated device winner."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def cli(*args):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return json.loads(subprocess.check_output([sys.executable, "-m", "beanfit", "suggest", *args], cwd=ROOT, env=env, text=True))


doc = cli("--catalog")
assert len(doc["models"]) == 11
base = ("--device", "iPhone15,3", "--ios", "26")
general = cli(*base)
assert general["selection"] is None and general["trial_order"][0] == "liquid12"
shopping = cli(*base, "--experience", "shopping_filters")
assert "liquid350" not in shopping["trial_order"] and "qwen08" not in shopping["trial_order"]
assert "liquid26" not in shopping["trial_order"]
small = cli(*base, "--memory-budget-mib", "191")
assert small["trial_order"] == ["liquid230"] and small["selection"] is None
vision = cli(*base, "--experience", "image_description")
assert vision["trial_order"] == [] and len(vision["candidates"][0]["artifacts"]) == 2
unknown = cli()
assert unknown["trial_order"] == [] and unknown["selection"] is None
print("On-device suggestion E2E passed: pinned catalog, task gates, resource screening, no invented winner")
