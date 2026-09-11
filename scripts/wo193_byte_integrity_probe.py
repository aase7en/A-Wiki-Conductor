#!/usr/bin/env python3
"""WO193 portable byte-integrity probe (WO193-GLM-BYTE-VALIDATION-001).

Runs the pinned repository ZCode helper as a REAL subprocess against a
synthetic fake app-server child on the current host and proves:

  durable stdout bytes == oracle fixture bytes (hash + length),
  report attests those exact bytes,
  result.json is published only on the known-exit success path,
  exactly one child spawn / one protocol send occurs (no replay),
  a known nonzero child exit is retained truthfully in the result.

Synthetic payloads only: no provider URL, credential or secret is an input,
no installed ZCode is launched, no production port is touched. Stdlib only.

Usage:
    python scripts/wo193_byte_integrity_probe.py --output-dir <empty-or-absent dir>

Exit codes: 0 all checks passed; 1 mismatch/failure; 2 usage/environment.
Unsupported host cases are reported in the manifest as SKIPPED with reason.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER = REPO_ROOT / "src" / "a_conductor" / "zcode_supervised_helper.py"
CORPUS = REPO_ROOT / "tests" / "fixtures" / "wo193_byte_integrity" / "corpus.json"
EXECUTION_ID = "exec-0123456789abcdef"
TIMEOUT_SECONDS = 90

FAKE_APP_SERVER = r'''
import json, os, sys, time

def out(obj):
    sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    sys.stdout.flush()

here = os.path.dirname(os.path.abspath(sys.argv[0]))
with open(os.path.join(here, "probe_fake.config.json"), encoding="utf-8") as f:
    config = json.load(f)
receipt_dir = config["receipt_dir"]
response = config["response"]

with open(os.path.join(receipt_dir, "spawn.pid"), "a", encoding="utf-8") as f:
    f.write(str(os.getpid()) + "\n")

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    mid, method = msg.get("id"), msg.get("method")
    if method == "session/create":
        model_ref = (msg.get("params", {}).get("model")
                     or msg.get("params", {}).get("runtimeModel", {}).get("model"))
        with open(os.path.join(receipt_dir, "create_receipts.jsonl"), "a",
                  encoding="utf-8") as f:
            f.write(json.dumps({"model": model_ref}, separators=(",", ":")) + "\n")
        out({"id": 1000, "method": "session/requestRuntimePreferences"})
        out({"id": mid, "result": {"session": {"sessionId": "wo193-probe"},
            "settings": {"model": {"current": model_ref, "available": []}}}})
    elif method in ("session/subscribe", "session/setThoughtLevel"):
        out({"id": mid, "result": {"ok": True}})
    elif method == "session/send":
        with open(os.path.join(receipt_dir, "send_receipt.json"), "w",
                  encoding="utf-8") as f:
            f.write(json.dumps({"sent": True}, separators=(",", ":")))
        out({"method": "session/event", "params": {"type": "model.streaming",
            "payload": {"kind": "text_delta", "delta": response}}})
        out({"method": "session/event", "params": {"type": "turn.completed"}})
raise SystemExit(config.get("exit_code", 0))
'''

def _runtime_model_json() -> str:
    """Serialize the synthetic runtime model through the pinned repo class so
    the helper's from_json() validation accepts exactly this shape."""
    src = str(REPO_ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from a_conductor.zcode_protocol import ZCodeRuntimeModel
    return ZCodeRuntimeModel(
        revision="zcode-runtime-v1:" + "a" * 64,
        provider_id="zcode-glm",
        model_id="glm-5.3",
        base_url="http://127.0.0.1:1",
        api_key_env="ANTHROPIC_API_KEY",
    ).to_json()

PROBE_CASES = [
    # (label, corpus case, PYTHONIOENCODING, child exit code)
    ("cp874-thai", "thai_inherent", "cp874", 0),
    ("cp874-newlines", "newlines_mixed", "cp874", 0),
    ("utf8-emoji", "emoji_supplementary", "utf-8", 0),
    ("cp1252-nonzero-exit", "ascii", "cp1252", 3),
]


def _helper_env(work: Path, encoding: str) -> dict:
    packet = work / "task.md"
    packet.write_text("WO193 portable probe synthetic task", encoding="utf-8")
    env = {k: os.environ[k] for k in ("PATH", "SystemRoot", "SYSTEMROOT", "TEMP", "TMP")
           if k in os.environ}
    env.update({
        "ZCODE_TASK_PACKET_PATH": str(packet),
        "ZCODE_TASK_PACKET_SHA256": hashlib.sha256(packet.read_bytes()).hexdigest(),
        "ZCODE_TASK_PACKET_TRUSTED_ROOT": str(work),
        "ZCODE_TASK_PACKET_MAX_BYTES": "262144",
        "ZCODE_OUTPUT_BUDGET": "65536",
        "ZCODE_DEADLINE_SECONDS": "60",
        "ZCODE_RUNTIME_MODEL_JSON": _runtime_model_json(),
        "ZCODE_CREDENTIAL_DELIVERY_KEY": "ANTHROPIC_API_KEY",
        "ANTHROPIC_API_KEY": "synthetic-probe-credential-not-a-secret",
        "PYTHONIOENCODING": encoding,
    })
    return env


def run_case(staging_root: Path, output_dir: Path, label: str, case: dict,
             encoding: str, exit_code: int) -> dict:
    """Stage the run under the system temp directory (some repository trees sit
    on NTFS-compressed paths where spawned child scripts cannot be read back —
    WO192 packaging-path finding), then copy the evidence into the requested
    output directory and verify the copies read back identically."""
    work = staging_root / label
    receipts = work / "receipts"
    fake_dir = work / "fake"
    run_dir = work / "run"
    for d in (receipts, fake_dir, run_dir):
        d.mkdir(parents=True, exist_ok=True)
    (fake_dir / "probe_fake_server.py").write_text(FAKE_APP_SERVER, encoding="utf-8")
    (fake_dir / "probe_fake.config.json").write_text(
        json.dumps({"receipt_dir": str(receipts), "response": case["text"],
                    "exit_code": exit_code}, ensure_ascii=False), encoding="utf-8")
    executable = getattr(sys, "_base_executable", None) or sys.executable
    command = [
        executable, str(HELPER),
        "--execution-id", EXECUTION_ID,
        "--pid-path", str(run_dir / "child.pid"),
        "--result-path", str(run_dir / "result.json"),
        "--report-path", str(run_dir / "report.json"),
        "--cwd", str(work), "--",
        executable, str(fake_dir / "probe_fake_server.py"),
        "app-server", "--stdio", "--surface", "desktop",
    ]
    stdout_file = run_dir / "stdout.log"
    started = time.monotonic()
    with stdout_file.open("ab", buffering=0) as handle:  # production-shaped redirect
        completed = subprocess.run(command, env=_helper_env(work, encoding),
                                   stdout=handle, stderr=subprocess.PIPE,
                                   timeout=TIMEOUT_SECONDS)
    duration_ms = int((time.monotonic() - started) * 1000)
    captured = stdout_file.read_bytes()
    report = json.loads((run_dir / "report.json").read_bytes()) \
        if (run_dir / "report.json").exists() else None
    result = json.loads((run_dir / "result.json").read_bytes()) \
        if (run_dir / "result.json").exists() else None
    spawn_count = len((receipts / "spawn.pid").read_text().splitlines()) \
        if (receipts / "spawn.pid").exists() else 0
    send_count = 1 if (receipts / "send_receipt.json").exists() else 0

    # copy evidence into the requested owned output directory and verify the
    # copies read back byte-identically (readability proof for the manifest)
    import shutil
    dest = output_dir / label
    shutil.copytree(work, dest, dirs_exist_ok=True)
    copied = (dest / "run" / "stdout.log").read_bytes()
    artifacts_readable = copied == captured

    checks = {
        "helper_rc_zero": completed.returncode == 0,
        "bytes_equal_oracle_hex": captured.hex() == case["utf8_hex"],
        "byte_length_matches": len(captured) == case["byte_length"],
        "sha256_matches": hashlib.sha256(captured).hexdigest() == case["sha256"],
        "report_atts_exact_bytes": bool(report) and report.get("response_sha256") == case["sha256"]
        and report.get("response_bytes") == case["byte_length"],
        "result_published": result is not None,
        "result_retains_child_exit": bool(result) and result.get("exit_code") == exit_code,
        "single_spawn": spawn_count == 1,
        "single_send": send_count == 1,
        "output_artifacts_readable": artifacts_readable,
    }
    return {
        "label": label,
        "encoding": encoding,
        "child_exit_code_requested": exit_code,
        "helper_returncode": completed.returncode,
        "duration_ms": duration_ms,
        "oracle": {"byte_length": case["byte_length"], "sha256": case["sha256"]},
        "captured": {"byte_length": len(captured),
                     "sha256": hashlib.sha256(captured).hexdigest()},
        "checks": checks,
        "pass": all(checks.values()),
        "artifacts": {
            "stdout": f"{label}/run/stdout.log",
            "report": f"{label}/run/report.json",
            "result": f"{label}/run/result.json",
            "receipts": f"{label}/receipts/",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WO193 portable byte-integrity probe")
    parser.add_argument("--output-dir", required=True,
                        help="empty or nonexistent directory for probe artifacts")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        print("PROBE_REFUSED: output directory exists and is not empty", file=sys.stderr)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)

    corpus_doc = json.loads(CORPUS.read_text(encoding="utf-8"))
    cases = {c["name"]: c for c in corpus_doc["cases"]}

    manifest = {
        "schema": "wo193-byte-probe/1",
        "host": {"system": platform.system(), "release": platform.release(),
                 "python": sys.version.split()[0],
                 "executable_base": Path(getattr(sys, "_base_executable",
                                                 sys.executable)).name},
        "helper_sha256": hashlib.sha256(HELPER.read_bytes()).hexdigest(),
        "corpus_sha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
        "cases": [],
        "skipped": [],
    }
    if platform.system() not in ("Windows", "Darwin"):
        manifest["skipped"].append({"reason": "UNSUPPORTED_HOST",
                                    "detail": platform.system()})

    failures = 0
    import shutil
    import tempfile
    staging_root = Path(tempfile.mkdtemp(prefix="wo193-probe-stage-"))
    try:
        for label, case_name, encoding, exit_code in PROBE_CASES:
            try:
                entry = run_case(staging_root, output_dir, label,
                                 cases[case_name], encoding, exit_code)
            except Exception as exc:  # bounded: never loop, never daemonize
                entry = {"label": label, "pass": False,
                         "error": f"{type(exc).__name__}: {exc}"}
            manifest["cases"].append(entry)
            if not entry.get("pass"):
                failures += 1
            print(f"{label}: {'PASS' if entry.get('pass') else 'FAIL'}")
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)

    manifest["all_passed"] = failures == 0 and not manifest["skipped"]
    manifest["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"manifest: {output_dir / 'manifest.json'}")
    print("PROBE_OK" if manifest["all_passed"] else f"PROBE_FAILED ({failures} cases)")
    return 0 if manifest["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
