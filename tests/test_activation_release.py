"""Release regressions exercise the real demo in a new one-commit checkout."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ActivationReleaseTests(unittest.TestCase):
    def test_real_demo_without_historical_tags_keeps_checkout_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / 'src', root / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.egg-info'))
            shutil.copytree(ROOT / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            (root / '.gitignore').write_text('__pycache__/\n*.pyc\n')
            env = dict(os.environ, GIT_AUTHOR_NAME='Synthetic QA', GIT_AUTHOR_EMAIL='synthetic@example.invalid',
                       GIT_COMMITTER_NAME='Synthetic QA', GIT_COMMITTER_EMAIL='synthetic@example.invalid')
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, env=env, stderr=subprocess.DEVNULL, text=True)
            git('init', '-q'); git('add', '.'); git('-c', 'commit.gpgsign=false', 'commit', '-qm', 'synthetic source')
            self.assertEqual(git('tag', '--list').strip(), '')
            result = subprocess.run([sys.executable, 'scripts/activation_demo.py'], cwd=root,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'OFFLINE_SYNTHETIC_PASS')
            self.assertEqual(git('status', '--porcelain').strip(), '')
            self.assertFalse((root / 'docs').exists())
            receipt = root / 'synthetic-receipt.json'
            subprocess.run([sys.executable, 'scripts/activation_demo.py', '--receipt', str(receipt)], cwd=root,
                           check=True, capture_output=True, text=True, timeout=30)
            self.assertEqual(json.loads(receipt.read_text())['source_revision'], git('rev-parse', 'HEAD').strip())
