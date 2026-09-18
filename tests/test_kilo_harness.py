from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from a_conductor.claude_code_harness import (
    HarnessDispatch,
    HarnessExecutionStatus,
    MutationIntent,
    TaskPacketFile,
)
from a_conductor.kilo_harness import (
    KiloHarnessAdapter,
    KiloHarnessError,
    KiloRunnerResult,
)
from a_conductor.provider_configuration import HarnessStrategy


def make_dispatch(worktree: Path, **overrides) -> HarnessDispatch:
    values = dict(
        execution_id="exec-wo253-test",
        task_contract_ref="work-order:WO-P1-253",
        project_id="a-wiki-conductor",
        worktree_path=str(worktree),
        expected_branch="feat/wo-p1-253-kilo-packet-integrity",
        expected_head="a" * 40,
        provider_id="cointh-glm",
        model_id="glm-5.3",
        harness_strategy=HarnessStrategy.LOCAL_CLI,
        mutation_intent=MutationIntent.PROJECT_MUTATION,
        timeout_seconds=120,
        max_output_bytes=32_768,
        effort_level="MAX",
    )
    values.update(overrides)
    return HarnessDispatch(**values)


def make_packet(
    worktree: Path,
    text: str = "# Task\nJSON: {\"access\": true}\nUnicode: ไทย Ω\n",
) -> TaskPacketFile:
    path = worktree / "runs" / "WO-P1-253" / "task.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return TaskPacketFile(
        task_contract_ref="work-order:WO-P1-253",
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


class FakeRunner:
    def __init__(self, result: KiloRunnerResult) -> None:
        self.result = result
        self.calls = []

    def run(self, invocation):
        self.calls.append(invocation)
        return self.result


class AckRunner:
    def __init__(
        self,
        *,
        stderr: str = "",
        text: str = "done",
        mutate_path: Path | None = None,
        duplicate_ack: bool = False,
    ) -> None:
        self.stderr = stderr
        self.text = text
        self.mutate_path = mutate_path
        self.duplicate_ack = duplicate_ack
        self.calls = []

    def run(self, invocation):
        self.calls.append(invocation)
        marker = invocation.argv[2].split("final line: ", 1)[1]
        if self.mutate_path is not None:
            self.mutate_path.write_text("# DIFFERENT TASK\n", encoding="utf-8")
        text = f"{self.text}\n{marker}"
        if self.duplicate_ack:
            text += f"\n{marker}"
        events = [
            {"type": "text", "part": {"text": text}},
            {"type": "step_finish", "part": {"reason": "stop"}},
        ]
        return KiloRunnerResult(
            exit_code=0,
            stdout="\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
            stderr=self.stderr,
            timed_out=False,
        )


def success_runner(*, stderr: str = "", text: str = "done") -> AckRunner:
    return AckRunner(stderr=stderr, text=text)



def test_valid_packet_builds_fixed_file_transport_without_task_text_in_argv(tmp_path) -> None:
    task_text = "# Task\nJSON: {\"access\": true}\nUnicode: ไทย Ω\nWindows: C:\\repo\\file.py\n"
    packet = make_packet(tmp_path, task_text)
    runner = success_runner()
    result = KiloHarnessAdapter(runner=runner, executable=r"C:\tools\kilo.exe").execute(
        make_dispatch(tmp_path),
        packet,
    )

    assert result.status is HarnessExecutionStatus.SUCCESS
    assert len(runner.calls) == 1
    invocation = runner.calls[0]
    assert invocation.cwd == str(tmp_path.resolve())
    assert invocation.timeout_seconds == 120
    assert invocation.max_output_bytes == 32_768
    assert invocation.argv[0] == r"C:\tools\kilo.exe"
    assert invocation.argv[1] == "run"

    file_index = invocation.argv.index("--file")
    assert file_index > 2
    assert invocation.argv[2].startswith("Execute the attached authorized task packet.")
    assert packet.sha256 in invocation.argv[2]
    assert packet.task_contract_ref not in invocation.argv[2]
    assert "SUNDAY_TASK_ACK" in invocation.argv[2]
    assert invocation.argv[file_index + 1] == str(Path(packet.path).resolve())
    assert invocation.argv.count(str(Path(packet.path).resolve())) == 1
    assert invocation.argv[invocation.argv.index("--model") + 1] == "cointh-glm/glm-5.3"
    assert invocation.argv[invocation.argv.index("--variant") + 1] == "max"
    assert "--pure" in invocation.argv
    assert "--auto" not in invocation.argv
    assert "--share" not in invocation.argv
    assert all(task_text not in arg for arg in invocation.argv)
    assert all("ไทย" not in arg and "Ω" not in arg for arg in invocation.argv)


def test_packet_hash_ref_scope_size_and_regular_file_fail_before_runner(tmp_path) -> None:
    runner = success_runner()
    adapter = KiloHarnessAdapter(runner=runner, max_task_packet_bytes=64)
    dispatch = make_dispatch(tmp_path)
    valid = make_packet(tmp_path, "ok")

    bad_hash = TaskPacketFile(valid.task_contract_ref, valid.path, "0" * 64)
    with pytest.raises(KiloHarnessError) as exc_info:
        adapter.execute(dispatch, bad_hash)
    assert exc_info.value.code == "TASK_PACKET_HASH_MISMATCH"

    wrong_ref = TaskPacketFile("work-order:OTHER", valid.path, valid.sha256)
    with pytest.raises(KiloHarnessError) as exc_info:
        adapter.execute(dispatch, wrong_ref)
    assert exc_info.value.code == "TASK_PACKET_REF_MISMATCH"

    outside_path = tmp_path.parent / "outside-wo253.md"
    outside_path.write_text("outside", encoding="utf-8")
    outside = TaskPacketFile(
        valid.task_contract_ref,
        str(outside_path),
        hashlib.sha256(outside_path.read_bytes()).hexdigest(),
    )
    with pytest.raises(KiloHarnessError) as exc_info:
        adapter.execute(dispatch, outside)
    assert exc_info.value.code == "TASK_PACKET_OUTSIDE_WORKTREE"

    oversized = make_packet(tmp_path, "x" * 65)
    with pytest.raises(KiloHarnessError) as exc_info:
        adapter.execute(dispatch, oversized)
    assert exc_info.value.code == "TASK_PACKET_TOO_LARGE"

    directory = tmp_path / "runs" / "WO-P1-253" / "packet-dir"
    directory.mkdir()
    nonregular = TaskPacketFile(valid.task_contract_ref, str(directory), "0" * 64)
    with pytest.raises(KiloHarnessError) as exc_info:
        adapter.execute(dispatch, nonregular)
    assert exc_info.value.code == "TASK_PACKET_NOT_REGULAR"

    assert runner.calls == []


def test_packet_mutation_after_identity_creation_fails_closed(tmp_path) -> None:
    packet = make_packet(tmp_path, "before")
    Path(packet.path).write_text("after", encoding="utf-8")
    runner = success_runner()

    with pytest.raises(KiloHarnessError) as exc_info:
        KiloHarnessAdapter(runner=runner).execute(make_dispatch(tmp_path), packet)
    assert exc_info.value.code == "TASK_PACKET_HASH_MISMATCH"
    assert runner.calls == []


def test_post_runner_packet_drift_never_returns_success(tmp_path) -> None:
    packet = make_packet(tmp_path, "before")
    runner = AckRunner(mutate_path=Path(packet.path))

    result = KiloHarnessAdapter(runner=runner).execute(make_dispatch(tmp_path), packet)

    assert result.status is HarnessExecutionStatus.FAILED
    assert result.error_code == "TASK_PACKET_POST_RUN_DRIFT"
    assert len(runner.calls) == 1


def test_exit_zero_missing_task_prose_without_exact_ack_is_not_success(tmp_path) -> None:
    raw = KiloRunnerResult(
        0,
        json.dumps({
            "type": "text",
            "part": {"text": "No task was provided; send the task itself."},
        }) + "\n",
        "",
        False,
    )

    result = KiloHarnessAdapter(runner=FakeRunner(raw)).execute(
        make_dispatch(tmp_path),
        make_packet(tmp_path),
    )

    assert result.status is HarnessExecutionStatus.OUTPUT_INVALID
    assert result.error_code == "TASK_PACKET_ACK_MISSING_OR_AMBIGUOUS"


def test_duplicate_completion_ack_is_ambiguous_and_fails_closed(tmp_path) -> None:
    result = KiloHarnessAdapter(runner=AckRunner(duplicate_ack=True)).execute(
        make_dispatch(tmp_path),
        make_packet(tmp_path),
    )

    assert result.status is HarnessExecutionStatus.OUTPUT_INVALID
    assert result.error_code == "TASK_PACKET_ACK_MISSING_OR_AMBIGUOUS"


def test_symlink_packet_is_rejected_without_runner(tmp_path) -> None:
    target = tmp_path / "runs" / "WO-P1-253" / "real.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("task", encoding="utf-8")
    link = target.with_name("link.md")
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable on this Windows runtime")

    packet = TaskPacketFile(
        "work-order:WO-P1-253",
        str(link),
        hashlib.sha256(target.read_bytes()).hexdigest(),
    )
    runner = success_runner()
    with pytest.raises(KiloHarnessError) as exc_info:
        KiloHarnessAdapter(runner=runner).execute(make_dispatch(tmp_path), packet)
    assert exc_info.value.code == "TASK_PACKET_NOT_REGULAR"
    assert runner.calls == []


def test_dispatch_policy_and_effort_fail_before_runner(tmp_path) -> None:
    packet = make_packet(tmp_path)
    cases = [
        (make_dispatch(tmp_path, harness_strategy=HarnessStrategy.CLAUDE_CODE_CLI), "KILO_HARNESS_STRATEGY_UNSUPPORTED"),
        (make_dispatch(tmp_path, provider_id="bad/provider"), "KILO_PROVIDER_ID_INVALID"),
        (make_dispatch(tmp_path, model_id="bad/model"), "KILO_MODEL_ID_INVALID"),
        (make_dispatch(tmp_path, effort_level="DEFAULT"), None),
    ]

    for dispatch, expected in cases:
        runner = success_runner()
        adapter = KiloHarnessAdapter(runner=runner)
        if expected is None:
            result = adapter.execute(dispatch, packet)
            assert result.status is HarnessExecutionStatus.SUCCESS
            assert "--variant" not in runner.calls[0].argv
        else:
            with pytest.raises(KiloHarnessError) as exc_info:
                adapter.execute(dispatch, packet)
            assert exc_info.value.code == expected
            assert runner.calls == []


def test_timeout_nonzero_invalid_ndjson_error_and_no_text_events_are_typed(tmp_path) -> None:
    dispatch = make_dispatch(tmp_path)
    packet = make_packet(tmp_path)
    cases = [
        (
            KiloRunnerResult(None, "", "", True),
            HarnessExecutionStatus.TIMEOUT,
        ),
        (
            KiloRunnerResult(2, "", "failed", False, "RUNNER_FAILED"),
            HarnessExecutionStatus.FAILED,
        ),
        (
            KiloRunnerResult(0, "not-json\n", "", False),
            HarnessExecutionStatus.OUTPUT_INVALID,
        ),
        (
            KiloRunnerResult(
                0,
                json.dumps({"type": "error", "error": {"message": "bad"}}) + "\n",
                "",
                False,
            ),
            HarnessExecutionStatus.FAILED,
        ),
        (
            KiloRunnerResult(
                0,
                json.dumps({"type": "step_finish", "part": {"reason": "stop"}}) + "\n",
                "",
                False,
            ),
            HarnessExecutionStatus.OUTPUT_INVALID,
        ),
    ]
    for raw, expected in cases:
        result = KiloHarnessAdapter(runner=FakeRunner(raw)).execute(dispatch, packet)
        assert result.status is expected


def test_output_budget_fails_closed_without_returning_content(tmp_path) -> None:
    secret = "synthetic-output-secret"
    raw = KiloRunnerResult(
        0,
        json.dumps({"type": "text", "part": {"text": secret * 100}}) + "\n",
        "",
        False,
    )
    result = KiloHarnessAdapter(runner=FakeRunner(raw)).execute(
        make_dispatch(tmp_path, max_output_bytes=80),
        make_packet(tmp_path),
        redaction_values=(secret,),
    )
    assert result.status is HarnessExecutionStatus.OUTPUT_LIMIT
    assert result.events is None
    assert secret not in repr(result)


def test_share_urls_and_declared_secret_values_are_redacted(tmp_path) -> None:
    secret = "synthetic-sensitive-value-253"
    fake_share = "https://app.kilo.ai/s/synthetic"
    text = f"result {secret} {fake_share}"
    stderr = f"notice {secret} {fake_share}"
    result = KiloHarnessAdapter(runner=success_runner(stderr=stderr, text=text)).execute(
        make_dispatch(tmp_path),
        make_packet(tmp_path),
        redaction_values=(secret,),
    )

    assert result.status is HarnessExecutionStatus.SUCCESS
    rendered = repr(result)
    assert secret not in rendered
    assert fake_share not in rendered
    assert "[REDACTED]" in rendered
    assert "[REDACTED_KILO_SHARE_URL]" in rendered


def test_invalid_runner_result_is_rejected(tmp_path) -> None:
    class BadRunner:
        def run(self, invocation):
            return {"exit_code": 0}

    with pytest.raises(KiloHarnessError) as exc_info:
        KiloHarnessAdapter(runner=BadRunner()).execute(
            make_dispatch(tmp_path),
            make_packet(tmp_path),
        )
    assert exc_info.value.code == "RUNNER_RESULT_INVALID"
