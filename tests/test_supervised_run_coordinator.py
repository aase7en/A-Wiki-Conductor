"""WO-P1-158 Phase A — shared SupervisedRunCoordinator equivalence proofs.

The coordinator extracted from ``SupervisedCommandRunner`` must preserve every
generic behavior: identical fingerprints, execution-id format, durable record
fields/refs, dedup/attach semantics, timeout/recovery classification, artifact
mapping, and store-write counts — with no extra threads, background workers,
or new retry authority. These tests pin adapter⇄coordinator equivalence.
"""

from __future__ import annotations

import hashlib
import re
import sys
import threading
from pathlib import Path

import pytest

from a_conductor.execution_record import DurableExecutionRecord, ExecutionProcessState
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.native_execution import (
    NativeExecutionError,
    NativeExecutionScope,
)
from a_conductor.supervised_command_runner import SupervisedCommandRunner
from a_conductor.supervised_execution import (
    SupervisedExecutionError,
    SupervisedExecutionService,
    SupervisedInspection,
    SupervisedInspectionState,
    SupervisedLaunchOutcome,
    SupervisedLaunchPlan,
    SupervisedCollectOutcome,
)
from a_conductor.supervised_run_coordinator import (
    SupervisedBackendPolicy,
    SupervisedRunCoordinator,
    SupervisedRunIdentity,
    native_backend_policy,
)


RUNTIME_PYTHON = getattr(sys, "_base_executable", sys.executable)
PYTHON_NAME = Path(sys.executable).name

IDENTITY = dict(
    job_id="job-001",
    work_order_ref="docs/work-orders/WO-P1-158-zero-relay-zcode.md",
    project_id="project-1",
    worker_id="a-worker-01",
    backend_id="supervised-native",
    branch="main",
    head_before="b" * 40,
    runtime_profile_ref="runtime:test",
)

_EXEC_ID_RE = re.compile(r"^exec-[0-9a-f]{16}$")


class ScriptedSupervised:
    """Deterministic in-memory supervised launcher for equivalence proofs."""

    def __init__(self, repo: Path, store, *, exit_code: int = 0, stdout: bytes = b"ok"):
        self.repo = repo
        self.store = store
        self.exit_code = exit_code
        self.stdout = stdout
        self.records: dict[str, DurableExecutionRecord] = {}
        self.launch_calls = 0
        self.collect_calls = 0
        self._lock = threading.Lock()

    def launch(self, plan: SupervisedLaunchPlan) -> SupervisedLaunchOutcome:
        with self._lock:
            self.launch_calls += 1
            record = plan.record
            run_dir = self.repo / record.run_dir_ref
            run_dir.mkdir(parents=True, exist_ok=True)
            (self.repo / record.stdout_ref).write_bytes(self.stdout)
            (self.repo / record.stderr_ref).write_bytes(b"")
            stored = replace_record_state(record, ExecutionProcessState.VERIFICATION_REQUIRED)
            stored = self.store.create(stored)
            self.records[record.execution_id] = stored
            return SupervisedLaunchOutcome(
                record=stored,
                supervisor_pid=None,
                child_pid=None,
                recovery_required=False,
            )

    def inspect(self, execution_id: str) -> SupervisedInspection:
        with self._lock:
            record = self.records.get(execution_id)
        if record is None:
            raise SupervisedExecutionError("NOT_FOUND")
        return SupervisedInspection(
            execution_id=execution_id,
            state=SupervisedInspectionState.RESULT_AVAILABLE,
            supervisor_pid=None,
            result_available=True,
            recovery_required=False,
        )

    def collect(self, execution_id: str, *, expected_version: int):
        with self._lock:
            self.collect_calls += 1
            record = self.records.get(execution_id)
        if record is None:
            raise SupervisedExecutionError("NOT_FOUND")
        result = make_child_result(execution_id, self.exit_code)
        return SupervisedCollectOutcome(
            record=record, result=result, recovery_required=False
        )


def replace_record_state(record, state):
    from dataclasses import replace as _replace

    return _replace(record, execution_state=state)


def make_child_result(execution_id: str, exit_code: int):
    from a_conductor.supervised_child import SupervisedChildResult

    return SupervisedChildResult(
        schema_version=1,
        execution_id=execution_id,
        child_pid=1234,
        exit_code=exit_code,
        started_at="2026-09-05T00:00:00+00:00",
        finished_at="2026-09-05T00:00:01+00:00",
    )


def _scope(repo: Path) -> NativeExecutionScope:
    return NativeExecutionScope(
        root=repo,
        mutation_allowed=True,
        allowed_executables=(PYTHON_NAME,),
        allowed_environment_overrides=(),
        max_timeout_seconds=60,
        max_output_bytes=64 * 1024,
        max_file_bytes=64 * 1024,
    )


def _identity(repo: Path) -> SupervisedRunIdentity:
    return SupervisedRunIdentity(repo_root=str(repo), **IDENTITY)


def _harness(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    supervised = ScriptedSupervised(repo, store)
    runner = SupervisedCommandRunner(
        scope=_scope(repo),
        execution_store=store,
        supervised=supervised,
        poll_interval_seconds=0.01,
        **IDENTITY,
    )
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        poll_interval_seconds=0.01,
    )
    return repo, store, supervised, runner, coordinator


ARGV = (RUNTIME_PYTHON, "-c", "print('phase-a')")


def test_same_fingerprint_and_operation_ref(tmp_path):
    _, _, _, runner, coordinator = _harness(tmp_path)
    fp_runner = runner.fingerprint_for(
        __import__("a_conductor.native_execution", fromlist=["NativeCommandSpec"]).NativeCommandSpec(
            argv=ARGV
        )
    )
    fp_coord = coordinator.fingerprint_for_argv(ARGV)
    assert fp_runner == fp_coord
    assert coordinator.operation_ref(ARGV).startswith("native:")
    assert len(coordinator.operation_ref(ARGV)) == len("native:") + 16


def test_same_success_result_record_shape_and_refs(tmp_path):
    repo, store, supervised, runner, coordinator = _harness(tmp_path)
    argv_a, argv_b = ARGV, (RUNTIME_PYTHON, "-c", "print('phase-a-b')")

    result_adapter = runner.run(
        __import__("a_conductor.native_execution", fromlist=["NativeCommandSpec"]).NativeCommandSpec(
            argv=argv_a
        )
    )
    result_direct = coordinator.run(argv_b, timeout_seconds=30)

    for result in (result_adapter, result_direct):
        assert result.exit_code == 0
        assert result.timed_out is False
        assert result.executable == PYTHON_NAME
        assert result.stdout == "ok"
        assert result.stdout_sha256 == hashlib.sha256(b"ok").hexdigest()
        assert result.stderr_sha256 == hashlib.sha256(b"").hexdigest()

    records_a = store.find_by_fingerprint(coordinator.fingerprint_for_argv(argv_a))
    records_b = store.find_by_fingerprint(coordinator.fingerprint_for_argv(argv_b))
    assert len(records_a) == 1 and len(records_b) == 1
    for record, argv in ((records_a[0], argv_a), (records_b[0], argv_b)):
        assert _EXEC_ID_RE.fullmatch(record.execution_id)
        assert record.run_dir_ref == f"runs/{record.execution_id}"
        assert record.stdout_ref == f"runs/{record.execution_id}/stdout.log"
        assert record.stderr_ref == f"runs/{record.execution_id}/stderr.log"
        assert record.result_ref == f"runs/{record.execution_id}/result.json"
        for field, expected in IDENTITY.items():
            assert getattr(record, field) == expected, field
        assert record.agent_ref == "agent:supervised-native"
        assert record.operation_ref == coordinator.operation_ref(argv)


def test_reuse_completed_uses_same_execution_id_no_new_launch(tmp_path):
    _, store, supervised, runner, coordinator = _harness(tmp_path)
    spec = __import__("a_conductor.native_execution", fromlist=["NativeCommandSpec"]).NativeCommandSpec(
        argv=ARGV
    )
    runner.run(spec)
    first_id = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))[0].execution_id
    launches_before = supervised.launch_calls

    coordinator.run(ARGV, timeout_seconds=30)

    assert supervised.launch_calls == launches_before          # no new launch
    records = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))
    assert len(records) == 1 and records[0].execution_id == first_id


def test_no_extra_store_writes_and_single_threaded(tmp_path):
    repo, store, supervised, runner, coordinator = _harness(tmp_path)
    threads_before = threading.active_count()
    coordinator.run(ARGV, timeout_seconds=30)
    assert threading.active_count() == threads_before          # no background worker
    records = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))
    assert len(records) == 1                                    # exactly one durable record


def test_timeout_classification_identical(tmp_path):
    import time as _time

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    class NeverResolves(ScriptedSupervised):
        def inspect(self, execution_id):
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.SUPERVISOR_RUNNING,
                supervisor_pid=None,
                result_available=False,
                recovery_required=False,
            )

    supervised = NeverResolves(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        poll_interval_seconds=0.001,
        clock_fn=_time.monotonic,
    )
    result = coordinator.run(ARGV, timeout_seconds=1)
    assert result.timed_out is True
    assert result.exit_code is None


def test_recovery_classification_identical(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    class RecoveryRequired(ScriptedSupervised):
        def inspect(self, execution_id):
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.RECOVERY_REQUIRED,
                supervisor_pid=None,
                result_available=False,
                recovery_required=True,
                error_code="CHILD_DIED",
            )

    supervised = RecoveryRequired(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        poll_interval_seconds=0.001,
    )
    result = coordinator.run(ARGV, timeout_seconds=30)
    assert result.exit_code is None
    assert result.stderr.startswith("SUPERVISOR_RECOVERY_REQUIRED:CHILD_DIED")
    assert result.timed_out is False


def test_stdout_cap_identical(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    big = b"x" * (70 * 1024)
    supervised = ScriptedSupervised(repo, store, stdout=big)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        poll_interval_seconds=0.01,
        max_output_bytes=64 * 1024,
    )
    result = coordinator.run(ARGV, timeout_seconds=30)
    assert result.stdout_truncated is True
    assert len(result.stdout.encode()) == 64 * 1024
    assert result.stdout_sha256 == hashlib.sha256(big).hexdigest()  # full-file digest


def test_adapter_scope_validation_unchanged(tmp_path):
    _, _, _, runner, _ = _harness(tmp_path)
    NativeCommandSpec = __import__(
        "a_conductor.native_execution", fromlist=["NativeCommandSpec"]
    ).NativeCommandSpec
    with pytest.raises(NativeExecutionError) as exc:
        runner.run(NativeCommandSpec(argv=("notepad.exe", "-x")))
    assert exc.value.code == "EXECUTABLE_NOT_ALLOWED"
    with pytest.raises(NativeExecutionError) as exc2:
        runner.run(NativeCommandSpec(argv=ARGV, timeout_seconds=9999))
    assert exc2.value.code == "TIMEOUT_INVALID"


def test_coordinator_validates_identity_and_dependencies(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    supervised = ScriptedSupervised(repo, store)
    with pytest.raises(ValueError):
        SupervisedRunCoordinator(
            execution_store=store,
            supervised=supervised,
            identity=SupervisedRunIdentity(
                job_id=" ", work_order_ref="w", project_id="p", worker_id="w",
                backend_id="b", branch="main", head_before="h",
                runtime_profile_ref="r", repo_root=str(repo),
            ),
        )
    with pytest.raises(ValueError):
        SupervisedRunCoordinator(
            execution_store=store,
            supervised=object(),
            identity=_identity(repo),
        )


def test_no_duplicate_authority_introduced():
    import inspect
    from a_conductor import supervised_run_coordinator as module
    source = inspect.getsource(module)
    for forbidden in ("threading.Thread", "Timer(", "while True:  # retry", "class .*Scheduler"):
        if forbidden == "while True:  # retry":
            assert forbidden not in source
        # no scheduler/thread spawn text in the coordinator
    assert "threading" not in source
    assert "Scheduler" not in source


# ---------------- backend-policy seam (GPT1 Q20 CHANGES_REQUIRED) ----------------

def test_coordinator_accepts_non_native_backend_policy(tmp_path):
    """The coordinator must represent a non-native backend: caller-supplied
    operation_ref, report_ref, artifact refs, agent identity and command
    summary flow into the durable record without any native hard-coding."""
    repo, store, supervised, _, coordinator = _harness(tmp_path)
    argv = ("C:/ZCode/ZCode.exe", "zcode.cjs", "app-server", "--stdio",
            "--surface", "desktop")

    def zcode_op_ref(a):
        return "zcode:task-packet-sha256:abcd1234"

    def zcode_summary(a):
        return "zcode app-server turn (task abcd1234)"

    def zcode_report(run_rel):
        return f"{run_rel}/report.json"

    policy = SupervisedBackendPolicy(
        derive_operation_ref=zcode_op_ref,
        command_summary=zcode_summary,
        agent_ref="agent:zcode-app-server",
        report_ref=zcode_report,
    )
    zcode_coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=SupervisedRunIdentity(
            job_id="job-1", work_order_ref="WO-P1-158", project_id="p1",
            worker_id="w1", backend_id="zcode-app-server", branch="main",
            head_before="b" * 40, runtime_profile_ref="rt:zcode",
            repo_root=str(repo),
        ),
        backend_policy=policy,
        poll_interval_seconds=0.01,
    )
    fingerprint_before = zcode_coordinator.fingerprint_for_argv(argv)
    zcode_coordinator.run(argv, timeout_seconds=30)
    record = store.find_by_fingerprint(fingerprint_before)[0]
    assert record.operation_ref == "zcode:task-packet-sha256:abcd1234"
    assert record.agent_ref == "agent:zcode-app-server"
    assert record.command_summary == "zcode app-server turn (task abcd1234)"
    assert record.report_ref.endswith("/report.json")
    assert record.stdout_ref.endswith("/stdout.log")   # default artifact refs
    assert record.result_ref.endswith("/result.json")
    assert record.backend_id == "zcode-app-server"


def test_native_default_policy_is_byte_identical_to_historical_behavior(tmp_path):
    """Default (no policy) coordinator must keep exact native outputs."""
    repo, store, supervised, runner, coordinator = _harness(tmp_path)
    argv = ARGV
    import hashlib as _h
    expected_op = f"native:{_h.sha256(chr(0).join(argv).encode()).hexdigest()[:16]}"
    assert coordinator.operation_ref(argv) == expected_op
    assert coordinator.fingerprint_for_argv(argv) == runner.fingerprint_for(
        __import__("a_conductor.native_execution", fromlist=["NativeCommandSpec"]).NativeCommandSpec(argv=argv)
    )
    coordinator.run(argv, timeout_seconds=30)
    record = store.find_by_fingerprint(coordinator.fingerprint_for_argv(argv))[0]
    assert record.agent_ref == "agent:supervised-native"
    assert record.command_summary == " ".join(argv[:3])[:200]
    assert record.report_ref is None


def test_policy_validates_callables_and_agent_ref(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError):
        SupervisedBackendPolicy(
            derive_operation_ref="not-callable", command_summary=lambda a: "s"
        )
    with pytest.raises(ValueError):
        SupervisedBackendPolicy(
            derive_operation_ref=lambda a: "x", command_summary=lambda a: "s",
            agent_ref=" ",
        )


# ---------------- WO-P1-246: author-attempt provenance mint/stamp ------------

import dataclasses as _dataclasses

from a_conductor.supervised_run_coordinator import mint_author_attempt_id
from a_conductor.zero_relay_author_provenance import (
    AuthorProvenanceError,
    classify_author_provenance,
)


def _binding(repo: Path):
    return classify_author_provenance(
        task_contract_ref=IDENTITY["work_order_ref"],
        packet_sha256="c" * 64,
    )


def _provenanced_harness(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    supervised = ScriptedSupervised(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=SupervisedRunIdentity(
            repo_root=str(repo),
            author_provenance=_binding(repo),
            **IDENTITY,
        ),
        poll_interval_seconds=0.01,
    )
    return repo, store, supervised, coordinator


def test_wo246_generic_native_run_gets_no_author_provenance(tmp_path):
    """Test 15 / 33: a binding-less identity never stamps a pair."""
    repo, store, supervised, runner, coordinator = _harness(tmp_path)
    result = coordinator.run(ARGV, timeout_seconds=30)
    assert result.exit_code == 0
    record = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))[0]
    assert record.author_attempt_id is None
    assert record.author_generation is None


def test_wo246_identity_rejects_provenance_shaped_non_binding(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError):
        SupervisedRunIdentity(
            repo_root=str(repo),
            author_provenance="author-attempt-v1:00000000000000000000000000000000",
            **IDENTITY,
        )
    with pytest.raises(ValueError):
        SupervisedRunIdentity(repo_root=str(repo), author_provenance=0, **IDENTITY)


def test_wo246_author_eligible_run_mints_generation0_pair(tmp_path):
    """Test 9 (coordinator seam): SAFE_TO_LAUNCH mints exactly one pair,
    persisted on the artifact-owning record before any external effect."""
    repo, store, supervised, coordinator = _provenanced_harness(tmp_path)
    result = coordinator.run(ARGV, timeout_seconds=30)
    assert result.exit_code == 0
    record = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))[0]
    assert record.author_generation == 0
    import re as _re

    assert _re.fullmatch(r"author-attempt-v1:[0-9a-f]{32}", record.author_attempt_id)
    # reopen: the persisted pair is the durable one
    reopened = SQLiteExecutionStore(tmp_path / "control.sqlite").get(record.execution_id)
    assert reopened.author_attempt_id == record.author_attempt_id
    assert reopened.author_generation == 0


def test_wo246_mint_failure_and_reuse_paths_never_mint_twice(tmp_path, monkeypatch):
    """Tests 19/20/21: REUSE_COMPLETED / ATTACH_RUNNING reuse the persisted
    pair; the mint is not called again; re-open reads the exact same pair."""
    import a_conductor.supervised_run_coordinator as coord_module

    repo, store, supervised, coordinator = _provenanced_harness(tmp_path)
    calls = []

    def counted_mint():
        calls.append(1)
        return mint_author_attempt_id()

    monkeypatch.setattr(coord_module, "mint_author_attempt_id", counted_mint)

    coordinator.run(ARGV, timeout_seconds=30)  # SAFE_TO_LAUNCH: mint once
    first = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))[0]
    assert len(calls) == 1

    coordinator.run(ARGV, timeout_seconds=30)  # REUSE_COMPLETED: no mint
    records = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))
    assert len(records) == 1
    assert len(calls) == 1
    assert records[0].author_attempt_id == first.author_attempt_id

    # re-open/restart reads the exact same pair
    reopened = SQLiteExecutionStore(tmp_path / "control.sqlite").get(first.execution_id)
    assert reopened.author_attempt_id == first.author_attempt_id
    assert reopened.author_generation == 0


def test_wo246_attach_running_reuses_persisted_pair_without_mint(tmp_path, monkeypatch):
    import a_conductor.supervised_run_coordinator as coord_module

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    class RunningThenResult(ScriptedSupervised):
        def launch(self, plan):
            outcome = super().launch(plan)
            with self._lock:
                record = self.records[outcome.record.execution_id]
                # leave the durable record in a live state -> ATTACH_RUNNING
                stored = store.set_execution_state(
                    record.execution_id,
                    ExecutionProcessState.RUNNING,
                    expected_version=record.version,
                )
                self.records[record.execution_id] = stored
            return outcome

    supervised = RunningThenResult(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=SupervisedRunIdentity(
            repo_root=str(repo), author_provenance=_binding(repo), **IDENTITY
        ),
        poll_interval_seconds=0.01,
    )
    calls = []
    monkeypatch.setattr(
        coord_module, "mint_author_attempt_id",
        lambda: (calls.append(1), mint_author_attempt_id())[1],
    )

    first = coordinator.run(ARGV, timeout_seconds=30)
    assert len(calls) == 1
    record = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))[0]
    assert record.execution_state is ExecutionProcessState.RUNNING

    second = coordinator.run(ARGV, timeout_seconds=30)  # ATTACH_RUNNING
    assert len(calls) == 1  # no new mint
    records = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))
    assert len(records) == 1
    assert records[0].author_attempt_id == record.author_attempt_id
    assert second.exit_code == 0


def test_wo246_predelegation_check_blocks_absent_or_malformed_pair(tmp_path, monkeypatch):
    """Test 16: a binding-carrying launch whose constructed record pair is
    absent or malformed fails closed BEFORE supervised.launch() — no
    external effect, controller.start never reached."""
    import a_conductor.supervised_run_coordinator as coord_module

    original_new_record = coord_module.new_execution_record

    def strip_pair(*args, **kwargs):
        record = original_new_record(*args, **kwargs)
        return _dataclasses.replace(record, author_attempt_id=None, author_generation=None)

    def mangle_pair(*args, **kwargs):
        record = original_new_record(*args, **kwargs)
        return _dataclasses.replace(record, author_attempt_id="not-the-minted-format")

    for patch in (strip_pair, mangle_pair):
        repo, store, supervised, coordinator = _provenanced_harness(tmp_path / "lane")
        monkeypatch.setattr(coord_module, "new_execution_record", patch)
        result = coordinator.run(ARGV, timeout_seconds=30)
        assert result.exit_code is None
        assert "SUPERVISOR_PROVENANCE_PAIR_INVALID" in result.stderr
        assert supervised.launch_calls == 0  # plan never handed to launch
        assert store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV)) == ()
    monkeypatch.setattr(coord_module, "new_execution_record", original_new_record)


def test_wo246_binding_contract_mismatch_fails_before_persistence(tmp_path):
    """§3.6: the binding's contract must equal the identity work_order_ref
    at mint, or the launch fails closed before the record exists."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    supervised = ScriptedSupervised(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=SupervisedRunIdentity(
            repo_root=str(repo),
            author_provenance=classify_author_provenance(
                task_contract_ref="WO-SOME-OTHER-CONTRACT",  # != identity ref
                packet_sha256="c" * 64,
            ),
            **IDENTITY,
        ),
        poll_interval_seconds=0.01,
    )
    result = coordinator.run(ARGV, timeout_seconds=30)
    assert result.exit_code is None
    assert "SUPERVISOR_PROVENANCE_AUTHORITY_INVALID" in result.stderr
    assert supervised.launch_calls == 0
    assert store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV)) == ()


def test_wo246_spawn_failure_retains_same_pair(tmp_path):
    """Test 18: launch recovery after durable create keeps the pair."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    class FailingLaunch(ScriptedSupervised):
        def launch(self, plan):
            with self._lock:
                self.launch_calls += 1
                stored = self.store.create(plan.record)  # durable create happens
            return SupervisedLaunchOutcome(
                record=stored,
                supervisor_pid=None,
                child_pid=None,
                recovery_required=True,
                error_code="SPAWN_REFUSED",
            )

    supervised = FailingLaunch(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=SupervisedRunIdentity(
            repo_root=str(repo), author_provenance=_binding(repo), **IDENTITY
        ),
        poll_interval_seconds=0.01,
    )
    result = coordinator.run(ARGV, timeout_seconds=30)
    assert result.exit_code is None
    assert "SUPERVISED_LAUNCH_FAILED:SPAWN_REFUSED" in result.stderr
    record = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))[0]
    assert record.author_attempt_id is not None
    assert record.author_generation == 0


def test_wo246_real_service_observes_stamped_pair_before_spawn(tmp_path):
    """Test 17: through the UNCHANGED SupervisedExecutionService.launch(),
    the record persisted by ExecutionStore.create() already carries the pair
    by the time controller.start(...) is reached."""
    from a_conductor.supervised_execution import (
        SupervisedExecutionService,
        SupervisedHelperKind,
    )

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "runs").mkdir()
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    observed: dict[str, object] = {}

    class ObservingController:
        def start(self, spec):
            execution_id = spec.expected_profile_marker
            record = store.get(execution_id)  # what has the store persisted?
            observed["attempt"] = record.author_attempt_id
            observed["generation"] = record.author_generation
            raise RuntimeError("spawn refused by test controller")

    class UnusedObserver:
        pass

    service = SupervisedExecutionService(
        store=store,
        controller=ObservingController(),
        observer=UnusedObserver(),
        allowed_target_executables=(PYTHON_NAME,),
        python_executable=RUNTIME_PYTHON,
        startup_poll_attempts=1,
        helper_kinds={SupervisedHelperKind.GENERIC_NATIVE},
    )
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=service,
        identity=SupervisedRunIdentity(
            repo_root=str(repo), author_provenance=_binding(repo), **IDENTITY
        ),
        poll_interval_seconds=0.01,
    )
    result = coordinator.run(ARGV, timeout_seconds=30)
    assert result.exit_code is None
    assert "SUPERVISED_LAUNCH_FAILED:SUPERVISOR_START_EXCEPTION" in result.stderr
    import re as _re

    assert _re.fullmatch(
        r"author-attempt-v1:[0-9a-f]{32}", observed["attempt"]
    ), observed
    assert observed["generation"] == 0

    # and the persisted record retains the same pair after the failure
    record = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))[0]
    assert record.author_attempt_id == observed["attempt"]
    assert record.author_generation == 0


def test_wo246_fingerprint_bytes_unchanged_by_provenance(tmp_path):
    """Test 29: the canonical fingerprint ignores the new provenance field."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    plain = _identity(repo)
    provenanced = SupervisedRunIdentity(
        repo_root=str(repo), author_provenance=_binding(repo), **IDENTITY
    )
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    def coordinator_for(identity):
        return SupervisedRunCoordinator(
            execution_store=store,
            supervised=ScriptedSupervised(repo, store),
            identity=identity,
            poll_interval_seconds=0.01,
        )

    argv = ("C:/ZCode/ZCode.exe", "zcode.cjs", "app-server", "--stdio")
    assert (
        coordinator_for(plain).fingerprint_for_argv(argv)
        == coordinator_for(provenanced).fingerprint_for_argv(argv)
    )


def test_wo246_no_bare_generation_or_required_trust_surface():
    """Test 13: the only provenance surface on identity/coordinator/assembly
    signatures is the proof-carrying binding."""
    import inspect

    from a_conductor import supervised_run_coordinator as coord_module
    from a_conductor import zcode_production_assembly as assembly_module

    for module in (coord_module, assembly_module):
        source = inspect.getsource(module)
        assert "author_provenance_required" not in source, module.__name__

    for function in (
        coord_module.SupervisedRunCoordinator.__init__,
        assembly_module.assemble_zcode_execution,
        assembly_module.assemble_zcode_review_execution,
        assembly_module._assemble_zcode_execution_impl,
    ):
        parameters = inspect.signature(function).parameters
        assert "author_generation" not in parameters, function
        assert "author_provenance_required" not in parameters, function

    fields = _dataclasses.fields(coord_module.SupervisedRunIdentity)
    provenance_fields = [f.name for f in fields if "author" in f.name or "provenance" in f.name]
    assert provenance_fields == ["author_provenance"]


# ---------------- WO-P1-205 Phase D exact execution handle ----------------

def test_phase_d_run_with_outcome_fresh_exposes_exact_durable_id(tmp_path):
    from a_conductor.supervised_run_coordinator import SupervisedRunOutcomeKind

    _, store, _, _, coordinator = _harness(tmp_path)
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)

    assert outcome.kind is SupervisedRunOutcomeKind.FRESH
    assert outcome.execution_id is not None
    assert store.get(outcome.execution_id).execution_id == outcome.execution_id
    assert outcome.native.exit_code == 0
    # Existing API remains behavior-compatible and returns only NativeCommandResult.
    legacy = coordinator.run(ARGV, timeout_seconds=30)
    assert legacy.exit_code == 0
    assert not hasattr(legacy, "execution_id")


def test_phase_d_run_with_outcome_reuse_preserves_exact_id(tmp_path):
    from a_conductor.supervised_run_coordinator import SupervisedRunOutcomeKind

    _, _, supervised, _, coordinator = _harness(tmp_path)
    first = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    launches = supervised.launch_calls
    second = coordinator.run_with_outcome(ARGV, timeout_seconds=30)

    assert first.kind is SupervisedRunOutcomeKind.FRESH
    assert second.kind is SupervisedRunOutcomeKind.REUSE_COMPLETED
    assert second.execution_id == first.execution_id
    assert supervised.launch_calls == launches


def test_phase_d_blocked_unknown_exposes_no_execution_id(tmp_path):
    from a_conductor.execution_deduplication import (
        DuplicateExecutionAssessment,
        DuplicateExecutionDecision,
    )
    from a_conductor.supervised_run_coordinator import SupervisedRunOutcomeKind

    _, _, _, _, coordinator = _harness(tmp_path)
    fingerprint = coordinator.fingerprint_for_argv(ARGV)

    class BlockedGuard:
        def assess(self, _spec):
            return DuplicateExecutionAssessment(
                decision=DuplicateExecutionDecision.BLOCKED_UNKNOWN,
                fingerprint=fingerprint,
                record=None,
                reason_code="AMBIGUOUS_HISTORY",
            )

    coordinator._guard = BlockedGuard()
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)

    assert outcome.kind is SupervisedRunOutcomeKind.BLOCKED_UNKNOWN
    assert outcome.execution_id is None
    assert outcome.native.exit_code is None
    assert outcome.native.stderr == "SUPERVISED_DUPLICATE_BLOCKED"


def test_phase_d_pre_persistence_provenance_failure_exposes_no_id(tmp_path):
    from a_conductor.supervised_run_coordinator import SupervisedRunOutcomeKind

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    supervised = ScriptedSupervised(repo, store)
    bad_binding = classify_author_provenance(
        task_contract_ref="different-contract",
        packet_sha256="c" * 64,
    )
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=SupervisedRunIdentity(
            repo_root=str(repo),
            author_provenance=bad_binding,
            **IDENTITY,
        ),
        poll_interval_seconds=0.01,
    )

    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)

    assert outcome.kind is SupervisedRunOutcomeKind.FAILED
    assert outcome.execution_id is None
    assert "SUPERVISOR_PROVENANCE_AUTHORITY_INVALID" in outcome.native.stderr
    assert store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV)) == ()


def test_phase_d_timeout_after_persistence_retains_exact_nonaccepted_id(tmp_path):
    import time as _time
    from a_conductor.supervised_run_coordinator import SupervisedRunOutcomeKind

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    class NeverResolves(ScriptedSupervised):
        def inspect(self, execution_id):
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.SUPERVISOR_RUNNING,
                supervisor_pid=None,
                result_available=False,
                recovery_required=False,
            )

    supervised = NeverResolves(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        poll_interval_seconds=0.001,
        clock_fn=_time.monotonic,
    )
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=1)

    assert outcome.kind is SupervisedRunOutcomeKind.TIMED_OUT
    assert outcome.execution_id is not None
    assert store.get(outcome.execution_id).execution_id == outcome.execution_id
    assert outcome.native.timed_out is True


def test_phase_d_attach_running_propagates_existing_exact_id(tmp_path):
    from a_conductor.execution_deduplication import (
        DuplicateExecutionAssessment,
        DuplicateExecutionDecision,
    )
    from a_conductor.supervised_run_coordinator import SupervisedRunOutcomeKind

    _, store, supervised, _, coordinator = _harness(tmp_path)
    first = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    record = store.get(first.execution_id)
    fingerprint = coordinator.fingerprint_for_argv(ARGV)

    class AttachGuard:
        def assess(self, _spec):
            return DuplicateExecutionAssessment(
                decision=DuplicateExecutionDecision.ATTACH_RUNNING,
                fingerprint=fingerprint,
                record=record,
                reason_code="EXISTING_ACTIVE_EXECUTION",
            )

    coordinator._guard = AttachGuard()
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)

    assert outcome.kind is SupervisedRunOutcomeKind.ATTACH_RUNNING
    assert outcome.execution_id == first.execution_id


def test_phase_d_recovery_after_persistence_retains_exact_nonaccepted_id(tmp_path):
    from a_conductor.supervised_run_coordinator import SupervisedRunOutcomeKind

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    class RecoveryRequired(ScriptedSupervised):
        def inspect(self, execution_id):
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.RECOVERY_REQUIRED,
                supervisor_pid=None,
                result_available=False,
                recovery_required=True,
                error_code="CHILD_DIED",
            )

    supervised = RecoveryRequired(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        poll_interval_seconds=0.001,
    )
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)

    assert outcome.kind is SupervisedRunOutcomeKind.RECOVERY_REQUIRED
    assert outcome.execution_id is not None
    assert store.get(outcome.execution_id).execution_id == outcome.execution_id
    assert "SUPERVISOR_RECOVERY_REQUIRED:CHILD_DIED" in outcome.native.stderr


# ---------------- WO-P1-498 / 498A: lease-bound PRE_DISPATCH GUARD ----------


def test_wo498_guard_required_missing_fails_closed_before_effects(tmp_path):
    """A FRESH route declared guard-required with no guard wired fails
    closed BEFORE execution-id mint, record persistence, or launch."""
    from a_conductor.supervised_run_coordinator import SupervisedRunOutcomeKind

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    supervised = ScriptedSupervised(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        pre_dispatch_guard=None,
        pre_dispatch_guard_required=True,
        poll_interval_seconds=0.01,
    )
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert outcome.kind is SupervisedRunOutcomeKind.FAILED
    assert outcome.execution_id is None
    assert outcome.native.stderr == "SUPERVISED_PRE_DISPATCH_GUARD_REQUIRED"
    assert supervised.launch_calls == 0
    assert store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV)) == ()


def test_wo498_guard_denies_fresh_before_persistence_or_launch(tmp_path):
    from a_conductor.supervised_run_coordinator import SupervisedRunOutcomeKind
    from a_conductor.pre_dispatch_guard import (
        PreDispatchGuardDecision,
        PreDispatchGuardDecisionKind,
    )

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    supervised = ScriptedSupervised(repo, store)

    class DenyingGuard:
        def check(self):
            return PreDispatchGuardDecision(
                PreDispatchGuardDecisionKind.DENY, "LEASE_STALE"
            )

    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        pre_dispatch_guard=DenyingGuard(),
        pre_dispatch_guard_required=True,
        poll_interval_seconds=0.01,
    )
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert outcome.kind is SupervisedRunOutcomeKind.FAILED
    assert outcome.execution_id is None
    assert outcome.native.stderr == "SUPERVISED_PRE_DISPATCH_GUARD_DENIED:LEASE_STALE"
    assert supervised.launch_calls == 0
    assert store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV)) == ()


def test_wo498_reuse_completed_and_attach_skip_guard(tmp_path):
    """ATTACH_RUNNING / REUSE_COMPLETED are dedupe-owned: the injected
    fresh-launch guard is consulted exactly once (the original FRESH)."""
    from a_conductor.supervised_run_coordinator import SupervisedRunOutcomeKind

    from a_conductor.execution_record import ExecutionProcessState
    from a_conductor.pre_dispatch_guard import (
        PreDispatchGuardDecision,
        PreDispatchGuardDecisionKind,
    )
    from a_conductor.supervised_execution import (
        SupervisedInspection,
        SupervisedInspectionState,
    )

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    class RunningThenResult(ScriptedSupervised):
        def launch(self, plan):
            outcome = super().launch(plan)
            with self._lock:
                record = self.records[outcome.record.execution_id]
                stored = store.set_execution_state(
                    record.execution_id,
                    ExecutionProcessState.RUNNING,
                    expected_version=record.version,
                )
                self.records[record.execution_id] = stored
            return outcome

        def inspect(self, execution_id):
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.RESULT_AVAILABLE,
                supervisor_pid=None,
                result_available=True,
                recovery_required=False,
            )

    supervised = RunningThenResult(repo, store)
    calls: list[str] = []

    class CountingGuard:
        def check(self):
            calls.append("guard")
            return PreDispatchGuardDecision(
                PreDispatchGuardDecisionKind.ALLOW, "PRE_DISPATCH_ALLOWED"
            )

    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        pre_dispatch_guard=CountingGuard(),
        pre_dispatch_guard_required=True,
        poll_interval_seconds=0.01,
    )
    first = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert first.kind is SupervisedRunOutcomeKind.FRESH
    launches = supervised.launch_calls
    assert calls == ["guard"]

    attach = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert attach.kind is SupervisedRunOutcomeKind.ATTACH_RUNNING
    assert supervised.launch_calls == launches
    assert calls == ["guard"]  # no second guard invocation on attach


def test_wo498_guard_configuration_leaves_fingerprint_bytes_unchanged(tmp_path):
    from a_conductor.pre_dispatch_guard import (
        PreDispatchGuardDecision,
        PreDispatchGuardDecisionKind,
    )

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    class AllowGuard:
        def check(self):
            return PreDispatchGuardDecision(
                PreDispatchGuardDecisionKind.ALLOW, "PRE_DISPATCH_ALLOWED"
            )

    plain = SupervisedRunCoordinator(
        execution_store=store,
        supervised=ScriptedSupervised(repo, store),
        identity=_identity(repo),
        poll_interval_seconds=0.01,
    )
    guarded = SupervisedRunCoordinator(
        execution_store=store,
        supervised=ScriptedSupervised(repo, store),
        identity=_identity(repo),
        pre_dispatch_guard=AllowGuard(),
        pre_dispatch_guard_required=True,
        poll_interval_seconds=0.01,
    )
    assert plain.fingerprint_for_argv(ARGV) == guarded.fingerprint_for_argv(ARGV)


def test_wo498_no_new_durable_authority_in_coordinator():
    """The guard seam adds no store/scheduler/lease registry surface."""
    import inspect

    from a_conductor import supervised_run_coordinator as module

    source = inspect.getsource(module)
    assert "SQLiteWorkerLeaseStore" not in source
    assert "create_table" not in source
    assert "CREATE INDEX" not in source
