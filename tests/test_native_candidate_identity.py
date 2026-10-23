"""Offline rejection checks for exact native test candidates."""
import hashlib
import importlib.util
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("device_text_qualification", Path(__file__).resolve().parents[1] / "iphone/scripts/device_text_qualification.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class CandidateIdentityTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'posix', 'The macOS devicectl console uses POSIX SIGINT')
    def test_owned_console_is_interrupted_and_reaped(self):
        process = subprocess.Popen([sys.executable, '-u', '-c',
            'import time; print("ready", flush=True); time.sleep(60)'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), 'ready')
            cleanup = runner.stop_owned_console(process)
            self.assertIsNotNone(process.poll())
            self.assertTrue(cleanup['interrupt_forwarding_requested'])
            self.assertFalse(cleanup['console_force_killed'])
            self.assertFalse(cleanup['remote_exit_verified'])
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()

    def test_wrong_build_bundle_or_executable_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            app = Path(temp) / "Synthetic.app"
            app.mkdir()
            executable = app / "Synthetic"
            executable.write_bytes(b"synthetic candidate")
            info = {"CFBundleIdentifier":"com.beanlabs.BeanFitPocket", "CFBundleExecutable":"Synthetic",
                    "CFBundleVersion":"2", "CFBundleShortVersionString":"0.1.0"}
            (app / "Info.plist").write_bytes(plistlib.dumps(info))
            digest = hashlib.sha256(executable.read_bytes()).hexdigest()
            identity = runner.app_identity(app, info["CFBundleIdentifier"], "2", digest)
            self.assertEqual(identity["app_build"], "2")
            self.assertEqual(identity["executable_sha256"], digest)
            for bundle, build, sha in [("wrong.bundle", "2", digest),
                                       (info["CFBundleIdentifier"], "1", digest),
                                       (info["CFBundleIdentifier"], "2", "0" * 64)]:
                with self.subTest(bundle=bundle, build=build, sha=sha):
                    with self.assertRaises(ValueError):
                        runner.app_identity(app, bundle, build, sha)
            executable.write_bytes(b"changed after review")
            with self.assertRaises(ValueError):
                runner.app_identity(app, info["CFBundleIdentifier"], "2", digest)
            info["CFBundleExecutable"] = "../outside"
            (app / "Info.plist").write_bytes(plistlib.dumps(info))
            with self.assertRaises(ValueError):
                runner.app_identity(app, info["CFBundleIdentifier"])


if __name__ == "__main__":
    unittest.main()
