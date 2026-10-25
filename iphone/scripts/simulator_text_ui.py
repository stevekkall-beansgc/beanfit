#!/usr/bin/env python3
"""Run owned text UI tests on a fresh disposable simulator, never a phone.

Uses an already-built xctestrun and explicit app/model paths. Captures the raw
Xcode result privately; publishes only sanitized counts after result finalization.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess


def run(command, **kwargs):
    return subprocess.run(command, capture_output=True, text=True, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, help="Exact installed iOS simulator runtime identifier")
    parser.add_argument("--xctestrun", type=Path, required=True)
    parser.add_argument("--pocket-app", type=Path, required=True)
    parser.add_argument("--beansprout-app", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New evidence directory")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    catalog = json.loads((root / "src/beanfit/catalog/on_device.json").read_text())
    artifact = next(m for m in catalog["models"] if m["id"] == "qwen2")["artifacts"][0]
    assert args.model.stat().st_size == artifact["bytes"]
    with args.model.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == artifact["sha256"]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    simulator = run(["xcrun", "simctl", "create", "BeanFit isolated text UI",
                     "com.apple.CoreSimulator.SimDeviceType.iPhone-14-Pro-Max", args.runtime]).stdout.strip()
    process = None
    report = {"evidence_kind": "simulator-ui-not-phone", "runtime": args.runtime,
              "model_sha256": artifact["sha256"], "qualified": False, "completed": False,
              "passed": False, "phone_operations": False}
    try:
        run(["xcrun", "simctl", "boot", simulator])
        run(["xcrun", "simctl", "bootstatus", simulator, "-b"], timeout=120)
        for app, bundle in [(args.pocket_app, "com.beanlabs.BeanFitPocket"),
                            (args.beansprout_app, "com.jumpingbeans.v2.imessageprototype")]:
            run(["xcrun", "simctl", "install", simulator, str(app.resolve())])
            container = Path(run(["xcrun", "simctl", "get_app_container", simulator, bundle, "data"]).stdout.strip())
            models = container / "Documents/Models"
            models.mkdir(parents=True, exist_ok=True)
            shutil.copy2(args.model, models / artifact["filename"])
        command = ["xcodebuild", "test-without-building", "-xctestrun", str(args.xctestrun.resolve()),
                   "-destination", "id=" + simulator, "-parallel-testing-enabled", "NO",
                   "-collect-test-diagnostics", "never", "-resultBundlePath", str(output / "tests.xcresult")]
        with (output / "xcode.log").open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=300)
            except subprocess.TimeoutExpired:
                report["error"] = "Xcode driver timed out; not a completed UI result"
                os.killpg(process.pid, signal.SIGINT)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                code = 124
        report["xcode_exit"] = code
        if code != 124:
            result = run(["xcrun", "xcresulttool", "get", "test-results", "summary",
                          "--path", str(output / "tests.xcresult")])
            summary = json.loads(result.stdout)
            report.update(completed=True, passed=code == 0 and summary["failedTests"] == 0 and summary["passedTests"] == 2 and summary["skippedTests"] == 0,
                          tests=summary["totalTestCount"], passed_tests=summary["passedTests"],
                          failed_tests=summary["failedTests"], skipped_tests=summary["skippedTests"])
        for bundle, name in [("com.beanlabs.BeanFitPocket", "pocket"),
                             ("com.jumpingbeans.v2.imessageprototype", "beansprout")]:
            container = Path(run(["xcrun", "simctl", "get_app_container", simulator, bundle, "data"]).stdout.strip())
            receipt = container / "Documents/text-ui-lifecycle.json"
            if receipt.exists():
                (output / (name + "-lifecycle.json")).write_text(receipt.read_text())
                events = [event for event in json.loads(receipt.read_text()) if event["reason"].startswith("Paused in background")]
                valid = bool(events) and all(event["model_unloaded"] and event["duration_ms"] <= 2000 for event in events)
                report[name + "_background_unload_passed"] = valid
                report[name + "_background_unload_ms"] = max((event["duration_ms"] for event in events), default=None)
                report["passed"] = report["passed"] and valid
            else:
                report[name + "_background_unload_passed"] = False
                report["passed"] = False
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        subprocess.run(["xcrun", "simctl", "shutdown", simulator], capture_output=True)
        removed = subprocess.run(["xcrun", "simctl", "delete", simulator], capture_output=True)
        report["temporary_simulator_removed"] = removed.returncode == 0
        report["passed"] = report["passed"] and report["temporary_simulator_removed"]
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
