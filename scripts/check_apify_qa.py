#!/usr/bin/env python3
"""Run the central registered Beanfit QA against this isolated candidate."""
import importlib.util
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
qa_path = Path('/Users/stephenkall/beans/platform/qa-kit/bin/run_all.py')
spec = importlib.util.spec_from_file_location('beanfit_isolated_qa', qa_path)
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)
original_load = qa.load_manifest

def isolated_manifest():
    manifest = original_load()
    for repo in manifest['repos']:
        if repo['name'] == 'beanfit':
            repo['path'] = str(root)
    return manifest

qa.load_manifest = isolated_manifest
qa.LOGS = root / 'docs/apify/qa-logs'
sys.argv = [str(qa_path), '--only', 'beanfit', '--all']
raise SystemExit(qa.main())
