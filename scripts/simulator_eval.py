#!/usr/bin/env python3
"""Explicit local iOS-simulator quality screen. No network or model downloads.

Results are NOT physical-device qualification or whole-stack memory evidence.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time


def grade(case, answer):
    if "expected_json" in case:
        try:
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("duplicate JSON key")
                    result[key] = value
                return result
            return json.loads(answer, object_pairs_hook=unique) == case["expected_json"]
        except (ValueError, TypeError):
            return False
    return answer.strip().rstrip(".").strip().casefold() == case["expected"].casefold()


def prompt_for(question, template):
    prompt = ("<|im_start|>system\nYou are a helpful assistant. Follow the requested output format. "
              "Use only the supplied facts. Never invent missing information.<|im_end|>\n"
              "<|im_start|>user\n" + question + "<|im_end|>\n<|im_start|>assistant\n")
    if template == "qwen3-no-thinking":
        prompt += "<think>\n\n</think>\n\n"
    return prompt


def summarize(trials, workload):
    passed = sum(t["quality_pass"] for t in trials)
    critical = {c["id"] for c in workload["cases"] if c.get("critical")}
    failures = sorted({t["case_id"] for t in trials if not t["quality_pass"]})
    complete = (Counter(t["case_id"] for t in trials) ==
                {c["id"]: workload["repeats"] for c in workload["cases"]}
                and all(t["outcome"] == "completed" for t in trials))
    quality = passed / len(trials) if trials else 0
    return {"passed": passed, "total": len(trials), "quality": quality,
            "failed_cases": failures, "critical_failures": sorted(critical.intersection(failures)),
            "simulator_quality_screen_pass": complete and quality >= workload["quality_floor"]
                and not critical.intersection(failures),
            "physical_device_qualified": False, "peak_stack_bytes": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--simulator", required=True)
    parser.add_argument("--workload", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--template", choices=["chatml", "qwen3-no-thinking"], default="chatml")
    args = parser.parse_args()
    hasher = hashlib.sha256()
    with args.model.open("rb") as model:
        for chunk in iter(lambda: model.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    if digest != args.sha256:
        parser.error("model SHA-256 mismatch")
    build = subprocess.run(["xcrun", "vtool", "-show-build", str(args.binary)],
                           capture_output=True, text=True, check=True).stdout
    if "platform IOSSIMULATOR" not in build:
        parser.error("binary must target iOS Simulator, not macOS")
    inventory = json.loads(subprocess.run(["xcrun", "simctl", "list", "devices", "-j"],
                            capture_output=True, text=True, check=True).stdout)
    matches = [(runtime, d) for runtime, devices in inventory["devices"].items()
               for d in devices if d["udid"] == args.simulator and d["state"] == "Booted"]
    if len(matches) != 1:
        parser.error("a known booted simulator is required")
    runtime, device = matches[0]
    workload_bytes = args.workload.read_bytes()
    workload = json.loads(workload_bytes)
    args.output.mkdir(parents=True, exist_ok=False)
    trials = []
    for case in workload["cases"]:
        for repeat in range(workload["repeats"]):
            tid = f'{case["id"]}-{repeat}'
            prompt = prompt_for(case["prompt"], args.template)
            start = time.monotonic()
            command = ["xcrun", "simctl", "spawn", args.simulator, str(args.binary),
                       "-m", str(args.model), "-ngl", "0", "-n", str(workload["max_output_tokens"]), prompt]
            try:
                run = subprocess.run(command, capture_output=True, text=True, timeout=30)
                # Upstream llama-simple echoes input. Never grade the echo.
                if run.returncode == 0 and run.stdout.startswith(prompt):
                    answer, outcome = run.stdout[len(prompt):].strip(), "completed"
                else:
                    answer, outcome = "", "failed"
                (args.output / f"{tid}.stdout.txt").write_text(run.stdout)
                (args.output / f"{tid}.stderr.txt").write_text(run.stderr)
            except subprocess.TimeoutExpired:
                answer, outcome = "", "timeout"
            trial = {"id": tid, "case_id": case["id"], "outcome": outcome,
                     "answer": answer, "quality_pass": outcome == "completed" and grade(case, answer),
                     "wall_ms": round((time.monotonic() - start) * 1000, 2)}
            trials.append(trial)
            print(json.dumps({"id": tid, "pass": trial["quality_pass"], "answer": answer}), flush=True)
    result = {"schema": "beanfit.simulator.quality.v1", "evidence_kind": "simulator",
              "recorded_at": datetime.now(timezone.utc).isoformat(), "simulator": device["name"],
              "simulator_runtime": runtime, "model_file": args.model.name,
              "model_sha256": digest, "model_bytes": args.model.stat().st_size,
              "binary_sha256": hashlib.sha256(args.binary.read_bytes()).hexdigest(),
              "workload_sha256": hashlib.sha256(workload_bytes).hexdigest(),
              "backend": "CPU-only; Metal and Accelerate disabled", "template": args.template,
              "sampling": "greedy", "context": "upstream llama-simple: prompt tokens + output cap - 1",
              "summary": summarize(trials, workload), "trials": trials,
              "limits": ["Mac-backed simulator, not iPhone hardware", "No total memory/battery/thermal qualification",
                         "Fixed fictional screening cases, not production product acceptance",
                         "Runtime has no configured network backend; network isolation not independently audited",
                         "wall_ms includes simulator launch and model load; not device latency"]}
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
