from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from a_conductor.execution_deduplication import (
    DuplicateExecutionDecision,
    DuplicateExecutionGuard,
    ExecutionFingerprintSpec,
    compute_execution_fingerprint,
)
from a_conductor.execution_record import (
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import SQLiteExecutionStore


def spec(repo: Path, **overrides) -> ExecutionFingerprintSpec:
    values = dict(
        project_id="project-1",
        job_id="job-1",
        work_order_ref="docs/work-orders/WO-1.md",
        backend_id="native-local",
        repo_root=str(repo.resolve()),
        branch="main",
        head_before="a" * 40,
        operation_ref="op:pytest-focused",
        runtime_profile_ref="runtime:python-311",
        target_argv=("python.exe", "-m", "pytest", "-q", "tests/test_x.py"),
    )
    values.update(overrides)
    return ExecutionFingerprintSpec(**values)


def record_from_spec(
    fp_spec: ExecutionFingerprintSpec,
    *,
    execution_id: str,
    worker_id: str = "a-worker-01",
    state: ExecutionProcessState = ExecutionProcessState.RUNNING,
):
    return new_execution_record(
        execution_id=execution_id,
        job_id=fp_spec.job_id,
        work_order_ref=fp_spec.work_order_ref,
        project_id=fp_spec.project_id,
        worker_id=worker_id,
        backend_id=fp_spec.backend_id,
        agent_ref="agent:chatgpt",
        repo_root=fp_spec.repo_root,
        branch=fp_spec.branch,
        head_before=fp_spec.head_before,
        operation_ref=fp_spec.operation_ref,
        command_fingerprint=compute_execution_fingerprint(fp_spec),
        command_summary="focused pytest",
        runtime_profile_ref=fp_spec.runtime_profile_ref,
        run_dir_ref=f"runs/{execution_id}",
        stdout_ref=f"runs/{execution_id}/stdout.log",
        stderr_ref=f"runs/{execution_id}/stderr.log",
        result_ref=f"runs/{execution_id}/result.json",
        report_ref=None,
        transport_state=TransportState.CONNECTED,
        execution_state=state,
    )


def test_fingerprint_is_deterministic_and_worker_independent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    first = spec(repo)
    second = spec(repo)

    assert compute_execution_fingerprint(first) == compute_execution_fingerprint(second)
    assert len(compute_execution_fingerprint(first)) == 64
    assert not hasattr(first, "worker_id")


def test_fingerprint_changes_for_backend_runtime_head_operation_or_argv(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    base = spec(repo)
    base_fp = compute_execution_fingerprint(base)

    variants = (
        spec(repo, backend_id="other-backend"),
        spec(repo, runtime_profile_ref="runtime:other"),
        spec(repo, head_before="b" * 40),
        spec(repo, operation_ref="op:compileall"),
        spec(repo, target_argv=("python.exe", "-m", "compileall", "-q", "src")),
    )
    assert all(compute_execution_fingerprint(item) != base_fp for item in variants)


def test_fingerprint_spec_rejects_shell_like_or_multiline_invalid_argv(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    for argv in (
        (),
        ("",),
        ("python.exe", "bad\narg"),
        ("python.exe", "bad\x00arg"),
    ):
        try:
            spec(repo, target_argv=argv)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid argv accepted: {argv!r}")


def test_store_find_by_fingerprint_is_newest_first_and_read_only(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    fp_spec = spec(repo)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    first = store.create(record_from_spec(fp_spec, execution_id="exec-001"))
    second = store.create(record_from_spec(fp_spec, execution_id="exec-002"))
    before = {
        first.execution_id: (store.get(first.execution_id).version, len(store.list_events(first.execution_id))),
        second.execution_id: (store.get(second.execution_id).version, len(store.list_events(second.execution_id))),
    }

    found = store.find_by_fingerprint(compute_execution_fingerprint(fp_spec))

    assert [record.execution_id for record in found] == ["exec-002", "exec-001"]
    after = {
        first.execution_id: (store.get(first.execution_id).version, len(store.list_events(first.execution_id))),
        second.execution_id: (store.get(second.execution_id).version, len(store.list_events(second.execution_id))),
    }
    assert after == before


def test_no_match_is_safe_to_launch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    guard = DuplicateExecutionGuard(store=store)

    assessment = guard.assess(spec(repo))

    assert assessment.decision is DuplicateExecutionDecision.SAFE_TO_LAUNCH
    assert assessment.record is None
    assert assessment.retry_authorized is False


def test_live_equivalent_attaches_even_if_existing_worker_differs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    fp_spec = spec(repo)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    existing = store.create(
        record_from_spec(
            fp_spec,
            execution_id="exec-live",
            worker_id="a-worker-03",
            state=ExecutionProcessState.PROCESS_STILL_RUNNING,
        )
    )
    guard = DuplicateExecutionGuard(store=store)

    assessment = guard.assess(fp_spec)

    assert assessment.decision is DuplicateExecutionDecision.ATTACH_RUNNING
    assert assessment.record == existing
    assert assessment.retry_authorized is False


def test_completed_result_states_reuse_evidence_instead_of_rerun(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    for index, state in enumerate(
        (
            ExecutionProcessState.VERIFICATION_REQUIRED,
            ExecutionProcessState.SUCCEEDED,
            ExecutionProcessState.FAILED,
        ),
        start=1,
    ):
        case = tmp_path / f"case-{index}"
        case.mkdir()
        fp_spec = spec(repo, operation_ref=f"op:case-{index}")
        store = SQLiteExecutionStore(case / "control.sqlite")
        existing = store.create(record_from_spec(fp_spec, execution_id=f"exec-{index}", state=state))
        guard = DuplicateExecutionGuard(store=store)

        assessment = guard.assess(fp_spec)

        assert assessment.decision is DuplicateExecutionDecision.REUSE_COMPLETED
        assert assessment.record == existing
        assert assessment.retry_authorized is False


def test_partial_unknown_recovery_and_cancelled_states_block(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    states = (
        ExecutionProcessState.PROCESS_EXITED_UNKNOWN_RESULT,
        ExecutionProcessState.PARTIAL,
        ExecutionProcessState.RECOVERY_REQUIRED,
        ExecutionProcessState.CANCELLED,
    )
    for index, state in enumerate(states, start=1):
        case = tmp_path / f"blocked-{index}"
        case.mkdir()
        fp_spec = spec(repo, operation_ref=f"op:blocked-{index}")
        store = SQLiteExecutionStore(case / "control.sqlite")
        store.create(record_from_spec(fp_spec, execution_id=f"exec-blocked-{index}", state=state))
        assessment = DuplicateExecutionGuard(store=store).assess(fp_spec)
        assert assessment.decision is DuplicateExecutionDecision.BLOCKED_UNKNOWN
        assert assessment.retry_authorized is False


def test_hash_match_with_durable_identity_mismatch_blocks_instead_of_trusting_hash(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    requested = spec(repo)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    existing = record_from_spec(requested, execution_id="exec-corrupt")
    # Simulate corrupted/inconsistent persisted identity while retaining the
    # same hash. The guard must not treat the hash as authority.
    store.create(replace(existing, branch="other-branch"))

    assessment = DuplicateExecutionGuard(store=store).assess(requested)

    assert assessment.decision is DuplicateExecutionDecision.BLOCKED_UNKNOWN
    assert assessment.reason_code == "DUPLICATE_IDENTITY_MISMATCH"
    assert assessment.retry_authorized is False


def test_newest_equivalent_record_is_authoritative_for_duplicate_decision(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    fp_spec = spec(repo)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    store.create(record_from_spec(fp_spec, execution_id="exec-old", state=ExecutionProcessState.FAILED))
    newest = store.create(record_from_spec(fp_spec, execution_id="exec-new", state=ExecutionProcessState.RUNNING))

    assessment = DuplicateExecutionGuard(store=store).assess(fp_spec)

    assert assessment.decision is DuplicateExecutionDecision.ATTACH_RUNNING
    assert assessment.record == newest


def test_duplicate_guard_exposes_no_launch_retry_or_mutation_surface(tmp_path: Path) -> None:
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    guard = DuplicateExecutionGuard(store=store)
    for forbidden in (
        "launch",
        "relaunch",
        "retry",
        "execute",
        "reset",
        "clean",
        "checkout",
        "commit",
        "push",
        "route_worker",
    ):
        assert not hasattr(guard, forbidden)
