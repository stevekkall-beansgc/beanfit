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
mac = cli("--platform", "mac")
assert mac == doc["mac_recommendations"]
assert mac["schema"] == "beanfit.mac.recommendations.v1"
assert next(m for m in mac["models"] if m["id"] == "lfm3_17b_mac")["runtime_status"] == "awaiting_runtime_support"
assert all(m["evidence"] and m["artifacts"] for m in mac["models"])
assert doc["native_release_hold"]["status"] == "held"
assert len(doc["models"]) == 15
assert len(doc["reference_models"]) == 3
base = ("--device", "iPhone15,3", "--ios", "26")
general = cli(*base)
assert general["selection"] is None and general["trial_order"][0] == "qwen2"
assert "liquid12" not in general["trial_order"]
assert next(row for row in general["candidates"] if row["id"] == "liquid12")["status"] == "known_task_failure"
shopping = cli(*base, "--experience", "shopping_filters")
assert "liquid350" not in shopping["trial_order"] and "qwen08" not in shopping["trial_order"]
assert "liquid26" not in shopping["trial_order"]
small = cli(*base, "--memory-budget-mib", "191")
assert small["trial_order"] == ["liquid230"] and small["selection"] is None
vision = cli(*base, "--experience", "image_description")
assert vision["trial_order"] == [] and len(vision["candidates"][0]["artifacts"]) == 2
for experience, first in (("transcription", "fluid_speech_mini"), ("semantic_search", "embeddinggemma300"),
                          ("decision_classification", "d1_omni600")):
    result = cli(*base, "--experience", experience)
    assert result["candidates"][0]["id"] == first
    assert result["trial_order"] == [] and result["selection"] is None
    assert all(row["status"] == "requires_runtime_integration" for row in result["candidates"])
reference_ids = {model["id"] for model in doc["reference_models"]}
for experience in doc["experiences"]:
    assert reference_ids.isdisjoint(row["id"] for row in cli(*base, "--experience", experience["id"])["candidates"])
unknown = cli()
assert unknown["trial_order"] == [] and unknown["selection"] is None
print("On-device suggestion E2E passed: pinned catalog, task gates, resource screening, no invented winner")
