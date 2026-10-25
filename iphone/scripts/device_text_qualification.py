#!/usr/bin/env python3
"""Run a frozen synthetic text/resource/thermal packet on one connected iPhone.

Uses the already imported, load-verified pinned model. Never downloads models,
creates signing assets, sends messages or exhausts system memory. Device IDs
are held in memory. The supplied development app may be installed explicitly.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import signal
import subprocess
import shutil
import tempfile
import time
import uuid


def app_identity(app, bundle, expected_build=None, expected_sha256=None):
    """Check the supplied local candidate before any device operation."""
    app = app.resolve()
    info = plistlib.loads((app / 'Info.plist').read_bytes())
    if info.get('CFBundleIdentifier') != bundle:
        raise ValueError('Candidate bundle does not match the requested app')
    executable = (app / info['CFBundleExecutable']).resolve()
    if executable.parent != app or not executable.is_file():
        raise ValueError('Invalid candidate executable')
    build = info['CFBundleVersion']
    if expected_build is not None and build != expected_build:
        raise ValueError('Candidate build does not match the reviewed build')
    hasher = hashlib.sha256()
    with executable.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError('Candidate executable does not match the reviewed hash')
    return {'bundle':bundle, 'app_version':info['CFBundleShortVersionString'],
            'app_build':build, 'executable_sha256':digest,
            'info_plist_sha256':hashlib.sha256((app / 'Info.plist').read_bytes()).hexdigest()}


def stop_owned_console(process):
    """Interrupt only our launch handle; devicectl forwards SIGINT to its app.

    Never discover/terminate arbitrary phone PIDs. The final physical packet must
    verify this platform forwarding behavior; a local process exit is not proof.
    """
    interrupted = process.poll() is None
    if interrupted:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                return {'interrupt_forwarding_requested':True, 'console_force_killed':True,
                        'remote_exit_verified':False}
    return {'interrupt_forwarding_requested':interrupted, 'console_force_killed':False,
            'remote_exit_verified':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--bundle', required=True, choices=['com.beanlabs.BeanFitPocket', 'com.jumpingbeans.v2.imessageprototype'])
    parser.add_argument('--phase', choices=['quality', 'resource', 'thermal'], required=True)
    parser.add_argument('--app', type=Path)
    parser.add_argument('--expected-build', help='Reject a different local or reported app build')
    parser.add_argument('--expected-app-sha256', help='Reviewed executable hash; requires --app')
    parser.add_argument('--model-id', default='qwen2', choices=['liquid12', 'qwen08', 'qwen2'],
                        help='Expected model in the supplied app build; changing this does not reconfigure the app')
    parser.add_argument('--model', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.expected_app_sha256 and not args.app:
        parser.error('--expected-app-sha256 requires --app')
    identity = app_identity(args.app, args.bundle, args.expected_build, args.expected_app_sha256) if args.app else None
    devices = json.loads(args.inventory.read_text())['result']['devices']
    physical = [d for d in devices if d['hardwareProperties'].get('reality') == 'physical'
                and d['connectionProperties'].get('tunnelState') == 'connected']
    assert len(physical) == 1, 'Connect one target iPhone'
    device = physical[0]['identifier']

    def run(*command, required=True):
        result = subprocess.run(['xcrun', 'devicectl', *command], capture_output=True, text=True, timeout=120)
        if required and result.returncode:
            raise RuntimeError('Device operation failed: ' + ' '.join(command[:3]))
        return result.returncode == 0

    packet = Path(__file__).resolve().parents[1] / 'Tests/TextQualityPacket.json'
    catalog = json.loads((Path(__file__).resolve().parents[2] / 'src/beanfit/catalog/on_device.json').read_text())
    artifact = next(m for m in catalog['models'] if m['id'] == args.model_id)['artifacts'][0]
    digest = hashlib.sha256(packet.read_bytes()).hexdigest()
    assert digest == '47f1797303c82d58180f913e697d30c590a69097afed98141d164862bd0d70c5'
    if args.model:
        assert args.model.stat().st_size == artifact['bytes']
        hasher = hashlib.sha256()
        with args.model.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                hasher.update(chunk)
        assert hasher.hexdigest() == artifact['sha256']
    args.output.mkdir(parents=True, exist_ok=False)
    if identity:
        (args.output / 'candidate-identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    if args.app:
        run('device', 'install', 'app', '--device', device, str(args.app))
    if args.model:
        with tempfile.TemporaryDirectory(prefix='beanfit-model-transfer-') as temp:
            models = Path(temp) / 'Models'; models.mkdir()
            try:
                os.link(args.model, models / artifact['filename'])
            except OSError:
                shutil.copy2(args.model, models / artifact['filename'])
            run('device', 'copy', 'to', '--device', device, '--source', str(models), '--destination', 'Documents/Models',
                '--domain-type', 'appDataContainer', '--domain-identifier', args.bundle)
    run('device', 'copy', 'to', '--device', device, '--source', str(packet), '--destination', 'Documents/text-quality-packet.json',
        '--domain-type', 'appDataContainer', '--domain-identifier', args.bundle)
    run_id = str(uuid.uuid4())
    report = None
    with tempfile.TemporaryDirectory(prefix='beanfit-qualification-') as temp:
        path = Path(temp) / 'report.json'
        deadline = time.monotonic() + 900
        last_count = -1
        # --console owns the launch lifetime and forwards catchable signals to
        # that app (installed devicectl help). Keep its device metadata ephemeral.
        with (Path(temp) / 'console.log').open('w') as console:
            process = subprocess.Popen(['xcrun', 'devicectl', 'device', 'process', 'launch',
                '--device', device, '--terminate-existing', '--console', args.bundle,
                '--text-qualify', '--phase=' + args.phase, '--run-id=' + run_id],
                stdout=console, stderr=subprocess.STDOUT)
            try:
                while time.monotonic() < deadline:
                    if run('device', 'copy', 'from', '--device', device, '--source', 'Documents/text-qualification.json',
                           '--destination', str(path), '--domain-type', 'appDataContainer', '--domain-identifier', args.bundle, required=False):
                        current = json.loads(path.read_text())
                        if current.get('run_id') == run_id:
                            report = current
                            (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
                            count = len(report['records'])
                            if count != last_count:
                                print(json.dumps({'phase':args.phase, 'records':count}), flush=True)
                                last_count = count
                            if report.get('completed') or report.get('error'):
                                break
                    if process.poll() is not None:
                        break
                    time.sleep(5)
            finally:
                cleanup = stop_owned_console(process)
                cleanup.update(run_id=run_id, completed=bool(report and report.get('completed')),
                               qualified=False, physical_cleanup_confirmation_required=True)
                (args.output / 'runner-cleanup.json').write_text(json.dumps(cleanup, indent=2) + '\n')
    assert report is not None, 'No fresh report'
    assert report['evidence_kind'] == 'physical-device-resident-and-footprint'
    assert report['packet_sha256'] == digest and not report['qualified']
    assert report['model_sha256'] == artifact['sha256']
    assert report['bundle'] == args.bundle and report['phase'] == args.phase
    if identity:
        assert report.get('app_build') == identity['app_build'] and report.get('app_version') == identity['app_version'], 'Reported app differs from supplied candidate'
    if args.expected_build:
        assert report.get('app_build') == args.expected_build, 'Reported build differs from reviewed candidate'
    if args.phase == 'quality' and report['completed']:
        assert len(report['records']) == 36
    print(json.dumps({key:report.get(key) for key in ['phase','completed','automatic_pass','error','peak_resident_bytes','conservative_peak_bytes','thermal_gate','model_unloaded']}))
    return 0 if report.get('automatic_pass') else 1


if __name__ == '__main__':
    raise SystemExit(main())
