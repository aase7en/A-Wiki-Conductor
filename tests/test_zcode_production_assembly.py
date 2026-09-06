"""WO-P1-158 — production assembly fault matrix (deterministic, no live ZCode)."""

from __future__ import annotations

import hashlib
import json
import os
from collections import deque
from dataclasses import dataclass, replace

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
from a_conductor.zcode_production_assembly import (
    ZCodeAssemblyError,
    ZCodeExecutionAuthorities,
    assemble_zcode_execution,
    verify_execution_context,
)


BINDING = HarnessRuntimeBinding(
    harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
    runtime_provider_ref="zcode-runtime/glm-main",
    runtime_model_ref="zcode-runtime/glm-5.3",
)
BASE_URL = "http://127.0.0.1:1"
EXEC = r"C:\ZCode\ZCode.exe"
BUNDLE = r"C:\ZCode\resources\glm\zcode.cjs"


@dataclass
class Snapshot:
    generation: int
    profile: ProviderConfiguration


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


class Transport:
    def __init__(self, script):
        self._script = deque(script)
        self.sent = []
        self.child_pid = 4242
        self.child_created_epoch_ms = 1788490277831
        self.parent_pid = 100
        self.child_env = None

    def send_line(self, t):
        self.sent.append(t)

    def read_line(self, timeout):
        return self._script.popleft() if self._script else None

    def alive(self):
        return True

    def close_stdin_and_wait(self, *, exit_wait_seconds):
        return 0


class Factory:
    def __init__(self, script):
        self.script = script
        self.calls = []
        self.last = None

    def open_transport(self, *, argv, environment, credential, execution_id, run_dir_ref):
        self.calls.append(dict(argv=argv, environment=environment,
                               credential=credential, execution_id=execution_id))
        self.last = Transport(self.script)
        key, value = credential.environment_entry
        self.last.child_env = {**environment, key: value}
        return self.last


class Secrets:
    def __init__(self, value="opaque-secret"):
        self.value = value
        self.requests = []

    def resolve(self, ref):
        self.requests.append(ref)
        return self.value


class FS:
    def __init__(self, root):
        from pathlib import Path
        self.root = Path(root)

    def _p(self, rel):
        return self.root / rel

    def write_atomic(self, rel, text):
        p = self._p(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def read_text(self, rel):
        return self._p(rel).read_text(encoding="utf-8")

    def append_text(self, rel, text):
        p = self._p(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.open("a", encoding="utf-8").write(text)

    def write_bytes_file(self, rel, data):
        p = self._p(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)


def _script():
    return [
        json.dumps({"id": 1, "result": {"session": {"sessionId": "s"}}}),
        json.dumps({"id": 100, "method": "session/requestRuntimePreferences"}),
        json.dumps({"id": 2, "result": {"ok": True}}),
        json.dumps({"method": "session/event",
                    "params": {"type": "model.streaming",
                               "payload": {"kind": "text_delta", "delta": "ZRA1-OK"}}}),
        json.dumps({"method": "session/event", "params": {"type": "turn.completed"}}),
    ]


def _packet(tmp_path):
    path = tmp_path / "task-packet.md"
    path.write_text("Return exactly ZRA1-OK.", encoding="utf-8")
    return TaskPacketFile(task_contract_ref="WO-P1-158-ZRA1", path=str(path),
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def _authorities(tmp_path, *, generation=1):
    return ZCodeExecutionAuthorities(
        provider_snapshot=Snapshot(generation, _profile()),
        secret_resolver=Secrets(),
        transport_factory=Factory(_script()),
        filesystem=FS(tmp_path),
        execution_store=SQLiteExecutionStore(tmp_path / "control.sqlite"),

        worker_id="a-worker-01",
        repo_root=str(tmp_path),
        branch="feat/wo-p1-158-zcode-zero-relay",
        head="h" * 40,
        dirty=False,
    )


def _assemble(tmp_path, *, generation=1, expected_generation=1, packet=None, authorities=None):
    return assemble_zcode_execution(
        authorities=authorities or _authorities(tmp_path, generation=generation),
        packet=packet or _packet(tmp_path),
        model_id="glm-5.3",
        expected_generation=expected_generation,
        authorized_base_url=BASE_URL,
        secret_reference="secret-ref:zcode-credential",
        workspace=str(tmp_path),
        executable=EXEC,
        bundle_js=BUNDLE,
    )


# ---- git/worktree gate -------------------------------------------------

def test_head_drift_rejected():
    with pytest.raises(ZCodeAssemblyError) as e:
        verify_execution_context(branch="b", head="a" * 40, dirty=False,
                                 expected_branch="b", expected_head="b" * 40)
    assert e.value.code == "ZCODE_HEAD_DRIFT"


def test_branch_mismatch_rejected():
    with pytest.raises(ZCodeAssemblyError) as e:
        verify_execution_context(branch="x", head="h" * 40, dirty=False,
                                 expected_branch="b", expected_head="h" * 40)
    assert e.value.code == "ZCODE_BRANCH_MISMATCH"


def test_dirty_worktree_rejected():
    with pytest.raises(ZCodeAssemblyError) as e:
        verify_execution_context(branch="b", head="h" * 40, dirty=True,
                                 expected_branch="b", expected_head="h" * 40)
    assert e.value.code == "ZCODE_WORKTREE_DIRTY"


# ---- provider gates ------------------------------------------------------

def test_provider_generation_drift_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, generation=1, expected_generation=2)
    assert e.value.code == "ZCODE_PROVIDER_GENERATION_DRIFT"


def test_wrong_provider_model_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        assemble_zcode_execution(
            authorities=_authorities(tmp_path),
            packet=_packet(tmp_path),
            model_id="not-a-model",
            expected_generation=1,
            authorized_base_url=BASE_URL,
            secret_reference="secret-ref:zcode-credential",
            workspace=str(tmp_path), executable=EXEC, bundle_js=BUNDLE,
        )
    assert e.value.code == "ZCODE_RUNTIME_BINDING_MISSING"


def test_missing_service_authorities_rejected(tmp_path):
    """The production lifecycle REQUIRES the real supervised-service
    authorities; there is no alternate in-process transport fallback."""
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path)
    assert e.value.code == "ZCODE_SERVICE_AUTHORITY_MISSING"


NT_ONLY = pytest.mark.skipif(os.name != "nt", reason="Windows real-helper integration")


def _service_assemble(tmp_path, *, mode: str = "ok", authorities=None,
                      base_url: str = BASE_URL, endpoint_base_url: str | None = None):
    """Assemble through the REAL supervised-service authorities + the
    deterministic fake app-server (same primitive as the E2E suite)."""
    import sys as _sys

    from tests.test_zcode_real_helper_e2e import (
        _packet as _e2e_packet,
        _write_fake_app_server,
        build_real_service_authorities,
    )

    runtime_python = getattr(_sys, "_base_executable", _sys.executable)
    fake_script = _write_fake_app_server(tmp_path / "fake", tmp_path / "receipts", mode)
    resolved = authorities if authorities is not None else build_real_service_authorities(tmp_path)
    return assemble_zcode_execution(
        authorities=resolved,
        packet=_e2e_packet(tmp_path),
        model_id="glm-5.3",
        expected_generation=1,
        authorized_base_url=base_url,
        secret_reference="secret-ref:zcode-credential",
        workspace=str(tmp_path),
        executable=runtime_python,
        bundle_js=str(fake_script),
        endpoint_base_url=endpoint_base_url,
        deadline_seconds=20.0,
    )


@NT_ONLY
def test_wrong_base_url_rejected_at_run(tmp_path):
    from a_conductor.zcode_runner import ZCodeRunError

    runner = _service_assemble(
        tmp_path, base_url="http://evil:9", endpoint_base_url=BASE_URL,
    )
    # PREP-time authorization fails closed with a typed error BEFORE any
    # durable record or child exists
    with pytest.raises(ZCodeRunError) as e:
        runner.run(operation_ref=None)
    assert e.value.code == "ZCODE_SELECTION_UNAUTHORIZED"
    assert not (tmp_path / "receipts" / "spawn.pid").exists()  # zero spawn


# ---- task authority ------------------------------------------------------

def test_task_packet_tamper_rejected_before_spawn(tmp_path):
    packet = _packet(tmp_path)
    (tmp_path / "task-packet.md").write_text("tampered", encoding="utf-8")
    authorities = _authorities(tmp_path)
    with pytest.raises(Exception):
        assemble_zcode_execution(
            authorities=authorities, packet=packet, model_id="glm-5.3",
            expected_generation=1, authorized_base_url=BASE_URL,
            secret_reference="secret-ref:zcode-credential",
            workspace=str(tmp_path), executable=EXEC, bundle_js=BUNDLE,
        )
    assert authorities.transport_factory.calls == []


# ---- credential + selection ----------------------------------------------

@NT_ONLY
def test_secret_resolver_failure_zero_spawn(tmp_path):
    from tests.test_zcode_real_helper_e2e import Secrets as _E2ESecrets, build_real_service_authorities

    class Broken:
        def resolve(self, ref):
            raise RuntimeError("down")

    authorities = replace(build_real_service_authorities(tmp_path), secret_resolver=Broken())
    runner = _service_assemble(tmp_path, authorities=authorities)
    result = runner.run(operation_ref=None)  # normalized failure, no raise
    assert result.exit_code is None
    assert "ZCODE_SECRET_RESOLUTION_FAILED" in result.stderr
    assert not (tmp_path / "receipts" / "spawn.pid").exists()  # zero spawn


@NT_ONLY
def test_full_chain_executes_and_no_credential_or_prompt_leak(tmp_path):
    import sqlite3

    from tests.test_zcode_real_helper_e2e import (
        PROMPT_MARKER, RESPONSE_TEXT, Secrets as _E2ESecrets, build_real_service_authorities,
    )

    probe = "zz-leak-probe-42"
    authorities = replace(build_real_service_authorities(tmp_path), secret_resolver=_E2ESecrets(value=probe))
    runner = _service_assemble(tmp_path, authorities=authorities)
    result = runner.run(operation_ref=None)
    assert result.exit_code == 0 and RESPONSE_TEXT in result.stdout
    assert authorities.secret_resolver.requests == ["secret-ref:zcode-credential"]
    # credential reached the REAL child environment (and only there)
    child_env = json.loads((tmp_path / "receipts" / "child_env.json").read_text(encoding="utf-8"))
    assert child_env["env"]["ANTHROPIC_API_KEY"] == probe
    # nothing durable under the repo carries the credential: every file
    # outside the receipt/fake probes (which live outside the run artifacts)
    # must be byte-clean of the secret
    for rel in tmp_path.rglob("*"):
        if rel.is_file() and "receipts" not in rel.parts:
            assert probe.encode() not in rel.read_bytes(), rel
    # prompt never rides any argv surface (helper argv is metadata-only)
    con = sqlite3.connect(tmp_path / "control.sqlite")
    summary = con.execute(
        "SELECT command_summary FROM execution_records LIMIT 1"
    ).fetchone()[0]
    con.close()
    assert PROMPT_MARKER not in summary
    assert PROMPT_MARKER not in json.dumps(child_env["argv"])


# ---- dedup / attach / UNKNOWN -------------------------------------------

@NT_ONLY
def test_duplicate_fingerprint_zero_second_spawn(tmp_path):
    runner = _service_assemble(tmp_path)
    first = runner.run(operation_ref=None)
    assert first.exit_code == 0
    second = runner.run(operation_ref=None)
    assert second.exit_code == 0
    # dedup reuses the completed execution: still exactly one child spawn
    spawns = (tmp_path / "receipts" / "spawn.pid").read_text(encoding="utf-8").split()
    assert len(spawns) == 1, spawns


@NT_ONLY
def test_unknown_execution_maps_recovery_not_success(tmp_path):
    runner = _service_assemble(tmp_path, mode="fail")
    result = runner.run(operation_ref=None)
    assert result.exit_code is None
    assert result.stderr.startswith("SUPERVISOR_RECOVERY_REQUIRED")
    run_dir = next((tmp_path / "runs").glob("exec-*"))
    stderr_log = (run_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
    assert "ZCODE_HELPER_EXIT code=TURN_FAILED" in stderr_log, stderr_log
    assert not (run_dir / "result.json").exists()  # never fabricated


# ---------------- Q29: authority-consume gates ----------------

def test_q29_git_gate_executed_in_assembly(tmp_path):
    from dataclasses import replace
    from a_conductor.zcode_production_assembly import ZCodeAssemblyError
    base = _authorities(tmp_path)
    dirty = replace(base, dirty=True)
    with pytest.raises(ZCodeAssemblyError) as e:
        assemble_zcode_execution(
            authorities=dirty, packet=_packet(tmp_path), model_id="glm-5.3",
            expected_generation=1, authorized_base_url=BASE_URL,
            secret_reference="secret-ref:zcode-credential",
            workspace=str(tmp_path), executable=EXEC, bundle_js=BUNDLE,
        )
    assert e.value.code == "ZCODE_WORKTREE_DIRTY"


def test_q29_head_drift_rejected_in_assembly(tmp_path):
    from dataclasses import replace
    from a_conductor.zcode_production_assembly import ZCodeAssemblyError
    base = _authorities(tmp_path)
    with pytest.raises(ZCodeAssemblyError) as e:
        assemble_zcode_execution(
            authorities=base, packet=_packet(tmp_path), model_id="glm-5.3",
            expected_generation=1, authorized_base_url=BASE_URL,
            secret_reference="secret-ref:zcode-credential",
            workspace=str(tmp_path), executable=EXEC, bundle_js=BUNDLE,
            expected_head="b" * 40,
        )
    assert e.value.code == "ZCODE_HEAD_DRIFT"


def test_q29_missing_lease_evidence_rejects(tmp_path):
    from dataclasses import replace
    from a_conductor.zcode_production_assembly import ZCodeAssemblyError
    base = _authorities(tmp_path)
    no_lease = replace(base, lease_evidence=False)
    with pytest.raises(ZCodeAssemblyError) as e:
        assemble_zcode_execution(
            authorities=no_lease, packet=_packet(tmp_path), model_id="glm-5.3",
            expected_generation=1, authorized_base_url=BASE_URL,
            secret_reference="secret-ref:zcode-credential",
            workspace=str(tmp_path), executable=EXEC, bundle_js=BUNDLE,
        )
    assert e.value.code == "ZCODE_LEASE_ADMISSION_MISSING"


def test_q29_missing_provider_admission_rejects(tmp_path):
    from dataclasses import replace
    from a_conductor.zcode_production_assembly import ZCodeAssemblyError
    base = _authorities(tmp_path)
    no_adm = replace(base, admission_evidence=False)
    with pytest.raises(ZCodeAssemblyError) as e:
        assemble_zcode_execution(
            authorities=no_adm, packet=_packet(tmp_path), model_id="glm-5.3",
            expected_generation=1, authorized_base_url=BASE_URL,
            secret_reference="secret-ref:zcode-credential",
            workspace=str(tmp_path), executable=EXEC, bundle_js=BUNDLE,
        )
    assert e.value.code == "ZCODE_PROVIDER_ADMISSION_MISSING"


@NT_ONLY
def test_q29_positive_evidence_accepts_and_confines_packet(tmp_path):
    from tests.test_zcode_real_helper_e2e import build_real_service_authorities

    base = build_real_service_authorities(tmp_path)
    ok = replace(base, lease_evidence=True, admission_evidence=True)
    runner = assemble_zcode_execution(
        authorities=ok,
        packet=_packet(tmp_path),
        model_id="glm-5.3",
        expected_generation=1,
        authorized_base_url=BASE_URL,
        secret_reference="secret-ref:zcode-credential",
        workspace=str(tmp_path), executable=EXEC, bundle_js=BUNDLE,
    )
    assert runner._task_packet.path  # confined path retained for TOCTOU


def test_q29_no_second_scheduler_or_store_created(tmp_path):
    import inspect
    from a_conductor import zcode_production_assembly as module
    source = inspect.getsource(module)
    for banned in ("WorkerLeaseBroker(", "acquire(", "SQLiteExecutionStore(", "threading"):
        assert banned not in source, banned
