"""WO-P1-158 Prompt-2 RED — full task identity + cross-process ATTACH +
launch-side CAS truth (binding GPT1 review 5558197043 items 5-7).

Objective A: collision-resistant task-derived operation identity with
explicit domain separation and NO 64-bit truncation.

Objective B: when no canonical result exists, the durable record ->
child.identity.json -> ACTUAL process observation reconciliation decides
ATTACH_RUNNING vs RECOVERY — never an immediate result-missing verdict.

Objective C: a durable SUCCEEDED transition failure can never be swallowed
into apparent success.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from a_conductor.claude_code_harness import TaskPacketFile
from a_conductor.execution_store import ExecutionStoreError, SQLiteExecutionStore
from a_conductor.supervised_execution import (
    SupervisedInspection,
    SupervisedInspectionState,
)
from a_conductor.zcode_protocol import ZCodeRuntimeModel
from a_conductor.zcode_runner import (
    ZCODE_BACKEND_ID,
    ZCodeBackendAdapter,
    ZCodeRunError,
    ZCodeServiceLifecycleLauncher,
    ZCodeTaskPacketIdentity,
)
from a_conductor.zcode_supervised_helper import (
    ZCodeChildIdentity,
    serialize_child_identity_document,
    target_argv_sha256,
)
from tests.test_zcode_runner import (
    BASE_URL, BINDING, EXEC, BUNDLE, FS, Selection, Secrets, TransportFactory,
    _packet_file, _script,
)


# ---------------- Objective A: full task identity ----------------

def _identity(tmp_path: Path, *, ref: str = "WO-P1-158-ZRA1", text: str = "x") -> ZCodeTaskPacketIdentity:
    path = tmp_path / f"packet-{ref}-{hashlib.sha256(text.encode()).hexdigest()[:8]}.md"
    path.write_text(text, encoding="utf-8")
    packet = TaskPacketFile(
        task_contract_ref=ref, path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    return ZCodeTaskPacketIdentity.from_task_packet_file(packet, trusted_root=str(tmp_path))


def test_operation_identity_is_domain_separated_full_sha256(tmp_path):
    """zcode-task-v1:<full SHA-256 over the canonical derivation>."""
    identity = _identity(tmp_path)
    ref = identity.canonical_operation_ref()
    prefix = "zcode-task-v1:"
    assert ref.startswith(prefix)
    digest_hex = ref[len(prefix):]
    assert len(digest_hex) == 64  # NO 64-bit truncation
    expected = hashlib.sha256(
        b"zcode-task-v1"
        + identity.task_contract_ref.encode("utf-8")
        + b"\x00"
        + identity.packet_sha256.encode("ascii")
    ).hexdigest()
    assert digest_hex == expected  # pinned exact canonical byte encoding


def test_identity_same_task_same_bytes_restart_stable(tmp_path):
    first = _identity(tmp_path)
    second = ZCodeTaskPacketIdentity.from_task_packet_file(
        TaskPacketFile(
            task_contract_ref=first.task_contract_ref,
            path=first.path,
            sha256=first.packet_sha256,
        ),
        trusted_root=str(tmp_path),
    )
    assert first.canonical_operation_ref() == second.canonical_operation_ref()


def test_identity_differs_for_packet_bytes_and_task_ref(tmp_path):
    a = _identity(tmp_path, ref="R", text="one")
    b = _identity(tmp_path, ref="R", text="two")   # same ref, different bytes
    c = _identity(tmp_path, ref="OTHER", text="one")  # different ref, same bytes
    assert a.canonical_operation_ref() != b.canonical_operation_ref()
    assert a.canonical_operation_ref() != c.canonical_operation_ref()


def test_malformed_packet_digest_rejected(tmp_path):
    identity = _identity(tmp_path)
    bad = ZCodeTaskPacketIdentity(
        task_contract_ref=identity.task_contract_ref,
        packet_sha256="zz" * 32,  # not hex
        content=identity.content,
        path=identity.path,
        trusted_root=identity.trusted_root,
    )
    with pytest.raises(ZCodeRunError):
        bad.canonical_operation_ref()


def test_truncated_legacy_identity_is_gone(tmp_path):
    identity = _identity(tmp_path)
    ref = identity.canonical_operation_ref()
    legacy = f"zcode:{identity.task_contract_ref}:{identity.packet_sha256[:16]}"
    assert ref != legacy
    assert identity.packet_sha256[:16] not in ref


# ---------------- Objective B: cross-process ATTACH_RUNNING ----------------

class _StubService:
    """Minimal service stand-in returning the classification under test."""

    def __init__(self, inspection: SupervisedInspection):
        self._inspection = inspection
        self.launch_calls = 0

    def launch(self, plan):
        self.launch_calls += 1
        raise AssertionError("inspect must never launch")

    def inspect(self, execution_id):
        return self._inspection

    def collect(self, execution_id, *, expected_version):
        raise AssertionError("not used in these tests")


class _Observer:
    def __init__(self, live):
        self._live = live

    def observe_child(self, pid):
        return self._live


def _launcher_with_state(tmp_path, *, live, recovery_code="SUPERVISOR_EXITED_RESULT_MISSING"):
    """Durable record + child.identity.json (ORIGINAL child facts) + a
    recovery-classified service inspection, as a fresh process/session would
    see after a supervisor exit. The observer reports the LIVE process view,
    which may agree or drift from the durable identity."""
    from a_conductor.execution_record import TransportState, new_execution_record

    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    execution_id = "exec-aaaa0000bbbb1111"
    repo = tmp_path
    record = new_execution_record(
        execution_id=execution_id,
        job_id="job:WO-P1-158-ZRA1", work_order_ref="WO-P1-158-ZRA1",
        project_id="zcode", worker_id="a-worker-01", backend_id=ZCODE_BACKEND_ID,
        agent_ref="agent:zcode-app-server", repo_root=str(repo),
        branch="b", head_before="h" * 40, operation_ref="zcode-task-v1:" + "0" * 64,
        command_fingerprint="f" * 64, command_summary="zcode",
        runtime_profile_ref="rt", run_dir_ref=f"runs/{execution_id}",
        stdout_ref=f"runs/{execution_id}/stdout.log",
        stderr_ref=f"runs/{execution_id}/stderr.log",
        result_ref=f"runs/{execution_id}/result.json",
        report_ref=f"runs/{execution_id}/report.json",
        transport_state=TransportState.CONNECTED,
    )
    store.create(record)
    original = _live_child()
    identity = ZCodeChildIdentity(
        child_pid=original["pid"],
        child_created_epoch_ms=original["created_epoch_ms"],
        executable=original["executable"],
        parent_pid=original["parent_pid"],
        target_argv_sha256=target_argv_sha256(
            (EXEC, BUNDLE, "app-server", "--stdio", "--surface", "desktop")
        ),
        execution_id=execution_id,
    )
    run_dir = repo / "runs" / execution_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "child.identity.json").write_text(
        serialize_child_identity_document(identity), encoding="utf-8"
    )
    service = _StubService(SupervisedInspection(
        execution_id=execution_id,
        state=SupervisedInspectionState.SUPERVISOR_EXITED_RESULT_MISSING,
        supervisor_pid=None,
        result_available=False,
        recovery_required=True,
        error_code=recovery_code,
    ))
    launcher = ZCodeServiceLifecycleLauncher(
        service=service,
        execution_store=store,
        child_observer=_Observer(live),
        selection_source=Selection(),
        expected_binding=BINDING,
        expected_base_url=BASE_URL,
        runtime_model=ZCodeRuntimeModel(
            revision="zcode-runtime-v1:" + "a" * 64,
            provider_id="zcode-glm",
            model_id="glm-5.3",
            base_url=BASE_URL,
            api_key_env="ANTHROPIC_API_KEY",
        ),
        secret_resolver=Secrets(),
        secret_reference="secret-ref:zcode-credential",
        packet=_identity(tmp_path),
        executable=EXEC,
        bundle_js=BUNDLE,
    )
    return launcher, execution_id, service


def _live_child():
    return {"pid": 4242, "created_epoch_ms": 1788490277831,
            "executable": EXEC, "parent_pid": 100}


def test_restart_with_live_exact_child_attaches_running(tmp_path):
    """New process/session: durable record + live EXACT child => ATTACH_RUNNING,
    not SUPERVISOR_EXITED_RESULT_MISSING."""
    launcher, execution_id, service = _launcher_with_state(tmp_path, live=_live_child())
    inspection = launcher.inspect(execution_id)
    assert inspection.state is SupervisedInspectionState.ATTACH_RUNNING
    assert inspection.recovery_required is False
    assert inspection.result_available is False
    assert service.launch_calls == 0  # no replay / no duplicate spawn


def test_pid_reuse_classifies_recovery(tmp_path):
    reused = {**_live_child(), "created_epoch_ms": 9999999999999}
    launcher, execution_id, _ = _launcher_with_state(tmp_path, live=reused)
    inspection = launcher.inspect(execution_id)
    assert inspection.recovery_required is True
    assert inspection.state is SupervisedInspectionState.SUPERVISOR_EXITED_RESULT_MISSING


def test_executable_mismatch_classifies_recovery(tmp_path):
    wrong_exe = {**_live_child(), "executable": r"C:\Evil\Other.exe"}
    launcher, execution_id, _ = _launcher_with_state(tmp_path, live=wrong_exe)
    assert launcher.inspect(execution_id).recovery_required is True


def test_parent_mismatch_classifies_recovery(tmp_path):
    wrong_parent = {**_live_child(), "parent_pid": 555}
    launcher, execution_id, _ = _launcher_with_state(tmp_path, live=wrong_parent)
    assert launcher.inspect(execution_id).recovery_required is True


def test_dead_child_result_missing_classifies_recovery(tmp_path):
    launcher, execution_id, _ = _launcher_with_state(tmp_path, live=None)
    inspection = launcher.inspect(execution_id)
    assert inspection.recovery_required is True
    assert inspection.state is SupervisedInspectionState.SUPERVISOR_EXITED_RESULT_MISSING


def test_canonical_result_available_passthrough_no_reconciliation(tmp_path):
    """result.json exists => collect path; reconciliation never rewrites it."""
    from a_conductor.supervised_execution import SupervisedInspection as SI

    launcher, execution_id, service = _launcher_with_state(tmp_path, live=None)
    service._inspection = SI(
        execution_id=execution_id,
        state=SupervisedInspectionState.RESULT_AVAILABLE,
        supervisor_pid=None, result_available=True, recovery_required=False,
    )
    inspection = launcher.inspect(execution_id)
    assert inspection.state is SupervisedInspectionState.RESULT_AVAILABLE
    assert inspection.result_available is True


def test_repeated_inspect_is_idempotent(tmp_path):
    launcher, execution_id, _ = _launcher_with_state(tmp_path, live=_live_child())
    first = launcher.inspect(execution_id)
    second = launcher.inspect(execution_id)
    assert first.state is second.state is SupervisedInspectionState.ATTACH_RUNNING
    assert first.recovery_required is second.recovery_required is False


# ---------------- Objective C: launch-side CAS truth ----------------

class _CASFailingStore(SQLiteExecutionStore):
    """Fail exactly the durable SUCCEEDED transition (version conflict or
    store fault) while every other operation works."""

    mode = "version_conflict"

    def set_execution_state(self, execution_id, state, *, expected_version, evidence_ref=None):
        from a_conductor.execution_record import ExecutionProcessState

        if state is ExecutionProcessState.SUCCEEDED:
            if self.mode == "version_conflict":
                raise ExecutionStoreError("EXECUTION_VERSION_CONFLICT")
            raise RuntimeError("store is down")
        return super().set_execution_state(
            execution_id, state, expected_version=expected_version,
            evidence_ref=evidence_ref,
        )


def _adapter(tmp_path, store) -> ZCodeBackendAdapter:
    return ZCodeBackendAdapter(
        transport_factory=TransportFactory(_script()),
        filesystem=FS(tmp_path),
        execution_store=store,
        selection_source=Selection(),
        expected_binding=BINDING,
        expected_base_url=BASE_URL,
        secret_resolver=Secrets(),
        secret_reference="secret-ref:zcode-credential",
        packet=_identity(tmp_path, ref="WO-P1-158-CAS"),
        workspace=str(tmp_path),
        executable=EXEC,
        bundle_js=BUNDLE,
    )


def _run_with_store(tmp_path, store):
    from a_conductor.supervised_run_coordinator import SupervisedRunCoordinator, SupervisedRunIdentity
    from a_conductor.zcode_runner import zcode_backend_policy

    packet = _identity(tmp_path, ref="WO-P1-158-CAS")
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=_adapter(tmp_path, store),
        identity=SupervisedRunIdentity(
            job_id="job:WO-P1-158-CAS", work_order_ref="WO-P1-158-CAS",
            project_id="zcode", worker_id="w", backend_id=ZCODE_BACKEND_ID,
            branch="main", head_before="h" * 40, runtime_profile_ref="rt",
            repo_root=str(tmp_path),
        ),
        backend_policy=zcode_backend_policy(operation_ref=packet.canonical_operation_ref()),
        poll_interval_seconds=0.01,
    )
    return coordinator.run(
        (EXEC, BUNDLE, "app-server", "--stdio", "--surface", "desktop"),
        timeout_seconds=30,
    )


def test_succeeded_cas_version_conflict_never_reports_success(tmp_path):
    store = _CASFailingStore(tmp_path / "cas.sqlite")
    result = _run_with_store(tmp_path, store)
    assert result.exit_code is None  # NOT success
    assert "ZCODE_DURABLE_STATE_TRANSITION_FAILED" in result.stderr


def test_succeeded_cas_store_exception_never_reports_success(tmp_path):
    store = _CASFailingStore(tmp_path / "cas2.sqlite")
    store.mode = "store_fault"
    result = _run_with_store(tmp_path, store)
    assert result.exit_code is None
    assert "ZCODE_DURABLE_STATE_TRANSITION_FAILED" in result.stderr


def test_cas_failure_retry_does_not_duplicate_execution(tmp_path):
    store = _CASFailingStore(tmp_path / "cas3.sqlite")
    first = _run_with_store(tmp_path, store)
    assert first.exit_code is None
    store.mode = "healthy"
    # retry: the durable result.json from the first attempt is collected —
    # exactly one child execution ever happened
    class _Counting(SQLiteExecutionStore):
        def __init__(self, path):
            super().__init__(path)
            self.spawns = 0

    second = _run_with_store(tmp_path, store)
    assert second.exit_code == 0  # reconciled from durable artifacts
    import sqlite3

    con = sqlite3.connect(tmp_path / "cas3.sqlite")
    rows = con.execute("SELECT COUNT(*) FROM execution_records").fetchone()[0]
    con.close()
    assert rows == 1  # no duplicate execution row


def test_healthy_store_still_succeeds(tmp_path):
    store = SQLiteExecutionStore(tmp_path / "healthy.sqlite")
    result = _run_with_store(tmp_path, store)
    assert result.exit_code == 0
