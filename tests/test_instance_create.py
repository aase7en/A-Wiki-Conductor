"""WO-P1-060 PR-B: materialize a new connector instance from a reference."""

from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.instance_create import (
    InstanceCreateError,
    _RuntimeForensicsHardeningState,
    _classify_start_script_runtime_forensics,
    _harden_start_script_runtime_forensics,
    create_instance,
    next_health_port,
)
from a_conductor.local_instances import discover_local_instances


def make_reference(root: Path) -> Path:
    ref = root / "wastewater"
    (ref / "profiles").mkdir(parents=True)
    (ref / "serena-home").mkdir()
    (ref / "config").mkdir()
    (ref / "instance.ps1").write_text(
        "\n".join(
            [
                "# Serena-Wastewater instance configuration",
                "$InstanceName = 'Serena-Wastewater'",
                "$ProjectPath = 'A:\\GitHub\\demo-old'",
                "$SerenaHome = 'C:\\AI\\serena-instances\\wastewater\\serena-home'",
                "$HealthListenAddress = '127.0.0.1:48113'",
                "$TunnelProfileName = 'serena-wastewater'",
                "$TunnelClientPath = 'C:\\AI\\tunnel\\tunnel-client.exe'",
                "$LegacySecretPath = 'C:\\AI\\tunnel\\secret.dpapi'",
            ]
        ),
        encoding="utf-8",
    )
    (ref / "start.ps1").write_text(
        "$ProfileTemplate = Join-Path $ProfilesDir 'serena-wastewater.yaml.template'\n"
        "$RuntimeProfile = Join-Path $RunDir 'serena-wastewater.yaml'\n"
        "$LogFile = Join-Path $LogsDir ('wastewater-' + $day)\n",
        encoding="utf-8",
    )
    (ref / "stop.ps1").write_text(
        "$RuntimeProfile = Join-Path $RunDir 'serena-wastewater.yaml'\n"
        "$LogFile = Join-Path $LogsDir ('wastewater-' + $day)\n",
        encoding="utf-8",
    )
    (ref / "Start-Serena-Wastewater.cmd").write_text(
        "@echo off\ntitle Sunday-works 3 - Wastewater\npowershell.exe -File start.ps1\n",
        encoding="utf-8",
    )
    (ref / "Stop-Serena-Wastewater.cmd").write_text(
        "@echo off\ntitle Sunday-works 3 - Stop\npowershell.exe -File stop.ps1\n",
        encoding="utf-8",
    )
    (ref / "profiles" / "serena-wastewater.yaml.template").write_text(
        "server:\n  listen_addr: 127.0.0.1:48113\nargs:\n  - --project A:/GitHub/demo-old\ntunnel_id: __TUNNEL_ID__\n",
        encoding="utf-8",
    )
    (ref / "serena-home" / "serena_config.yml").write_text(
        "projects:\n- 'A:\\GitHub\\demo-old'\n",
        encoding="utf-8",
    )
    return ref


@pytest.fixture()
def sandbox(tmp_path: Path):
    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    project = tmp_path / "my-project"
    project.mkdir()
    return instances_root, make_reference(instances_root), project


def test_create_instance_materializes_full_layout(sandbox) -> None:
    instances_root, ref, project = sandbox
    created = create_instance(
        instances_root,
        "Research",
        project,
        health_port=48114,
        reference_root=ref,
        work_number=4,
    )

    assert (created / "instance.ps1").is_file()
    ps1 = (created / "instance.ps1").read_text(encoding="utf-8")
    assert "$InstanceName = 'Serena-Research'" in ps1
    assert "$HealthListenAddress = '127.0.0.1:48114'" in ps1
    assert str(project) in ps1
    assert "tunnel-client.exe" in ps1  # shared paths carried from reference

    start = (created / "start.ps1").read_text(encoding="utf-8")
    assert "serena-research.yaml.template" in start
    assert "serena-research.yaml" in start
    assert "'research-'" in start
    assert "wastewater" not in start

    start_cmd = (created / "Start-Serena-Research.cmd").read_text(encoding="utf-8")
    assert "title Sunday-works 4 - Research" in start_cmd
    assert sum(1 for line in start_cmd.splitlines() if line.lower().startswith("title ")) == 1

    template = (created / "profiles" / "serena-research.yaml.template").read_text(
        encoding="utf-8"
    )
    assert "127.0.0.1:48114" in template
    assert f'--project "{project.as_posix()}"' in template
    assert "__TUNNEL_ID__" in template

    config = (created / "serena-home" / "serena_config.yml").read_text(encoding="utf-8")
    assert f"projects:\n- '{project}'" in config

    assert (created / "run").is_dir()
    assert (created / "logs").is_dir()


def test_created_instance_is_discoverable(sandbox) -> None:
    instances_root, ref, project = sandbox
    create_instance(
        instances_root, "Research", project, health_port=48114, reference_root=ref
    )
    instances = discover_local_instances(instances_root)
    names = {instance.name for instance in instances}
    assert "Serena-Wastewater" in names
    assert "Serena-Research" in names


def test_create_instance_with_tunnel_id_writes_config(sandbox) -> None:
    instances_root, ref, project = sandbox
    tunnel = "tunnel_" + "a" * 32
    created = create_instance(
        instances_root,
        "Research",
        project,
        health_port=48114,
        tunnel_id=tunnel,
        reference_root=ref,
    )
    assert (created / "config" / "tunnel-id.txt").read_text(encoding="utf-8").strip() == tunnel


def test_create_instance_guards(sandbox) -> None:
    instances_root, ref, project = sandbox
    create_instance(
        instances_root, "Research", project, health_port=48114, reference_root=ref
    )
    with pytest.raises(InstanceCreateError) as exc:
        create_instance(
            instances_root, "research", project, health_port=48115, reference_root=ref
        )
    assert exc.value.code == "NAME_ALREADY_EXISTS"

    with pytest.raises(InstanceCreateError) as exc:
        create_instance(
            instances_root, "Bad Name!", project, health_port=48115, reference_root=ref
        )
    assert exc.value.code == "NAME_INVALID"

    with pytest.raises(InstanceCreateError) as exc:
        create_instance(
            instances_root,
            "Other",
            instances_root / "missing",
            health_port=48115,
            reference_root=ref,
        )
    assert exc.value.code == "PROJECT_NOT_FOUND"

    with pytest.raises(InstanceCreateError) as exc:
        create_instance(
            instances_root,
            "Other",
            project,
            health_port=48115,
            tunnel_id="nope",
            reference_root=ref,
        )
    assert exc.value.code == "TUNNEL_ID_INVALID"

    empty_root = instances_root.parent / "empty-instances"
    empty_root.mkdir()
    with pytest.raises(InstanceCreateError) as exc:
        create_instance(empty_root, "Other", project, health_port=48115)
    assert exc.value.code == "REFERENCE_MISSING"


def test_create_instance_auto_reference_and_work_number(sandbox) -> None:
    instances_root, _ref, project = sandbox
    created = create_instance(instances_root, "Research", project, health_port=48114)
    cmd = (created / "Start-Serena-Research.cmd").read_text(encoding="utf-8")
    # sandbox has exactly one reference instance -> next window number is 2
    assert "title Sunday-works 2 - Research" in cmd


def test_next_health_port_is_max_plus_one(sandbox) -> None:
    instances_root, ref, project = sandbox
    create_instance(
        instances_root, "Research", project, health_port=48200, reference_root=ref
    )
    instances = discover_local_instances(instances_root)
    assert next_health_port(instances) == 48201


# --- facade --------------------------------------------------------------


def test_facade_creates_instance_and_lists_it(tmp_path: Path) -> None:
    from a_conductor.desktop_control import DesktopControlService

    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    make_reference(instances_root)
    project = tmp_path / "proj"
    project.mkdir()

    service = DesktopControlService.open(
        tmp_path / "cc.sqlite", instances_root=instances_root
    )
    created = service.create_instance("Research", str(project))
    assert created.name == "Serena-Research"
    names = {instance.name for instance in service.instances()}
    assert "Serena-Research" in names


# --- UI ------------------------------------------------------------------


@pytest.fixture()
def root():
    import tkinter as tk

    try:
        window = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk display unavailable: {exc}")
    window.withdraw()
    yield window
    try:
        window.destroy()
    except tk.TclError:
        pass


def test_add_instance_button_and_flow(root, tmp_path: Path) -> None:
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    make_reference(instances_root)
    project = tmp_path / "proj"
    project.mkdir()

    service = DesktopControlService.open(
        tmp_path / "ui.sqlite", instances_root=instances_root
    )
    app = AConductorDesktopApp(root, service=service)

    assert app.add_instance_button is not None
    app.add_instance("Research", str(project))

    names = {instance.name for instance in service.instances()}
    assert "Serena-Research" in names


def test_add_instance_missing_fields_shows_error(root, tmp_path: Path, monkeypatch) -> None:
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    service = DesktopControlService.open(
        tmp_path / "ui.sqlite", instances_root=instances_root
    )
    app = AConductorDesktopApp(root, service=service)

    codes: list[str] = []
    monkeypatch.setattr(app, "_handle_error", lambda code: codes.append(code))
    app.add_instance("bad name!", str(tmp_path))
    assert codes and codes[0] == "NAME_INVALID"


def test_create_instance_hardens_legacy_reference_runtime_forensics(sandbox) -> None:
    instances_root, ref, project = sandbox
    (ref / "start.ps1").write_text(
        "$ProfilesDir = Join-Path $Root 'profiles'\n"
        "$RunDir = Join-Path $Root 'run'\n"
        "$LogsDir = Join-Path $Root 'logs'\n"
        "$ProfileTemplate = Join-Path $ProfilesDir 'serena-wastewater.yaml.template'\n"
        "$RuntimeProfile = Join-Path $RunDir 'serena-wastewater.yaml'\n"
        "$RuntimeStdout = Join-Path $LogsDir 'wastewater-runtime.stdout.log'\n"
        "$RuntimeStderr = Join-Path $LogsDir 'wastewater-runtime.stderr.log'\n"
        "Write-Log \"STARTING: health=$HealthListenAddress project=$ProjectPath\"\n"
        "$RuntimeProcess = Start-Process -FilePath $TunnelClientPath -PassThru\n"
        "Wait-Process -Id $RuntimeProcess.Id\n",
        encoding="utf-8",
    )
    created = create_instance(
        instances_root, "Research", project, health_port=48114, reference_root=ref
    )
    start = (created / "start.ps1").read_text(encoding="utf-8")
    assert "runtime-archive" in start
    assert "$RuntimeProcess.WaitForExit()" in start
    assert "$RuntimeProcess.ExitCode" in start
    assert "TUNNEL_START_FAILED" in start
    assert "exit_code=" in start


def _legacy_method_wait_launcher() -> str:
    return (
        "$RuntimeStdout = Join-Path $LogsDir 'runtime.stdout.log'\n"
        "$RuntimeStderr = Join-Path $LogsDir 'runtime.stderr.log'\n"
        "$DpapiSentinel = 'DPAPI_SENTINEL'\n"
        "$TunnelValidationSentinel = 'TUNNEL_SENTINEL'\n"
        "$ProjectValidationSentinel = 'PROJECT_SENTINEL'\n"
        "$DoctorSentinel = 'DOCTOR_SENTINEL'\n"
        "$EnvironmentSentinel = 'ENV_SENTINEL'\n"
        "Write-Log \"STARTING: health=$HealthListenAddress project=$ProjectPath\"\n"
        "try {\n"
        "    $RuntimeProcess = Start-Process -FilePath $TunnelClientPath -PassThru\n"
        "    $RuntimeProcess.WaitForExit()\n"
        "    if ($RuntimeProcess.ExitCode -ne 0) {\n"
        "        Fail 'TUNNEL_START_FAILED' \"Tunnel client exited with code $($RuntimeProcess.ExitCode).\"\n"
        "    }\n"
        "}\n"
        "finally {\n"
        "    $env:CONTROL_PLANE_API_KEY = $null\n"
        "    $env:SERENA_HOME = $null\n"
        "    $ControlPlaneApiKey = $null\n"
        "}\n"
    )


def _legacy_wait_process_launcher() -> str:
    return (
        "$RuntimeStdout = Join-Path $LogsDir 'runtime.stdout.log'\n"
        "$RuntimeStderr = Join-Path $LogsDir 'runtime.stderr.log'\n"
        "Write-Log \"STARTING: health=$HealthListenAddress project=$ProjectPath\"\n"
        "$RuntimeProcess = Start-Process -FilePath $TunnelClientPath -PassThru\n"
        "Wait-Process -Id $RuntimeProcess.Id\n"
    )


def test_create_instance_hardens_live_method_wait_reference(sandbox) -> None:
    instances_root, ref, project = sandbox
    (ref / "start.ps1").write_text(_legacy_method_wait_launcher(), encoding="utf-8")
    created = create_instance(
        instances_root, "Research", project, health_port=48114, reference_root=ref
    )
    start = (created / "start.ps1").read_text(encoding="utf-8")
    assert "runtime-archive" in start
    assert "$RuntimeProcess.Refresh()" in start
    assert "$RuntimeExitCode = $RuntimeProcess.ExitCode" in start
    assert "if ($RuntimeProcess.ExitCode -ne 0)" not in start[start.rfind("$RuntimeProcess.WaitForExit()") :]
    assert "finally {" in start
    assert "$env:CONTROL_PLANE_API_KEY = $null" in start


def test_hardener_supports_live_method_wait_variant() -> None:
    hardened = _harden_start_script_runtime_forensics(_legacy_method_wait_launcher())
    assert "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'" in hardened
    assert "Move-Item -LiteralPath $RuntimeLog -Destination $Archived -Force" in hardened
    assert "    $RuntimeProcess.WaitForExit()\n    $RuntimeProcess.Refresh()\n    $RuntimeExitCode = $RuntimeProcess.ExitCode" in hardened
    assert 'Write-Log "STOPPED: tunnel-client exit_code=0"' in hardened
    assert "exit_code={0}" in hardened
    assert "    exit $RuntimeExitCode\n}\nfinally {" in hardened
    assert "    $env:CONTROL_PLANE_API_KEY = $null" in hardened


def test_hardener_keeps_existing_wait_process_variant_supported() -> None:
    hardened = _harden_start_script_runtime_forensics(_legacy_wait_process_launcher())
    assert "runtime-archive" in hardened
    assert "$RuntimeProcess.WaitForExit()" in hardened
    assert "$RuntimeProcess.Refresh()" in hardened
    assert "$RuntimeExitCode = $RuntimeProcess.ExitCode" in hardened


@pytest.mark.parametrize(
    "launcher",
    (_legacy_method_wait_launcher(), _legacy_wait_process_launcher()),
)
def test_runtime_forensics_hardening_is_idempotent(launcher: str) -> None:
    once = _harden_start_script_runtime_forensics(launcher)
    twice = _harden_start_script_runtime_forensics(once)
    assert twice == once
    assert once.count("$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'") == 1
    assert once.count("$RuntimeProcess.Refresh()") == 1
    assert once.count("$RuntimeExitCode = $RuntimeProcess.ExitCode") == 1


def test_already_hardened_launcher_stays_byte_identical() -> None:
    hardened = _harden_start_script_runtime_forensics(_legacy_wait_process_launcher())
    assert _harden_start_script_runtime_forensics(hardened) == hardened


def test_runtime_archive_word_in_comment_does_not_fake_hardened_state() -> None:
    source = "# operator note: preserve runtime-archive evidence\n" + _legacy_method_wait_launcher()

    hardened = _harden_start_script_runtime_forensics(source)

    assert hardened != source
    assert hardened.count("$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'") == 1
    assert hardened.count("$RuntimeProcess.Refresh()") == 1
    assert hardened.count("$RuntimeExitCode = $RuntimeProcess.ExitCode") == 1
    terminal = hardened[hardened.index("$RuntimeProcess.WaitForExit()") :]
    assert "if ($RuntimeProcess.ExitCode -ne 0)" not in terminal


@pytest.mark.parametrize(
    "marker",
    (
        "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'\n",
        "$RuntimeExitCode = $RuntimeProcess.ExitCode\n",
    ),
)
def test_partial_structural_hardening_marker_fails_unchanged(marker: str) -> None:
    source = marker + _legacy_method_wait_launcher()

    assert _harden_start_script_runtime_forensics(source) == source


def test_classifier_ignores_marker_text_inside_comments() -> None:
    source = (
        "# $RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'\n"
        "# Move-Item -LiteralPath $RuntimeLog -Destination $Archived -Force\n"
        "# Write-Log \"STARTING: comment only\"\n"
        "# $RuntimeProcess.WaitForExit()\n"
        "# $RuntimeProcess.Refresh()\n"
        "# $RuntimeExitCode = $RuntimeProcess.ExitCode\n"
        "# Write-Log \"STOPPED: tunnel-client exit_code=0\"\n"
        "# Write-Log \"exit_code={0}\"\n"
        "# exit $RuntimeExitCode\n"
        "$ProfileTemplate = 'unchanged-generic-reference'\n"
    )

    classified, state = _classify_start_script_runtime_forensics(source)

    assert classified == source
    assert state is _RuntimeForensicsHardeningState.PASSTHROUGH_UNRECOGNIZED


def test_create_instance_allows_comment_only_forensics_markers(sandbox) -> None:
    instances_root, ref, project = sandbox
    source = (ref / "start.ps1").read_text(encoding="utf-8") + (
        "# $RuntimeProcess.WaitForExit()\n"
        "# $RuntimeExitCode = $RuntimeProcess.ExitCode\n"
    )
    (ref / "start.ps1").write_text(source, encoding="utf-8")

    created = create_instance(
        instances_root, "Research", project, health_port=48114, reference_root=ref
    )

    start = (created / "start.ps1").read_text(encoding="utf-8")
    assert "# $RuntimeProcess.WaitForExit()" in start
    assert "# $RuntimeExitCode = $RuntimeProcess.ExitCode" in start


def test_classifier_ignores_marker_text_inside_quoted_strings() -> None:
    source = (
        "$Note = '$RuntimeProcess.WaitForExit()'\n"
        "$Note2 = \"$RuntimeExitCode = $RuntimeProcess.ExitCode\"\n"
        "$ProfileTemplate = 'unchanged-generic-reference'\n"
    )

    classified, state = _classify_start_script_runtime_forensics(source)

    assert classified == source
    assert state is _RuntimeForensicsHardeningState.PASSTHROUGH_UNRECOGNIZED


@pytest.mark.parametrize(
    "wrapper",
    (
        (
            "<#\n"
            "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'\n"
            "$RuntimeProcess.WaitForExit()\n"
            "$RuntimeProcess.Refresh()\n"
            "$RuntimeExitCode = $RuntimeProcess.ExitCode\n"
            "exit $RuntimeExitCode\n"
            "#>\n"
        ),
        (
            "$Help = @\"\n"
            "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'\n"
            "$RuntimeProcess.WaitForExit()\n"
            "$RuntimeProcess.Refresh()\n"
            "$RuntimeExitCode = $RuntimeProcess.ExitCode\n"
            "exit $RuntimeExitCode\n"
            "\"@\n"
        ),
        (
            "<#\n"
            "outer comment\n"
            "<#\n"
            "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'\n"
            "$RuntimeProcess.WaitForExit()\n"
            "#>\n"
            "$RuntimeProcess.Refresh()\n"
            "#>\n"
        ),
    ),
)
def test_classifier_ignores_nonexecuting_multiline_marker_regions(wrapper: str) -> None:
    source = wrapper + "$ProfileTemplate = 'unchanged-generic-reference'\n"

    classified, state = _classify_start_script_runtime_forensics(source)

    assert classified == source
    assert state is _RuntimeForensicsHardeningState.PASSTHROUGH_UNRECOGNIZED


def test_indented_here_string_terminator_does_not_release_marker_authority() -> None:
    source = (
        "$Help = @\"\n"
        "    \"@\n"
        "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'\n"
        "$RuntimeProcess.WaitForExit()\n"
        "$RuntimeProcess.Refresh()\n"
        "$RuntimeExitCode = $RuntimeProcess.ExitCode\n"
        "exit $RuntimeExitCode\n"
        "\"@\n"
        "$ProfileTemplate = 'unchanged-generic-reference'\n"
    )

    classified, state = _classify_start_script_runtime_forensics(source)

    assert classified == source
    assert state is _RuntimeForensicsHardeningState.PASSTHROUGH_UNRECOGNIZED


@pytest.mark.parametrize(
    "wrapper",
    (
        "<#\n$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'\n#>\n",
        "$Help = @\"\n$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'\n\"@\n",
    ),
)
def test_nonexecuting_marker_cannot_suppress_real_legacy_hardening(wrapper: str) -> None:
    source = wrapper + _legacy_method_wait_launcher()

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.TRANSFORMED
    assert classified != source
    terminal = classified[classified.rfind("$RuntimeProcess.WaitForExit()") :]
    assert "$RuntimeProcess.Refresh()" in terminal
    assert "$RuntimeExitCode = $RuntimeProcess.ExitCode" in terminal
    assert "if ($RuntimeProcess.ExitCode -ne 0)" not in terminal


@pytest.mark.parametrize(
    "legacy_launcher",
    (_legacy_wait_process_launcher, _legacy_method_wait_launcher),
)
def test_create_instance_rejects_complete_markers_with_legacy_seam_before_materializing(
    sandbox, legacy_launcher
) -> None:
    instances_root, ref, project = sandbox
    source = (
        "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'\n"
        "$RuntimeProcess.Refresh()\n"
        "$RuntimeExitCode = $RuntimeProcess.ExitCode\n"
        "exit $RuntimeExitCode\n"
        + legacy_launcher()
    )
    (ref / "start.ps1").write_text(source, encoding="utf-8")

    with pytest.raises(InstanceCreateError) as exc_info:
        create_instance(
            instances_root, "Research", project, health_port=48114, reference_root=ref
        )

    assert exc_info.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "research").exists()


def test_create_instance_rejects_partial_structural_marker_before_materializing(sandbox) -> None:
    instances_root, ref, project = sandbox
    source = (
        "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'\n"
        + _legacy_method_wait_launcher()
    )
    (ref / "start.ps1").write_text(source, encoding="utf-8")

    with pytest.raises(InstanceCreateError) as exc_info:
        create_instance(
            instances_root, "Research", project, health_port=48114, reference_root=ref
        )

    assert exc_info.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "research").exists()


def test_create_instance_accepts_already_hardened_reference(sandbox) -> None:
    instances_root, ref, project = sandbox
    hardened = _harden_start_script_runtime_forensics(_legacy_wait_process_launcher())
    (ref / "start.ps1").write_text(hardened, encoding="utf-8")

    created = create_instance(
        instances_root, "Research", project, health_port=48114, reference_root=ref
    )

    start = (created / "start.ps1").read_text(encoding="utf-8")
    assert start == hardened


def test_method_wait_hardening_preserves_preflight_and_credential_sentinels() -> None:
    source = _legacy_method_wait_launcher()
    hardened = _harden_start_script_runtime_forensics(source)
    sentinels = (
        "$DpapiSentinel = 'DPAPI_SENTINEL'",
        "$TunnelValidationSentinel = 'TUNNEL_SENTINEL'",
        "$ProjectValidationSentinel = 'PROJECT_SENTINEL'",
        "$DoctorSentinel = 'DOCTOR_SENTINEL'",
        "$EnvironmentSentinel = 'ENV_SENTINEL'",
    )
    positions = [hardened.index(item) for item in sentinels]
    assert positions == sorted(positions)
    for item in sentinels:
        assert hardened.count(item) == 1


@pytest.mark.parametrize(
    "malformed",
    (
        "$RuntimeStdout = 'out'\n$RuntimeStderr = 'err'\n$RuntimeProcess.WaitForExit()\n",
        "$RuntimeStdout = 'out'\nWrite-Log \"STARTING: x\"\n$RuntimeProcess.WaitForExit()\n",
        "$RuntimeStderr = 'err'\nWrite-Log \"STARTING: x\"\n$RuntimeProcess.WaitForExit()\n",
        "$RuntimeStdout = 'out'\n$RuntimeStderr = 'err'\nWrite-Log \"STARTING: x\"\nWait-SomethingElse\n",
    ),
)
def test_unknown_or_incomplete_launcher_is_returned_unchanged(malformed: str) -> None:
    assert _harden_start_script_runtime_forensics(malformed) == malformed


def test_ambiguous_multiple_terminal_waits_are_returned_unchanged() -> None:
    source = _legacy_wait_process_launcher() + "Wait-Process -Id $RuntimeProcess.Id\n"
    assert _harden_start_script_runtime_forensics(source) == source


def test_method_wait_hardening_removes_stale_direct_exit_branch() -> None:
    hardened = _harden_start_script_runtime_forensics(_legacy_method_wait_launcher())
    terminal = hardened[hardened.index("$RuntimeProcess.WaitForExit()") :]
    assert "if ($RuntimeProcess.ExitCode -ne 0)" not in terminal
    assert terminal.count("$RuntimeProcess.WaitForExit()") == 1
    assert terminal.count("$RuntimeProcess.Refresh()") == 1
    assert terminal.count("$RuntimeExitCode = $RuntimeProcess.ExitCode") == 1
