import json
import unittest
from unittest import mock

from beanfit.register import build_pair_payload, credential_path, save_device_credential
from tests.fixtures import M5_MAX_128


class BuildPairPayload(unittest.TestCase):
    def test_shape(self):
        payload = build_pair_payload(M5_MAX_128, "coding", None)
        self.assertIn("hardware", payload["profile"])
        self.assertEqual(payload["profile"]["hardware"]["chip"], "Apple M5 Max")
        self.assertEqual(payload["recommendations"]["use_case"], "coding")
        self.assertTrue(payload["recommendations"]["ranked"])
        self.assertTrue(payload["label"].startswith("Apple M5 Max"))

    def test_label_override(self):
        payload = build_pair_payload(M5_MAX_128, "chat", "studio")
        self.assertEqual(payload["label"], "studio")


class CredentialFile(unittest.TestCase):
    def test_saved_with_restricted_mode(self):
        import os
        import sys
        import tempfile
        if sys.platform == "win32":
            # Windows has no POSIX permission bits; os.open(mode=0o600) is a
            # no-op there and st_mode reports the default ACL mapping (0o666).
            # The owner-only property is enforced where the platform can.
            self.skipTest("POSIX mode bits do not exist on Windows")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "device.json")
            save_device_credential(path, {"device_token": "secret"})
            mode = os.stat(path).st_mode & 0o777
            self.assertEqual(mode, 0o600)
            doc = json.loads(open(path).read())
            self.assertEqual(doc["device_token"], "secret")

    def test_default_path_is_private_dir(self):
        self.assertIn("beanfit", credential_path())


if __name__ == "__main__":
    unittest.main()
