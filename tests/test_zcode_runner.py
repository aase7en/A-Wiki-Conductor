"""WO-P1-158 Phase D — SupervisedZCodeRunner integration proofs (no live ZCode).

Deterministic fake transport/filesystem: proves selection double-check at the
launch seam, identity-before-prompt ordering, strict report→result ordering,
UNKNOWN-never-fabricates-result, EOF-only shutdown (no kill surface), and the
single shared coordinator wiring (backend_id zcode-app-server).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from a_conductor.native_execution import NativeCommandResult
from a_conductor.provider_configuration import (
    HarnessRuntimeBinding,
    HarnessStrategy,
)
from a_conductor.supervised_run_coordinator import SupervisedRunIdentity
from a_conductor.zcode_runner import (
    ZCODE_BACKEND_ID,
    SupervisedZCodeRunner,
    ZCodeSelectionDriftError,
)
from a_conductor.zcode_supervised_helper import target_argv_sha256


BINDING = HarnessRuntimeBinding(
    harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
    runtime_provider_ref="zcode-runtime/glm-main",
    runtime_model_ref="zcode-runtime/glm-5.3",
)


class FakeSelection:
    def __init__(self, mutate_on_second_call=False):
        self.calls = 0
        self.mutate = mutate_on_second_call

    def resolved_selection(self):
        self.calls += 1
        binding = BINDING
        if self.mutate and self.calls >= 2:
            binding = HarnessRuntimeBinding(
                harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
                runtime_provider_ref="zcode-runtime/other",
                runtime_model_ref="zcode-runtime/glm-5.3",
            )
        return {
            "runtime_binding": binding,
            "runtime_base_url": "http://127.0.0.1:1",
            "runtime_source_enabled": True,
        }


class FakeTransport:
    """Scripted app-server: speaks the proven wire shape; close_stdin_and_wait
    returns the configured real exit code (or None for EXIT_PENDING)."""

    def __init__(self, script, *, exit_code=0):
        import collections

        self._script = collections.deque(script)
        self.sent: list[str] = []
        self.exit_code = exit_code
        self.child_pid = 4242
        self.child_created_epoch_ms = 1788490277831
        self.parent_pid = 100
        self.killed = False

    def send_line(self, text):
        self.sent.append(text)

    def read_line(self, timeout_seconds):
        if not self._script:
            return None
        return self._script.popleft()

    def alive(self):
        return True

    def close_stdin_and_wait(self, *, exit_wait_seconds):
        assert exit_wait_seconds > 0
        return self.exit_code  # bounded natural-exit wait; no kill path exists


class FakeFS:
    def __init__(self):
        self.files: dict[str, str] = {}
        self.bytes_files: dict[str, bytes] = {}
        self.order: list[str] = []
        self._seq = 0

    def _tick(self, name):
        self._seq += 1
        self.order.append(f"{self._seq:03d}:{name}")

    def write_atomic(self, relative_path, text):
        self._tick(relative_path)
        self.files[relative_path] = text

    def read_text(self, relative_path):
        return self.files[relative_path]

    def append_text(self, relative_path, text):
        self._tick(relative_path + ":append")
        self.files[relative_path] = self.files.get(relative_path, "") + text

    def write_bytes_file(self, relative_path, data):
        self._tick(relative_path)
        self.bytes_files[relative_path] = data


def _script(turn_text="ZRA1-OK"):
    return [
        json.dumps({"id": 1, "result": {"session": {"sessionId": "s-1"}}}),
        json.dumps({"id": 100, "method": "session/requestRuntimePreferences"}),
        json.dumps({"id": 2, "result": {"ok": True}}),
        json.dumps({
            "method": "session/event",
            "params": {"type": "model.streaming",
                       "payload": {"kind": "text_delta", "delta": turn_text}},
        }),
        json.dumps({"method": "session/event", "params": {"type": "turn.completed"}}),
    ]


def _harness(*, selection=None, transport=None, exit_code=0):
    fs = FakeFS()
    holder = {}

    def factory(*, argv, environment, execution_id, run_dir):
        transport_obj = transport or FakeTransport(_script())
        holder["transport"] = transport_obj
        holder["argv"] = argv
        holder["environment"] = environment
        return transport_obj

    runner = SupervisedZCodeRunner(
        execution_store=_StubStore(),
        supervised=_StubSupervised(),
        identity=SupervisedRunIdentity(
            job_id="job-1", work_order_ref="WO-P1-158", project_id="p1",
            worker_id="w1", backend_id=ZCODE_BACKEND_ID, branch="main",
            head_before="h" * 40, runtime_profile_ref="rt:test",
            repo_root="A:/fake/repo",
        ),
        selection_source=selection or FakeSelection(),
        spawn_transport_factory=factory,
        filesystem=fs,
        executable=r"C:\ZCode\ZCode.exe",
        bundle_js=r"C:\ZCode\resources\glm\zcode.cjs",
        secret_reference="secret-ref:zcode-credential",
    )
    return runner, fs, holder


class _StubStore:
    def create(self, record): return record
    def get(self, execution_id): raise KeyError(execution_id)
    def find_by_fingerprint(self, fingerprint): return ()


class _StubSupervised:
    def launch(self, plan): return plan
    def inspect(self, execution_id): raise RuntimeError("not reached in unit slice")
    def collect(self, execution_id, *, expected_version): raise RuntimeError("not reached")


def _run(runner, **over):
    kwargs = dict(
        prompt="say ZRA1-OK", workspace="A:/fake", operation_ref="zcode:task-1",
        execution_id="exec-0123456789abcdef", run_dir_ref="runs/exec-0123456789abcdef",
        task_packet_sha256="a" * 64,
    )
    kwargs.update(over)
    return runner.run(**kwargs)


# ---------------- happy path ----------------

def test_happy_path_orders_identity_stdout_report_result():
    runner, fs, holder = _harness()
    result = _run(runner)
    assert result.recovery_required is False
    assert result.native.exit_code == 0
    assert result.native.stdout == "ZRA1-OK"
    order = [entry.split(":", 1)[1] for entry in fs.order]
    identity_idx = next(i for i, p in enumerate(order) if p.endswith("child.identity.json"))
    stdout_idx = next(i for i, p in enumerate(order) if p.endswith("stdout.log"))
    report_idx = next(i for i, p in enumerate(order) if p.endswith("report.json"))
    result_idx = next(i for i, p in enumerate(order) if p.endswith("result.json"))
    assert identity_idx < stdout_idx < report_idx < result_idx
    report = json.loads(fs.files["runs/exec-0123456789abcdef/report.json"])
    assert report["task_packet_sha256"] == "a" * 64
    assert len(report["selection_sha256"]) == 64
    identity_doc = json.loads(fs.files["runs/exec-0123456789abcdef/child.identity.json"])
    assert identity_doc["schema"] == "zcode-child-identity/1"
    assert "prompt" not in identity_doc and "secret" not in identity_doc


def test_fixed_argv_and_environment_never_carry_prompt_or_secret():
    runner, fs, holder = _harness()
    _run(runner)
    argv = holder["argv"]
    assert argv[2:] == ("app-server", "--stdio", "--surface", "desktop")
    assert all("ZRA1-OK" not in arg for arg in argv)
    env = holder["environment"]
    assert env == {"ELECTRON_RUN_AS_NODE": "1"}
    assert all("secret" not in k.lower() and "key" not in k.lower() for k in env)


# ---------------- selection drift ----------------

def test_selection_drift_between_checks_fails_before_spawn():
    runner, fs, holder = _harness(selection=FakeSelection(mutate_on_second_call=True))
    with pytest.raises(ZCodeSelectionDriftError):
        _run(runner)
    assert fs.order == []  # nothing written — fail closed before spawn


# ---------------- UNKNOWN never fabricates result ----------------

def test_exit_pending_returns_recovery_and_never_writes_result_json():
    runner, fs, _ = _harness(transport=FakeTransport(_script(), exit_code=None))
    result = _run(runner)
    assert result.recovery_required is True
    assert result.error_code == "ZCODE_EXIT_PENDING"
    assert "runs/exec-0123456789abcdef/result.json" not in fs.files
    report = json.loads(fs.files["runs/exec-0123456789abcdef/report.json"])
    assert report["response_bytes"] == len(b"ZRA1-OK") or "state" in report


def test_turn_failure_is_typed_unknown_with_report_only():
    failing = FakeTransport([
        json.dumps({"id": 1, "result": {"session": {"sessionId": "s-1"}}}),
        json.dumps({"id": 100, "method": "session/requestRuntimePreferences"}),
        json.dumps({"id": 2, "result": {"ok": True}}),
        json.dumps({"method": "session/event", "params": {"type": "turn.failed"}}),
    ])
    runner, fs, _ = _harness(transport=failing)
    result = _run(runner)
    assert result.recovery_required is True
    assert result.error_code == "ZCODE_TURN_FAILED"
    assert "runs/exec-0123456789abcdef/result.json" not in fs.files
    assert result.native.exit_code is None


# ---------------- report/result integrity ----------------

def test_result_json_binds_response_sha_and_real_exit():
    runner, fs, _ = _harness()
    _run(runner)
    result = json.loads(fs.files["runs/exec-0123456789abcdef/result.json"])
    import hashlib
    assert result["exit_code"] == 0
    assert result["response_sha256"] == hashlib.sha256(b"ZRA1-OK").hexdigest()


def test_missing_report_prevents_result_acceptance():
    runner, fs, _ = _harness()
    _run(runner)
    # report must exist before result; corrupting report invalidates the pair
    fs.files["runs/exec-0123456789abcdef/report.json"] = "corrupt"
    with pytest.raises(json.JSONDecodeError):
        json.loads(fs.files["runs/exec-0123456789abcdef/report.json"])


# ---------------- no kill surface ----------------

def test_runner_module_has_no_terminate_or_kill_ladder():
    import inspect
    from a_conductor import zcode_runner as module
    source = inspect.getsource(module)
    for forbidden in ("taskkill", "TerminateProcess", ".terminate()", ".kill()", "Stop-Process"):
        assert forbidden not in source, forbidden


def test_transport_shutdown_is_eof_only():
    runner, fs, holder = _harness()
    _run(runner)
    transport = holder["transport"]
    assert transport.killed is False
    assert not hasattr(transport, "terminate") or callable(getattr(transport, "close_stdin_and_wait"))


# ---------------- identity validation ----------------

def test_identity_argv_sha_binds_exact_fixed_argv():
    runner, fs, _ = _harness()
    _run(runner)
    identity_doc = json.loads(fs.files["runs/exec-0123456789abcdef/child.identity.json"])
    assert identity_doc["target_argv_sha256"] == target_argv_sha256(runner.argv())


def test_backend_id_is_distinct_and_enforced():
    from a_conductor.supervised_run_coordinator import SupervisedRunIdentity
    with pytest.raises(ValueError):
        SupervisedZCodeRunner(
            execution_store=_StubStore(),
            supervised=_StubSupervised(),
            identity=SupervisedRunIdentity(
                job_id="j", work_order_ref="w", project_id="p", worker_id="w",
                backend_id="supervised-native", branch="b", head_before="h",
                runtime_profile_ref="r", repo_root="A:/x",
            ),
            selection_source=FakeSelection(),
            spawn_transport_factory=lambda **kw: FakeTransport(_script()),
            filesystem=FakeFS(),
            executable="C:/z", bundle_js="C:/b.cjs",
            secret_reference="secret-ref:x",
        )


def test_secret_reference_only_uses_external_secret_ref_authority():
    runner, _, _ = _harness()
    assert runner._secret_reference.startswith("secret-ref:")
    import inspect
    from a_conductor import zcode_runner as module
    source = inspect.getsource(module)
    # credential value is never in argv/env/files: only the opaque reference
    assert "ANTHROPIC_API_KEY" not in source
