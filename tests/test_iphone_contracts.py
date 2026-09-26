"""Exercise the actual Swift product contracts on macOS builders."""
from pathlib import Path
import subprocess
import sys
import unittest


@unittest.skipUnless(sys.platform == "darwin", "Swift iPhone contracts require an Apple SDK")
class IPhoneContracts(unittest.TestCase):
    def test_native_contracts(self):
        root = Path(__file__).resolve().parents[1]
        subprocess.run(["bash", str(root / "iphone/scripts/test_contracts.sh")],
                       cwd=root, check=True, timeout=180)
