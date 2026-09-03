from __future__ import annotations

import json
import sys
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from a_conductor.agent_change_packets import AgentMailboxAssignment
from a_conductor.native_execution import NativeCommandResult
from a_conductor.review_mailbox_adapter import (
    MAX_REVIEW_RESULT_BYTES,
    ReviewMailboxAdapterError,
    ReviewMailboxResultReader,
    ReviewResultForwarder,
)


def assignment(tmp_path: Path) -> AgentMailboxAssignment:
    task = tmp_path / "task.md"
    result = tmp_path / "result.json"
    task.write_text("review exactly this\n", encoding="utf-8")
    return AgentMailboxAssignment(
        agent_id="glm", task_id="task-147", provider_id="zai",
        model_id="glm-5.3", role="independent-review",
        worktree=str(tmp_path.resolve()), branch="feat/review",
        base_head="a" * 40, task_ref=str(task.resolve()),
        result_ref=str(result.resolve()),
        task_sha256=sha256(task.read_bytes()).hexdigest(),
    )


def write_result(a: AgentMailboxAssignment, **overrides) -> Path:
    payload = {
        "task_id": a.task_id,
        "provider_id": a.provider_id,
        "model_id": a.model_id,
        "reviewed_head": a.base_head,
        "task_sha256": a.task_sha256,
        "verdict": "PASS",
        "findings": [],
        "retest": {"ok": True},
        "ci": {"ok": True},
        "ready": True,
        "merge": True,
    }
    payload.update(overrides)
    path = Path(a.result_ref)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def assert_code(exc_info, code: str) -> None:
    assert exc_info.value.code == code
def test_reader_binds_assignment_and_strips_trusted_fields(tmp_path: Path) -> None:
    a = assignment(tmp_path)
    write_result(a)

    result = ReviewMailboxResultReader().read(a)

    assert result.task_id == a.task_id
    assert result.provider_id == a.provider_id
    assert result.model_id == a.model_id
    assert result.reviewed_head == a.base_head
    assert result.task_sha256 == a.task_sha256
    assert result.awiki_payload == {
        "task_id": a.task_id,
        "reviewed_head": a.base_head,
        "task_sha256": a.task_sha256,
        "model": a.model_id,
        "verdict": "PASS",
        "findings": [],
    }
    assert "retest" not in result.awiki_payload
    assert "ci" not in result.awiki_payload
    assert "ready" not in result.awiki_payload
    assert "merge" not in result.awiki_payload


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("task_id", "other", "REVIEW_TASK_MISMATCH"),
        ("provider_id", "other", "REVIEW_PROVIDER_MISMATCH"),
        ("model_id", "other", "REVIEW_MODEL_MISMATCH"),
        ("reviewed_head", "b" * 40, "REVIEW_HEAD_MISMATCH"),
        ("task_sha256", "b" * 64, "REVIEW_TASK_HASH_MISMATCH"),
    ],
)
def test_reader_rejects_identity_mismatch(
    tmp_path: Path, field: str, value: str, code: str
) -> None:
    a = assignment(tmp_path)
    write_result(a, **{field: value})

    with pytest.raises(ReviewMailboxAdapterError) as exc_info:
        ReviewMailboxResultReader().read(a)
    assert_code(exc_info, code)


def test_reader_rejects_task_packet_hash_drift(tmp_path: Path) -> None:
    a = assignment(tmp_path)
    write_result(a)
    Path(a.task_ref).write_text("changed\n", encoding="utf-8")

    with pytest.raises(ReviewMailboxAdapterError) as exc_info:
        ReviewMailboxResultReader().read(a)
    assert_code(exc_info, "TASK_PACKET_HASH_MISMATCH")
def test_reader_rejects_oversized_result_before_read(
    tmp_path: Path, monkeypatch
) -> None:
    a = assignment(tmp_path)
    result_path = Path(a.result_ref)
    result_path.write_bytes(b"x" * (MAX_REVIEW_RESULT_BYTES + 1))
    original = Path.read_bytes

    def guarded_read(path: Path) -> bytes:
        if path == result_path:
            raise AssertionError("oversized result must not be read")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    with pytest.raises(ReviewMailboxAdapterError) as exc_info:
        ReviewMailboxResultReader().read(a)
    assert_code(exc_info, "REVIEW_RESULT_TOO_LARGE")


class FakeRunner:
    def __init__(self, result: NativeCommandResult) -> None:
        self.result = result
        self.calls = []
        self.forwarded_payload = None

    def run(self, spec):
        self.calls.append(spec)
        if "--file" in spec.argv:
            path = Path(spec.argv[spec.argv.index("--file") + 1])
            self.forwarded_payload = json.loads(path.read_text(encoding="utf-8"))
        return self.result
def command_result(
    *, exit_code: int | None = 0, timed_out: bool = False,
    stdout: str = '{"ok": true, "task_id": "task-147", "cycle": "P8-c1"}',
    stdout_truncated: bool = False,
) -> NativeCommandResult:
    return NativeCommandResult(
        executable=Path(sys.executable).name,
        argument_count=10,
        exit_code=exit_code,
        timed_out=timed_out,
        stdout=stdout,
        stderr="",
        stdout_sha256=sha256(stdout.encode()).hexdigest(),
        stderr_sha256=sha256(b"").hexdigest(),
        stdout_truncated=stdout_truncated,
        stderr_truncated=False,
    )


def test_forwarder_uses_only_awiki_cli_and_sanitized_payload(tmp_path: Path) -> None:
    a = assignment(tmp_path)
    write_result(a)
    review = ReviewMailboxResultReader().read(a)
    runner = FakeRunner(command_result())

    output = ReviewResultForwarder(
        runner=runner, python_executable=sys.executable
    ).forward(a, review)

    assert output["ok"] is True
    assert output["task_id"] == a.task_id
    spec = runner.calls[0]
    assert tuple(spec.argv[:7]) == (
        sys.executable, "-m", "conductor", "review", "ingest", "--task", a.task_id
    )
    assert spec.argv[-1] == "--json"
    assert spec.mutation_intent is True
    assert spec.cwd == "."
    assert runner.forwarded_payload == review.awiki_payload
    assert "provider_id" not in runner.forwarded_payload
    assert "model_id" not in runner.forwarded_payload
    assert "retest" not in runner.forwarded_payload
    assert "ci" not in runner.forwarded_payload


@pytest.mark.parametrize(
    ("result", "code"),
    [
        (command_result(timed_out=True), "AWIKI_REVIEW_FORWARD_TIMEOUT"),
        (command_result(exit_code=1), "AWIKI_REVIEW_FORWARD_FAILED"),
        (command_result(stdout_truncated=True), "AWIKI_REVIEW_FORWARD_TRUNCATED"),
        (command_result(stdout="not-json"), "AWIKI_REVIEW_RESPONSE_INVALID"),
        (command_result(stdout='{"ok": false, "task_id": "task-147"}'), "AWIKI_REVIEW_REJECTED"),
        (command_result(stdout='{"ok": true, "task_id": "other"}'), "AWIKI_REVIEW_TASK_MISMATCH"),
    ],
)
def test_forwarder_fails_closed_on_command_or_response_boundary(
    tmp_path: Path, result: NativeCommandResult, code: str
) -> None:
    a = assignment(tmp_path)
    write_result(a)
    review = ReviewMailboxResultReader().read(a)
    runner = FakeRunner(result)

    with pytest.raises(ReviewMailboxAdapterError) as exc_info:
        ReviewResultForwarder(
            runner=runner, python_executable=sys.executable
        ).forward(a, review)
    assert_code(exc_info, code)


def test_forwarder_refuses_result_object_for_other_assignment(tmp_path: Path) -> None:
    a = assignment(tmp_path)
    write_result(a)
    review = ReviewMailboxResultReader().read(a)
    other = replace(a, task_id="task-other")

    with pytest.raises(ReviewMailboxAdapterError) as exc_info:
        ReviewResultForwarder(
            runner=FakeRunner(command_result()), python_executable=sys.executable
        ).forward(other, review)
    assert_code(exc_info, "REVIEW_TASK_MISMATCH")
