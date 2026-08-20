from __future__ import annotations

import pytest

from a_conductor.operator_protocol import OperatorAction
from a_conductor.telegram_operator_commands import (
    TelegramOperatorCommandError,
    parse_telegram_operator_command,
)


def test_status_and_group_addressed_status_map_to_same_request() -> None:
    direct = parse_telegram_operator_command("/a status")
    group = parse_telegram_operator_command("/a@AConductorBot status")
    assert direct.action is OperatorAction.STATUS
    assert group.action is OperatorAction.STATUS


def test_read_only_job_commands_map_correctly() -> None:
    job = parse_telegram_operator_command("/a job job-104")
    events = parse_telegram_operator_command("/a events job-104")
    assert job.action is OperatorAction.JOB_GET
    assert job.job_id == "job-104"
    assert events.action is OperatorAction.JOB_EVENTS
    assert events.job_id == "job-104"


def test_create_maps_bounded_work_order_and_attempt_budget() -> None:
    request = parse_telegram_operator_command(
        "/a create job-104 A-Wiki:WO-OCR-104 wastewater 5"
    )
    assert request.action is OperatorAction.JOB_CREATE
    assert request.job_id == "job-104"
    assert request.work_order_ref == "A-Wiki:WO-OCR-104"
    assert request.project_id == "wastewater"
    assert request.max_attempts == 5


def test_create_defaults_attempt_budget_through_operator_protocol() -> None:
    request = parse_telegram_operator_command(
        "/a create job-104 A-Wiki:WO-OCR-104 wastewater"
    )
    assert request.max_attempts == 3


@pytest.mark.parametrize(
    "text,action",
    [
        ("/a ready job-1 2", OperatorAction.JOB_READY),
        ("/a claim job-1 2 a-worker-01", OperatorAction.JOB_CLAIM),
        ("/a gate job-1 3 a-worker-01", OperatorAction.JOB_GATE),
        (
            "/a checkpoint job-1 4 checkpoint:verify-1",
            OperatorAction.JOB_CHECKPOINT,
        ),
        (
            "/a checkpoint job-1 4 checkpoint:verify-1 native:sha256:abc123",
            OperatorAction.JOB_CHECKPOINT,
        ),
        (
            "/a exec job-1 4 a-worker-01 verify.pytest.ocr",
            OperatorAction.JOB_EXECUTE,
        ),
    ],
)
def test_mutating_commands_map_to_bounded_operator_actions(
    text: str,
    action: OperatorAction,
) -> None:
    request = parse_telegram_operator_command(text)
    assert request.action is action


def test_numeric_fields_use_strict_decimal_tokens() -> None:
    with pytest.raises(TelegramOperatorCommandError) as exc_info:
        parse_telegram_operator_command("/a ready job-1 0x10")
    assert exc_info.value.code == "TELEGRAM_NUMBER_INVALID"

    with pytest.raises(TelegramOperatorCommandError) as exc_info:
        parse_telegram_operator_command("/a create job-1 A-Wiki:WO-1 project-1 3.0")
    assert exc_info.value.code == "TELEGRAM_NUMBER_INVALID"


@pytest.mark.parametrize(
    "text",
    [
        "/a run wastewater",
        "/a fix everything",
        "/a shell git-status",
        "/a prompt do-something",
    ],
)
def test_free_form_and_generic_execution_macros_are_not_protocol_commands(text: str) -> None:
    with pytest.raises(TelegramOperatorCommandError) as exc_info:
        parse_telegram_operator_command(text)
    assert exc_info.value.code == "TELEGRAM_COMMAND_UNSUPPORTED"


@pytest.mark.parametrize(
    "text",
    [
        "/a",
        "/a status extra",
        "/a job",
        "/a job job-1 extra",
        "/a claim job-1 2",
        "/a exec job-1 2 a-worker-01",
        "/a checkpoint job-1 2 checkpoint:x evidence:x extra",
    ],
)
def test_exact_token_counts_are_enforced(text: str) -> None:
    with pytest.raises(TelegramOperatorCommandError) as exc_info:
        parse_telegram_operator_command(text)
    assert exc_info.value.code in {
        "TELEGRAM_COMMAND_INVALID",
        "TELEGRAM_COMMAND_UNSUPPORTED",
    }


@pytest.mark.parametrize(
    "text",
    [
        "/a status\n/a exec job-1 2 a-worker-01 verify.pytest.ocr",
        "/a status\r/a job job-1",
        " /a status\t\n ",
    ],
)
def test_multiline_command_chaining_is_rejected(text: str) -> None:
    with pytest.raises(TelegramOperatorCommandError) as exc_info:
        parse_telegram_operator_command(text)
    assert exc_info.value.code == "TELEGRAM_COMMAND_INVALID"


def test_quotes_are_not_shell_or_grouping_syntax() -> None:
    with pytest.raises(TelegramOperatorCommandError):
        parse_telegram_operator_command('/a job "job-1"')


def test_non_a_commands_are_not_consumed() -> None:
    for text in ("hello", "/start", "/help", "/hermes status"):
        with pytest.raises(TelegramOperatorCommandError) as exc_info:
            parse_telegram_operator_command(text)
        assert exc_info.value.code == "TELEGRAM_NOT_A_CONDUCTOR_COMMAND"


def test_bot_username_suffix_is_validated() -> None:
    with pytest.raises(TelegramOperatorCommandError) as exc_info:
        parse_telegram_operator_command("/a@bad-name status")
    assert exc_info.value.code == "TELEGRAM_COMMAND_INVALID"


def test_command_length_is_bounded() -> None:
    with pytest.raises(TelegramOperatorCommandError) as exc_info:
        parse_telegram_operator_command("/a job " + "x" * 600)
    assert exc_info.value.code == "TELEGRAM_COMMAND_INVALID"
