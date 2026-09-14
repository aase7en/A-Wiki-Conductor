from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from a_conductor.execution_artifacts import ExecutionArtifactKind, ExecutionArtifactSlice
from a_conductor.execution_record import DurableExecutionRecord, ExecutionProcessState, TransportState
from a_conductor.zero_relay import ResultIdentity, ReviewDisposition, ReviewEvidence
from a_conductor.zero_relay_review_execution import DirectReviewExecutionHandoff
from a_conductor.zero_relay_review_task import DirectReviewRoute, DirectReviewV2Route
from a_conductor.zero_relay_review_evidence import (
    ZeroRelayReviewEvidenceError,
    compose_direct_review_evidence,
    compose_direct_review_evidence_from_store,
    parse_review_v2_response,
)

CONTRACT = "runs/zra2-review-v2-" + "a" * 64 + ".task.json"
HEAD = "b" * 40
TASK_SHA = "c" * 64


def _raw(**overrides) -> bytes:
    payload = {
        "schema": "zra2-review-result-v2",
        "review_contract_ref": CONTRACT,
        "reviewed_head": HEAD,
        "review_task_sha256": TASK_SHA,
        "verdict": "ACCEPTED",
        "findings": [],
    }
    payload.update(overrides)
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _parse(raw: bytes):
    return parse_review_v2_response(
        raw,
        expected_contract_ref=CONTRACT,
        expected_reviewed_head=HEAD,
        expected_review_task_sha256=TASK_SHA,
    )


def test_exact_accepted_response_validates() -> None:
    result = _parse(_raw())
    assert result.review_contract_ref == CONTRACT
    assert result.reviewed_head == HEAD
    assert result.review_task_sha256 == TASK_SHA
    assert result.disposition is ReviewDisposition.ACCEPTED
    assert result.findings == ()


def test_exact_rejected_response_preserves_bounded_findings() -> None:
    result = _parse(_raw(verdict="REJECTED", findings=["P1: stale identity", "P2: malformed report"]))
    assert result.disposition is ReviewDisposition.REJECTED
    assert result.findings == ("P1: stale identity", "P2: malformed report")


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b"not-json", "REVIEW_RESULT_JSON_INVALID"),
        (b"[]", "REVIEW_RESULT_ROOT_INVALID"),
        (b"\xff", "REVIEW_RESULT_UTF8_INVALID"),
        (_raw(verdict="PASS"), "REVIEW_RESULT_VERDICT_INVALID"),
        (_raw(schema="zra2-review-result-v1"), "REVIEW_RESULT_SCHEMA_MISMATCH"),
        (_raw(review_contract_ref="runs/other.task.json"), "REVIEW_RESULT_CONTRACT_MISMATCH"),
        (_raw(reviewed_head="d" * 40), "REVIEW_RESULT_HEAD_MISMATCH"),
        (_raw(review_task_sha256="e" * 64), "REVIEW_RESULT_TASK_SHA_MISMATCH"),
    ],
)
def test_invalid_or_rebound_response_fails_closed(raw: bytes, code: str) -> None:
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _parse(raw)
    assert exc.value.code == code


def test_duplicate_json_key_is_rejected() -> None:
    raw = (
        '{"schema":"zra2-review-result-v2","review_contract_ref":"' + CONTRACT +
        '","reviewed_head":"' + HEAD + '","review_task_sha256":"' + TASK_SHA +
        '","verdict":"ACCEPTED","verdict":"REJECTED","findings":[]}'
    ).encode("utf-8")
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _parse(raw)
    assert exc.value.code == "REVIEW_RESULT_DUPLICATE_KEY"


def test_prefix_suffix_or_markdown_fence_is_rejected() -> None:
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _parse(b"```json\n" + _raw() + b"\n```")
    assert exc.value.code == "REVIEW_RESULT_JSON_INVALID"


def test_unknown_authority_like_field_is_rejected() -> None:
    raw = json.loads(_raw().decode("utf-8"))
    raw["ready"] = True
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _parse(json.dumps(raw).encode("utf-8"))
    assert exc.value.code == "REVIEW_RESULT_KEYS_INVALID"


def test_response_size_and_findings_are_bounded() -> None:
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _parse(_raw(findings=["x" * 40000]))
    assert exc.value.code == "REVIEW_RESULT_TOO_LARGE"

    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _parse(_raw(findings=["x"] * 65))
    assert exc.value.code == "REVIEW_RESULT_FINDINGS_INVALID"

    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _parse(_raw(findings=["x" * 2049]))
    assert exc.value.code == "REVIEW_RESULT_FINDINGS_INVALID"



def test_nonstandard_json_constants_and_surrogates_fail_closed() -> None:
    nan_raw = (
        '{"schema":"zra2-review-result-v2","review_contract_ref":"' + CONTRACT +
        '","reviewed_head":"' + HEAD + '","review_task_sha256":"' + TASK_SHA +
        '","verdict":"ACCEPTED","findings":[NaN]}'
    ).encode("utf-8")
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _parse(nan_raw)
    assert exc.value.code == "REVIEW_RESULT_JSON_INVALID"

    surrogate = _raw(findings=["\ud800 escaped surrogate"])
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _parse(surrogate)
    assert exc.value.code == "REVIEW_RESULT_FINDINGS_INVALID"


def test_validated_parser_result_type_is_not_public_constructor_surface() -> None:
    import a_conductor.zero_relay_review_evidence as module
    assert not hasattr(module, "ValidatedDirectReviewResult")

def test_identical_replay_is_deterministic() -> None:
    raw = _raw(verdict="REJECTED", findings=["one"])
    assert _parse(raw) == _parse(raw)


AUTHOR = ResultIdentity(
    task_contract_ref="work-order:author", task_sha256="1" * 64,
    result_ref="runs/author/result.json", result_sha256="2" * 64,
    attempt_id="attempt-1", generation=0, author_execution_id="exec-author",
)
RUNTIME_EXEC = "exec-review-runtime"
DISPATCH_EXEC = "graph-dispatch-review"
WORKTREE = "A:/GitHub/_worktrees/review"
BRANCH = "feat/review"


def _route() -> DirectReviewRoute:
    return DirectReviewV2Route(
        role="independent-review", mutation_intent="READ_ONLY",
        review_contract_ref=CONTRACT, review_task_path=f"{WORKTREE}/runs/review.md",
        review_task_sha256=TASK_SHA, review_result_ref="runs/review-result.json",
        author_execution_id=AUTHOR.author_execution_id, author_result_sha256=AUTHOR.result_sha256,
        author_attempt_id=AUTHOR.attempt_id, author_generation=AUTHOR.generation,
        author_digest="3" * 64, reviewer_worker_id="reviewer-1",
        dispatch_execution_id=DISPATCH_EXEC, provider_id="cointh-glm", model_id="glm-5.3",
        project_id="a-sunday-conductor", worktree=WORKTREE, branch=BRANCH, reviewed_head=HEAD,
        author_task_contract_ref=AUTHOR.task_contract_ref,
        author_task_sha256=AUTHOR.task_sha256,
        author_result_ref=AUTHOR.result_ref,
    )


def _handoff(**overrides) -> DirectReviewExecutionHandoff:
    values = dict(
        review_contract_ref=CONTRACT, dispatch_execution_id=DISPATCH_EXEC,
        runtime_execution_id=RUNTIME_EXEC, supervised_job_id=f"job:{CONTRACT}",
        fingerprint="4" * 64, record_version=7, record_state="SUCCEEDED",
        stdout_ref=f"runs/{RUNTIME_EXEC}/stdout.log", stderr_ref=f"runs/{RUNTIME_EXEC}/stderr.log",
        result_ref=f"runs/{RUNTIME_EXEC}/result.json", report_ref=f"runs/{RUNTIME_EXEC}/report.json",
        task_packet_path=f"{WORKTREE}/runs/review.md", task_packet_sha256=TASK_SHA,
        provider_id="cointh-glm", model_id="glm-5.3", project_id="a-sunday-conductor",
        worker_id="reviewer-1", repo_root=WORKTREE, branch=BRANCH, head=HEAD,
        admission_id="admission-1", admission_batch_id="batch-1", admission_status="RELEASED",
        lease_id="lease-1", lease_session_id="lease-session-1", lease_task_id=CONTRACT,
        lease_released=True, cleanup_terminal=True, exit_code=0, outcome="EXECUTED",
    )
    values.update(overrides)
    return DirectReviewExecutionHandoff(**values)


def _record(**overrides) -> DurableExecutionRecord:
    values = dict(
        execution_id=RUNTIME_EXEC, job_id=f"job:{CONTRACT}", work_order_ref=CONTRACT,
        project_id="a-sunday-conductor", worker_id="reviewer-1", backend_id="zcode-app-server",
        agent_ref="agent:zcode-app-server", repo_root=WORKTREE, branch=BRANCH, head_before=HEAD,
        operation_ref="zcode-task-v1:" + "5" * 64, command_fingerprint="4" * 64,
        command_summary="zcode independent review", runtime_profile_ref="runtime:review",
        run_dir_ref=f"runs/{RUNTIME_EXEC}", stdout_ref=f"runs/{RUNTIME_EXEC}/stdout.log",
        stderr_ref=f"runs/{RUNTIME_EXEC}/stderr.log", result_ref=f"runs/{RUNTIME_EXEC}/result.json",
        report_ref=f"runs/{RUNTIME_EXEC}/report.json", transport_state=TransportState.CONNECTED,
        execution_state=ExecutionProcessState.SUCCEEDED, exit_code=0, version=7,
    )
    values.update(overrides)
    return DurableExecutionRecord(**values)


def _slice(kind: ExecutionArtifactKind, raw: bytes, *, ref: str, **overrides) -> ExecutionArtifactSlice:
    values = dict(
        execution_id=RUNTIME_EXEC, kind=kind, artifact_ref=ref, total_bytes=len(raw),
        offset=0, returned_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), raw=raw,
        text=raw.decode("utf-8", errors="replace"), truncated=False,
    )
    values.update(overrides)
    return ExecutionArtifactSlice(**values)


def _report(stdout_raw: bytes, **overrides) -> bytes:
    payload = {
        "schema": "zcode-report/1", "execution_id": RUNTIME_EXEC,
        "task_packet_sha256": TASK_SHA, "response_bytes": len(stdout_raw),
        "response_sha256": hashlib.sha256(stdout_raw).hexdigest(), "session_id": "session-zcode-1",
    }
    payload.update(overrides)
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _compose(*, response=None, report=None, record=None, handoff=None, route=None):
    response = _raw() if response is None else response
    report = _report(response) if report is None else report
    rec = _record() if record is None else record
    ho = _handoff() if handoff is None else handoff
    rt = _route() if route is None else route
    return compose_direct_review_evidence(
        author=AUTHOR, route=rt, handoff=ho, record=rec,
        stdout=_slice(ExecutionArtifactKind.STDOUT, response, ref=rec.stdout_ref),
        report=_slice(ExecutionArtifactKind.REPORT, report, ref=rec.report_ref),
    )


def test_compose_exact_durable_review_evidence() -> None:
    evidence = _compose()
    assert evidence == ReviewEvidence(
        task_contract_ref=AUTHOR.task_contract_ref, task_sha256=AUTHOR.task_sha256,
        result_ref=AUTHOR.result_ref, result_sha256=AUTHOR.result_sha256,
        attempt_id=AUTHOR.attempt_id, generation=AUTHOR.generation,
        reviewer_execution_id=RUNTIME_EXEC, disposition=ReviewDisposition.ACCEPTED,
    )


def test_dispatch_and_runtime_execution_ids_remain_distinct() -> None:
    assert DISPATCH_EXEC != RUNTIME_EXEC
    assert _compose().reviewer_execution_id == RUNTIME_EXEC


@pytest.mark.parametrize(
    ("record", "handoff", "code"),
    [
        (_record(execution_id="exec-foreign"), _handoff(), "REVIEW_EXECUTION_ID_MISMATCH"),
        (_record(worker_id="foreign"), _handoff(), "REVIEW_EXECUTION_WORKER_MISMATCH"),
        (_record(head_before="d" * 40), _handoff(), "REVIEW_EXECUTION_HEAD_MISMATCH"),
        (_record(command_fingerprint="6" * 64), _handoff(), "REVIEW_EXECUTION_FINGERPRINT_MISMATCH"),
        (_record(version=8), _handoff(), "REVIEW_EXECUTION_VERSION_MISMATCH"),
        (_record(exit_code=1), _handoff(), "REVIEW_EXECUTION_EXIT_MISMATCH"),
    ],
)
def test_durable_record_handoff_mismatch_fails_closed(record, handoff, code) -> None:
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _compose(record=record, handoff=handoff)
    assert exc.value.code == code


def test_author_reviewer_execution_alias_fails_closed() -> None:
    record = _record(execution_id=AUTHOR.author_execution_id)
    handoff = _handoff(runtime_execution_id=AUTHOR.author_execution_id)
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _compose(record=record, handoff=handoff)
    assert exc.value.code == "AUTHOR_REVIEWER_NOT_DISTINCT"


def test_verification_required_cannot_authorize_accepted() -> None:
    record = _record(execution_state=ExecutionProcessState.VERIFICATION_REQUIRED)
    handoff = _handoff(record_state="VERIFICATION_REQUIRED")
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _compose(record=record, handoff=handoff)
    assert exc.value.code == "REVIEW_EXECUTION_NOT_ACCEPTANCE_ELIGIBLE"


def test_verification_required_may_preserve_rejected_evidence() -> None:
    record = _record(execution_state=ExecutionProcessState.VERIFICATION_REQUIRED)
    handoff = _handoff(record_state="VERIFICATION_REQUIRED")
    evidence = _compose(response=_raw(verdict="REJECTED"), record=record, handoff=handoff)
    assert evidence.disposition is ReviewDisposition.REJECTED


def test_report_runtime_packet_and_response_binding_fail_closed() -> None:
    response = _raw()
    cases = [
        (_report(response, execution_id="foreign"), "REVIEW_REPORT_EXECUTION_MISMATCH"),
        (_report(response, task_packet_sha256="9" * 64), "REVIEW_REPORT_TASK_SHA_MISMATCH"),
        (_report(response, response_bytes=len(response) + 1), "REVIEW_REPORT_RESPONSE_BYTES_MISMATCH"),
        (_report(response, response_sha256="9" * 64), "REVIEW_REPORT_RESPONSE_SHA_MISMATCH"),
        (_report(response, exit_state="EXIT_PENDING"), "REVIEW_REPORT_EXIT_PENDING"),
        (_report(response, schema="other"), "REVIEW_REPORT_SCHEMA_MISMATCH"),
    ]
    for report, code in cases:
        with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
            _compose(response=response, report=report)
        assert exc.value.code == code


def test_inprocess_report_contract_mismatch_fails_closed() -> None:
    response = _raw()
    report = _report(response, task_contract_ref="runs/foreign.task.json", selection_sha256="7" * 64)
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _compose(response=response, report=report)
    assert exc.value.code == "REVIEW_REPORT_CONTRACT_MISMATCH"


def test_helper_report_without_contract_ref_is_accepted_by_trusted_cross_binding() -> None:
    response = _raw()
    evidence = _compose(response=response, report=_report(response))
    assert evidence.disposition is ReviewDisposition.ACCEPTED


def test_stdout_digest_read_toctou_and_truncation_fail_closed() -> None:
    response = _raw()
    report = _report(response)
    rec = _record()
    good_report = _slice(ExecutionArtifactKind.REPORT, report, ref=rec.report_ref)
    cases = [
        _slice(ExecutionArtifactKind.STDOUT, response, ref=rec.stdout_ref, sha256="0" * 64),
        _slice(ExecutionArtifactKind.STDOUT, response, ref=rec.stdout_ref, truncated=True),
        _slice(ExecutionArtifactKind.STDOUT, response, ref=rec.stdout_ref, offset=1, total_bytes=len(response) + 1),
    ]
    for stdout in cases:
        with pytest.raises(ZeroRelayReviewEvidenceError):
            compose_direct_review_evidence(
                author=AUTHOR, route=_route(), handoff=_handoff(), record=rec,
                stdout=stdout, report=good_report,
            )


class _ArtifactStore:
    def __init__(self, records):
        self.records = list(records)
        self.calls = 0

    def get(self, execution_id: str):
        assert execution_id == RUNTIME_EXEC
        index = min(self.calls, len(self.records) - 1)
        self.calls += 1
        return self.records[index]


def _store_authority_fixture(tmp_path: Path):
    route = dataclasses.replace(
        _route(),
        worktree=str(tmp_path),
        review_task_path=str(tmp_path / "runs" / "review.md"),
    )
    handoff = _handoff(
        repo_root=str(tmp_path),
        task_packet_path=route.review_task_path,
    )
    record = _record(repo_root=str(tmp_path))
    response = _raw()
    report = _report(response)
    run_dir = tmp_path / record.run_dir_ref
    run_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / record.stdout_ref).write_bytes(response)
    (tmp_path / record.report_ref).write_bytes(report)
    return route, handoff, record


def test_store_authority_wrapper_reads_fresh_record_and_exact_artifacts(tmp_path: Path) -> None:
    route, handoff, record = _store_authority_fixture(tmp_path)
    store = _ArtifactStore([record])
    evidence = compose_direct_review_evidence_from_store(
        author=AUTHOR, route=route, handoff=handoff, store=store
    )
    assert evidence.disposition is ReviewDisposition.ACCEPTED
    assert evidence.reviewer_execution_id == RUNTIME_EXEC
    assert store.calls >= 4  # before + service rereads + after


def test_store_authority_wrapper_rejects_record_rollover_during_capture(tmp_path: Path) -> None:
    route, handoff, record = _store_authority_fixture(tmp_path)
    drifted = dataclasses.replace(
        record,
        execution_state=ExecutionProcessState.RECOVERY_REQUIRED,
        version=record.version + 1,
    )
    # call 1 = wrapper before; calls 2/3 = artifact-service rereads; call 4 = wrapper after
    store = _ArtifactStore([record, record, record, drifted])
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        compose_direct_review_evidence_from_store(
            author=AUTHOR, route=route, handoff=handoff, store=store
        )
    assert exc.value.code == "REVIEW_EXECUTION_RECORD_DRIFT"


# ---------- WO223 R3 repair RED: Astra F1/F4 ----------

@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("task_contract_ref", "work-order:foreign"),
        ("task_sha256", "9" * 64),
        ("result_ref", "runs/foreign.json"),
    ],
)
def test_r3_full_author_identity_rebinding_is_rejected(field: str, value: str) -> None:
    response = _raw()
    rec = _record()
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        compose_direct_review_evidence(
            author=dataclasses.replace(AUTHOR, **{field: value}),
            route=_route(),
            handoff=_handoff(),
            record=rec,
            stdout=_slice(ExecutionArtifactKind.STDOUT, response, ref=rec.stdout_ref),
            report=_slice(ExecutionArtifactKind.REPORT, _report(response), ref=rec.report_ref),
        )
    assert exc.value.code == "AUTHOR_IDENTITY_MISMATCH"


def test_r3_deep_response_and_report_json_fail_with_typed_errors() -> None:
    deep = b"[" * 1500 + b"0" + b"]" * 1500
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _parse(deep)
    assert exc.value.code == "REVIEW_RESULT_JSON_INVALID"

    response = _raw()
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        _compose(response=response, report=deep)
    assert exc.value.code == "REVIEW_REPORT_JSON_INVALID"



def test_r3_v2_evidence_rejects_legacy_route_without_full_author_provenance() -> None:
    v2 = _route()
    legacy = DirectReviewRoute(
        role=v2.role,
        mutation_intent=v2.mutation_intent,
        review_contract_ref=v2.review_contract_ref,
        review_task_path=v2.review_task_path,
        review_task_sha256=v2.review_task_sha256,
        review_result_ref=v2.review_result_ref,
        author_execution_id=v2.author_execution_id,
        author_result_sha256=v2.author_result_sha256,
        author_attempt_id=v2.author_attempt_id,
        author_generation=v2.author_generation,
        author_digest=v2.author_digest,
        reviewer_worker_id=v2.reviewer_worker_id,
        dispatch_execution_id=v2.dispatch_execution_id,
        provider_id=v2.provider_id,
        model_id=v2.model_id,
        project_id=v2.project_id,
        worktree=v2.worktree,
        branch=v2.branch,
        reviewed_head=v2.reviewed_head,
    )
    response = _raw()
    rec = _record()
    with pytest.raises(ZeroRelayReviewEvidenceError) as exc:
        compose_direct_review_evidence(
            author=AUTHOR,
            route=legacy,
            handoff=_handoff(),
            record=rec,
            stdout=_slice(ExecutionArtifactKind.STDOUT, response, ref=rec.stdout_ref),
            report=_slice(ExecutionArtifactKind.REPORT, _report(response), ref=rec.report_ref),
        )
    assert exc.value.code == "REVIEW_V2_ROUTE_PROVENANCE_MISSING"
