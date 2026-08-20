from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

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
