from pathlib import Path

import pytest

from a_conductor.runtime_safety import PortBindingState, ProcessOwnership, classify_process_ownership
from a_conductor.windows_observer import (
    CommandResult,
    HealthProbeObservation,
    HealthProbeState,
    PidMetadataStatus,
    WindowsRuntimeObserver,
)


class FakeRunner:
    def __init__(self, results: list[CommandResult]) -> None:
        self.results = list(results)
        self.calls: list[tuple[tuple[str, ...], int]] = []

    def run(self, argv: tuple[str, ...], timeout_seconds: int) -> CommandResult:
        self.calls.append((argv, timeout_seconds))
        return self.results.pop(0)


class FakeHttpProbe:
    def __init__(self, observation: HealthProbeObservation) -> None:
        self.observation = observation
        self.calls: list[tuple[str, int]] = []

    def get(self, url: str, timeout_seconds: int) -> HealthProbeObservation:
        self.calls.append((url, timeout_seconds))
        return self.observation


def make_observer(
    results: list[CommandResult] | None = None,
    health: HealthProbeObservation | None = None,
) -> tuple[WindowsRuntimeObserver, FakeRunner, FakeHttpProbe]:
    runner = FakeRunner(results or [])
    probe = FakeHttpProbe(
        health
        or HealthProbeObservation(
            state=HealthProbeState.READY,
            status_code=200,
            error_code=None,
        )
    )
    return WindowsRuntimeObserver(runner=runner, http_probe=probe), runner, probe


def test_pid_metadata_absent_is_read_only(tmp_path: Path) -> None:
    observer, runner, _ = make_observer()
    pid_path = tmp_path / "runtime.pid"

    metadata = observer.read_pid_metadata(pid_path)

    assert metadata.status is PidMetadataStatus.ABSENT
    assert metadata.pid is None
    assert not pid_path.exists()
    assert runner.calls == []


def test_pid_metadata_invalid_is_not_deleted(tmp_path: Path) -> None:
    observer, _, _ = make_observer()
    pid_path = tmp_path / "runtime.pid"
    pid_path.write_text("not-a-pid", encoding="utf-8")

    metadata = observer.read_pid_metadata(pid_path)

    assert metadata.status is PidMetadataStatus.INVALID
    assert metadata.pid is None
    assert pid_path.read_text(encoding="utf-8") == "not-a-pid"


def test_pid_metadata_valid_parses_positive_pid(tmp_path: Path) -> None:
    observer, _, _ = make_observer()
    pid_path = tmp_path / "runtime.pid"
    pid_path.write_text("1234\n", encoding="utf-8")

    metadata = observer.read_pid_metadata(pid_path)

    assert metadata.status is PidMetadataStatus.VALID
    assert metadata.pid == 1234


@pytest.mark.parametrize("text", ["0", "-1", "", "  "])
def test_non_positive_or_empty_pid_metadata_is_invalid(tmp_path: Path, text: str) -> None:
    observer, _, _ = make_observer()
    pid_path = tmp_path / "runtime.pid"
    pid_path.write_text(text, encoding="utf-8")

    assert observer.read_pid_metadata(pid_path).status is PidMetadataStatus.INVALID


def test_process_observation_queries_exact_pid_and_redacts_command_line() -> None:
    process_json = (
        '{"ProcessId":1234,"Name":"runtime.exe",'
        '"ExecutablePath":"C:\\\\tools\\\\runtime.exe",'
        '"CommandLine":"runtime.exe --profile-file C:\\\\run\\\\worker-01.yaml --secret hidden"}'
    )
    observer, runner, _ = make_observer(
        [CommandResult(return_code=0, stdout=process_json, stderr="")]
    )

    observation = observer.observe_process(
        pid=1234,
        expected_executable_name="runtime.exe",
        expected_profile_marker="worker-01.yaml",
    )

    assert classify_process_ownership(observation) is ProcessOwnership.OWNED
    assert not hasattr(observation, "command_line")
    argv, timeout = runner.calls[0]
    assert timeout == 5
    script = argv[-1]
    assert "ProcessId=1234" in script
    assert "Get-CimInstance Win32_Process" in script
    assert "hidden" not in repr(observation)


def test_process_observation_missing_process_returns_process_exists_false() -> None:
    observer, _, _ = make_observer(
        [CommandResult(return_code=0, stdout="", stderr="")]
    )

    observation = observer.observe_process(
        pid=1234,
        expected_executable_name="runtime.exe",
        expected_profile_marker="worker-01.yaml",
    )

    assert observation.process_exists is False
    assert observation.executable_matches is None
    assert observation.profile_matches is None


def test_process_observation_nonzero_runner_result_is_unknown() -> None:
    observer, _, _ = make_observer(
        [CommandResult(return_code=1, stdout="", stderr="access denied")]
    )

    observation = observer.observe_process(
        pid=1234,
        expected_executable_name="runtime.exe",
        expected_profile_marker="worker-01.yaml",
    )

    assert observation.process_exists is None
    assert classify_process_ownership(observation) is ProcessOwnership.UNKNOWN


@pytest.mark.parametrize("pid", [0, -1])
def test_process_observation_rejects_invalid_pid_before_runner(pid: int) -> None:
    observer, runner, _ = make_observer()

    with pytest.raises(ValueError, match="pid must be >= 1"):
        observer.observe_process(
            pid=pid,
            expected_executable_name="runtime.exe",
            expected_profile_marker="worker-01.yaml",
        )

    assert runner.calls == []


def test_port_observation_queries_exact_port_and_classifies_owner() -> None:
    port_json = '{"LocalAddress":"127.0.0.1","LocalPort":18011,"OwningProcess":1234}'
    observer, runner, _ = make_observer(
        [CommandResult(return_code=0, stdout=port_json, stderr="")]
    )

    state = observer.observe_port_binding(port=18011, expected_pid=1234)

    assert state is PortBindingState.OWNED
    script = runner.calls[0][0][-1]
    assert "LocalPort 18011" in script
    assert "Get-NetTCPConnection" in script


def test_port_observation_empty_result_is_free() -> None:
    observer, _, _ = make_observer(
        [CommandResult(return_code=0, stdout="", stderr="")]
    )

    assert observer.observe_port_binding(port=18011, expected_pid=None) is PortBindingState.FREE


@pytest.mark.parametrize("port", [0, -1, 65536])
def test_port_observation_rejects_invalid_port_before_runner(port: int) -> None:
    observer, runner, _ = make_observer()

    with pytest.raises(ValueError, match="port must be between 1 and 65535"):
        observer.observe_port_binding(port=port, expected_pid=None)

    assert runner.calls == []


def test_ready_probe_is_loopback_bounded_and_read_only() -> None:
    ready = HealthProbeObservation(
        state=HealthProbeState.READY,
        status_code=200,
        error_code=None,
    )
    observer, _, probe = make_observer(health=ready)

    observation = observer.probe_ready(
        health_host="127.0.0.1",
        health_port=18011,
        timeout_seconds=2,
    )

    assert observation is ready
    assert probe.calls == [("http://127.0.0.1:18011/readyz", 2)]


@pytest.mark.parametrize("host", ["example.com", "10.0.0.5", "0.0.0.0"])
def test_ready_probe_rejects_non_loopback_targets(host: str) -> None:
    observer, _, probe = make_observer()

    with pytest.raises(ValueError, match="loopback"):
        observer.probe_ready(health_host=host, health_port=18011, timeout_seconds=2)

    assert probe.calls == []


def test_observer_generated_commands_contain_no_mutation_primitives() -> None:
    process_json = '{"ProcessId":1234,"Name":"runtime.exe","ExecutablePath":null,"CommandLine":"runtime.exe worker-01.yaml"}'
    port_json = '{"LocalAddress":"127.0.0.1","LocalPort":18011,"OwningProcess":1234}'
    observer, runner, _ = make_observer(
        [
            CommandResult(return_code=0, stdout=process_json, stderr=""),
            CommandResult(return_code=0, stdout=port_json, stderr=""),
        ]
    )

    observer.observe_process(
        pid=1234,
        expected_executable_name="runtime.exe",
        expected_profile_marker="worker-01.yaml",
    )
    observer.observe_port_binding(port=18011, expected_pid=1234)

    combined = "\n".join(call[0][-1] for call in runner.calls).lower()
    for forbidden in (
        "stop-process",
        "start-process",
        "remove-item",
        "taskkill",
        "set-content",
        "new-item",
    ):
        assert forbidden not in combined
