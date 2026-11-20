from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from a_conductor.execution_artifacts import ExecutionArtifactKind, ExecutionArtifactSlice
from a_conductor.execution_record import (
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.goal_closeout_assembly import ProductionCloseoutResult
from a_conductor.native_execution import NativeCommandResult
from a_conductor.supervised_run_coordinator import (
    SupervisedRunOutcome,
    SupervisedRunOutcomeKind,
)
from a_conductor.zero_relay import (
    RelayDecision,
    RelayOutcome,
    ResultIdentity,
    ReviewDisposition,
    ReviewEvidence,
)
from a_conductor.zero_relay_review_execution import DirectReviewExecutionHandoff
from a_conductor.zero_relay_review_task import DirectReviewRoute
from a_conductor.zero_relay_review_verification import VerifiedReviewExecution
from a_conductor.zero_relay_closeout import (
    ZeroRelayCloseoutError,
    compose_zero_relay_closeout,
)


TASK_SHA = "a" * 64
RESULT_SHA = "b" * 64
HEAD = "c" * 40
ATTEMPT = "author-attempt-v1:" + "1" * 32
RESULT_REF = "runs/exec-author/result.json"


def _native(*, exit_code=0, timed_out=False, stderr=""):
    empty = hashlib.sha256(b"").hexdigest()
    return NativeCommandResult(
        executable="ZCode.exe",
        argument_count=6,
        exit_code=exit_code,
        timed_out=timed_out,
        stdout="",
        stderr=stderr,
        stdout_sha256=empty,
        stderr_sha256=hashlib.sha256(stderr.encode()).hexdigest(),
        stdout_truncated=False,
        stderr_truncated=False,
    )


def _route(*, reviewed_head=HEAD):
    return DirectReviewRoute(
        role="independent-review",
        mutation_intent="READ_ONLY",
        review_contract_ref="review-contract",
        review_task_path="runs/review/task.md",
        review_task_sha256="d" * 64,
        review_result_ref="runs/review/result.json",
        author_execution_id="exec-author",
        author_result_sha256=RESULT_SHA,
        author_attempt_id=ATTEMPT,
        author_generation=0,
        author_digest="e" * 64,
        reviewer_worker_id="worker-review",
        dispatch_execution_id="dispatch-review",
        provider_id="cointh-glm",
        model_id="glm-5.3",
        project_id="project-1",
        worktree="A:/repo",
        branch="main",
        reviewed_head=reviewed_head,
    )


def _handoff(*, head=HEAD):
    return DirectReviewExecutionHandoff(
        review_contract_ref="review-contract",
        dispatch_execution_id="dispatch-review",
        runtime_execution_id="exec-review",
        supervised_job_id="job-review",
        fingerprint="f" * 64,
        record_version=1,
        record_state="SUCCEEDED",
        stdout_ref="runs/exec-review/stdout.log",
        stderr_ref="runs/exec-review/stderr.log",
        result_ref="runs/exec-review/result.json",
        report_ref="runs/exec-review/report.json",
        task_packet_path="runs/review/task.md",
        task_packet_sha256="d" * 64,
        provider_id="cointh-glm",
        model_id="glm-5.3",
        project_id="project-1",
        worker_id="worker-review",
        repo_root="A:/repo",
        branch="main",
        head=head,
        admission_id="admission-1",
        admission_batch_id="batch-1",
        admission_status="RELEASED",
        lease_id="lease-review",
        lease_session_id="session-review",
        lease_task_id="review-task",
        lease_released=True,
        cleanup_terminal=True,
        exit_code=0,
        outcome="SUCCEEDED",
    )


class _Facade:
    def __init__(self):
        self.calls: list[str] = []
        self._candidate_sha = HEAD

    def next_stage(self, job_id: str):
        self.calls.append(job_id)
        return ProductionCloseoutResult("VERIFY_CHECKPOINT", "CHECKPOINTED", "ok")


def test_nonaccepted_author_outcome_never_reaches_closeout():
    facade = _Facade()
    outcome = SupervisedRunOutcome(
        kind=SupervisedRunOutcomeKind.TIMED_OUT,
        execution_id="exec-author",
        native=_native(exit_code=None, timed_out=True),
    )

    with pytest.raises(ZeroRelayCloseoutError) as exc:
        compose_zero_relay_closeout(
            author_outcome=outcome,
            execution_store=object(),
            expected_task_contract_ref="WO-P1-205",
            expected_task_sha256=TASK_SHA,
            expected_author_worker_id="worker-1",
            review_route=_route(),
            review_handoff=_handoff(),
            expected_candidate_sha=HEAD,
            closeout_facade=facade,
            job_id="job-1",
        )

    assert exc.value.code == "AUTHOR_EXECUTION_NOT_ACCEPTABLE"
    assert facade.calls == []


def test_candidate_drift_blocks_before_store_or_closeout():
    facade = _Facade()
    outcome = SupervisedRunOutcome(
        kind=SupervisedRunOutcomeKind.FRESH,
        execution_id="exec-author",
        native=_native(),
    )

    with pytest.raises(ZeroRelayCloseoutError) as exc:
        compose_zero_relay_closeout(
            author_outcome=outcome,
            execution_store=object(),
            expected_task_contract_ref="WO-P1-205",
            expected_task_sha256=TASK_SHA,
            expected_author_worker_id="worker-1",
            review_route=_route(reviewed_head="9" * 40),
            review_handoff=_handoff(),
            expected_candidate_sha=HEAD,
            closeout_facade=facade,
            job_id="job-1",
        )

    assert exc.value.code == "CANDIDATE_SHA_MISMATCH"
    assert facade.calls == []


def test_accepted_flow_uses_existing_authorities_and_calls_one_facade_stage(monkeypatch):
    import a_conductor.zero_relay_closeout as module

    facade = _Facade()
    outcome = SupervisedRunOutcome(
        kind=SupervisedRunOutcomeKind.FRESH,
        execution_id="exec-author",
        native=_native(),
    )
    record = new_execution_record(
        execution_id="exec-author",
        job_id="job-1",
        work_order_ref="WO-P1-205",
        project_id="project-1",
        worker_id="worker-1",
        backend_id="zcode-app-server",
        agent_ref="agent:zcode-app-server",
        repo_root="A:/repo",
        branch="main",
        head_before=HEAD,
        operation_ref="zcode-task-v1:" + TASK_SHA,
        command_fingerprint="1" * 64,
        command_summary="zcode",
        runtime_profile_ref="runtime:zcode",
        run_dir_ref="runs/exec-author",
        stdout_ref="runs/exec-author/stdout.log",
        stderr_ref="runs/exec-author/stderr.log",
        result_ref=RESULT_REF,
        report_ref="runs/exec-author/report.json",
        transport_state=TransportState.CONNECTED,
        execution_state=ExecutionProcessState.VERIFICATION_REQUIRED,
        author_attempt_id=ATTEMPT,
        author_generation=0,
    )
    promoted = replace(record, execution_state=ExecutionProcessState.SUCCEEDED, version=record.version + 1)
    raw = json.dumps(
        {
            "schema_version": 1,
            "execution_id": "exec-author",
            "child_pid": 123,
            "exit_code": 0,
            "started_at": "2026-09-21T00:00:00+00:00",
            "finished_at": "2026-09-21T00:00:01+00:00",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    artifact = ExecutionArtifactSlice(
        execution_id="exec-author",
        kind=ExecutionArtifactKind.RESULT,
        artifact_ref=RESULT_REF,
        total_bytes=len(raw),
        offset=0,
        returned_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
        raw=raw,
        text=raw.decode(),
        truncated=False,
    )
    identity = ResultIdentity(
        task_contract_ref="WO-P1-205",
        task_sha256=TASK_SHA,
        result_ref=RESULT_REF,
        result_sha256=artifact.sha256,
        attempt_id=ATTEMPT,
        generation=0,
        author_execution_id="exec-author",
    )
    review = ReviewEvidence(
        task_contract_ref=identity.task_contract_ref,
        task_sha256=identity.task_sha256,
        result_ref=identity.result_ref,
        result_sha256=identity.result_sha256,
        attempt_id=identity.attempt_id,
        generation=identity.generation,
        reviewer_execution_id="exec-review",
        disposition=ReviewDisposition.ACCEPTED,
    )

    class Store:
        def get(self, execution_id):
            assert execution_id == "exec-author"
            return record

    class Artifacts:
        def __init__(self, *, store):
            assert isinstance(store, Store)

        def read_chunk(self, execution_id, kind, *, offset, max_bytes):
            assert execution_id == "exec-author"
            assert kind is ExecutionArtifactKind.RESULT
            assert offset == 0
            return artifact

    monkeypatch.setattr(module, "ExecutionArtifactService", Artifacts)
    monkeypatch.setattr(
        module,
        "verify_review_execution_for_promotion",
        lambda **kwargs: VerifiedReviewExecution(record=promoted, promoted=True),
    )
    monkeypatch.setattr(module, "compose_result_identity", lambda **kwargs: identity)
    monkeypatch.setattr(
        module,
        "compose_direct_review_evidence_from_store",
        lambda **kwargs: review,
    )
    monkeypatch.setattr(
        module,
        "classify_relay_decision",
        lambda *args, **kwargs: RelayOutcome(RelayDecision.ACCEPTED, None),
    )

    result = compose_zero_relay_closeout(
        author_outcome=outcome,
        execution_store=Store(),
        expected_task_contract_ref="WO-P1-205",
        expected_task_sha256=TASK_SHA,
        expected_author_worker_id="worker-1",
        review_route=_route(),
        review_handoff=_handoff(),
        expected_candidate_sha=HEAD,
        closeout_facade=facade,
        job_id="job-1",
    )

    assert result.result_identity == identity
    assert result.review_evidence == review
    assert result.relay_outcome.decision is RelayDecision.ACCEPTED
    assert result.closeout_result.stage == "VERIFY_CHECKPOINT"
    assert facade.calls == ["job-1"]


def test_rejected_review_never_reaches_closeout(monkeypatch):
    import a_conductor.zero_relay_closeout as module

    facade = _Facade()
    outcome = SupervisedRunOutcome(
        kind=SupervisedRunOutcomeKind.FRESH,
        execution_id="exec-author",
        native=_native(),
    )

    class Store:
        def get(self, execution_id):
            return object()

    # Candidate binding must pass, but a non-ACCEPTED relay decision is terminal
    # before the existing closeout facade can mutate anything.
    identity = ResultIdentity(
        task_contract_ref="WO-P1-205",
        task_sha256=TASK_SHA,
        result_ref=RESULT_REF,
        result_sha256=RESULT_SHA,
        attempt_id=ATTEMPT,
        generation=0,
        author_execution_id="exec-author",
    )
    monkeypatch.setattr(
        module,
        "_compose_author_and_review",
        lambda **kwargs: (
            identity,
            _accepted_review_for(identity),
            RelayOutcome(RelayDecision.REJECTED, None),
        ),
    )

    with pytest.raises(ZeroRelayCloseoutError) as exc:
        compose_zero_relay_closeout(
            author_outcome=outcome,
            execution_store=Store(),
            expected_task_contract_ref="WO-P1-205",
            expected_task_sha256=TASK_SHA,
            expected_author_worker_id="worker-1",
            review_route=_route(),
            review_handoff=_handoff(),
            expected_candidate_sha=HEAD,
            closeout_facade=facade,
            job_id="job-1",
        )

    assert exc.value.code == "RELAY_NOT_ACCEPTED"
    assert facade.calls == []


def test_review_handoff_candidate_drift_blocks_before_store_or_closeout():
    facade = _Facade()
    outcome = SupervisedRunOutcome(
        kind=SupervisedRunOutcomeKind.FRESH,
        execution_id="exec-author",
        native=_native(),
    )

    with pytest.raises(ZeroRelayCloseoutError) as exc:
        compose_zero_relay_closeout(
            author_outcome=outcome,
            execution_store=object(),
            expected_task_contract_ref="WO-P1-205",
            expected_task_sha256=TASK_SHA,
            expected_author_worker_id="worker-1",
            review_route=_route(),
            review_handoff=_handoff(head="9" * 40),
            expected_candidate_sha=HEAD,
            closeout_facade=facade,
            job_id="job-1",
        )

    assert exc.value.code == "REVIEW_HANDOFF_CANDIDATE_SHA_MISMATCH"
    assert facade.calls == []


def test_foreign_author_worker_fails_before_promotion_or_closeout(monkeypatch):
    import a_conductor.zero_relay_closeout as module

    facade = _Facade()
    outcome = SupervisedRunOutcome(
        kind=SupervisedRunOutcomeKind.FRESH,
        execution_id="exec-author",
        native=_native(),
    )
    record = new_execution_record(
        execution_id="exec-author",
        job_id="job-1",
        work_order_ref="WO-P1-205",
        project_id="project-1",
        worker_id="foreign-worker",
        backend_id="zcode-app-server",
        agent_ref="agent:zcode-app-server",
        repo_root="A:/repo",
        branch="main",
        head_before=HEAD,
        operation_ref="zcode-task-v1:" + TASK_SHA,
        command_fingerprint="1" * 64,
        command_summary="zcode",
        runtime_profile_ref="runtime:zcode",
        run_dir_ref="runs/exec-author",
        stdout_ref="runs/exec-author/stdout.log",
        stderr_ref="runs/exec-author/stderr.log",
        result_ref=RESULT_REF,
        report_ref="runs/exec-author/report.json",
        transport_state=TransportState.CONNECTED,
        execution_state=ExecutionProcessState.VERIFICATION_REQUIRED,
        author_attempt_id=ATTEMPT,
        author_generation=0,
    )

    class Store:
        def get(self, execution_id):
            assert execution_id == "exec-author"
            return record

    def _unexpected_promotion(**_kwargs):
        raise AssertionError("foreign author worker reached promotion authority")

    monkeypatch.setattr(module, "verify_review_execution_for_promotion", _unexpected_promotion)

    with pytest.raises(ZeroRelayCloseoutError) as exc:
        compose_zero_relay_closeout(
            author_outcome=outcome,
            execution_store=Store(),
            expected_task_contract_ref="WO-P1-205",
            expected_task_sha256=TASK_SHA,
            expected_author_worker_id="worker-1",
            review_route=_route(),
            review_handoff=_handoff(),
            expected_candidate_sha=HEAD,
            closeout_facade=facade,
            job_id="job-1",
        )

    assert exc.value.code == "AUTHOR_EXECUTION_IDENTITY_MISMATCH"
    assert facade.calls == []


def _seed_real_author_store(tmp_path, *, result_execution_id="exec-author", generation=0):
    repo = tmp_path / "repo"
    run_dir = repo / "runs" / "exec-author"
    run_dir.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "execution.sqlite")
    record = new_execution_record(
        execution_id="exec-author",
        job_id="job-1",
        work_order_ref="WO-P1-205",
        project_id="project-1",
        worker_id="worker-1",
        backend_id="zcode-app-server",
        agent_ref="agent:zcode-app-server",
        repo_root=str(repo),
        branch="main",
        head_before=HEAD,
        operation_ref="zcode-task-v1:" + TASK_SHA,
        command_fingerprint="1" * 64,
        command_summary="zcode",
        runtime_profile_ref="runtime:zcode",
        run_dir_ref="runs/exec-author",
        stdout_ref="runs/exec-author/stdout.log",
        stderr_ref="runs/exec-author/stderr.log",
        result_ref=RESULT_REF,
        report_ref="runs/exec-author/report.json",
        transport_state=TransportState.CONNECTED,
        execution_state=ExecutionProcessState.RUNNING,
        author_attempt_id=ATTEMPT,
        author_generation=generation,
    )
    created = store.create(record)
    with_result = store.set_result_metadata(
        created.execution_id,
        exit_code=0,
        finished_at="2026-09-21T00:00:01+00:00",
        expected_version=created.version,
    )
    ready = store.set_execution_state(
        with_result.execution_id,
        ExecutionProcessState.VERIFICATION_REQUIRED,
        expected_version=with_result.version,
    )
    stdout = b"author-output"
    report_raw = json.dumps(
        {
            "schema": "zcode-report/1",
            "execution_id": "exec-author",
            "task_packet_sha256": TASK_SHA,
            "response_bytes": len(stdout),
            "response_sha256": hashlib.sha256(stdout).hexdigest(),
            "session_id": "session-author-1",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    result_raw = json.dumps(
        {
            "schema_version": 1,
            "execution_id": result_execution_id,
            "child_pid": 123,
            "exit_code": 0,
            "started_at": "2026-09-21T00:00:00+00:00",
            "finished_at": "2026-09-21T00:00:01+00:00",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    (run_dir / "stdout.log").write_bytes(stdout)
    (run_dir / "report.json").write_bytes(report_raw)
    (run_dir / "result.json").write_bytes(result_raw)
    return store, ready, result_raw


def _accepted_review_for(author):
    return ReviewEvidence(
        task_contract_ref=author.task_contract_ref,
        task_sha256=author.task_sha256,
        result_ref=author.result_ref,
        result_sha256=author.result_sha256,
        attempt_id=author.attempt_id,
        generation=author.generation,
        reviewer_execution_id="exec-review",
        disposition=ReviewDisposition.ACCEPTED,
    )


def test_real_store_promotes_verified_author_and_hashes_exact_result(monkeypatch, tmp_path):
    import a_conductor.zero_relay_closeout as module

    store, ready, result_raw = _seed_real_author_store(tmp_path)
    facade = _Facade()
    monkeypatch.setattr(
        module,
        "compose_direct_review_evidence_from_store",
        lambda *, author, **_kwargs: _accepted_review_for(author),
    )

    result = compose_zero_relay_closeout(
        author_outcome=SupervisedRunOutcome(
            kind=SupervisedRunOutcomeKind.FRESH,
            execution_id="exec-author",
            native=_native(),
        ),
        execution_store=store,
        expected_task_contract_ref="WO-P1-205",
        expected_task_sha256=TASK_SHA,
        expected_author_worker_id="worker-1",
        review_route=_route(),
        review_handoff=_handoff(),
        expected_candidate_sha=HEAD,
        closeout_facade=facade,
        job_id="job-1",
    )

    promoted = store.get("exec-author")
    assert ready.execution_state is ExecutionProcessState.VERIFICATION_REQUIRED
    assert promoted.execution_state is ExecutionProcessState.SUCCEEDED
    assert promoted.version == ready.version + 1
    assert result.result_identity.result_sha256 == hashlib.sha256(result_raw).hexdigest()
    assert result.result_identity.author_execution_id == "exec-author"
    assert result.relay_outcome.decision is RelayDecision.ACCEPTED
    assert facade.calls == ["job-1"]


def test_foreign_result_identity_fails_before_author_promotion(monkeypatch, tmp_path):
    import a_conductor.zero_relay_closeout as module

    store, ready, _ = _seed_real_author_store(
        tmp_path,
        result_execution_id="exec-foreign",
    )
    facade = _Facade()
    monkeypatch.setattr(
        module,
        "compose_direct_review_evidence_from_store",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("foreign result reached review composition")
        ),
    )

    with pytest.raises(ZeroRelayCloseoutError) as exc:
        compose_zero_relay_closeout(
            author_outcome=SupervisedRunOutcome(
                kind=SupervisedRunOutcomeKind.FRESH,
                execution_id="exec-author",
                native=_native(),
            ),
            execution_store=store,
            expected_task_contract_ref="WO-P1-205",
            expected_task_sha256=TASK_SHA,
            expected_author_worker_id="worker-1",
            review_route=_route(),
            review_handoff=_handoff(),
            expected_candidate_sha=HEAD,
            closeout_facade=facade,
            job_id="job-1",
        )

    assert exc.value.code == "AUTHOR_RESULT_EXECUTION_MISMATCH"
    assert store.get("exec-author").execution_state is ExecutionProcessState.VERIFICATION_REQUIRED
    assert store.get("exec-author").version == ready.version
    assert facade.calls == []


def test_generation1_fails_closed_without_repair_lineage_authority(monkeypatch):
    import a_conductor.zero_relay_closeout as module

    facade = _Facade()
    identity = ResultIdentity(
        task_contract_ref="WO-P1-205",
        task_sha256=TASK_SHA,
        result_ref=RESULT_REF,
        result_sha256=RESULT_SHA,
        attempt_id=ATTEMPT,
        generation=1,
        author_execution_id="exec-author",
    )
    review = _accepted_review_for(identity)
    monkeypatch.setattr(
        module,
        "_compose_author_and_review",
        lambda **_kwargs: (
            identity,
            review,
            RelayOutcome(RelayDecision.ACCEPTED, None),
        ),
    )

    with pytest.raises(ZeroRelayCloseoutError) as exc:
        compose_zero_relay_closeout(
            author_outcome=SupervisedRunOutcome(
                kind=SupervisedRunOutcomeKind.FRESH,
                execution_id="exec-author",
                native=_native(),
            ),
            execution_store=object(),
            expected_task_contract_ref="WO-P1-205",
            expected_task_sha256=TASK_SHA,
            expected_author_worker_id="worker-1",
            review_route=_route(),
            review_handoff=_handoff(),
            expected_candidate_sha=HEAD,
            closeout_facade=facade,
            job_id="job-1",
        )

    assert exc.value.code == "AUTHOR_REPAIR_LINEAGE_UNAVAILABLE"
    assert facade.calls == []
