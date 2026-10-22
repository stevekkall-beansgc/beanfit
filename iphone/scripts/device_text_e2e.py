#!/usr/bin/env python3
"""Install an explicitly supplied development app and run synthetic text probes.

Requires an operator-connected physical iPhone. No providers, messages, model
downloads, certificate creation, or public distribution. Device IDs stay in
memory, not in reports. All captured input/output is the frozen synthetic set.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device-inventory', type=Path, required=True)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--model-id', default='qwen2', choices=['liquid12', 'qwen08', 'qwen2'],
                        help='Expected model in the supplied build; does not change the app model')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skip-model-copy', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    catalog = json.loads((root / 'src/beanfit/catalog/on_device.json').read_text())
    model = next(m for m in catalog['models'] if m['id'] == args.model_id)['artifacts'][0]
    assert args.model.stat().st_size == model['bytes']
    hasher = hashlib.sha256()
    with args.model.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    assert digest == model['sha256']
    devices = json.loads(args.device_inventory.read_text())['result']['devices']
    physical = [d for d in devices if d['hardwareProperties'].get('reality') == 'physical'
                and d['connectionProperties'].get('tunnelState') == 'connected']
    assert len(physical) == 1, 'Connect exactly one target physical iPhone'
    device = physical[0]['identifier']
    assert args.bundle in ('com.beanlabs.BeanFitPocket', 'com.jumpingbeans.v2.imessageprototype')
    args.output.mkdir(parents=True, exist_ok=True)

    def run(*command, required=True):
        result = subprocess.run(['xcrun', 'devicectl', *command], capture_output=True, text=True, timeout=120)
        if required and result.returncode:
            raise RuntimeError('Device operation failed: ' + ' '.join(command[:3]))
        return result.returncode == 0

    run('device', 'install', 'app', '--device', device, str(args.app))
    if not args.skip_model_copy:
        with tempfile.TemporaryDirectory(prefix='beanfit-transfer-') as temp:
            folder = Path(temp) / 'Models'; folder.mkdir()
            try:
                os.link(args.model, folder / args.model.name)
            except OSError:
                shutil.copy2(args.model, folder / args.model.name)
            run('device', 'copy', 'to', '--device', device, '--source', str(folder),
                '--destination', 'Documents/Models', '--domain-type', 'appDataContainer', '--domain-identifier', args.bundle)
    run_id = str(uuid.uuid4())
    run('device', 'process', 'launch', '--device', device, '--terminate-existing', args.bundle,
        '--text-smoke', '--run-id=' + run_id)
    report = None
    with tempfile.TemporaryDirectory(prefix='beanfit-phone-report-') as temp:
        path = Path(temp) / 'text-smoke.json'
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            if run('device', 'copy', 'from', '--device', device, '--source', 'Documents/text-smoke.json',
                   '--destination', str(path), '--domain-type', 'appDataContainer', '--domain-identifier', args.bundle, required=False):
                current = json.loads(path.read_text())
                if current.get('run_id') == run_id:
                    report = current
                    if report.get('completed') or report.get('error'):
                        break
            time.sleep(3)
        assert report is not None, 'No fresh phone report was recovered'
        (args.output / 'text-smoke.json').write_text(json.dumps(report, indent=2) + '\n')
    for name in ['text-measurements.json', 'text-smoke.png']:
        run('device', 'copy', 'from', '--device', device, '--source', 'Documents/' + name,
            '--destination', str(args.output / name), '--domain-type', 'appDataContainer', '--domain-identifier', args.bundle,
            required=report['completed'] or name != 'text-smoke.png')
    assert report['completed'] and not report['qualified'], 'Phone run incomplete: ' + report.get('error', 'no completion')
    assert report['evidence_kind'] == 'physical-device-process-only'
    assert report['model_sha256'] == model['sha256'] and report['model_unloaded']
    assert len(report['records']) == 13
    passed = sum(r['passed'] for r in report['records'])
    print(json.dumps({'bundle':args.bundle,'completed':True,'functional_passes':passed,'functional_checks':13,
                      'memory_warnings':report['memory_warnings'],'model_unloaded':report['model_unloaded'],'qualified':False}))
    return 0 if passed == 13 else 1


if __name__ == '__main__':
    raise SystemExit(main())
