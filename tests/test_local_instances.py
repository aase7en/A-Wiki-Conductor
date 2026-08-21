from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.local_instances import (
    DEFAULT_INSTANCES_ROOT,
    InstanceHealthState,
    InstanceOrchestrationOutcome,
    InstanceResultCode,
    LocalInstance,
    LocalInstanceOrchestrator,
    discover_local_instances,
    instance_health_state,
)


def make_instance_dir(
    root: Path,
    folder: str,
    *,
    name: str = "Serena-Demo",
    project: str = r"A:\GitHub\demo",
    address: str = "127.0.0.1:18999",
    with_scripts: bool = True,
    extra_line: str = "",
) -> Path:
    instance_root = root / folder
    instance_root.mkdir(parents=True)
    lines = [
        "# demo instance",
        f"$InstanceName = '{name}'",
        f"$ProjectPath = '{project}'",
        f"$HealthListenAddress = '{address}'",
    ]
    if extra_line:
        lines.append(extra_line)
    (instance_root / "instance.ps1").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if with_scripts:
        (instance_root / "Start-Serena-Demo.cmd").write_text("@echo off\r\n", encoding="utf-8")
        (instance_root / "Stop-Serena-Demo.cmd").write_text("@echo off\r\n", encoding="utf-8")
    return instance_root


class _Observation:
    def __init__(self, state: str, error_code: str | None) -> None:
        self.state = state
        self.error_code = error_code


def _observation_for(state: InstanceHealthState) -> _Observation:
    if state is InstanceHealthState.READY:
        return _Observation("READY", None)
    if state is InstanceHealthState.STOPPED:
        return _Observation("NOT_READY", "TRANSPORT_ERROR")
    return _Observation("NOT_READY", "HTTP_503")


class FakeProbe:
    def __init__(self, states: list[InstanceHealthState]) -> None:
        self.states = list(states)
        self.calls = 0

    def get(self, url: str, timeout_seconds: int):
        self.calls += 1
        state = self.states.pop(0) if self.states else InstanceHealthState.STOPPED
        return _observation_for(state)


def probe_returning(state: InstanceHealthState):
    class Probe:
        def __init__(self) -> None:
            self.calls = 0

        def get(self, url: str, timeout_seconds: int):
            self.calls += 1
            return _observation_for(state)

    return Probe()


def test_discovery_parses_instance_ps1_fields(tmp_path: Path) -> None:
    make_instance_dir(tmp_path, "demo", name="Serena-Demo", project=r"A:\GitHub\demo", address="127.0.0.1:18999")
    (tmp_path / "not-an-instance").mkdir()

    instances = discover_local_instances(tmp_path)

    assert len(instances) == 1
    instance = instances[0]
    assert instance.name == "Serena-Demo"
    assert instance.project_path == r"A:\GitHub\demo"
    assert instance.health_address == "127.0.0.1:18999"
    assert instance.instance_root == (tmp_path / "demo").resolve()


def test_discovery_skips_incomplete_instance_files(tmp_path: Path) -> None:
    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / "instance.ps1").write_text(
        "$InstanceName = 'OnlyName'\n", encoding="utf-8"
    )

    assert discover_local_instances(tmp_path) == ()


def test_default_instances_root_is_configured() -> None:
    assert "serena-instances" in str(DEFAULT_INSTANCES_ROOT)


def test_health_state_maps_probe_results(tmp_path: Path) -> None:
    make_instance_dir(tmp_path, "demo")
    instance = discover_local_instances(tmp_path)[0]

    ready = instance_health_state(instance, probe=probe_returning(InstanceHealthState.READY))
    down = instance_health_state(instance, probe=probe_returning(InstanceHealthState.STOPPED))
    unknown = instance_health_state(instance, probe=probe_returning(InstanceHealthState.UNKNOWN))

    assert (ready, down, unknown) == (
        InstanceHealthState.READY,
        InstanceHealthState.STOPPED,
        InstanceHealthState.UNKNOWN,
    )


def test_orchestrator_start_already_ready_does_not_launch(tmp_path: Path) -> None:
    make_instance_dir(tmp_path, "demo")
    instance = discover_local_instances(tmp_path)[0]
    launched: list[Path] = []

    orchestrator = LocalInstanceOrchestrator(
        instances_root=tmp_path,
        probe=probe_returning(InstanceHealthState.READY),
        launcher=lambda script, cwd: launched.append(script),
    )

    outcome = orchestrator.start(instance)

    assert outcome.result_code is InstanceResultCode.ALREADY_RUNNING
    assert launched == []
    assert outcome.exit_code is None


def test_orchestrator_start_launches_and_polls_to_ready(tmp_path: Path) -> None:
    make_instance_dir(tmp_path, "demo")
    instance = discover_local_instances(tmp_path)[0]
    launched: list[Path] = []
    poll_states = [
        InstanceHealthState.STOPPED,   # pre-check
        InstanceHealthState.STOPPED,   # first poll
        InstanceHealthState.STOPPED,   # second poll
        InstanceHealthState.READY,     # third poll
    ]
    probe = FakeProbe(poll_states)
    sleeps: list[float] = []
    now = {"t": 0.0}

    def fake_sleep(seconds: float) -> None:
        now["t"] += seconds
        sleeps.append(seconds)

    orchestrator = LocalInstanceOrchestrator(
        instances_root=tmp_path,
        probe=probe,
        launcher=lambda script, cwd: launched.append(script),
        sleep_fn=fake_sleep,
        clock_fn=lambda: now["t"],
    )

    outcome = orchestrator.start(instance)

    assert outcome.result_code is InstanceResultCode.RUNNING
    assert len(launched) == 1
    assert launched[0].name == "Start-Serena-Demo.cmd"
    assert launched[0].parent == instance.instance_root
    assert len(sleeps) >= 2


def test_orchestrator_start_timeout_reports_not_ready(tmp_path: Path) -> None:
    make_instance_dir(tmp_path, "demo")
    instance = discover_local_instances(tmp_path)[0]

    now = {"t": 0.0}

    orchestrator = LocalInstanceOrchestrator(
        instances_root=tmp_path,
        probe=probe_returning(InstanceHealthState.STOPPED),
        launcher=lambda script, cwd: None,
        sleep_fn=lambda s: now.__setitem__("t", now["t"] + s),
        clock_fn=lambda: now["t"],
        startup_timeout_seconds=1,
        poll_interval_seconds=0.1,
    )

    outcome = orchestrator.start(instance)

    assert outcome.result_code is InstanceResultCode.STARTED_NOT_READY


def test_orchestrator_start_rejects_instance_outside_root(tmp_path: Path) -> None:
    make_instance_dir(tmp_path, "demo")
    instance = discover_local_instances(tmp_path)[0]
    other_root = tmp_path / "elsewhere"

    orchestrator = LocalInstanceOrchestrator(
        instances_root=other_root,
        probe=probe_returning(InstanceHealthState.STOPPED),
        launcher=lambda script, cwd: None,
    )

    with pytest.raises(RuntimeError) as exc:
        orchestrator.start(instance)
    assert "INSTANCE_OUTSIDE_ROOT" in str(exc.value)


def test_orchestrator_start_missing_script_fails_closed(tmp_path: Path) -> None:
    make_instance_dir(tmp_path, "demo", with_scripts=False)
    instance = discover_local_instances(tmp_path)[0]

    orchestrator = LocalInstanceOrchestrator(
        instances_root=tmp_path,
        probe=probe_returning(InstanceHealthState.STOPPED),
        launcher=lambda script, cwd: None,
    )

    outcome = orchestrator.start(instance)
    assert outcome.result_code is InstanceResultCode.SCRIPT_MISSING


def test_orchestrator_stop_waits_script_and_confirms(tmp_path: Path) -> None:
    make_instance_dir(tmp_path, "demo")
    instance = discover_local_instances(tmp_path)[0]
    waited: list[tuple[list[str], int]] = []
    # pre-check says READY, after-stop check says STOPPED
    probe = FakeProbe([InstanceHealthState.READY, InstanceHealthState.STOPPED])

    def waiter(argv: list[str], timeout: int) -> tuple[int, str]:
        waited.append((argv, timeout))
        return 0, "... STOPPED"

    orchestrator = LocalInstanceOrchestrator(
        instances_root=tmp_path,
        probe=probe,
        launcher=lambda script, cwd: None,
        waiter=waiter,
    )

    outcome = orchestrator.stop(instance)

    assert outcome.result_code is InstanceResultCode.STOPPED
    assert len(waited) == 1
    assert waited[0][0][0].endswith("cmd.exe")
    assert any("Stop-Serena-Demo.cmd" in part for part in waited[0][0])
    assert outcome.exit_code == 0


def test_orchestrator_stop_already_stopped_skips_script(tmp_path: Path) -> None:
    make_instance_dir(tmp_path, "demo")
    instance = discover_local_instances(tmp_path)[0]
    waited: list[tuple[list[str], int]] = []

    orchestrator = LocalInstanceOrchestrator(
        instances_root=tmp_path,
        probe=probe_returning(InstanceHealthState.STOPPED),
        launcher=lambda script, cwd: None,
        waiter=lambda argv, timeout: waited.append((argv, timeout)) or (0, ""),
    )

    outcome = orchestrator.stop(instance)

    assert outcome.result_code is InstanceResultCode.ALREADY_STOPPED
    assert waited == []


def test_orchestrator_stop_failure_reports_output(tmp_path: Path) -> None:
    make_instance_dir(tmp_path, "demo")
    instance = discover_local_instances(tmp_path)[0]
    probe = FakeProbe([InstanceHealthState.READY, InstanceHealthState.READY])

    orchestrator = LocalInstanceOrchestrator(
        instances_root=tmp_path,
        probe=probe,
        launcher=lambda script, cwd: None,
        waiter=lambda argv, timeout: (2, "PID_MISMATCH: refusing"),
    )

    outcome = orchestrator.stop(instance)

    assert outcome.result_code is InstanceResultCode.STOP_FAILED
    assert outcome.exit_code == 2
    assert "PID_MISMATCH" in outcome.output_tail
