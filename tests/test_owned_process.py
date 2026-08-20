from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from a_conductor.owned_process import (
    OwnedProcessMutationState,
    OwnedProcessSpec,
    WindowsExactPidTerminator,
    WindowsOwnedProcessController,
    WindowsProcessSpawner,
)
from a_conductor.runtime_safety import (
    ProcessObservation,
    ProcessOwnership,
    classify_process_ownership,
)
from a_conductor.windows_io import LoopbackReadyzHttpProbe, StrictPowerShellInspectionRunner
from a_conductor.windows_observer import (
    PidMetadataObservation,
    PidMetadataStatus,
    WindowsRuntimeObserver,
)


HELPER = Path(__file__).parent / "support" / "dummy_runtime.py"


class FakeObserver:
    def __init__(
        self,
        metadata: PidMetadataObservation,
        process: ProcessObservation | None = None,
    ) -> None:
        self.metadata = metadata
        self.process = process
        self.read_calls: list[Path] = []
        self.observe_calls: list[tuple[int, str, str]] = []

    def read_pid_metadata(self, pid_path: Path) -> PidMetadataObservation:
        self.read_calls.append(pid_path)
        return self.metadata

    def observe_process(
        self,
        *,
        pid: int,
        expected_executable_name: str,
        expected_profile_marker: str,
    ) -> ProcessObservation:
        self.observe_calls.append(
            (pid, expected_executable_name, expected_profile_marker)
        )
        assert self.process is not None
        return self.process


class FakeChild:
    def __init__(self, pid: int = 43210) -> None:
        self.pid = pid
        self.terminated = False
        self.killed = False
        self.waited = False

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float | None = None) -> int:
        self.waited = True
        return 0

    def poll(self) -> int | None:
        return None if not (self.terminated or self.killed) else 0


class FakeSpawner:
    def __init__(self, child: FakeChild | None = None) -> None:
        self.child = child or FakeChild()
        self.calls: list[OwnedProcessSpec] = []

    def spawn(self, spec: OwnedProcessSpec):
        self.calls.append(spec)
        return self.child


class FakeTerminator:
    def __init__(self, result: bool = True) -> None:
        self.result = result
        self.calls: list[tuple[int, int]] = []

    def terminate(self, pid: int, timeout_seconds: int) -> bool:
        self.calls.append((pid, timeout_seconds))
        return self.result


def spec(root: Path, *, marker: str = "owned-marker") -> OwnedProcessSpec:
    return OwnedProcessSpec(
        allowed_root=root,
        cwd=root,
        pid_path=root / "run" / "runtime.pid",
        stdout_path=root / "logs" / "stdout.log",
        stderr_path=root / "logs" / "stderr.log",
        command=(sys.executable, "-c", "print('ok')", "--marker", marker),
        expected_executable_name=Path(sys.executable).name,
        expected_profile_marker=marker,
        stop_timeout_seconds=5,
    )


def test_spec_rejects_mutable_path_outside_allowed_root(tmp_path: Path) -> None:
    root = tmp_path / "owned"

    with pytest.raises(ValueError, match="must stay under allowed_root"):
        OwnedProcessSpec(
            allowed_root=root,
            cwd=root,
            pid_path=tmp_path / "outside.pid",
            stdout_path=root / "stdout.log",
            stderr_path=root / "stderr.log",
            command=(sys.executable, "--marker", "owned-marker"),
            expected_executable_name=Path(sys.executable).name,
            expected_profile_marker="owned-marker",
        )


def test_spec_rejects_executable_mismatch(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="command executable does not match"):
        OwnedProcessSpec(
            allowed_root=tmp_path,
            cwd=tmp_path,
            pid_path=tmp_path / "runtime.pid",
            stdout_path=tmp_path / "stdout.log",
            stderr_path=tmp_path / "stderr.log",
            command=(sys.executable, "--marker", "owned-marker"),
            expected_executable_name="definitely-not-python.exe",
            expected_profile_marker="owned-marker",
        )


def test_spec_rejects_missing_profile_marker(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="profile marker is not present"):
        OwnedProcessSpec(
            allowed_root=tmp_path,
            cwd=tmp_path,
            pid_path=tmp_path / "runtime.pid",
            stdout_path=tmp_path / "stdout.log",
            stderr_path=tmp_path / "stderr.log",
            command=(sys.executable, "-c", "print('ok')"),
            expected_executable_name=Path(sys.executable).name,
            expected_profile_marker="owned-marker",
        )


def test_start_stale_pid_requires_recovery_and_does_not_spawn(tmp_path: Path) -> None:
    observer = FakeObserver(
        PidMetadataObservation(PidMetadataStatus.VALID, 1234),
        ProcessObservation(True, 1234, False, None, None),
    )
    spawner = FakeSpawner()
    controller = WindowsOwnedProcessController(
        observer=observer,
        spawner=spawner,
        terminator=FakeTerminator(),
    )

    result = controller.start(spec(tmp_path))

    assert result.state is OwnedProcessMutationState.RECOVERY_REQUIRED
    assert result.reason_code == "STALE_PID_METADATA"
    assert spawner.calls == []


def test_start_owned_process_is_idempotent_and_does_not_spawn(tmp_path: Path) -> None:
    observer = FakeObserver(
        PidMetadataObservation(PidMetadataStatus.VALID, 1234),
        ProcessObservation(True, 1234, True, True, True),
    )
    spawner = FakeSpawner()
    controller = WindowsOwnedProcessController(
        observer=observer,
        spawner=spawner,
        terminator=FakeTerminator(),
    )

    result = controller.start(spec(tmp_path))

    assert result.state is OwnedProcessMutationState.ALREADY_RUNNING
    assert result.pid == 1234
    assert spawner.calls == []


def test_stop_pid_mismatch_refuses_and_keeps_pid_metadata(tmp_path: Path) -> None:
    runtime = spec(tmp_path)
    runtime.pid_path.parent.mkdir(parents=True)
    runtime.pid_path.write_text("1234", encoding="utf-8")
    observer = FakeObserver(
        PidMetadataObservation(PidMetadataStatus.VALID, 1234),
        ProcessObservation(True, 1234, True, False, True),
    )
    terminator = FakeTerminator()
    controller = WindowsOwnedProcessController(
        observer=observer,
        spawner=FakeSpawner(),
        terminator=terminator,
    )

    result = controller.stop(runtime)

    assert result.state is OwnedProcessMutationState.REFUSED
    assert result.reason_code == "PID_MISMATCH"
    assert terminator.calls == []
    assert runtime.pid_path.read_text(encoding="utf-8") == "1234"


def test_stop_stale_pid_requires_recovery_and_does_not_delete_metadata(tmp_path: Path) -> None:
    runtime = spec(tmp_path)
    runtime.pid_path.parent.mkdir(parents=True)
    runtime.pid_path.write_text("1234", encoding="utf-8")
    observer = FakeObserver(
        PidMetadataObservation(PidMetadataStatus.VALID, 1234),
        ProcessObservation(True, 1234, False, None, None),
    )
    terminator = FakeTerminator()
    controller = WindowsOwnedProcessController(
        observer=observer,
        spawner=FakeSpawner(),
        terminator=terminator,
    )

    result = controller.stop(runtime)

    assert result.state is OwnedProcessMutationState.RECOVERY_REQUIRED
    assert result.reason_code == "STALE_PID_METADATA"
    assert terminator.calls == []
    assert runtime.pid_path.exists()


def test_pid_persistence_failure_cleans_up_only_exact_new_child(
    tmp_path: Path,
    monkeypatch,
) -> None:
    observer = FakeObserver(PidMetadataObservation(PidMetadataStatus.ABSENT, None))
    child = FakeChild()
    spawner = FakeSpawner(child)
    controller = WindowsOwnedProcessController(
        observer=observer,
        spawner=spawner,
        terminator=FakeTerminator(),
    )
    monkeypatch.setattr(
        "a_conductor.owned_process._write_pid_atomic",
        lambda path, pid: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    result = controller.start(spec(tmp_path))

    assert result.state is OwnedProcessMutationState.RECOVERY_REQUIRED
    assert result.reason_code == "PID_METADATA_PERSISTENCE_FAILED"
    assert child.terminated is True
    assert child.waited is True


def test_exact_pid_terminator_uses_shell_false_and_integer_pid(monkeypatch) -> None:
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr("a_conductor.owned_process.subprocess.run", fake_run)
    terminator = WindowsExactPidTerminator()

    assert terminator.terminate(1234, 5) is True
    argv, kwargs = calls[0]
    assert argv[0].lower().endswith("powershell.exe")
    assert "Stop-Process -Id 1234" in argv[-1]
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 5


@pytest.mark.skipif(os.name != "nt", reason="Windows owned-process integration")
def test_real_dummy_process_start_idempotent_stop(tmp_path: Path) -> None:
    root = tmp_path / "owned-runtime"
    marker = "stage-a-production-owned-process"
    state_file = root / "dummy-state.json"
    runtime_python = getattr(sys, "_base_executable", sys.executable)
    runtime = OwnedProcessSpec(
        allowed_root=root,
        cwd=root,
        pid_path=root / "run" / "runtime.pid",
        stdout_path=root / "logs" / "stdout.log",
        stderr_path=root / "logs" / "stderr.log",
        command=(
            runtime_python,
            str(HELPER),
            "--state-file",
            str(state_file),
            "--marker",
            marker,
        ),
        expected_executable_name=Path(runtime_python).name,
        expected_profile_marker=marker,
        stop_timeout_seconds=5,
    )
    observer = WindowsRuntimeObserver(
        runner=StrictPowerShellInspectionRunner(),
        http_probe=LoopbackReadyzHttpProbe(),
    )
    terminator = WindowsExactPidTerminator()
    controller = WindowsOwnedProcessController(observer=observer, terminator=terminator)
    started_pid: int | None = None

    try:
        started = controller.start(runtime)
        assert started.state is OwnedProcessMutationState.STARTED
        assert started.pid is not None
        started_pid = started.pid
        assert runtime.pid_path.read_text(encoding="utf-8").strip() == str(started_pid)

        deadline = time.monotonic() + 5
        state: dict[str, object] | None = None
        while time.monotonic() < deadline:
            if state_file.is_file():
                state = json.loads(state_file.read_text(encoding="utf-8"))
                break
            time.sleep(0.05)
        assert state is not None
        assert state["pid"] == started_pid

        url = f"http://127.0.0.1:{state['port']}/readyz"
        with urlopen(url, timeout=1) as response:
            assert response.status == 200

        second = controller.start(runtime)
        assert second.state is OwnedProcessMutationState.ALREADY_RUNNING
        assert second.pid == started_pid

        stopped = controller.stop(runtime)
        assert stopped.state is OwnedProcessMutationState.STOPPED
        assert stopped.pid == started_pid
        assert not runtime.pid_path.exists()
        observed = observer.observe_process(
            pid=started_pid,
            expected_executable_name=runtime.expected_executable_name,
            expected_profile_marker=runtime.expected_profile_marker,
        )
        assert classify_process_ownership(observed) is ProcessOwnership.STALE
        started_pid = None
    finally:
        if started_pid is not None:
            observed = observer.observe_process(
                pid=started_pid,
                expected_executable_name=runtime.expected_executable_name,
                expected_profile_marker=runtime.expected_profile_marker,
            )
            if classify_process_ownership(observed) is ProcessOwnership.OWNED:
                terminator.terminate(started_pid, 5)


def test_start_invalid_pid_metadata_requires_recovery_without_spawn(tmp_path: Path) -> None:
    observer = FakeObserver(PidMetadataObservation(PidMetadataStatus.INVALID, None))
    spawner = FakeSpawner()
    controller = WindowsOwnedProcessController(observer=observer, spawner=spawner, terminator=FakeTerminator())

    result = controller.start(spec(tmp_path))

    assert result.state is OwnedProcessMutationState.RECOVERY_REQUIRED
    assert result.reason_code == "PID_METADATA_INVALID"
    assert spawner.calls == []


def test_start_unknown_pid_metadata_requires_recovery_without_spawn(tmp_path: Path) -> None:
    observer = FakeObserver(PidMetadataObservation(PidMetadataStatus.UNKNOWN, None))
    spawner = FakeSpawner()
    controller = WindowsOwnedProcessController(observer=observer, spawner=spawner, terminator=FakeTerminator())

    result = controller.start(spec(tmp_path))

    assert result.state is OwnedProcessMutationState.RECOVERY_REQUIRED
    assert result.reason_code == "PID_METADATA_UNKNOWN"
    assert spawner.calls == []


def test_start_unknown_process_ownership_refuses_duplicate_spawn(tmp_path: Path) -> None:
    observer = FakeObserver(
        PidMetadataObservation(PidMetadataStatus.VALID, 1234),
        ProcessObservation(True, 1234, None, None, None),
    )
    spawner = FakeSpawner()
    controller = WindowsOwnedProcessController(observer=observer, spawner=spawner, terminator=FakeTerminator())

    result = controller.start(spec(tmp_path))

    assert result.state is OwnedProcessMutationState.REFUSED
    assert result.reason_code == "PROCESS_OWNERSHIP_UNKNOWN"
    assert spawner.calls == []


def test_stop_absent_metadata_is_idempotent_not_running(tmp_path: Path) -> None:
    observer = FakeObserver(PidMetadataObservation(PidMetadataStatus.ABSENT, None))
    terminator = FakeTerminator()
    controller = WindowsOwnedProcessController(observer=observer, spawner=FakeSpawner(), terminator=terminator)

    result = controller.stop(spec(tmp_path))

    assert result.state is OwnedProcessMutationState.NOT_RUNNING
    assert result.reason_code == "NOT_RUNNING"
    assert terminator.calls == []


def test_stop_failure_keeps_owned_pid_metadata_for_recovery(tmp_path: Path) -> None:
    runtime = spec(tmp_path)
    runtime.pid_path.parent.mkdir(parents=True)
    runtime.pid_path.write_text("1234", encoding="utf-8")
    observer = FakeObserver(
        PidMetadataObservation(PidMetadataStatus.VALID, 1234),
        ProcessObservation(True, 1234, True, True, True),
    )
    terminator = FakeTerminator(result=False)
    controller = WindowsOwnedProcessController(observer=observer, spawner=FakeSpawner(), terminator=terminator)

    result = controller.stop(runtime)

    assert result.state is OwnedProcessMutationState.RECOVERY_REQUIRED
    assert result.reason_code == "PROCESS_STOP_FAILED"
    assert runtime.pid_path.read_text(encoding="utf-8") == "1234"


def test_stop_detects_pid_metadata_change_before_cleanup(tmp_path: Path) -> None:
    runtime = spec(tmp_path)
    runtime.pid_path.parent.mkdir(parents=True)
    runtime.pid_path.write_text("1234", encoding="utf-8")

    class SequencedObserver:
        def __init__(self) -> None:
            self.read_count = 0
            self.observe_count = 0

        def read_pid_metadata(self, pid_path: Path) -> PidMetadataObservation:
            self.read_count += 1
            if self.read_count == 1:
                return PidMetadataObservation(PidMetadataStatus.VALID, 1234)
            return PidMetadataObservation(PidMetadataStatus.VALID, 9999)

        def observe_process(self, *, pid: int, expected_executable_name: str, expected_profile_marker: str) -> ProcessObservation:
            self.observe_count += 1
            if self.observe_count == 1:
                return ProcessObservation(True, pid, True, True, True)
            return ProcessObservation(True, pid, False, None, None)

    controller = WindowsOwnedProcessController(
        observer=SequencedObserver(),
        spawner=FakeSpawner(),
        terminator=FakeTerminator(result=True),
    )

    result = controller.stop(runtime)

    assert result.state is OwnedProcessMutationState.RECOVERY_REQUIRED
    assert result.reason_code == "PID_METADATA_CHANGED"
    assert runtime.pid_path.exists()


def test_spec_accepts_allowlisted_serena_home_override(tmp_path: Path) -> None:
    root = tmp_path / "owned"
    runtime = OwnedProcessSpec(
        allowed_root=root,
        cwd=root,
        pid_path=root / "run" / "runtime.pid",
        stdout_path=root / "logs" / "stdout.log",
        stderr_path=root / "logs" / "stderr.log",
        command=(sys.executable, "--marker", "owned-marker"),
        expected_executable_name=Path(sys.executable).name,
        expected_profile_marker="owned-marker",
        environment_overrides=(("SERENA_HOME", str(root / "serena-home")),),
    )
    assert runtime.environment_overrides == (("SERENA_HOME", str((root / "serena-home").resolve())),)


@pytest.mark.parametrize(
    "overrides",
    [
        (("OPENAI_API_KEY", "secret"),),
        (("SERENA_HOME", ""),),
        (("SERENA_HOME", "bad\x00value"),),
        (("SERENA_HOME", "one"), ("SERENA_HOME", "two")),
    ],
)
def test_spec_rejects_invalid_environment_overrides(tmp_path: Path, overrides) -> None:
    root = tmp_path / "owned"
    with pytest.raises(ValueError):
        OwnedProcessSpec(
            allowed_root=root,
            cwd=root,
            pid_path=root / "run" / "runtime.pid",
            stdout_path=root / "logs" / "stdout.log",
            stderr_path=root / "logs" / "stderr.log",
            command=(sys.executable, "--marker", "owned-marker"),
            expected_executable_name=Path(sys.executable).name,
            expected_profile_marker="owned-marker",
            environment_overrides=overrides,
        )


def test_spec_rejects_serena_home_outside_allowed_root(tmp_path: Path) -> None:
    root = tmp_path / "owned"
    with pytest.raises(ValueError, match="SERENA_HOME"):
        OwnedProcessSpec(
            allowed_root=root,
            cwd=root,
            pid_path=root / "run" / "runtime.pid",
            stdout_path=root / "logs" / "stdout.log",
            stderr_path=root / "logs" / "stderr.log",
            command=(sys.executable, "--marker", "owned-marker"),
            expected_executable_name=Path(sys.executable).name,
            expected_profile_marker="owned-marker",
            environment_overrides=(("SERENA_HOME", str(tmp_path / "outside")),),
        )


def test_spawner_uses_safe_inherited_environment_plus_overrides(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "owned"
    runtime = OwnedProcessSpec(
        allowed_root=root,
        cwd=root,
        pid_path=root / "run" / "runtime.pid",
        stdout_path=root / "logs" / "stdout.log",
        stderr_path=root / "logs" / "stderr.log",
        command=(sys.executable, "--marker", "owned-marker"),
        expected_executable_name=Path(sys.executable).name,
        expected_profile_marker="owned-marker",
        environment_overrides=(("SERENA_HOME", str(root / "serena-home")),),
    )
    captured = {}

    def fake_popen(argv, **kwargs):
        captured["argv"] = argv
        captured.update(kwargs)
        return FakeChild(pid=45678)

    monkeypatch.setattr("a_conductor.owned_process.subprocess.Popen", fake_popen)
    source = {
        "Path": r"C:\\Tools",
        "SYSTEMROOT": r"C:\\Windows",
        "TEMP": r"C:\\Temp",
        "OPENAI_API_KEY": "parent-secret",
        "CUSTOM_SECRET": "also-secret",
        "SERENA_HOME": "wrong-parent-home",
    }

    child = WindowsProcessSpawner(environment_source=source).spawn(runtime)

    assert child.pid == 45678
    env = captured["env"]
    assert env["Path"] == source["Path"]
    assert env["SYSTEMROOT"] == source["SYSTEMROOT"]
    assert env["TEMP"] == source["TEMP"]
    assert env["SERENA_HOME"] == str((root / "serena-home").resolve())
    assert "OPENAI_API_KEY" not in env
    assert "CUSTOM_SECRET" not in env
    assert captured["shell"] is False
