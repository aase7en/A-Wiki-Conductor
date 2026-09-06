"""WO-P1-158 — production assembly fault matrix (deterministic, no live ZCode)."""

from __future__ import annotations

import hashlib
import json
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
        lease_broker=None,  # lease gate is a separate pre-condition check
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
        _assemble(tmp_path)
        # model mismatch: request a model the profile does not carry
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


def test_wrong_base_url_rejected_at_run(tmp_path):
    authorities = _authorities(tmp_path)
    runner = assemble_zcode_execution(
        authorities=authorities,
        packet=_packet(tmp_path),
        model_id="glm-5.3",
        expected_generation=1,
        authorized_base_url="http://evil:9",
        secret_reference="secret-ref:zcode-credential",
        workspace=str(tmp_path), executable=EXEC, bundle_js=BUNDLE,
        endpoint_base_url=BASE_URL,  # endpoint authority reports the truth
    )
    with pytest.raises(Exception):
        runner.run(operation_ref=None)
    assert authorities.transport_factory.calls == []  # zero spawn


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

def test_secret_resolver_failure_zero_spawn(tmp_path):
    class Broken:
        def resolve(self, ref):
            raise RuntimeError("down")
    from a_conductor.zcode_production_assembly import ZCodeExecutionAuthorities
    base = _authorities(tmp_path)
    authorities = replace(base, secret_resolver=Broken())
    runner = _assemble(tmp_path, authorities=authorities)
    with pytest.raises(Exception):
        runner.run(operation_ref=None)
    assert authorities.transport_factory.calls == []


def test_full_chain_executes_and_no_credential_or_prompt_leak(tmp_path):
    secrets = Secrets(value="zz-leak-probe-42")
    base = _authorities(tmp_path)
    authorities = replace(base, secret_resolver=secrets)
    runner = _assemble(tmp_path, authorities=authorities)
    result = runner.run(operation_ref=None)
    assert result.exit_code == 0 and "ZRA1-OK" in result.stdout
    assert secrets.requests == ["secret-ref:zcode-credential"]
    # credential reached the runtime channel but nothing durable
    assert authorities.transport_factory.last.child_env["ANTHROPIC_API_KEY"] == "zz-leak-probe-42"
    for rel in authorities.filesystem.root.rglob("*"):
        if rel.is_file():
            assert b"zz-leak-probe-42" not in rel.read_bytes(), rel
    # prompt never in argv
    call = authorities.transport_factory.calls[0]
    assert all("ZRA1-OK" not in a for a in call["argv"])


# ---- dedup / attach / UNKNOWN -------------------------------------------

def test_duplicate_fingerprint_zero_second_spawn(tmp_path):
    authorities = _authorities(tmp_path)
    runner = _assemble(tmp_path, authorities=authorities)
    runner.run(operation_ref=None)
    first = len(authorities.transport_factory.calls)
    runner.run(operation_ref=None)
    assert len(authorities.transport_factory.calls) == first  # dedup reuses


def test_unknown_execution_maps_recovery_not_success(tmp_path):
    failing = Factory([
        json.dumps({"id": 1, "result": {"session": {"sessionId": "s"}}}),
        json.dumps({"id": 100, "method": "session/requestRuntimePreferences"}),
        json.dumps({"id": 2, "result": {"ok": True}}),
        json.dumps({"method": "session/event", "params": {"type": "turn.failed"}}),
    ])
    base = _authorities(tmp_path)
    authorities = replace(base, transport_factory=failing)
    runner = _assemble(tmp_path, authorities=authorities)
    result = runner.run(operation_ref=None)
    assert result.exit_code is None and "TURN_FAILED" in result.stderr
