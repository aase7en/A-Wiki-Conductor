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
    from a_conductor.platform_support import default_instances_root

    assert "serena-instances" in str(default_instances_root())


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


def test_orchestrator_start_applies_brain_before_launch(tmp_path: Path) -> None:
    from a_conductor.worker_serena_settings import WorkerSerenaSettings

    make_instance_dir(tmp_path, "demo")
    instance = discover_local_instances(tmp_path)[0]
    calls: list[str] = []
    poll_states = [
        InstanceHealthState.STOPPED,   # pre-check
        InstanceHealthState.READY,     # first poll after launch
    ]
    probe = FakeProbe(poll_states)
    profile = WorkerSerenaSettings(
        worker_id="global-brain",
        brain_folders=(r"A:\GitHub\A-Wiki",),
    )

    orchestrator = LocalInstanceOrchestrator(
        instances_root=tmp_path,
        probe=probe,
        launcher=lambda script, cwd: calls.append("launch"),
        sleep_fn=lambda _s: None,
        clock_fn=lambda: 0.0,
        brain_settings_provider=lambda: profile,
        brain_applier=lambda inst, prof: calls.append("brain") or "APPLIED",
    )

    outcome = orchestrator.start(instance)

    assert outcome.result_code is InstanceResultCode.RUNNING
    assert calls == ["brain", "launch"]


def test_orchestrator_start_without_provider_skips_brain(tmp_path: Path) -> None:
    make_instance_dir(tmp_path, "demo")
    instance = discover_local_instances(tmp_path)[0]
    calls: list[str] = []

    orchestrator = LocalInstanceOrchestrator(
        instances_root=tmp_path,
        probe=FakeProbe([InstanceHealthState.STOPPED, InstanceHealthState.READY]),
        launcher=lambda script, cwd: calls.append("launch"),
        sleep_fn=lambda _s: None,
        clock_fn=lambda: 0.0,
        brain_applier=lambda inst, prof: calls.append("brain") or "APPLIED",
    )

    outcome = orchestrator.start(instance)

    assert outcome.result_code is InstanceResultCode.RUNNING
    assert calls == ["launch"]


def test_discovery_reports_tunnel_configured_flag(tmp_path: Path) -> None:
    make_instance_dir(tmp_path, "demo")
    (tmp_path / "demo" / "config").mkdir()
    (tmp_path / "demo" / "config" / "tunnel-id.txt").write_text(
        "tunnel_" + "a1b2c3d4" * 4 + "\n", encoding="utf-8"
    )
    make_instance_dir(tmp_path, "other", name="Serena-Other")

    instances = {item.name: item for item in discover_local_instances(tmp_path)}

    assert instances["Serena-Demo"].tunnel_configured is True
    assert instances["Serena-Other"].tunnel_configured is False


def test_facade_set_instance_tunnel_id_validates_and_writes(tmp_path: Path) -> None:
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.serena_config_store import SerenaConfigStoreError

    make_instance_dir(tmp_path, "demo")
    service = DesktopControlService(
        control_center=object(),
        lifecycle=object(),
        instances_root=tmp_path,
    )
    valid = "tunnel_" + "0123abcd" * 4

    written = service.set_instance_tunnel_id("Serena-Demo", valid)
    assert written == (tmp_path / "demo" / "config" / "tunnel-id.txt").resolve()
    assert written.read_text(encoding="utf-8").strip() == valid

    instances = {item.name: item for item in service.instances()}
    assert instances["Serena-Demo"].tunnel_configured is True

    for bad in ("not-a-tunnel", "tunnel_xyz", "", "tunnel_" + "z" * 32):
        try:
            service.set_instance_tunnel_id("Serena-Demo", bad)
        except SerenaConfigStoreError as exc:
            assert "TUNNEL_ID_INVALID" in str(exc)
        else:
            raise AssertionError(f"invalid id accepted: {bad!r}")

    try:
        service.set_instance_tunnel_id("Serena-Missing", valid)
    except SerenaConfigStoreError as exc:
        assert "INSTANCE_NOT_FOUND" in str(exc)
    else:
        raise AssertionError("missing instance accepted")


def make_full_instance_dir(root: Path, folder: str, project: str) -> Path:
    instance_root = make_instance_dir(root, folder, project=project)
    template = instance_root / "profiles" / "serena-demo.yaml.template"
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text(
        "config_version: 1\n"
        '  tunnel_id: "__TUNNEL_ID__"\n'
        "mcp:\n"
        "  commands:\n"
        "    - channel: main\n"
        f"      command: 'serena start-mcp-server --context chatgpt --project {project.replace(chr(92), '/')} --enable-web-dashboard false'\n",
        encoding="utf-8",
    )
    return instance_root


def _to_fwd(path: str) -> str:
    return path.replace(chr(92), "/")


def test_rebind_instance_project_rewrites_both_files(tmp_path: Path) -> None:
    from a_conductor.instance_rebind import rebind_instance_project

    real_new = tmp_path / "new-project"
    real_new.mkdir()
    make_full_instance_dir(tmp_path, "demo", r"A:\GitHub\old-project")
    instances = {i.name: i for i in discover_local_instances(tmp_path)}
    assert instances["Serena-Demo"].project_path == r"A:\GitHub\old-project"

    result = rebind_instance_project(instances["Serena-Demo"], tmp_path, str(real_new))

    assert result == "REBOUND"
    ps1 = (tmp_path / "demo" / "instance.ps1").read_text(encoding="utf-8")
    template = (tmp_path / "demo" / "profiles" / "serena-demo.yaml.template").read_text(encoding="utf-8")
    assert f"$ProjectPath = '{real_new}'" in ps1
    assert _to_fwd(str(real_new)) in template
    assert r"A:\GitHub\old-project" not in ps1

    # backups exist
    assert (tmp_path / "demo" / "instance.ps1.bak").is_file()
    assert (tmp_path / "demo" / "profiles" / "serena-demo.yaml.template.bak").is_file()

    # discovery reflects the new binding
    refreshed = {i.name: i for i in discover_local_instances(tmp_path)}
    assert refreshed["Serena-Demo"].project_path == str(real_new)


def test_rebind_idempotent_same_project(tmp_path: Path) -> None:
    from a_conductor.instance_rebind import rebind_instance_project

    same_dir = tmp_path / "same"
    same_dir.mkdir()
    make_full_instance_dir(tmp_path, "demo", str(same_dir))
    instance = {i.name: i for i in discover_local_instances(tmp_path)}["Serena-Demo"]

    result = rebind_instance_project(instance, tmp_path, str(same_dir))
    assert result == "SKIPPED_SAME_PROJECT"
    assert not (tmp_path / "demo" / "instance.ps1.bak").exists()


def test_rebind_guards(tmp_path: Path) -> None:
    from a_conductor.instance_rebind import rebind_instance_project

    make_full_instance_dir(tmp_path, "demo", r"A:\GitHub\old")
    instance = {i.name: i for i in discover_local_instances(tmp_path)}["Serena-Demo"]

    # outside root
    try:
        rebind_instance_project(instance, tmp_path / "elsewhere", str(tmp_path))
    except RuntimeError as exc:
        assert "INSTANCE_OUTSIDE_ROOT" in str(exc)
    else:
        raise AssertionError("outside root accepted")

    # non-absolute new path
    assert rebind_instance_project(instance, tmp_path, "relative/path") == "SKIPPED_PATH_INVALID"

    # nonexistent new path
    assert rebind_instance_project(instance, tmp_path, str(tmp_path / "nope")) == "SKIPPED_PATH_NOT_FOUND"

    # missing template file
    (tmp_path / "demo" / "profiles" / "serena-demo.yaml.template").unlink()
    assert rebind_instance_project(instance, tmp_path, str(tmp_path)) == "TEMPLATE_MISSING"
