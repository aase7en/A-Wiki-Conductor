from __future__ import annotations

from dataclasses import fields

import pytest

from a_conductor.execution_record import (
    DurableExecutionReceipt,
    DurableExecutionRecord,
    ExecutionProcessState,
    ReceiptDisposition,
    TransportState,
    compute_receipt_id,
    new_execution_record,
    new_execution_receipt,
)


def make_record(**overrides) -> DurableExecutionRecord:
    values = dict(
        execution_id="exec-001",
        job_id="job-001",
        work_order_ref="docs/work-orders/WO-1.md",
        project_id="project-1",
        worker_id="a-worker-01",
        backend_id="serena-local",
        agent_ref="agent:chatgpt",
        repo_root=r"A:\GitHub\example",
        branch="main",
        head_before="a" * 40,
        operation_ref="op:pytest-focused",
        command_fingerprint="b" * 64,
        command_summary="pytest focused regression",
        runtime_profile_ref="runtime:serena-phase6",
        run_dir_ref="runs/exec-001",
        stdout_ref="runs/exec-001/stdout.log",
        stderr_ref="runs/exec-001/stderr.log",
        result_ref="runs/exec-001/result.json",
        report_ref="runs/exec-001/report.txt",
        transport_state=TransportState.CONNECTED,
        execution_state=ExecutionProcessState.QUEUED,
    )
    values.update(overrides)
    return new_execution_record(**values)


def test_transport_and_execution_state_are_separate_dimensions() -> None:
    record = make_record(
        transport_state=TransportState.LOST,
        execution_state=ExecutionProcessState.RUNNING,
    )
    assert record.transport_state is TransportState.LOST
    assert record.execution_state is ExecutionProcessState.RUNNING


def test_required_transport_states_exist() -> None:
    assert {state.value for state in TransportState} == {
        "CONNECTED",
        "DEGRADED",
        "LOST",
        "UNAVAILABLE",
    }


def test_required_execution_states_exist() -> None:
    assert {state.value for state in ExecutionProcessState} == {
        "QUEUED",
        "STARTING",
        "RUNNING",
        "PROCESS_STILL_RUNNING",
        "PROCESS_EXITED_UNKNOWN_RESULT",
        "SUCCEEDED",
        "FAILED",
        "PARTIAL",
        "CANCELLED",
        "RECOVERY_REQUIRED",
        "VERIFICATION_REQUIRED",
    }


def test_new_execution_record_starts_at_version_one() -> None:
    assert make_record().version == 1


def test_command_fingerprint_must_be_lowercase_sha256_hex() -> None:
    for value in ("x" * 64, "A" * 64, "a" * 63, "a" * 65):
        with pytest.raises(ValueError):
            make_record(command_fingerprint=value)


def test_command_summary_is_bounded_and_single_line() -> None:
    with pytest.raises(ValueError):
        make_record(command_summary="x" * 257)
    with pytest.raises(ValueError):
        make_record(command_summary="pytest\nrm -rf something")


def test_optional_refs_may_be_absent_before_launch() -> None:
    record = make_record(
        agent_ref=None,
        runtime_profile_ref=None,
        run_dir_ref=None,
        stdout_ref=None,
        stderr_ref=None,
        result_ref=None,
        report_ref=None,
    )
    assert record.run_dir_ref is None
    assert record.stdout_ref is None


def test_pid_must_be_positive_when_known() -> None:
    with pytest.raises(ValueError):
        make_record(pid=0)
    with pytest.raises(ValueError):
        make_record(pid=-1)


def test_exit_code_must_be_integer_when_known() -> None:
    with pytest.raises(ValueError):
        make_record(exit_code=True)


def test_raw_secret_or_output_fields_do_not_exist() -> None:
    names = {field.name for field in fields(DurableExecutionRecord)}
    for forbidden in (
        "prompt",
        "transcript",
        "command",
        "argv",
        "environment",
        "env",
        "stdout",
        "stderr",
        "token",
        "secret",
    ):
        assert forbidden not in names


def test_identity_and_reference_text_rejects_nul() -> None:
    with pytest.raises(ValueError):
        make_record(operation_ref="op:good\x00bad")


def receipt_values(**overrides) -> dict:
    values = dict(
        execution_id="exec-001",
        attempt_id="attempt-001",
        result_digest="c" * 64,
        binding_digest="d" * 64,
        claim_generation=3,
        authority_sha="1" * 40,
        execution_sha="2" * 40,
        disposition=ReceiptDisposition.ACCEPTED,
        evidence_ref="evidence:dex-collect-1",
    )
    values.update(overrides)
    return values


def test_receipt_disposition_vocabulary_is_closed() -> None:
    assert {item.value for item in ReceiptDisposition} == {"ACCEPTED", "QUARANTINED"}


def test_receipt_identity_is_deterministic_over_contract_tuple() -> None:
    first = compute_receipt_id(
        execution_id="exec-001",
        attempt_id="attempt-001",
        result_digest="c" * 64,
        binding_digest="d" * 64,
    )
    second = compute_receipt_id(
        execution_id="exec-001",
        attempt_id="attempt-001",
        result_digest="c" * 64,
        binding_digest="d" * 64,
    )
    assert first == second
    assert len(first) == 64
    different_attempt = compute_receipt_id(
        execution_id="exec-001",
        attempt_id="attempt-002",
        result_digest="c" * 64,
        binding_digest="d" * 64,
    )
    assert different_attempt != first


def test_new_execution_receipt_derives_identity_and_allows_unknown_timestamp() -> None:
    receipt = new_execution_receipt(**receipt_values())
    assert receipt.receipt_id == compute_receipt_id(
        execution_id="exec-001",
        attempt_id="attempt-001",
        result_digest="c" * 64,
        binding_digest="d" * 64,
    )
    assert receipt.recorded_at is None
    bare = new_execution_receipt(**receipt_values(evidence_ref=None))
    assert bare.evidence_ref is None


def test_receipt_id_must_match_contract_identity() -> None:
    values = receipt_values()
    with pytest.raises(ValueError):
        DurableExecutionReceipt(receipt_id="e" * 64, recorded_at=None, **values)


def test_receipt_digests_must_be_lowercase_sha256_hex() -> None:
    for field in ("result_digest", "binding_digest"):
        for value in ("C" * 64, "c" * 63, "c" * 65, "x" * 64, 64):
            with pytest.raises(ValueError):
                new_execution_receipt(**receipt_values(**{field: value}))


def test_receipt_claim_generation_must_be_positive() -> None:
    for value in (0, -1, True, "3"):
        with pytest.raises(ValueError):
            new_execution_receipt(**receipt_values(claim_generation=value))


def test_receipt_pinned_shas_must_be_exact_git_shape() -> None:
    for field in ("authority_sha", "execution_sha"):
        for value in ("1" * 39, "A" * 40, "1" * 41, "g" * 40):
            with pytest.raises(ValueError):
                new_execution_receipt(**receipt_values(**{field: value}))


def test_receipt_attempt_and_execution_must_be_single_line_bounded() -> None:
    for field in ("attempt_id", "execution_id"):
        for value in ("", "   ", "attempt\n2", "attempt\x002", "a" * 1025):
            with pytest.raises(ValueError):
                new_execution_receipt(**receipt_values(**{field: value}))


def test_receipt_disposition_must_be_enum_member() -> None:
    with pytest.raises(ValueError):
        new_execution_receipt(**receipt_values(disposition="ACCEPTED"))


def test_receipt_optional_text_fields_are_single_line() -> None:
    with pytest.raises(ValueError):
        new_execution_receipt(**receipt_values(evidence_ref="evidence:one\ntwo"))
    with pytest.raises(ValueError):
        new_execution_receipt(**receipt_values(evidence_ref="evidence:one\x00two"))
    with pytest.raises(ValueError):
        DurableExecutionReceipt(
            **receipt_values(),
            receipt_id=compute_receipt_id(
                execution_id="exec-001",
                attempt_id="attempt-001",
                result_digest="c" * 64,
                binding_digest="d" * 64,
            ),
            recorded_at="2026-09-20T00:00:00Z\nextra",
        )


def test_receipt_has_no_raw_secret_or_output_fields() -> None:
    names = {field.name for field in fields(DurableExecutionReceipt)}
    for forbidden in (
        "prompt",
        "transcript",
        "command",
        "argv",
        "environment",
        "env",
        "stdout",
        "stderr",
        "token",
        "secret",
    ):
        assert forbidden not in names
