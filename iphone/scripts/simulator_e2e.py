#!/usr/bin/env python3
"""Owned native E2E. Requires a built app, booted simulator, and pinned model.
No model downloads, signing, physical devices, or live product calls.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', required=True)
    parser.add_argument('--device', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    subprocess.run(['python3', str(root / 'scripts/offline_e2e.py')], check=True)
    bundle = 'com.beanlabs.BeanFitPocket'
    run('xcrun', 'simctl', 'install', args.device, args.app)
    container = Path(run('xcrun', 'simctl', 'get_app_container', args.device, bundle, 'data'))
    documents = container / 'Documents'
    models = documents / 'Models'
    models.mkdir(parents=True, exist_ok=True)
    source = Path(args.model)
    shutil.copy2(source, models / source.name)
    smoke = documents / 'smoke.json'
    smoke.unlink(missing_ok=True)
    subprocess.run(['xcrun', 'simctl', 'terminate', args.device, bundle], capture_output=True)
    run('xcrun', 'simctl', 'launch', args.device, bundle, '--smoke', '--model=qwen08')
    deadline = time.monotonic() + 240
    while not smoke.exists() and time.monotonic() < deadline:
        time.sleep(1)
    result = json.loads(smoke.read_text())
    required = {'load', 'local_inference', 'product_preferences', 'catalog_rule', 'unload',
                'typed_preferences', 'invalid_preferences_rejected', 'inclusive_budget',
                'no_matches', 'review_required'}
    assert set(result['checks']) == required, result
    assert all(result['checks'].values()), result
    assert result['phoneQualified'] is False, result
    report = json.loads((documents / 'beanfit-measurements.json').read_text())
    assert report['qualified'] is False
    assert len(report['measurements']) == 3
    assert all(m['evidenceKind'] == 'simulator' and m['outcome'] == 'completed'
               and m['observedPeakProcessBytes'] > 0 for m in report['measurements'])
    # Regression guard: verification must not retain a second complete model's
    # worth of temporary buffers. This is not a product memory budget.
    load = report['measurements'][0]
    assert load['observedPeakProcessBytes'] - load['baselineProcessBytes'] < source.stat().st_size * 1.5 + 128 * 1024 * 1024, load
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for name in ('smoke.json', 'beanfit-measurements.json'):
        shutil.copy2(documents / name, output / name)
    print('Native simulator E2E: 10/10 checks passed; not phone qualification')


if __name__ == '__main__':
    main()
