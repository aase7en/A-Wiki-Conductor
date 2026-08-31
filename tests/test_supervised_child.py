from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

import a_conductor.supervised_child as supervised_child
from a_conductor.supervised_child import (
    SupervisedChildError,
    run_supervised_child,
)


class FakeChild:
    def __init__(self, *, pid: int = 4321, exit_code: int = 0) -> None:
        self.pid = pid
        self._exit_code = exit_code
        self.wait_calls = 0

    def wait(self) -> int:
        self.wait_calls += 1
        return self._exit_code


class FakePopenFactory:
    def __init__(self, child: FakeChild | None = None, error: Exception | None = None) -> None:
        self.child = child or FakeChild()
        self.error = error
        self.calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def __call__(self, argv, **kwargs):
        self.calls.append((tuple(argv), dict(kwargs)))
        if self.error is not None:
            raise self.error
        return self.child


def clock_values(*values: str):
    iterator = iter(values)
    return lambda: next(iterator)


def test_child_launches_exact_argv_without_shell_and_writes_bounded_result(tmp_path: Path) -> None:
    pid_path = tmp_path / "child.pid"
    result_path = tmp_path / "result.json"
    factory = FakePopenFactory(FakeChild(pid=777, exit_code=0))
    target = ("python.exe", "-c", "print('hello')")

    exit_code = run_supervised_child(
        execution_id="exec-001",
        pid_path=pid_path,
        result_path=result_path,
        cwd=tmp_path,
        target_argv=target,
        popen_factory=factory,
        now_factory=clock_values(
            "2026-08-20T03:00:00Z",
            "2026-08-20T03:00:01Z",
        ),
    )

    assert exit_code == 0
    assert pid_path.read_text(encoding="utf-8") == "777\n"
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload == {
        "schema_version": 1,
        "execution_id": "exec-001",
        "child_pid": 777,
        "exit_code": 0,
        "started_at": "2026-08-20T03:00:00Z",
        "finished_at": "2026-08-20T03:00:01Z",
    }
    argv, kwargs = factory.calls[0]
    assert argv == target
    assert kwargs["cwd"] == str(tmp_path.resolve())
    assert kwargs["shell"] is False
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert factory.child.wait_calls == 1


def test_result_json_never_contains_target_argv_environment_or_output(tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    secret_arg = "SUPER_SECRET_ARG_SHOULD_NOT_PERSIST"
    factory = FakePopenFactory()
    run_supervised_child(
        execution_id="exec-001",
        pid_path=tmp_path / "child.pid",
        result_path=result_path,
        cwd=tmp_path,
        target_argv=("python.exe", "-c", secret_arg),
        popen_factory=factory,
        now_factory=clock_values("start", "finish"),
    )
    raw = result_path.read_text(encoding="utf-8")
    assert secret_arg not in raw
    payload = json.loads(raw)
    for forbidden in ("argv", "command", "environment", "env", "stdout", "stderr", "token", "secret"):
        assert forbidden not in payload


def test_nonzero_target_exit_is_recorded_without_inference(tmp_path: Path) -> None:
    factory = FakePopenFactory(FakeChild(pid=8, exit_code=7))
    result_path = tmp_path / "result.json"
    exit_code = run_supervised_child(
        execution_id="exec-001",
        pid_path=tmp_path / "child.pid",
        result_path=result_path,
        cwd=tmp_path,
        target_argv=("python.exe", "-V"),
        popen_factory=factory,
        now_factory=clock_values("start", "finish"),
    )
    assert exit_code == 7
    assert json.loads(result_path.read_text(encoding="utf-8"))["exit_code"] == 7


def test_child_start_failure_writes_no_false_result(tmp_path: Path) -> None:
    factory = FakePopenFactory(error=OSError("boom"))
    result_path = tmp_path / "result.json"
    with pytest.raises(SupervisedChildError) as exc_info:
        run_supervised_child(
            execution_id="exec-001",
            pid_path=tmp_path / "child.pid",
            result_path=result_path,
            cwd=tmp_path,
            target_argv=("python.exe", "-V"),
            popen_factory=factory,
            now_factory=clock_values("start"),
        )
    assert exc_info.value.code == "CHILD_START_FAILED"
    assert not result_path.exists()
    assert not (tmp_path / "child.pid").exists()


def test_invalid_target_argv_is_rejected_before_popen(tmp_path: Path) -> None:
    factory = FakePopenFactory()
    with pytest.raises(ValueError):
        run_supervised_child(
            execution_id="exec-001",
            pid_path=tmp_path / "child.pid",
            result_path=tmp_path / "result.json",
            cwd=tmp_path,
            target_argv=(),
            popen_factory=factory,
        )
    assert factory.calls == []



def test_stream_redactor_catches_secret_split_across_chunks() -> None:
    secret = b"synthetic-secret-crossing-a-chunk-boundary"
    redactor = supervised_child._StreamingRedactor((secret,))
    output = b"".join((
        redactor.feed(b"prefix:" + secret[:7]),
        redactor.feed(secret[7:19]),
        redactor.feed(secret[19:] + b":suffix"),
        redactor.feed(b"", final=True),
    ))
    assert secret not in output
    assert output == b"prefix:[REDACTED]:suffix"



class PipeChild(FakeChild):
    def __init__(self, stdout: bytes = b"", stderr: bytes = b"") -> None:
        super().__init__(pid=9191, exit_code=0)
        self.stdout = io.BytesIO(stdout)
        self.stderr = io.BytesIO(stderr)


def test_capture_failure_publishes_no_terminal_result(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "synthetic-secret")
    factory = FakePopenFactory(PipeChild())

    def fail_pump(source, target, secrets, errors):
        errors.append(OSError("capture failed"))

    monkeypatch.setattr(supervised_child, "_pump_redacted", fail_pump)
    result_path = tmp_path / "result.json"
    with pytest.raises(SupervisedChildError, match="OUTPUT_CAPTURE_FAILED"):
        run_supervised_child(
            execution_id="exec-capture-fail", pid_path=tmp_path / "child.pid",
            result_path=result_path, cwd=tmp_path, target_argv=("python.exe", "-V"),
            popen_factory=factory, now_factory=clock_values("start"),
        )
    assert not result_path.exists()



def test_terminal_result_is_written_only_after_both_drains_finish(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "synthetic-secret")
    factory = FakePopenFactory(PipeChild(b"out", b"err"))
    completed = []

    def record_pump(source, target, secrets, errors):
        source.read()
        completed.append(object())

    real_write = supervised_child._write_bytes_atomic
    result_path = tmp_path / "result.json"

    def checked_write(path, payload):
        if Path(path) == result_path:
            assert len(completed) == 2
        return real_write(path, payload)

    monkeypatch.setattr(supervised_child, "_pump_redacted", record_pump)
    monkeypatch.setattr(supervised_child, "_write_bytes_atomic", checked_write)
    exit_code = run_supervised_child(
        execution_id="exec-drain-order", pid_path=tmp_path / "child.pid",
        result_path=result_path, cwd=tmp_path, target_argv=("python.exe", "-V"),
        popen_factory=factory, now_factory=clock_values("start", "finish"),
    )
    assert exit_code == 0
    assert result_path.exists()



def test_oversized_redaction_value_fails_before_child_launch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "x" * (16 * 1024 + 1))
    factory = FakePopenFactory()
    with pytest.raises(SupervisedChildError, match="REDACTION_SECRET_TOO_LARGE"):
        run_supervised_child(
            execution_id="exec-redaction-bound", pid_path=tmp_path / "child.pid",
            result_path=tmp_path / "result.json", cwd=tmp_path,
            target_argv=("python.exe", "-V"), popen_factory=factory,
            now_factory=clock_values("start"),
        )
    assert factory.calls == []
