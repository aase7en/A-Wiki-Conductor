from __future__ import annotations

from dataclasses import fields

import pytest

from a_conductor.execution_record import (
    DurableExecutionRecord,
    ExecutionProcessState,
    TransportState,
    new_execution_record,
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
