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
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from a_conductor.agent_change_packets import AgentChangeApplier, AgentResultPacket
from a_conductor.claude_code_harness import TaskPacketFile
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.native_execution import NativeExecutionScope, NativeFileSystem
from a_conductor.provider_config_store import (
    ProviderAdmissionKind,
    ProviderAdmissionRecord,
    SQLiteProviderConfigStore,
)
from a_conductor.provider_configuration import (
    ActorCapabilityEvidence,
    EgressBoundary,
    HarnessRuntimeBinding,
    HarnessStrategy,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderHealth,
    ProviderModelConfiguration,
    ProviderObservation,
    ProviderTrustClass,
    ProtocolFamily,
)
from a_conductor.registry import windows_worktree_key
from a_conductor.worker_lease import (
    LeaseMutationIntent,
    LeaseOutcomeKind,
    SQLiteWorkerLeaseStore,
    WorkerLease,
    WorkerLeaseBroker,
    WorkerLeaseCandidate,
    WorkerLeaseRequest,
)
from a_conductor.zcode_production_assembly import ZCodeExecutionAuthorities, assemble_zcode_execution

BINDING = HarnessRuntimeBinding(
    harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
    runtime_provider_ref="zcode-runtime/glm-main",
    runtime_model_ref="zcode-runtime/glm-5.3",
)
BASE_URL = "http://127.0.0.1:1"
ENDPOINT = ProviderEndpointConfig(endpoint_ref="zcode-desktop", base_url=BASE_URL)
SECRET = "wo158-e2e-opaque-secret-1f4a9c"
PROMPT_MARKER = "ZRA1-E2E-PROMPT-MARKER-4815162342"
RESPONSE_TEXT = "ZRA1-REAL-HELPER-OK"
BRANCH = "feat/wo-p1-158-zcode-zero-relay"
HEAD = "h" * 40
TASK_REF = "WO-P1-158-ZRA1-E2E"

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
        create_params = msg.get("params", {})
        runtime_model = create_params.get("runtimeModel", {})
        model_ref = create_params.get("model") or runtime_model.get("model")
        if receipt_dir:
            with open(os.path.join(receipt_dir, "create_receipts.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps({"model": model_ref, "runtimeModel": runtime_model}, separators=(",", ":")) + "\n")
        out({"id": 1000, "method": "session/requestRuntimePreferences"})
        out({"id": mid, "result": {
            "session": {"sessionId": "fake-session-1"},
            "settings": {"model": {"current": model_ref, "available": []}},
        }})
    elif method == "session/subscribe":
        out({"id": mid, "result": {"ok": True}})
    elif method == "session/send":
        content = msg.get("params", {}).get("content", "")
        if receipt_dir:
            with open(os.path.join(receipt_dir, "send_receipt.json"), "w", encoding="utf-8") as f:
                json.dump({"received_at_ns": time.time_ns(), "content": content}, f)
        if mode == "quiet":
            pass
        elif mode == "flood":
            out({"method": "session/event", "params": {"type": "model.streaming",
                "payload": {"kind": "text_delta", "delta": "f" * 200000}}})
        elif mode == "huge":
            out({"method": "session/event", "params": {"type": "model.streaming",
                "payload": {"kind": "text_delta", "delta": "x" * (64 * 1024 + 1)}}})
        elif mode == "fail":
            out({"method": "session/event", "params": {"type": "turn.failed"}})
        else:
            out({"method": "session/event", "params": {"type": "model.streaming",
                "payload": {"kind": "text_delta", "delta": "%s"}}})
            out({"method": "session/event", "params": {"type": "turn.completed"}})
if mode == "delayed" and receipt_dir:
    import time as _t
    _t.sleep(2.0)
    with open(os.path.join(receipt_dir, "exit_receipt.json"), "w", encoding="utf-8") as f:
        f.write(str(_t.time_ns()))
sys.exit(0)
'''.replace("%s", RESPONSE_TEXT)


class Snapshot:
    def __init__(self, generation, profile, endpoint=ENDPOINT):
        self.generation = generation
        self.profile = profile
        self.endpoint = endpoint


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
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
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


def build_lease(tmp_path: Path) -> WorkerLease:
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc).isoformat()
    return WorkerLease(
        lease_id="lease-e2e-0001",
        worker_id="a-worker-01",
        session_id="sess-e2e",
        task_id=TASK_REF,
        project_id="zcode",
        runtime_id=None,
        worktree_key=windows_worktree_key(str(tmp_path)),
        branch=BRANCH,
        expected_head=HEAD,
        required_capabilities=("code",),
        allowed_scope=("src/a_conductor", "src/a_conductor/*"),
        forbidden_scope=("secrets", "secrets/*"),
        mutable_scope=("src/a_conductor/*",),
        mutation_intent=LeaseMutationIntent.MUTATION,
        acquired_at=now,
        heartbeat_at=now,
        lease_ttl_seconds=600,
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    )


def build_admission() -> ProviderAdmissionRecord:
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    return ProviderAdmissionRecord(
        admission_id="provider-admission-e2e-0001",
        provider_id="zcode-glm",
        execution_id="exec-e2e-bound-0001",
        batch_id="batch-e2e-0001",
        acquired_at=now,
        expires_at=now + timedelta(minutes=10),
        status="ACTIVE",  # canonical SQLiteProviderConfigStore record state
        configuration_generation=1,
    )


def build_real_service_authorities(tmp_path: Path) -> ZCodeExecutionAuthorities:
    """REAL owned-process authorities (Windows) + accepted typed lease and
    provider-admission records for the production service path."""
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
        lease_evidence=build_lease(tmp_path),
        admission_evidence=build_admission(),
        dispatch_batch_id="batch-e2e-0001",
        dispatch_execution_id="exec-e2e-bound-0001",
        project_id="zcode",
        requested_mutable_scope=("src/a_conductor/zcode_runner.py",),
        worker_id="a-worker-01",
        repo_root=str(tmp_path),
        branch=BRANCH,
        head=HEAD,
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
        expected_base_url=BASE_URL,
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


@NT_ONLY
def test_restart_after_complete_collects_durably_no_respawn(tmp_path: Path) -> None:
    """Restart/recovery after the real helper E2E: a FRESH session (new
    authorities/runner over the SAME durable store) re-runs the same task —
    dedup reuses the completed execution, collects the canonical result from
    durable artifacts, and spawns ZERO additional children."""
    result, _, _, receipts = _run_e2e(tmp_path)
    assert result.exit_code == 0
    spawns_after_first = (receipts / "spawn.pid").read_text(encoding="utf-8").split()
    assert len(spawns_after_first) == 1

    # fresh process/session: brand-new authorities + runner over the same DB
    runtime_python = getattr(sys, "_base_executable", sys.executable)
    fake_script = tmp_path / "fake" / "fake_app_server.py"
    authorities = build_real_service_authorities(tmp_path)
    runner = assemble_zcode_execution(
        authorities=authorities,
        packet=_packet(tmp_path),
        model_id="glm-5.3",
        expected_generation=1,
        expected_base_url=BASE_URL,
        secret_reference="secret-ref:zcode-credential",
        workspace=str(tmp_path),
        executable=runtime_python,
        bundle_js=str(fake_script),
        deadline_seconds=30.0,
    )
    second = runner.run(timeout_seconds=90)
    assert second.exit_code == 0
    assert second.stdout == RESPONSE_TEXT  # collected from durable artifacts
    spawns_after_restart = (receipts / "spawn.pid").read_text(encoding="utf-8").split()
    assert len(spawns_after_restart) == 1  # zero respawn — reuse, not replay

    import sqlite3

    con = sqlite3.connect(tmp_path / "control.sqlite")
    rows = con.execute("SELECT COUNT(*) FROM execution_records").fetchone()[0]
    con.close()
    assert rows == 1  # exactly one durable execution


@NT_ONLY
def test_flooding_child_becomes_typed_overflow_e2e(tmp_path: Path) -> None:
    """P2-1: the bounded reader cannot grow without bound — a flooding child
    (single giant line) becomes a TYPED overflow failure; no result is
    fabricated, shutdown stays safe, diagnostics leak nothing."""
    result, elapsed, _, receipts = _run_e2e(tmp_path, mode="flood")
    run_dir = _run_dir_files(tmp_path / "control.sqlite", tmp_path)
    assert result.exit_code is None
    stderr_log = (run_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
    assert "ZCODE_HELPER_EXIT code=CHILD_OUTPUT_OVERFLOW" in stderr_log, stderr_log
    assert "Traceback" not in stderr_log
    # diagnostics carry neither the credential nor the prompt
    assert SECRET not in stderr_log
    assert PROMPT_MARKER not in stderr_log
    assert not (run_dir / "result.json").exists()
    assert elapsed < 60.0  # bounded, no hang


@NT_ONLY
def test_finished_at_follows_real_terminal_exit_e2e(tmp_path: Path) -> None:
    """P2-2: finished_at corresponds to the KNOWN terminal-exit boundary. The
    child completes the protocol, then delays its natural exit by 2s and
    receipts the exit instant; the canonical finished_at must be >= that
    receipt (a pre-exit capture would precede it)."""
    from datetime import datetime

    result, _, _, receipts = _run_e2e(tmp_path, mode="delayed", deadline_seconds=30.0)
    run_dir = _run_dir_files(tmp_path / "control.sqlite", tmp_path)
    assert result.exit_code == 0
    receipt_ns = int((receipts / "exit_receipt.json").read_text(encoding="utf-8").strip())
    receipt_ms = receipt_ns / 1_000_000
    result_doc = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    finished_ms = datetime.fromisoformat(result_doc["finished_at"]).timestamp() * 1000
    started_ms = datetime.fromisoformat(result_doc["started_at"]).timestamp() * 1000
    assert started_ms < receipt_ms <= finished_ms, (started_ms, receipt_ms, finished_ms)


# WO-P1-178 composes canonical provider/lease authorities through the already
# accepted real-helper path.  The test remains test-only: no production seam is
# introduced here.

@NT_ONLY
def test_same_packet_two_models_no_reuse_e2e(tmp_path: Path) -> None:
    """P1-1 critical negative: the SAME verified TaskPacket under a DIFFERENT
    model/runtime binding in the SAME provider generation must NOT reuse the
    previous execution — two spawns, two durable rows."""
    import sqlite3
    from dataclasses import replace as _replace

    from a_conductor.provider_configuration import HarnessRuntimeBinding as _B

    result, _, _, receipts = _run_e2e(tmp_path)
    assert result.exit_code == 0
    assert len((receipts / "spawn.pid").read_text(encoding="utf-8").split()) == 1

    two_model_profile = _replace(
        _profile(),
        models=(
            _profile().models[0],
            ProviderModelConfiguration(
                model_id="glm-4.7",
                display_name="GLM 4.7",
                actor_capabilities=(ActorCapabilityEvidence("code", "DECLARED", "wo158"),),
                runtime_binding=_B(
                    harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
                    runtime_provider_ref="zcode-runtime/glm-main",
                    runtime_model_ref="zcode-runtime/glm-4.7",
                ),
            ),
        ),
    )
    authorities = build_real_service_authorities(tmp_path)
    authorities = _replace(
        authorities, provider_snapshot=Snapshot(1, two_model_profile)
    )
    runtime_python = getattr(sys, "_base_executable", sys.executable)
    fake_script = tmp_path / "fake" / "fake_app_server.py"
    runner = assemble_zcode_execution(
        authorities=authorities,
        packet=_packet(tmp_path),
        model_id="glm-4.7",
        expected_generation=1,
        expected_base_url=BASE_URL,
        secret_reference="secret-ref:zcode-credential",
        workspace=str(tmp_path),
        executable=runtime_python,
        bundle_js=str(fake_script),
        deadline_seconds=30.0,
    )
    second = runner.run(timeout_seconds=90)
    assert second.exit_code == 0
    # NOT reused: a second real child spawned and a second durable row exists
    spawns = (receipts / "spawn.pid").read_text(encoding="utf-8").split()
    assert len(spawns) == 2, spawns
    con = sqlite3.connect(tmp_path / "control.sqlite")
    rows = con.execute("SELECT COUNT(*) FROM execution_records").fetchone()[0]
    refs = con.execute(
        "SELECT runtime_profile_ref FROM execution_records"
    ).fetchall()
    con.close()
    assert rows == 2, rows
    assert len({r[0] for r in refs}) == 2  # two distinct derived runtime identities

    # WO176: prove the ACTUAL child protocol payloads differ by the authorized
    # models; this is stronger than the pre-WO176 two-hash/two-spawn proof.
    creates = [
        json.loads(line)
        for line in (receipts / "create_receipts.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(creates) == 2, creates
    assert [item["model"] for item in creates] == [
        {"providerId": "zcode-glm", "modelId": "glm-5.3"},
        {"providerId": "zcode-glm", "modelId": "glm-4.7"},
    ]
    for item in creates:
        runtime_model = item["runtimeModel"]
        assert runtime_model["provider"]["baseURL"] == BASE_URL
        assert runtime_model["provider"]["apiKey"] == {
            "source": "env", "name": "ANTHROPIC_API_KEY"
        }
    assert SECRET not in (receipts / "create_receipts.jsonl").read_text(encoding="utf-8")


@NT_ONLY
def test_zra_comp_1_canonical_authorities_result_boundary_and_replay(tmp_path: Path) -> None:
    """WO178: compose canonical admission + lease through the real helper.

    This closes the gap between individually tested authority primitives and
    one zero-relay-shaped execution.  Provider admission and WorkerLease are
    acquired from their canonical SQLite stores; the accepted production
    assembly must consume those exact records, materialize the authorized
    provider/model on the child wire, collect a durable result, cross the
    AgentResultPacket/apply boundary without changes, and deduplicate replay
    without a second child spawn.
    """
    provider_store = SQLiteProviderConfigStore(tmp_path / "provider.sqlite")
    provider_store.save_endpoint(ENDPOINT)
    generation = provider_store.save_provider(_profile())
    now = datetime.now(timezone.utc)
    provider_store.save_observation(
        ProviderObservation(
            provider_id="zcode-glm",
            health=ProviderHealth.AVAILABLE,
            observed_at=now,
            provenance="wo178-zra-comp-1",
            configuration_generation=generation,
        )
    )
    snapshot = provider_store.load_provider_snapshot("zcode-glm")
    assert snapshot is not None
    assert snapshot.generation == generation
    assert snapshot.endpoint == ENDPOINT

    batch_id = "batch-zra-comp-1"
    execution_id = "exec-zra-comp-1"
    comp_branch = "test/wo-p1-178-zra-comp-1"
    comp_head = "a" * 40
    admission_outcome = provider_store.acquire_admission(
        provider_id="zcode-glm",
        execution_id=execution_id,
        batch_id=batch_id,
        expected_max_concurrency=1,
        now=now,
        ttl_seconds=600,
        expected_configuration_generation=generation,
    )
    assert admission_outcome.kind is ProviderAdmissionKind.ADMITTED
    admission = admission_outcome.admission
    assert admission is not None and admission.status == "ACTIVE"

    lease_store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    broker = WorkerLeaseBroker(
        store=lease_store,
        lease_id_factory=lambda: "lease-zra-comp-1",
        clock=lambda: datetime.now(timezone.utc),
    )
    lease_request = WorkerLeaseRequest(
        session_id="session-zra-comp-1",
        task_id=TASK_REF,
        project_id="zcode",
        ordered_worker_ids=("a-worker-01",),
        required_capabilities=("code",),
        required_runtime_id=None,
        worktree=str(tmp_path),
        branch=comp_branch,
        expected_head=comp_head,
        mutation_intent=LeaseMutationIntent.MUTATION,
        allowed_scope=("src/a_conductor", "src/a_conductor/*"),
        forbidden_scope=("secrets", "secrets/*"),
        mutable_scope=("src/a_conductor/zcode_runner.py",),
        lease_ttl_seconds=600,
    )
    candidate = WorkerLeaseCandidate(
        worker_id="a-worker-01",
        state="READY",
        reserved=False,
        active_task=False,
        capabilities=("code",),
        runtime_id=None,
        project_id="zcode",
        worktree=str(tmp_path),
        branch=comp_branch,
        head=comp_head,
        health_fresh=True,
        ownership_known=True,
        dirty_state="CLEAN",
        mutation_authorized=True,
    )
    lease_outcome = broker.acquire(lease_request, (candidate,))
    assert lease_outcome.kind is LeaseOutcomeKind.LEASED
    lease = lease_outcome.lease
    assert lease is not None

    base_authorities = build_real_service_authorities(tmp_path)
    authorities = replace(
        base_authorities,
        provider_snapshot=snapshot,
        lease_evidence=lease,
        admission_evidence=admission,
        dispatch_batch_id=batch_id,
        dispatch_execution_id=execution_id,
        branch=comp_branch,
        head=comp_head,
    )
    runtime_python = getattr(sys, "_base_executable", sys.executable)
    receipts = tmp_path / "receipts"
    fake_script = _write_fake_app_server(tmp_path / "fake", receipts, "ok")
    packet = _packet(tmp_path)
    runner = assemble_zcode_execution(
        authorities=authorities,
        packet=packet,
        model_id="glm-5.3",
        expected_generation=generation,
        expected_base_url=BASE_URL,
        secret_reference="secret-ref:zcode-credential",
        workspace=str(tmp_path),
        executable=runtime_python,
        bundle_js=str(fake_script),
        deadline_seconds=30.0,
    )

    first = runner.run(timeout_seconds=90)
    assert first.exit_code == 0, first.stderr
    assert first.stdout == RESPONSE_TEXT
    spawns_after_first = (receipts / "spawn.pid").read_text(encoding="utf-8").split()
    assert len(spawns_after_first) == 1

    create_doc = json.loads(
        (receipts / "create_receipts.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert create_doc["model"] == {"providerId": "zcode-glm", "modelId": "glm-5.3"}
    assert create_doc["runtimeModel"]["provider"]["baseURL"] == BASE_URL
    assert create_doc["runtimeModel"]["provider"]["apiKey"] == {
        "source": "env", "name": "ANTHROPIC_API_KEY"
    }
    assert SECRET not in json.dumps(create_doc, sort_keys=True)

    run_dir = _run_dir_files(tmp_path / "control.sqlite", tmp_path)
    assert (run_dir / "report.json").is_file()
    assert (run_dir / "result.json").is_file()
    packet_result = AgentResultPacket(
        task_id=TASK_REF,
        provider_id="zcode-glm",
        model_id="glm-5.3",
        status="NO_CHANGES",
        base_head=comp_head,
        evidence_refs=(
            str(run_dir / "report.json"),
            str(run_dir / "result.json"),
        ),
    )

    class _UnusedContinuity:
        def continuity_snapshot(self, request):
            del request
            raise AssertionError("NO_CHANGES must not require a mutation continuity gate")

    applier = AgentChangeApplier(
        filesystem=NativeFileSystem(NativeExecutionScope(tmp_path, mutation_allowed=True)),
        lease_store=lease_store,
        continuity_provider=_UnusedContinuity(),
        clock=lambda: datetime.now(timezone.utc),
    )
    apply_result = applier.apply(
        packet_result,
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        actual_head=comp_head,
    )
    assert apply_result.changed_paths == ()

    second = runner.run(timeout_seconds=90)
    assert second.exit_code == 0
    assert second.stdout == RESPONSE_TEXT
    assert (receipts / "spawn.pid").read_text(encoding="utf-8").split() == spawns_after_first

    released_admission = provider_store.release_admission(
        admission.admission_id,
        provider_id=admission.provider_id,
        execution_id=admission.execution_id,
        batch_id=admission.batch_id,
        now=datetime.now(timezone.utc),
    )
    assert released_admission.status == "RELEASED"
    lease_release = lease_store.release(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        released_at=datetime.now(timezone.utc),
    )
    assert lease_release.released is True
