#!/usr/bin/env python3
"""Owned offline CLI E2E: synthetic mobile receipts never qualify a real phone."""
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
env = {**os.environ, "PYTHONPATH": str(root / "src")}
command = [sys.executable, "-m", "beanfit", "mobile", "--profile",
           str(root / "examples/mobile/profile.synthetic.json"), "--receipts",
           str(root / "examples/mobile/receipts.synthetic.json")]
run = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, check=True)
result = json.loads(run.stdout)
assert result["selection"] is None
assert result["status"] == "needs_device_evidence"
rows = result["candidates"]
assert "quality_below_floor" in rows[0]["reasons"]
assert rows[1]["passes_demo_gates"] and rows[2]["passes_demo_gates"]
assert rows[1]["peak_stack_bytes"] < rows[2]["peak_stack_bytes"]
assert all(not row["qualified_for_tested_profile"] for row in rows)
print(json.dumps({"status": "OFFLINE_SYNTHETIC_PASS", "physical_measurements": 0,
                  "provider_calls": 0, "phone_installs": 0,
                  "smallest_demo_passing_candidate": rows[1]["candidate"]["id"],
                  "real_selection": result["selection"]}))
