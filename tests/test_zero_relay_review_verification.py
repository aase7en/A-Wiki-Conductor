"""WO-P1-223 RE1 — verdict-blind reviewer execution verification (RED-first).

Closes the RE-1 production reachability gap: the accepted ZRA-1 supervised
transport durably lands every exit-0 reviewer run in ``VERIFICATION_REQUIRED``
while C1 acceptance eligibility requires ``SUCCEEDED``. The verifier proves
durable execution truth (exact runtime execution id, refs, complete
non-truncated stdout/report bytes, strict ``zcode-report/1`` schema, task
packet SHA, response byte count/hash, durable ``exit_code=0`` and source
state) and performs exactly ONE existing-store version-CAS promotion
``(VERIFICATION_REQUIRED, N) -> (SUCCEEDED, N+1)``.

It is verdict-blind: it never parses semantic verdicts and never creates
review evidence. No live provider, no new store/service/lifecycle authority.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from a_conductor.execution_record import (
    DurableExecutionRecord,
    ExecutionProcessState,
    TransportState,
)
from a_conductor.execution_store import ExecutionStoreError, SQLiteExecutionStore

# Module under test — the import error IS the pre-implementation RED.
from a_conductor.zero_relay_review_verification import (  # noqa: E402
    VerifiedReviewExecution,
    ZeroRelayReviewVerificationError,
    verify_review_execution_for_promotion,
)

TASK_SHA = "c" * 64
CONTRACT = "zra2-review-v1:" + "a" * 64
EXEC_ID = "exec-verify-0001"


def _record(
    *,
    execution_id: str = EXEC_ID,
    repo_root: str,
    state: ExecutionProcessState = ExecutionProcessState.VERIFICATION_REQUIRED,
    exit_code: int | None = 0,
    version: int = 1,
    stdout_ref: str | None | object = ...,
    report_ref: str | None | object = ...,
) -> DurableExecutionRecord:
    if stdout_ref is ...:
        stdout_ref = f"runs/{execution_id}/stdout.log"
    if report_ref is ...:
        report_ref = f"runs/{execution_id}/report.json"
    return DurableExecutionRecord(
        execution_id=execution_id,
        job_id=f"job:{CONTRACT}",
        work_order_ref=CONTRACT,
        project_id="zcode",
        worker_id="a-worker-01",
        backend_id="zcode-app-server",
        agent_ref="agent:zcode-app-server",
        repo_root=repo_root,
        branch="feat/wo-p1-223",
        head_before="a" * 40,
        operation_ref="zcode-task-v1:" + "5" * 64,
        command_fingerprint="4" * 64,
        command_summary="zcode reviewer turn",
        runtime_profile_ref="zcode-runtime-v1:" + "6" * 64,
        run_dir_ref=f"runs/{execution_id}",
        stdout_ref=stdout_ref,
        stderr_ref=f"runs/{execution_id}/stderr.log",
        result_ref=f"runs/{execution_id}/result.json",
        report_ref=report_ref,
        transport_state=TransportState.CONNECTED,
        execution_state=state,
        exit_code=exit_code,
        finished_at="2026-09-14T00:00:00Z",
        version=version,
    )


def _report_bytes(stdout: bytes, *, execution_id: str = EXEC_ID, **overrides) -> bytes:
    payload = {
        "schema": "zcode-report/1",
        "execution_id": execution_id,
        "task_packet_sha256": TASK_SHA,
        "response_bytes": len(stdout),
        "response_sha256": hashlib.sha256(stdout).hexdigest(),
        "session_id": "session-zcode-1",
    }
    payload.update(overrides)
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write_artifacts(
    root: Path,
    execution_id: str,
    *,
    stdout: bytes,
    report: bytes,
) -> None:
    run_dir = root / "runs" / execution_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stdout.log").write_bytes(stdout)
    (run_dir / "report.json").write_bytes(report)


class _Repo:
    """Real SQLite execution store + on-disk artifacts under one tmp root."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "repo"
        self.root.mkdir(parents=True, exist_ok=True)
        self.store = SQLiteExecutionStore(tmp_path / "exec.sqlite")

    def seed(
        self,
        *,
        state: ExecutionProcessState = ExecutionProcessState.VERIFICATION_REQUIRED,
        exit_code: int | None = 0,
        stdout: bytes = b'{"reviewer":"output"}',
        report: bytes | None = None,
        stdout_ref: str | None | object = ...,
    ) -> DurableExecutionRecord:
        """Create the record through the canonical store API, mirroring the
        accepted supervised collect semantics (result metadata before the
        terminal execution-state transition)."""
        created = self.store.create(
            _record(
                repo_root=str(self.root),
                state=ExecutionProcessState.RUNNING,
                stdout_ref=stdout_ref,
            )
        )
        with_result = self.store.set_result_metadata(
            created.execution_id,
            exit_code=exit_code if exit_code is not None else 0,
            finished_at="2026-09-14T00:00:00Z",
            expected_version=created.version,
        )
        final = self.store.set_execution_state(
            with_result.execution_id,
            state,
            expected_version=with_result.version,
        )
        if report is None:
            report = _report_bytes(stdout)
        _write_artifacts(self.root, EXEC_ID, stdout=stdout, report=report)
        return final


def _verify(store, record, *, task_sha: str = TASK_SHA, contract: str = CONTRACT):
    return verify_review_execution_for_promotion(
        execution_store=store,
        record=record,
        expected_task_packet_sha256=task_sha,
        expected_contract_ref=contract,
    )


# ── happy path: exact promotion (VERIFICATION_REQUIRED, N) -> (SUCCEEDED, N+1)


def test_exit_zero_verification_required_promotes_once_with_version_bump(tmp_path):
    repo = _Repo(tmp_path)
    seeded = repo.seed()
    assert seeded.execution_state is ExecutionProcessState.VERIFICATION_REQUIRED
    verified = _verify(repo.store, seeded)
    assert isinstance(verified, VerifiedReviewExecution)
    assert verified.promoted is True
    assert verified.record.execution_state is ExecutionProcessState.SUCCEEDED
    assert verified.record.version == seeded.version + 1
    assert verified.record.exit_code == 0
    # the durable store row itself is the promoted one
    reread = repo.store.get(seeded.execution_id)
    assert reread.execution_state is ExecutionProcessState.SUCCEEDED
    assert reread.version == seeded.version + 1
    # promotion wrote exactly one additional event carrying the evidence ref
    events = repo.store.list_events(seeded.execution_id)
    promotion_events = [e for e in events if e.evidence_ref is not None]
    assert len(promotion_events) == 1
    assert promotion_events[0].evidence_ref == (
        f"zra2-review-verification:{seeded.execution_id}"
    )
    assert promotion_events[0].execution_state is ExecutionProcessState.SUCCEEDED


def test_helper_report_without_contract_ref_and_inprocess_report_with_ref_both_pass(
    tmp_path,
):
    """The exact existing report vocabulary: the supervised-helper shape
    (no ``task_contract_ref``) and the in-process shape (with it, matching
    the trusted contract) both verify."""
    repo = _Repo(tmp_path)
    assert _verify(repo.store, repo.seed()).promoted is True

    repo2 = _Repo(tmp_path / "inproc")
    stdout = b'{"k":1}'
    seeded2 = repo2.seed(
        stdout=stdout,
        report=_report_bytes(
            stdout, task_contract_ref=CONTRACT, selection_sha256="7" * 64
        ),
    )
    assert _verify(repo2.store, seeded2).promoted is True


# ── already-SUCCEEDED replay: verification only, no mutation


def test_already_succeeded_replay_verifies_then_no_ops(tmp_path):
    repo = _Repo(tmp_path)
    seeded = repo.seed(state=ExecutionProcessState.SUCCEEDED)
    events_before = repo.store.list_events(seeded.execution_id)
    verified = _verify(repo.store, seeded)
    assert verified.promoted is False
    assert verified.record == seeded
    # zero new events, identical durable version: no mutation at all
    assert repo.store.list_events(seeded.execution_id) == events_before
    assert repo.store.get(seeded.execution_id).version == seeded.version


# ── invalid source states / nonzero exit fail closed with no promotion


@pytest.mark.parametrize(
    "state",
    [
        ExecutionProcessState.QUEUED,
        ExecutionProcessState.STARTING,
        ExecutionProcessState.RUNNING,
        ExecutionProcessState.PROCESS_STILL_RUNNING,
        ExecutionProcessState.PROCESS_EXITED_UNKNOWN_RESULT,
        ExecutionProcessState.FAILED,
        ExecutionProcessState.PARTIAL,
        ExecutionProcessState.CANCELLED,
        ExecutionProcessState.RECOVERY_REQUIRED,
    ],
)
def test_invalid_source_states_fail_closed_without_promotion(tmp_path, state):
    repo = _Repo(tmp_path)
    seeded = repo.seed(state=state)
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, seeded)
    assert exc.value.code == "REVIEW_VERIFICATION_SOURCE_STATE_INVALID"
    assert repo.store.get(seeded.execution_id).execution_state is state


def test_nonzero_exit_code_fails_closed_without_promotion(tmp_path):
    repo = _Repo(tmp_path)
    # a VR-shaped record with a nonzero durable exit contradicts exit-0 truth
    seeded = repo.seed(exit_code=3)
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, seeded)
    assert exc.value.code == "REVIEW_VERIFICATION_EXIT_NONZERO"
    assert (
        repo.store.get(seeded.execution_id).execution_state
        is ExecutionProcessState.VERIFICATION_REQUIRED
    )
    # a FAILED record is an invalid source state regardless of its exit
    repo2 = _Repo(tmp_path / "failed")
    failed = repo2.seed(exit_code=3, state=ExecutionProcessState.FAILED)
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo2.store, failed)
    assert exc.value.code == "REVIEW_VERIFICATION_SOURCE_STATE_INVALID"
    assert (
        repo2.store.get(failed.execution_id).execution_state
        is ExecutionProcessState.FAILED
    )


def test_missing_exit_code_fails_closed(tmp_path):
    repo = _Repo(tmp_path)
    stdout = b'{"reviewer":"output"}'
    created = repo.store.create(
        _record(
            repo_root=str(repo.root),
            state=ExecutionProcessState.RUNNING,
            exit_code=None,
        )
    )
    # terminal state reached WITHOUT any durable exit truth
    final = repo.store.set_execution_state(
        created.execution_id,
        ExecutionProcessState.VERIFICATION_REQUIRED,
        expected_version=created.version,
    )
    _write_artifacts(
        repo.root, EXEC_ID, stdout=stdout, report=_report_bytes(stdout)
    )
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, final)
    assert exc.value.code == "REVIEW_VERIFICATION_EXIT_NONZERO"


def test_missing_artifact_refs_fail_closed(tmp_path):
    repo = _Repo(tmp_path)
    seeded = repo.seed(stdout_ref=None)
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, seeded)
    assert exc.value.code == "REVIEW_VERIFICATION_ARTIFACT_REF_MISSING"
    assert (
        repo.store.get(seeded.execution_id).execution_state
        is ExecutionProcessState.VERIFICATION_REQUIRED
    )


# ── truncated / mismatched artifacts and reports fail closed


def test_stdout_larger_than_read_bound_fails_closed(tmp_path):
    """A whole-response capture that cannot fit the bounded artifact read is
    truncated evidence and fails closed (TOCTOU slice guard)."""
    from a_conductor.execution_artifacts import MAX_ARTIFACT_READ_BYTES

    repo = _Repo(tmp_path)
    stdout = b"x" * (MAX_ARTIFACT_READ_BYTES + 1)
    seeded = repo.seed(stdout=stdout)  # report matches the FULL bytes
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, seeded)
    assert exc.value.code == "REVIEW_STDOUT_SLICE_INVALID"
    assert (
        repo.store.get(seeded.execution_id).execution_state
        is ExecutionProcessState.VERIFICATION_REQUIRED
    )


def test_byte_tampered_stdout_fails_closed_on_report_binding(tmp_path):
    repo = _Repo(tmp_path)
    seeded = repo.seed()
    run_dir = repo.root / "runs" / EXEC_ID
    original = (run_dir / "stdout.log").read_bytes()
    (run_dir / "stdout.log").write_bytes(original + b"tail")
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, seeded)
    assert exc.value.code == "REVIEW_REPORT_RESPONSE_BYTES_MISMATCH"
    assert (
        repo.store.get(seeded.execution_id).execution_state
        is ExecutionProcessState.VERIFICATION_REQUIRED
    )


def test_missing_artifact_files_fail_closed(tmp_path):
    repo = _Repo(tmp_path)
    repo.seed()
    (repo.root / "runs" / EXEC_ID / "stdout.log").unlink()
    seeded = repo.store.get(EXEC_ID)
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, seeded)
    assert exc.value.code == "REVIEW_VERIFICATION_ARTIFACT_READ_FAILED"
    assert (
        repo.store.get(EXEC_ID).execution_state
        is ExecutionProcessState.VERIFICATION_REQUIRED
    )


def test_report_binding_mismatches_fail_closed_without_promotion(tmp_path):
    stdout = b'{"reviewer":"output"}'
    cases = [
        (_report_bytes(stdout, execution_id="exec-foreign"),
         "REVIEW_REPORT_EXECUTION_MISMATCH"),
        (_report_bytes(stdout, task_packet_sha256="9" * 64),
         "REVIEW_REPORT_TASK_SHA_MISMATCH"),
        (_report_bytes(stdout, task_contract_ref="zra2-review-v1:" + "f" * 64),
         "REVIEW_REPORT_CONTRACT_MISMATCH"),
        (_report_bytes(stdout, response_bytes=len(stdout) + 1),
         "REVIEW_REPORT_RESPONSE_BYTES_MISMATCH"),
        (_report_bytes(stdout, response_sha256="9" * 64),
         "REVIEW_REPORT_RESPONSE_SHA_MISMATCH"),
        (_report_bytes(stdout, exit_state="EXIT_PENDING"),
         "REVIEW_REPORT_EXIT_PENDING"),
        (_report_bytes(stdout, exit_state="WHATEVER"),
         "REVIEW_REPORT_EXIT_STATE_INVALID"),
        (_report_bytes(stdout, schema="zcode-report/2"),
         "REVIEW_REPORT_SCHEMA_MISMATCH"),
        (b"not-json", "REVIEW_REPORT_JSON_INVALID"),
        (
            b'{"schema":"zcode-report/1","schema":"zcode-report/1",'
            b'"execution_id":"' + EXEC_ID.encode("ascii")
            + b'","task_packet_sha256":"' + TASK_SHA.encode("ascii")
            + b'","response_bytes":' + str(len(stdout)).encode("ascii")
            + b',"response_sha256":"'
            + hashlib.sha256(stdout).hexdigest().encode("ascii")
            + b'","session_id":"s"}',
            "REVIEW_REPORT_DUPLICATE_KEY",
        ),
        (_report_bytes(stdout, ready=True), "REVIEW_REPORT_KEYS_INVALID"),
    ]
    for index, (report_bytes, code) in enumerate(cases):
        repo = _Repo(tmp_path / f"case-{index}")
        seeded = repo.seed(stdout=stdout, report=report_bytes)
        with pytest.raises(ZeroRelayReviewVerificationError) as exc:
            _verify(repo.store, seeded)
        assert exc.value.code == code, code
        assert (
            repo.store.get(seeded.execution_id).execution_state
            is ExecutionProcessState.VERIFICATION_REQUIRED
        ), code


def test_expected_task_sha_mismatch_fails_closed(tmp_path):
    repo = _Repo(tmp_path)
    seeded = repo.seed()
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, seeded, task_sha="d" * 64)
    assert exc.value.code == "REVIEW_REPORT_TASK_SHA_MISMATCH"


def test_invalid_expected_inputs_fail_closed(tmp_path):
    repo = _Repo(tmp_path)
    seeded = repo.seed()
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, seeded, task_sha="not-a-sha")
    assert exc.value.code == "REVIEW_VERIFICATION_EXPECTED_TASK_SHA_INVALID"
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, seeded, contract="  ")
    assert exc.value.code == "REVIEW_VERIFICATION_EXPECTED_CONTRACT_INVALID"
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, "not-a-record")
    assert exc.value.code == "REVIEW_VERIFICATION_RECORD_INVALID"
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(object(), seeded)
    assert exc.value.code == "REVIEW_VERIFICATION_STORE_INVALID"


# ── record drift / store faults


def test_record_drift_against_store_fails_closed(tmp_path):
    repo = _Repo(tmp_path)
    seeded = repo.seed()
    drifted = dataclasses.replace(seeded, version=seeded.version + 5)
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, drifted)
    assert exc.value.code == "REVIEW_VERIFICATION_RECORD_DRIFT"


def test_missing_execution_record_fails_closed(tmp_path):
    repo = _Repo(tmp_path)
    seeded = repo.seed()
    orphan = dataclasses.replace(seeded, execution_id="exec-never-created")
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(repo.store, orphan)
    assert exc.value.code == "REVIEW_VERIFICATION_RECORD_NOT_FOUND"


# ── CAS / version conflict fails closed


class _StoreFacade:
    """Real store behind a facade with a faulting promotion CAS."""

    def __init__(self, inner, *, fail_code: str | None = None,
                 lie: bool = False) -> None:
        self._inner = inner
        self._fail_code = fail_code
        self._lie = lie

    def get(self, execution_id: str):
        return self._inner.get(execution_id)

    def set_execution_state(self, execution_id, state, *, expected_version,
                            evidence_ref=None):
        if self._lie:
            return self._inner.get(execution_id)
        if self._fail_code is not None:
            raise ExecutionStoreError(self._fail_code)
        return self._inner.set_execution_state(
            execution_id, state,
            expected_version=expected_version, evidence_ref=evidence_ref,
        )


def test_cas_version_conflict_fails_closed(tmp_path):
    repo = _Repo(tmp_path)
    seeded = repo.seed()
    conflict = _StoreFacade(repo.store, fail_code="EXECUTION_VERSION_CONFLICT")
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(conflict, seeded)
    assert exc.value.code == "REVIEW_PROMOTION_VERSION_CONFLICT"
    # the real row was never promoted
    assert (
        repo.store.get(seeded.execution_id).execution_state
        is ExecutionProcessState.VERIFICATION_REQUIRED
    )


def test_promotion_store_fault_fails_closed(tmp_path):
    repo = _Repo(tmp_path)
    seeded = repo.seed()
    broken = _StoreFacade(repo.store, fail_code="EXECUTION_STORE_WRITE_FAILED")
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(broken, seeded)
    assert exc.value.code == "REVIEW_PROMOTION_FAILED"


def test_promotion_result_shape_lies_fail_closed(tmp_path):
    repo = _Repo(tmp_path)
    seeded = repo.seed()
    lying = _StoreFacade(repo.store, lie=True)
    with pytest.raises(ZeroRelayReviewVerificationError) as exc:
        _verify(lying, seeded)
    assert exc.value.code == "REVIEW_PROMOTION_RESULT_INVALID"


# ── verdict-blindness authority fence


def test_verifier_module_is_verdict_blind_and_adds_no_authority():
    import inspect
    from a_conductor import zero_relay_review_verification as module

    source = inspect.getsource(module)
    for banned in (
        "ReviewEvidence(",
        "from .zero_relay import",
        "ReviewDisposition",
        "ResultIdentity",
        "parse_review_v2_response",
        "ACCEPTED",
        "REJECTED",
        "ReviewBus",
        "mailbox",
        "agent_id",
        "a_wiki",
        "A_Wiki",
        "SQLiteExecutionStore(",
        "SQLiteJobStore(",
        "WorkerLeaseBroker(",
        "threading.Lock",
        "SELECT ",
        "ORDER BY rowid DESC",
        "LIMIT 1",
    ):
        assert banned not in source, banned


def test_verifier_reuses_the_accepted_c1_report_authority():
    """Report vocabulary and complete-slice verification are single-sourced
    from the accepted C1 module (exact same function objects), never
    re-implemented here."""
    from a_conductor import zero_relay_review_evidence as evidence
    from a_conductor import zero_relay_review_verification as verification

    assert verification._parse_zcode_report is evidence._parse_zcode_report
    assert verification._verify_complete_artifact is evidence._verify_complete_artifact


def test_exact_replay_is_deterministic(tmp_path):
    repo = _Repo(tmp_path)
    seeded = repo.seed()
    first = _verify(repo.store, seeded)
    second = _verify(repo.store, first.record)
    assert second.promoted is False
    assert second.record == first.record
