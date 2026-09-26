#!/usr/bin/env python3
"""Run BeanFit's owned activation and mobile offline E2Es, failing on either."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
for name in ("activation_demo.py", "mobile_demo.py"):
    subprocess.run([sys.executable, str(root / "scripts" / name)], cwd=root, check=True)
