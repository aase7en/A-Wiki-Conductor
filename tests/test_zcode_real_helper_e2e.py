"""WO-P1-158 Prompt-1 RED E2E — the REAL specialized helper happy path.

The test must actually launch:

    production assembly
    -> SupervisedRunCoordinator
    -> SupervisedExecutionService
    -> SupervisedHelperKind.ZCODE_APP_SERVER_V1
    -> zcode_supervised_helper.py
    -> exactly one fake app-server child
    -> protocol
    -> canonical artifacts
    -> durable collect

No in-process transport substitute may satisfy these tests (GPT1 review
comment 5558197043: the current suite passed while the real happy-path
helper crashed before child spawn with NameError: Path is not defined).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import pytest

from a_conductor.claude_code_harness import TaskPacketFile
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.provider_configuration import (
    ActorCapabilityEvidence,
    EgressBoundary,
    HarnessRuntimeBinding,
    HarnessStrategy,
    ProviderConfiguration,
    ProviderModelConfiguration,
    ProviderTrustClass,
    ProtocolFamily,
)
from a_conductor.zcode_production_assembly import ZCodeExecutionAuthorities, assemble_zcode_execution

BINDING = HarnessRuntimeBinding(
    harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
    runtime_provider_ref="zcode-runtime/glm-main",
    runtime_model_ref="zcode-runtime/glm-5.3",
)
BASE_URL = "http://127.0.0.1:1"
SECRET = "wo158-e2e-opaque-secret-1f4a9c"
PROMPT_MARKER = "ZRA1-E2E-PROMPT-MARKER-4815162342"
RESPONSE_TEXT = "ZRA1-REAL-HELPER-OK"

FAKE_APP_SERVER = r'''
import json, os, sys, time

def out(obj):
    sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    sys.stdout.flush()

here = os.path.dirname(os.path.abspath(sys.argv[0]))
with open(os.path.join(here, "fake_app_server.config.json"), encoding="utf-8") as f:
    config = json.load(f)
receipt_dir = config.get("receipt_dir", "")
mode = config.get("mode", "ok")

self_observation = None
src_dir = config.get("src_dir", "")
if src_dir:
    try:
        sys.path.insert(0, src_dir)
        from a_conductor.zcode_process_truth import observe_child_process
        self_observation = observe_child_process(os.getpid())
    except Exception:
        self_observation = None

if receipt_dir:
    with open(os.path.join(receipt_dir, "spawn.pid"), "a", encoding="utf-8") as f:
        f.write(str(os.getpid()) + "\n")
    with open(os.path.join(receipt_dir, "child_env.json"), "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "argv": sys.argv, "env": dict(os.environ),
                   "started_ns": time.time_ns(),
                   "self_observed_executable": (self_observation or {}).get("executable")}, f)

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    mid, method = msg.get("id"), msg.get("method")
    if method == "session/create":
        out({"id": 1000, "method": "session/requestRuntimePreferences"})
        out({"id": mid, "result": {"session": {"sessionId": "fake-session-1"}}})
    elif method == "session/subscribe":
        out({"id": mid, "result": {"ok": True}})
    elif method == "session/send":
        content = msg.get("params", {}).get("content", "")
        if receipt_dir:
            with open(os.path.join(receipt_dir, "send_receipt.json"), "w", encoding="utf-8") as f:
                json.dump({"received_at_ns": time.time_ns(), "content": content}, f)
        if mode == "quiet":
            pass
        elif mode == "huge":
            out({"method": "session/event", "params": {"type": "model.streaming",
                "payload": {"kind": "text_delta", "delta": "x" * (64 * 1024 + 1)}}})
        elif mode == "fail":
            out({"method": "session/event", "params": {"type": "turn.failed"}})
        else:
            out({"method": "session/event", "params": {"type": "model.streaming",
                "payload": {"kind": "text_delta", "delta": "%s"}}})
            out({"method": "session/event", "params": {"type": "turn.completed"}})
sys.exit(0)
'''.replace("%s", RESPONSE_TEXT)


class Snapshot:
    def __init__(self, generation, profile):
        self.generation = generation
        self.profile = profile


class Secrets:
    def __init__(self, value=SECRET):
        self.value = value
        self.requests: list[str] = []

    def resolve(self, ref):
        self.requests.append(ref)
        return self.value


def _profile():
    return ProviderConfiguration(
        provider_id="zcode-glm",
        display_name="ZCode GLM",
        provider_type="zcode-app-server",
        protocol_family=ProtocolFamily.CUSTOM,
        endpoint_ref="zcode-desktop",
        credential_ref="secret-ref:zcode-credential",
        trust_class=ProviderTrustClass.FIRST_PARTY,
        egress_boundary=EgressBoundary.LOCAL_MACHINE,
        harness_strategies=(HarnessStrategy.ZCODE_APP_SERVER,),
        max_concurrency=1,
        models=(ProviderModelConfiguration(
            model_id="glm-5.3",
            display_name="GLM 5.3",
            actor_capabilities=(ActorCapabilityEvidence("code", "DECLARED", "wo158"),),
            runtime_binding=BINDING,
        ),),
        enabled=True,
        schema_version="1.1.0",
    )


def _write_fake_app_server(fake_dir: Path, receipt_dir: Path, mode: str) -> Path:
    fake_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    src_dir = Path(__file__).resolve().parent.parent / "src"
    script = fake_dir / "fake_app_server.py"
    script.write_text(FAKE_APP_SERVER, encoding="utf-8")
    (fake_dir / "fake_app_server.config.json").write_text(
        json.dumps({"mode": mode, "receipt_dir": str(receipt_dir), "src_dir": str(src_dir)}),
        encoding="utf-8",
    )
    return script


def _packet(tmp_path: Path, text: str | None = None) -> TaskPacketFile:
    text = text if text is not None else f"{PROMPT_MARKER} Return exactly {RESPONSE_TEXT}."
    path = tmp_path / "task-packet.md"
    path.write_text(text, encoding="utf-8")
    return TaskPacketFile(
        task_contract_ref="WO-P1-158-ZRA1-E2E",
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def build_real_service_authorities(tmp_path: Path) -> ZCodeExecutionAuthorities:
    """REAL owned-process authorities (Windows) for the production service."""
    from a_conductor.owned_process import WindowsOwnedProcessController
    from a_conductor.windows_io import LoopbackReadyzHttpProbe, StrictPowerShellInspectionRunner
    from a_conductor.windows_observer import WindowsRuntimeObserver

    runtime_python = getattr(sys, "_base_executable", sys.executable)
    observer = WindowsRuntimeObserver(
        runner=StrictPowerShellInspectionRunner(),
        http_probe=LoopbackReadyzHttpProbe(),
    )
    return ZCodeExecutionAuthorities(
        provider_snapshot=Snapshot(1, _profile()),
        secret_resolver=Secrets(),
        execution_store=SQLiteExecutionStore(tmp_path / "control.sqlite"),
        supervised_controller=WindowsOwnedProcessController(observer=observer),
        supervised_observer=observer,
        python_executable=runtime_python,
        worker_id="a-worker-01",
        repo_root=str(tmp_path),
        branch="feat/wo-p1-158-zcode-zero-relay",
        head="h" * 40,
        dirty=False,
    )


def _run_e2e(tmp_path: Path, *, mode: str = "ok", deadline_seconds: float = 30.0,
             tamper_after_intake: bool = False):
    runtime_python = getattr(sys, "_base_executable", sys.executable)
    fake_script = _write_fake_app_server(tmp_path / "fake", tmp_path / "receipts", mode)
    packet = _packet(tmp_path)
    authorities = build_real_service_authorities(tmp_path)
    runner = assemble_zcode_execution(
        authorities=authorities,
        packet=packet,
        model_id="glm-5.3",
        expected_generation=1,
        authorized_base_url=BASE_URL,
        secret_reference="secret-ref:zcode-credential",
        workspace=str(tmp_path),
        executable=runtime_python,
        bundle_js=str(fake_script),
        deadline_seconds=deadline_seconds,
    )
    if tamper_after_intake:
        (tmp_path / "task-packet.md").write_text("TAMPERED " + PROMPT_MARKER, encoding="utf-8")
    started = time.monotonic()
    result = runner.run(timeout_seconds=int(deadline_seconds) + 60)
    elapsed = time.monotonic() - started
    return result, elapsed, authorities, tmp_path / "receipts"


def _run_dir_files(store_db: Path, repo: Path) -> Path:
    import sqlite3

    con = sqlite3.connect(store_db)
    row = con.execute("SELECT run_dir_ref FROM execution_records ORDER BY rowid DESC LIMIT 1").fetchone()
    con.close()
    return repo / row[0]


NT_ONLY = pytest.mark.skipif(os.name != "nt", reason="Windows real-helper integration")


@NT_ONLY
def test_real_helper_happy_path_e2e(tmp_path: Path) -> None:
    """The full real chain executes: assembly -> coordinator -> service ->
    specialized helper -> one fake app-server child -> artifacts -> collect."""
    result, elapsed, authorities, receipts = _run_e2e(tmp_path)
    store_db = tmp_path / "control.sqlite"
    run_dir = _run_dir_files(store_db, tmp_path)

    # 1. helper CLI started and the chain succeeded end to end
    assert result.exit_code == 0, result.stderr
    # 7. response returned through the canonical artifact mapping
    assert result.stdout == RESPONSE_TEXT
    # 2. exactly one app-server child spawned
    spawn_pids = (receipts / "spawn.pid").read_text(encoding="utf-8").split()
    assert len(spawn_pids) == 1, spawn_pids
    child_pid = int(spawn_pids[0])

    # 3. exact verified packet bytes reached the child via the protocol
    send_receipt = json.loads((receipts / "send_receipt.json").read_text(encoding="utf-8"))
    expected_prompt = f"{PROMPT_MARKER} Return exactly {RESPONSE_TEXT}."
    assert send_receipt["content"] == expected_prompt

    # 4. identity written BEFORE the first task send
    identity_stat = (run_dir / "child.identity.json").stat()
    assert identity_stat.st_mtime_ns < send_receipt["received_at_ns"]

    # 5. the accepted secret reached the real child environment
    child_env = json.loads((receipts / "child_env.json").read_text(encoding="utf-8"))
    assert child_env["pid"] == child_pid
    assert child_env["env"]["ANTHROPIC_API_KEY"] == SECRET

    # 6. prompt/credential confinement: prompt never in child argv/env;
    #    the credential env is explicit-only (no arbitrary inheritance)
    env_snapshot = json.dumps(child_env["env"])
    assert PROMPT_MARKER not in env_snapshot
    assert PROMPT_MARKER not in json.dumps(child_env["argv"])
    allowed_env_keys = {"ELECTRON_RUN_AS_NODE", "ANTHROPIC_API_KEY"}
    assert set(child_env["env"]) == allowed_env_keys, sorted(child_env["env"])

    # 9. report written before result
    report_stat = (run_dir / "report.json").stat()
    result_stat = (run_dir / "result.json").stat()
    assert report_stat.st_mtime_ns <= result_stat.st_mtime_ns

    # 10. canonical six-key result written only on the real terminal exit
    result_doc = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert set(result_doc) == {
        "schema_version", "execution_id", "child_pid", "exit_code",
        "started_at", "finished_at",
    }
    assert result_doc["exit_code"] == 0
    assert result_doc["child_pid"] == child_pid

    # 11. child identity is exact: observed PID/creation/executable/parent
    identity_doc = json.loads((run_dir / "child.identity.json").read_text(encoding="utf-8"))
    assert identity_doc["child_pid"] == child_pid
    # executable exactness: the child's OWN OS observation (same primitive,
    # same authority) agrees byte-for-byte with the durable identity
    self_observed = child_env["self_observed_executable"]
    assert isinstance(self_observed, str) and self_observed
    assert identity_doc["executable"].casefold() == self_observed.casefold()
    supervisor_pid = int((run_dir / "supervisor.pid").read_text(encoding="utf-8").strip())
    assert identity_doc["parent_pid"] == supervisor_pid  # actual parent = the helper
    started_ms = int(time.time() * 1000) - 120_000
    assert started_ms <= identity_doc["child_created_epoch_ms"] <= int(time.time() * 1000) + 5_000

    # durable collect happened through the canonical store
    import sqlite3

    con = sqlite3.connect(store_db)
    row = con.execute(
        "SELECT execution_state, pid FROM execution_records ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    con.close()
    assert row[0] in ("VERIFICATION_REQUIRED", "SUCCEEDED")
    assert row[1] == child_pid
    # the helper finished promptly (bounded protocol, no hangs)
    assert elapsed < 60.0


@NT_ONLY
def test_packet_tamper_after_intake_fails_typed_pre_send(tmp_path: Path) -> None:
    """TaskPacketFile re-read occurs: bytes changed after intake are rejected
    immediately before the protocol send; no result is ever fabricated."""
    result, _, authorities, receipts = _run_e2e(tmp_path, tamper_after_intake=True)
    run_dir = _run_dir_files(tmp_path / "control.sqlite", tmp_path)

    assert result.exit_code is None  # failure mapping, not success
    assert result.stderr.startswith("SUPERVISOR_RECOVERY_REQUIRED")
    # the helper's typed code is durable in the captured stderr artifact
    stderr_log = (run_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
    assert "ZCODE_HELPER_EXIT code=ZCODE_TASK_PACKET_TOCTOU" in stderr_log, stderr_log
    # 14. no traceback on expected runtime failure
    assert "Traceback" not in stderr_log
    # the tampered bytes never reached a child (no send receipt at all)
    assert not (receipts / "send_receipt.json").exists()
    # no canonical result fabricated
    assert not (run_dir / "result.json").exists()


@NT_ONLY
def test_response_budget_enforced_e2e(tmp_path: Path) -> None:
    """64 KiB limit enforced in the real child pipe."""
    result, _, authorities, receipts = _run_e2e(tmp_path, mode="huge")
    run_dir = _run_dir_files(tmp_path / "control.sqlite", tmp_path)
    assert result.exit_code is None
    stderr_log = (run_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
    assert "ZCODE_HELPER_EXIT code=RESPONSE_BUDGET_EXCEEDED" in stderr_log, stderr_log
    assert "Traceback" not in stderr_log
    assert not (run_dir / "result.json").exists()


@NT_ONLY
def test_deadline_is_actually_bounded_e2e(tmp_path: Path) -> None:
    """A silent child cannot block the helper: read timeouts are honored and
    the bounded deadline produces a typed failure (no infinite readline)."""
    result, elapsed, _, receipts = _run_e2e(tmp_path, mode="quiet", deadline_seconds=4.0)
    run_dir = _run_dir_files(tmp_path / "control.sqlite", tmp_path)
    assert result.exit_code is None
    stderr_log = (run_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
    assert "ZCODE_HELPER_EXIT code=TURN_DEADLINE_EXCEEDED" in stderr_log, stderr_log
    assert "Traceback" not in stderr_log
    # 12. bounded: the helper honored the 4s protocol deadline + bounded exit
    # wait — a blocking readline() would hang forever on the silent child
    assert elapsed < 30.0, f"helper did not respect the bounded deadline: {elapsed}"
    assert not (run_dir / "result.json").exists()


def test_helper_source_has_no_kill_ladder() -> None:
    """13. no terminate/kill ladder in the specialized helper."""
    source = (Path(__file__).parent.parent / "src" / "a_conductor" / "zcode_supervised_helper.py").read_text(
        encoding="utf-8"
    )
    for banned in (".terminate(", ".kill(", "taskkill", "TerminateProcess", "Stop-Process"):
        assert banned not in source, banned
