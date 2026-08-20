from __future__ import annotations

from dataclasses import fields

import pytest

from a_conductor.operator_protocol import (
    OPERATOR_PROTOCOL_VERSION,
    OperatorAction,
    OperatorProtocolError,
    OperatorRequest,
    OperatorResponse,
    parse_operator_request,
)


def test_status_request_is_minimal_and_versioned() -> None:
    request = parse_operator_request(
        {"protocol_version": OPERATOR_PROTOCOL_VERSION, "action": "status"}
    )
    assert request.action is OperatorAction.STATUS
    assert request.protocol_version == "operator.v1"
    assert request.job_id is None


def test_job_create_accepts_only_bounded_operational_fields() -> None:
    request = parse_operator_request(
        {
            "protocol_version": "operator.v1",
            "action": "job.create",
            "job_id": "job-104",
            "work_order_ref": "A-Wiki:WO-OCR-104",
            "project_id": "wastewater",
            "max_attempts": 5,
        }
    )
    assert request == OperatorRequest(
        protocol_version="operator.v1",
        action=OperatorAction.JOB_CREATE,
        job_id="job-104",
        work_order_ref="A-Wiki:WO-OCR-104",
        project_id="wastewater",
        max_attempts=5,
    )


@pytest.mark.parametrize(
    "action,payload",
    [
        ("job.get", {"job_id": "job-1"}),
        ("job.events", {"job_id": "job-1"}),
        ("job.ready", {"job_id": "job-1", "expected_version": 2}),
        (
            "job.claim",
            {"job_id": "job-1", "expected_version": 2, "worker_id": "a-worker-01"},
        ),
        (
            "job.gate",
            {"job_id": "job-1", "expected_version": 3, "worker_id": "a-worker-01"},
        ),
        (
            "job.checkpoint",
            {
                "job_id": "job-1",
                "expected_version": 4,
                "checkpoint_ref": "checkpoint:verify-1",
                "evidence_ref": "native:sha256:abc123",
            },
        ),
        (
            "job.execute",
            {
                "job_id": "job-1",
                "expected_version": 4,
                "worker_id": "a-worker-01",
                "operation_ref": "verify.pytest.ocr",
            },
        ),
    ],
)
def test_supported_actions_parse(action: str, payload: dict[str, object]) -> None:
    request = parse_operator_request(
        {"protocol_version": "operator.v1", "action": action, **payload}
    )
    assert request.action.value == action


@pytest.mark.parametrize(
    "forbidden_field,forbidden_value",
    [
        ("command", "git reset --hard"),
        ("argv", ["git", "reset", "--hard"]),
        ("shell", True),
        ("prompt", "fix everything"),
        ("goal", "make the repo work"),
        ("transcript", "private conversation"),
        ("token", "secret"),
        ("payload", {"anything": "goes"}),
    ],
)
def test_unknown_or_dangerous_extra_fields_are_rejected(
    forbidden_field: str,
    forbidden_value: object,
) -> None:
    with pytest.raises(OperatorProtocolError) as exc_info:
        parse_operator_request(
            {
                "protocol_version": "operator.v1",
                "action": "job.execute",
                "job_id": "job-1",
                "expected_version": 4,
                "worker_id": "a-worker-01",
                "operation_ref": "verify.pytest.ocr",
                forbidden_field: forbidden_value,
            }
        )
    assert exc_info.value.code == "OPERATOR_FIELDS_INVALID"


def test_wrong_protocol_version_and_unknown_action_are_rejected() -> None:
    with pytest.raises(OperatorProtocolError) as exc_info:
        parse_operator_request({"protocol_version": "operator.v2", "action": "status"})
    assert exc_info.value.code == "OPERATOR_VERSION_UNSUPPORTED"

    with pytest.raises(OperatorProtocolError) as exc_info:
        parse_operator_request({"protocol_version": "operator.v1", "action": "shell.run"})
    assert exc_info.value.code == "OPERATOR_ACTION_UNSUPPORTED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_id", "job one"),
        ("worker_id", "../worker"),
        ("operation_ref", "pytest tests -q"),
        ("work_order_ref", "line\nfeed"),
        ("project_id", ""),
        ("checkpoint_ref", "x" * 161),
    ],
)
def test_identifiers_are_compact_and_option_safe(field: str, value: str) -> None:
    base: dict[str, object] = {
        "protocol_version": "operator.v1",
        "action": "job.execute",
        "job_id": "job-1",
        "expected_version": 1,
        "worker_id": "a-worker-01",
        "operation_ref": "verify.pytest.ocr",
    }
    if field in {"work_order_ref", "project_id"}:
        base = {
            "protocol_version": "operator.v1",
            "action": "job.create",
            "job_id": "job-1",
            "work_order_ref": "A-Wiki:WO-1",
            "project_id": "project-1",
            "max_attempts": 3,
        }
    elif field == "checkpoint_ref":
        base = {
            "protocol_version": "operator.v1",
            "action": "job.checkpoint",
            "job_id": "job-1",
            "expected_version": 1,
            "checkpoint_ref": "checkpoint:one",
        }
    base[field] = value

    with pytest.raises(OperatorProtocolError) as exc_info:
        parse_operator_request(base)
    assert exc_info.value.code == "OPERATOR_IDENTIFIER_INVALID"


@pytest.mark.parametrize("value", [0, -1, True, "1", 1.5])
def test_expected_version_must_be_positive_integer(value: object) -> None:
    with pytest.raises(OperatorProtocolError) as exc_info:
        parse_operator_request(
            {
                "protocol_version": "operator.v1",
                "action": "job.ready",
                "job_id": "job-1",
                "expected_version": value,
            }
        )
    assert exc_info.value.code == "OPERATOR_VERSION_INVALID"


@pytest.mark.parametrize("value", [0, -1, 101, True, "3"])
def test_max_attempts_is_bounded(value: object) -> None:
    with pytest.raises(OperatorProtocolError) as exc_info:
        parse_operator_request(
            {
                "protocol_version": "operator.v1",
                "action": "job.create",
                "job_id": "job-1",
                "work_order_ref": "A-Wiki:WO-1",
                "project_id": "project-1",
                "max_attempts": value,
            }
        )
    assert exc_info.value.code == "OPERATOR_ATTEMPT_BUDGET_INVALID"


def test_missing_required_and_action_inapplicable_fields_are_rejected() -> None:
    with pytest.raises(OperatorProtocolError) as exc_info:
        parse_operator_request(
            {
                "protocol_version": "operator.v1",
                "action": "job.claim",
                "job_id": "job-1",
                "expected_version": 1,
            }
        )
    assert exc_info.value.code == "OPERATOR_FIELDS_INVALID"

    with pytest.raises(OperatorProtocolError) as exc_info:
        parse_operator_request(
            {
                "protocol_version": "operator.v1",
                "action": "job.get",
                "job_id": "job-1",
                "worker_id": "a-worker-01",
            }
        )
    assert exc_info.value.code == "OPERATOR_FIELDS_INVALID"


def test_request_and_response_types_have_no_generic_execution_or_prompt_fields() -> None:
    forbidden = {
        "command",
        "argv",
        "shell",
        "prompt",
        "goal",
        "transcript",
        "payload",
        "token",
        "secret",
        "stdout",
        "stderr",
    }
    assert forbidden.isdisjoint({field.name for field in fields(OperatorRequest)})
    assert forbidden.isdisjoint({field.name for field in fields(OperatorResponse)})


def test_response_is_bounded_operational_metadata_only() -> None:
    response = OperatorResponse(
        ok=True,
        code="OK",
        job_id="job-1",
        state="VERIFYING",
        version=5,
        worker_id="a-worker-01",
        attempt_count=1,
        max_attempts=3,
        refs=("native:sha256:abc123",),
    )
    assert response.refs == ("native:sha256:abc123",)

    with pytest.raises(OperatorProtocolError) as exc_info:
        OperatorResponse(ok=True, code="OK", refs=("contains spaces",))
    assert exc_info.value.code == "OPERATOR_IDENTIFIER_INVALID"
