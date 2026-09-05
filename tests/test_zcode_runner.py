"""WO-P1-158 Phase D — canonical SupervisedZCodeRunner proofs (no live ZCode).

Proves the GPT2 repair contract: the runner routes through
SupervisedRunCoordinator.run (durable record + dedup + collect/CAS), the
result.json is the canonical six-key SupervisedChildResult, task authority is
a verified TaskPacketFile (TOCTOU-closed), selection must be AUTHORIZED (not
merely stable), the credential flows only through the accepted secret-ref
authority into process memory, child identity fails closed when real process
metadata is missing, and UNKNOWN/EXIT_PENDING never fabricates result.json.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass

import pytest

from a_conductor.claude_code_harness import TaskPacketFile
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.provider_configuration import (
    HarnessRuntimeBinding,
    HarnessStrategy,
)
from a_conductor.supervised_child import SupervisedChildResult
from a_conductor.supervised_run_coordinator import SupervisedRunIdentity
from a_conductor.zcode_runner import (
    ZCODE_BACKEND_ID,
    SupervisedZCodeRunner,
    ZCodeBackendAdapter,
    ZCodeRunError,
    ZCodeTaskPacketIdentity,
)


BINDING = HarnessRuntimeBinding(
    harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
    runtime_provider_ref="zcode-runtime/glm-main",
    runtime_model_ref="zcode-runtime/glm-5.3",
)
BASE_URL = "http://127.0.0.1:1"
EXEC = r"C:\ZCode\ZCode.exe"
BUNDLE = r"C:\ZCode\resources\glm\zcode.cjs"
ARGV = (EXEC, BUNDLE, "app-server", "--stdio", "--surface", "desktop")


class Selection:
    def __init__(self, *, binding=None, base_url=None):
        self.binding = binding or BINDING
        self.base_url = base_url or BASE_URL

    def resolved_selection(self):
        return {
            "runtime_binding": self.binding,
            "runtime_base_url": self.base_url,
            "runtime_source_enabled": True,
        }


class Secrets:
    def __init__(self, value="opaque-credential-value"):
        self.value = value
        self.requests: list[str] = []

    def resolve(self, ref):
        self.requests.append(ref)
        return self.value


class Transport:
    def __init__(self, script, *, exit_code=0, pid=4242, created=1788490277831, parent=100):
        self._script = deque(script)
        self.sent: list[str] = []
        self.child_pid = pid
        self.child_created_epoch_ms = created
        self.parent_pid = parent
        self.exit_code = exit_code
        self.killed = False
        self.env_seen: dict | None = None

    def send_line(self, text):
        self.sent.append(text)

    def read_line(self, timeout_seconds):
        if not self._script:
            return None
        item = self._script.popleft()
        return item

    def alive(self):
        return True

    def close_stdin_and_wait(self, *, exit_wait_seconds):
        return self.exit_code


class TransportFactory:
    def __init__(self, script, **transport_kwargs):
        self.script = script
        self.kwargs = transport_kwargs
        self.calls: list[dict] = []
        self.last: Transport | None = None

    def open_transport(self, *, argv, environment, execution_id, run_dir_ref):
        self.calls.append(
            {"argv": argv, "environment": dict(environment),
             "execution_id": execution_id, "run_dir_ref": run_dir_ref}
        )
        self.last = Transport(self.script, **self.kwargs)
        return self.last


class FS:
    """Disk-backed run-dir-confined artifact IO under the repo root."""

    def __init__(self, root):
        from pathlib import Path
        self.root = Path(root)
        self.order: list[str] = []
        self._n = 0

    def _tick(self, name):
        self._n += 1
        self.order.append(f"{self._n:03d}:{name}")

    def _path(self, p):
        from pathlib import Path
        target = self.root / p
        if self.root.resolve() not in target.resolve().parents and target.resolve() != self.root.resolve():
            raise ValueError("artifact path escapes run dir")
        return target

    def write_atomic(self, p, text):
        self._tick(p)
        target = self._path(p)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(target)

    def read_text(self, p):
        return self._path(p).read_text(encoding="utf-8")

    def append_text(self, p, text):
        target = self._path(p)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(text)

    def write_bytes_file(self, p, data):
        self._tick(p)
        target = self._path(p)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def exists(self, p):
        return self._path(p).exists()

    def read_bytes(self, p):
        return self._path(p).read_bytes()

    def all_paths(self):
        return sorted(str(rel) for rel in self.root.rglob("*") if rel.is_file())


def _script(text="ZRA1-OK"):
    return [
        json.dumps({"id": 1, "result": {"session": {"sessionId": "s-1"}}}),
        json.dumps({"id": 100, "method": "session/requestRuntimePreferences"}),
        json.dumps({"id": 2, "result": {"ok": True}}),
        json.dumps({"method": "session/event",
                    "params": {"type": "model.streaming",
                               "payload": {"kind": "text_delta", "delta": text}}}),
        json.dumps({"method": "session/event", "params": {"type": "turn.completed"}}),
    ]


def _packet_file(tmp_path, content="Return exactly ZRA1-OK."):
    path = tmp_path / "task-packet.md"
    path.write_text(content, encoding="utf-8")
    return TaskPacketFile(
        task_contract_ref="WO-P1-158-ZRA1",
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _runner(tmp_path, *, selection=None, secrets=None, factory=None, packet=None):
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    packet = packet or _packet_file(tmp_path)
    identity_packet = ZCodeTaskPacketIdentity.from_task_packet_file(packet)
    fs = FS(tmp_path)
    factory = factory or TransportFactory(_script())
    adapter = ZCodeBackendAdapter(
        transport_factory=factory,
        filesystem=fs,
        execution_store=store,
        selection_source=selection or Selection(),
        expected_binding=BINDING,
        expected_base_url=BASE_URL,
        secret_resolver=secrets or Secrets(),
        secret_reference="secret-ref:zcode-credential",
        packet=identity_packet,
        workspace=str(tmp_path),
        executable=EXEC,
        bundle_js=BUNDLE,
    )
    runner = SupervisedZCodeRunner(
        execution_store=store,
        identity=SupervisedRunIdentity(
            job_id="job-1", work_order_ref="WO-P1-158", project_id="p1",
            worker_id="w1", backend_id=ZCODE_BACKEND_ID, branch="main",
            head_before="h" * 40, runtime_profile_ref="rt:zcode",
            repo_root=str(tmp_path),
        ),
        adapter=adapter,
        executable=EXEC,
        bundle_js=BUNDLE,
        poll_interval_seconds=0.01,
    )
    return runner, store, fs, factory, packet


# ---------------- canonical lifecycle ----------------

def test_runner_routes_through_coordinator_with_durable_record(tmp_path):
    runner, store, fs, factory, _ = _runner(tmp_path)
    result = runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    assert result.exit_code == 0 and result.timed_out is False
    # durable record exists through the canonical store
    from a_conductor.supervised_run_coordinator import SupervisedRunCoordinator
    from a_conductor.zcode_runner import zcode_backend_policy
    lookup = SupervisedRunCoordinator(
        execution_store=store,
        supervised=_NoopSupervised(),
        identity=SupervisedRunIdentity(
            job_id="job-1", work_order_ref="WO-P1-158", project_id="p1",
            worker_id="w1", backend_id=ZCODE_BACKEND_ID, branch="main",
            head_before="h" * 40, runtime_profile_ref="rt:zcode",
            repo_root=str(tmp_path),
        ),
        backend_policy=zcode_backend_policy(operation_ref="zcode:WO-P1-158-ZRA1"),
    )
    records = store.find_by_fingerprint(lookup.fingerprint_for_argv(runner.argv()))
    assert len(records) == 1
    record = records[0]
    assert record.backend_id == ZCODE_BACKEND_ID
    assert record.agent_ref == "agent:zcode-app-server"
    assert record.operation_ref == "zcode:WO-P1-158-ZRA1"
    assert record.report_ref.endswith("/report.json")
    run_rel = record.run_dir_ref
    # identity → stdout → stderr → report → result ordering
    order = [e.split(":", 1)[1] for e in fs.order]
    assert order.index(f"{run_rel}/child.identity.json") < order.index(f"{run_rel}/stdout.log")
    assert order.index(f"{run_rel}/stdout.log") < order.index(f"{run_rel}/report.json")
    assert order.index(f"{run_rel}/report.json") < order.index(f"{run_rel}/result.json")
    assert fs.exists(f"{run_rel}/result.json")
    # canonical six-key result
    result_doc = json.loads(fs.read_text(f"{run_rel}/result.json"))
    assert set(result_doc) == {
        "schema_version", "execution_id", "child_pid",
        "exit_code", "started_at", "finished_at",
    }
    assert result_doc["child_pid"] == 4242
    assert result_doc["exit_code"] == 0
    parsed = SupervisedChildResult(**result_doc)  # canonical contract accepts it
    assert parsed.execution_id == record.execution_id


class _NoopSupervised:
    def launch(self, plan): return plan
    def inspect(self, eid): raise RuntimeError
    def collect(self, eid, *, expected_version): raise RuntimeError


def test_duplicate_run_reuses_execution_no_second_launch(tmp_path):
    runner, store, fs, factory, _ = _runner(tmp_path)
    runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    first_calls = len(factory.calls)
    runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    assert len(factory.calls) == first_calls  # dedup: no second child


# ---------------- task authority ----------------

def test_task_packet_hash_mismatch_rejects_before_any_spawn(tmp_path):
    packet = _packet_file(tmp_path)
    tampered = TaskPacketFile(
        task_contract_ref=packet.task_contract_ref,
        path=packet.path,
        sha256="f" * 64,  # wrong hash
    )
    with pytest.raises(ZCodeRunError) as exc:
        _runner(tmp_path, packet=tampered)
    assert exc.value.code == "ZCODE_TASK_PACKET_HASH_MISMATCH"


def test_prompt_never_enters_argv_or_environment(tmp_path):
    runner, store, fs, factory, _ = _runner(tmp_path)
    runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    call = factory.calls[0]
    assert call["argv"] == ARGV
    assert all("ZRA1-OK" not in a for a in call["argv"])
    assert call["environment"] == {"ELECTRON_RUN_AS_NODE": "1"}


# ---------------- selection authorization ----------------

def test_selection_must_be_authorized_not_merely_stable(tmp_path):
    wrong = Selection(
        binding=HarnessRuntimeBinding(
            harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
            runtime_provider_ref="zcode-runtime/wrong-provider",
            runtime_model_ref="zcode-runtime/glm-5.3",
        )
    )
    runner, *_ = _runner(tmp_path, selection=wrong)
    with pytest.raises(ZCodeRunError) as exc:
        runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    assert exc.value.code == "ZCODE_SELECTION_UNAUTHORIZED"


def test_selection_base_url_mismatch_rejects(tmp_path):
    runner, *_ = _runner(tmp_path, selection=Selection(base_url="http://evil:9"))
    with pytest.raises(ZCodeRunError) as exc:
        runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    assert exc.value.code == "ZCODE_SELECTION_UNAUTHORIZED"


# ---------------- credential boundary ----------------

def test_credential_resolved_via_secret_ref_only_into_memory(tmp_path):
    secrets = Secrets()
    runner, *_ = _runner(tmp_path, secrets=secrets)
    runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    assert secrets.requests == ["secret-ref:zcode-credential"]
    # nothing durable carries the value
    secrets_value = secrets.value
    for text in list(runner.__dict__.values()):  # runner holds no secret text
        assert not isinstance(text, str) or secrets_value not in text


def test_secret_resolution_failure_fails_closed(tmp_path):
    class Broken:
        def resolve(self, ref):
            raise RuntimeError("vault down")
    runner, *_ = _runner(tmp_path, secrets=Broken())
    with pytest.raises(ZCodeRunError) as exc:
        runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    assert exc.value.code == "ZCODE_SECRET_RESOLUTION_FAILED"


# ---------------- child identity ----------------

def test_missing_child_metadata_fails_closed_before_prompt(tmp_path):
    factory = TransportFactory(_script(), pid=None)
    runner, store, fs, *_ = _runner(tmp_path, factory=factory)
    with pytest.raises(ZCodeRunError) as exc:
        runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    assert exc.value.code == "ZCODE_CHILD_IDENTITY_UNAVAILABLE"
    # zero prompt dispatch: no protocol send happened
    assert factory.last is None or factory.last.sent == []


def test_identity_document_is_bounded_and_prompt_free(tmp_path):
    runner, store, fs, *_ = _runner(tmp_path)
    runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    run_rel = next(p for p in fs.all_paths() if p.endswith("child.identity.json")).replace("\\", "/").rsplit("/", 1)[0]
    doc = json.loads(fs.read_text(f"{run_rel}/child.identity.json"))
    assert doc["schema"] == "zcode-child-identity/1"
    assert doc["child_pid"] == 4242
    assert "prompt" not in doc and "secret" not in doc and "credential" not in doc


# ---------------- UNKNOWN never fabricates result ----------------

def test_exit_pending_writes_report_only(tmp_path):
    factory = TransportFactory(_script(), exit_code=None)
    runner, store, fs, *_ = _runner(tmp_path, factory=factory)
    result = runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    run_rel = next(p for p in fs.all_paths() if p.endswith("report.json")).replace("\\", "/").rsplit("/", 1)[0]
    assert not fs.exists(f"{run_rel}/result.json")
    report = json.loads(fs.read_text(f"{run_rel}/report.json"))
    assert report.get("exit_state") == "EXIT_PENDING" or report.get("state") == "UNKNOWN"


def test_turn_failure_is_typed_unknown(tmp_path):
    failing = TransportFactory([
        json.dumps({"id": 1, "result": {"session": {"sessionId": "s-1"}}}),
        json.dumps({"id": 100, "method": "session/requestRuntimePreferences"}),
        json.dumps({"id": 2, "result": {"ok": True}}),
        json.dumps({"method": "session/event", "params": {"type": "turn.failed"}}),
    ])
    runner, store, fs, *_ = _runner(tmp_path, factory=failing)
    result = runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    run_rel = next(p for p in fs.all_paths() if p.endswith("report.json")).replace("\\", "/").rsplit("/", 1)[0]
    assert not fs.exists(f"{run_rel}/result.json")
    stderr_text = fs.read_text(f"{run_rel}/stderr.log") if fs.exists(f"{run_rel}/stderr.log") else ""
    assert "TURN_FAILED" in stderr_text and "TURN_FAILED" in result.stderr


# ---------------- no kill surface ----------------

def test_runner_module_has_no_kill_ladder():
    import inspect
    from a_conductor import zcode_runner as module
    source = inspect.getsource(module)
    for forbidden in ("taskkill", "TerminateProcess", ".terminate()", ".kill()", "Stop-Process"):
        assert forbidden not in source, forbidden


def test_transport_shutdown_is_eof_only(tmp_path):
    runner, store, fs, factory, _ = _runner(tmp_path)
    runner.run(operation_ref="zcode:WO-P1-158-ZRA1")
    assert factory.last.killed is False
    assert factory.last.exit_code == 0  # natural exit recorded
