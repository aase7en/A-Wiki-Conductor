"""WO-P1-060 PR-B: materialize a new connector instance from a reference."""

from __future__ import annotations

import tempfile
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
    ),
)
def test_classifier_ignores_nonexecuting_multiline_marker_regions(wrapper: str) -> None:
    source = wrapper + "$ProfileTemplate = 'unchanged-generic-reference'\n"

    classified, state = _classify_start_script_runtime_forensics(source)

    assert classified == source
    assert state is _RuntimeForensicsHardeningState.PASSTHROUGH_UNRECOGNIZED


def test_nested_block_comment_opener_ends_at_first_closer() -> None:
    # Round-4 correction of the previous nesting misconception: PowerShell block
    # comments do NOT nest, so the first #> closes and later marker lines are
    # live code that must fail closed.
    source = (
        "<#\n"
        "outer comment\n"
        "<#\n"
        "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'\n"
        "$RuntimeProcess.WaitForExit()\n"
        "#>\n"
        "$RuntimeProcess.Refresh()\n"
        "#>\n"
        "$ProfileTemplate = 'unchanged-generic-reference'\n"
    )

    classified, state = _classify_start_script_runtime_forensics(source)

    assert classified == source
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


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


# --- WO-P1-215 repair-2: enclosing brace-ancestry fail-closed proof -------


def _hardened_wait_process_launcher() -> str:
    return _harden_start_script_runtime_forensics(_legacy_wait_process_launcher())


def _hardened_method_wait_launcher() -> str:
    return _harden_start_script_runtime_forensics(_legacy_method_wait_launcher())


def _false_guard_wrap(source: str) -> str:
    body = "\n".join(
        ("    " + line if line.strip() else line) for line in source.splitlines()
    )
    return "if ($false) {\n" + body + "\n}\n"


def _false_guard_wrap_exit(source: str) -> str:
    return source.replace(
        "exit $RuntimeExitCode",
        "if ($false) {\n    exit $RuntimeExitCode\n}",
    )


@pytest.mark.parametrize(
    "hardened",
    (_hardened_wait_process_launcher(), _hardened_method_wait_launcher()),
)
def test_classifier_rejects_full_false_guard_wrap(hardened: str) -> None:
    wrapped = _false_guard_wrap(hardened)

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


@pytest.mark.parametrize(
    "hardened",
    (_hardened_wait_process_launcher(), _hardened_method_wait_launcher()),
)
def test_classifier_rejects_partial_false_guard_wrap(hardened: str) -> None:
    wrapped = _false_guard_wrap_exit(hardened)

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


@pytest.mark.parametrize(
    "hardened",
    (_hardened_wait_process_launcher(), _hardened_method_wait_launcher()),
)
def test_classifier_accepts_canonical_hardened_ancestry(hardened: str) -> None:
    classified, state = _classify_start_script_runtime_forensics(hardened)

    assert classified == hardened
    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED


def test_create_instance_refuses_false_guard_wrap_before_materializing(sandbox) -> None:
    instances_root, ref, project = sandbox
    (ref / "start.ps1").write_text(
        _false_guard_wrap(_hardened_wait_process_launcher()), encoding="utf-8"
    )

    with pytest.raises(InstanceCreateError) as raised:
        create_instance(
            instances_root, "Research", project, health_port=48114, reference_root=ref
        )

    assert raised.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "Research").exists()


def test_classifier_rejects_legacy_seam_inside_false_guard() -> None:
    wrapped = _false_guard_wrap(_legacy_wait_process_launcher())

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_classifier_rejects_noncanonical_truthy_guard_around_exit() -> None:
    wrapped = _hardened_wait_process_launcher().replace(
        "exit $RuntimeExitCode",
        "if ($true) {\n    exit $RuntimeExitCode\n}",
    )

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_classifier_fails_closed_on_unbalanced_brace_prefix() -> None:
    wrapped = "}\n" + _hardened_wait_process_launcher()

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


# --- WO-P1-215 repair-2 rev-2: terminal control flow + block-shape bounds -


@pytest.mark.parametrize(
    "terminal",
    ("exit 0\n", "throw 'unreachable'\n", "return\n"),
)
@pytest.mark.parametrize(
    "hardened",
    (_hardened_wait_process_launcher(), _hardened_method_wait_launcher()),
)
def test_classifier_rejects_terminal_flow_before_forensic_body(
    terminal: str, hardened: str
) -> None:
    wrapped = terminal + hardened

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


@pytest.mark.parametrize(
    "hardened",
    (_hardened_wait_process_launcher(), _hardened_method_wait_launcher()),
)
def test_classifier_rejects_terminal_flow_after_first_marker(hardened: str) -> None:
    first_marker = "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'"
    wrapped = hardened.replace(first_marker, first_marker + "\nexit 0", 1)

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


@pytest.mark.parametrize(
    "hardened",
    (_hardened_wait_process_launcher(), _hardened_method_wait_launcher()),
)
def test_create_instance_refuses_terminal_flow_before_forensic_body(
    sandbox, hardened: str
) -> None:
    instances_root, ref, project = sandbox
    (ref / "start.ps1").write_text("exit 0\n" + hardened, encoding="utf-8")

    with pytest.raises(InstanceCreateError) as raised:
        create_instance(
            instances_root, "Research", project, health_port=48114, reference_root=ref
        )

    assert raised.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "Research").exists()


def test_classifier_rejects_catch_weakened_try_shape() -> None:
    wrapped = _hardened_method_wait_launcher().replace("finally {", "catch {")

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_classifier_rejects_noncanonical_replaced_finally_header() -> None:
    wrapped = _hardened_method_wait_launcher().replace("finally {", "if ($never) {")

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


@pytest.mark.parametrize(
    "hardened",
    (_hardened_wait_process_launcher(), _hardened_method_wait_launcher()),
)
def test_classifier_rejects_unmatched_brace_after_forensic_body(hardened: str) -> None:
    wrapped = hardened + "}\n"

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


@pytest.mark.parametrize(
    "hardened",
    (_hardened_wait_process_launcher(), _hardened_method_wait_launcher()),
)
def test_classifier_rejects_unclosed_block_after_forensic_body(hardened: str) -> None:
    wrapped = hardened + "if ($never) {\n"

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


# --- WO-P1-215 repair-2 rev-3: loop-control terminal tokens ---------------


@pytest.mark.parametrize(
    "terminal",
    ("break\n", "BREAK\n", "continue\n"),
)
@pytest.mark.parametrize(
    "hardened",
    (_hardened_wait_process_launcher(), _hardened_method_wait_launcher()),
)
def test_classifier_rejects_loop_terminator_before_forensic_body(
    terminal: str, hardened: str
) -> None:
    wrapped = terminal + hardened

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


@pytest.mark.parametrize(
    "terminal",
    ("break", "continue"),
)
@pytest.mark.parametrize(
    "hardened",
    (_hardened_wait_process_launcher(), _hardened_method_wait_launcher()),
)
def test_classifier_rejects_loop_terminator_between_markers(
    terminal: str, hardened: str
) -> None:
    first_marker = "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'"
    wrapped = hardened.replace(first_marker, first_marker + "\n" + terminal, 1)

    classified, state = _classify_start_script_runtime_forensics(wrapped)

    assert classified == wrapped
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


@pytest.mark.parametrize(
    "terminal",
    ("break", "continue"),
)
@pytest.mark.parametrize(
    "hardened",
    (_hardened_wait_process_launcher(), _hardened_method_wait_launcher()),
)
def test_create_instance_refuses_loop_terminator_before_forensic_body(
    sandbox, terminal: str, hardened: str
) -> None:
    instances_root, ref, project = sandbox
    (ref / "start.ps1").write_text(terminal + "\n" + hardened, encoding="utf-8")

    with pytest.raises(InstanceCreateError) as raised:
        create_instance(
            instances_root, "Research", project, health_port=48114, reference_root=ref
        )

    assert raised.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "Research").exists()


# --- WO-P1-679 review repair P1: real FirstInstanceCreator generator --------


def _wizard_reference(root: Path, name: str = "sunday-worker-1") -> Path:
    from a_conductor.setup_wizard import FirstInstanceCreator

    project = root.parent / "wizard-project"
    project.mkdir(exist_ok=True)
    creator = FirstInstanceCreator(instances_root=root)
    return creator.create(
        name=name,
        project_path=project,
        health_port=18011,
        tunnel_client_path=root.parent / "tunnel-client.exe",
        api_key_file=root.parent / "secret.dpapi",
    )


def test_wizard_generated_start_script_is_already_hardened(tmp_path: Path) -> None:
    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    wizard_target = _wizard_reference(instances_root)
    wizard_start = (wizard_target / "start.ps1").read_text(encoding="utf-8-sig")

    classified, state = _classify_start_script_runtime_forensics(wizard_start)

    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED
    assert classified == wizard_start


def test_create_instance_clones_from_wizard_generated_reference(tmp_path: Path) -> None:
    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    wizard_target = _wizard_reference(instances_root)
    project = tmp_path / "proj"
    project.mkdir()

    created = create_instance(
        instances_root,
        "Research",
        project,
        health_port=18012,
        reference_root=wizard_target,
    )

    start = (created / "start.ps1").read_text(encoding="utf-8")
    assert "serena-research.yaml.template" in start
    assert "serena-research.yaml" in start
    assert "'research-'" in start
    _, state = _classify_start_script_runtime_forensics(start)
    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED


# --- WO-P1-679 review repair P2: try/finally pairing fail-closed ------------


@pytest.mark.parametrize(
    "malformed_builder",
    (
        lambda hard, method: hard + "finally {\n}\n",
        lambda hard, method: method.split("finally {")[0],
        lambda hard, method: method.replace("finally {", "try {"),
    ),
    ids=["dangling-finally", "truncated-no-finally", "finally-replaced-by-try"],
)
def test_malformed_try_finally_grammar_fails_closed(malformed_builder) -> None:
    hard = _hardened_wait_process_launcher()
    method = _hardened_method_wait_launcher()
    malformed = malformed_builder(hard, method)

    classified, state = _classify_start_script_runtime_forensics(malformed)

    assert classified == malformed
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


# --- WO-P1-679 review repair P2: literal data has no control authority ------


@pytest.mark.parametrize("slug", ("return", "break", "exit", "throw", "continue"))
def test_control_word_slugs_stay_legal(sandbox, slug: str) -> None:
    instances_root, ref, project = sandbox
    (ref / "start.ps1").write_text(
        "$ProfileTemplate = Join-Path $ProfilesDir 'serena-wastewater.yaml.template'\n"
        "$RuntimeProfile = Join-Path $RunDir 'serena-wastewater.yaml'\n"
        "$LogFile = Join-Path $LogsDir ('wastewater-' + $day)\n"
        + _legacy_wait_process_launcher(),
        encoding="utf-8",
    )

    created = create_instance(
        instances_root, slug, project, health_port=48114, reference_root=ref
    )

    start = (created / "start.ps1").read_text(encoding="utf-8")
    assert f"serena-{slug}.yaml.template" in start
    assert f"'{slug}-'" in start
    _, state = _classify_start_script_runtime_forensics(start)
    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED


def test_preflight_validates_final_substituted_script_before_materialization(
    sandbox, monkeypatch
) -> None:
    instances_root, ref, project = sandbox
    real = _classify_start_script_runtime_forensics
    calls: list[str] = []

    def spy(text: str):
        calls.append(text)
        if "serena-preflight" in text:
            return text, _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS
        return real(text)

    monkeypatch.setattr(
        "a_conductor.instance_create._classify_start_script_runtime_forensics", spy
    )

    with pytest.raises(InstanceCreateError) as raised:
        create_instance(
            instances_root, "preflight", project, health_port=48115, reference_root=ref
        )

    assert raised.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "preflight").exists()
    assert any("serena-preflight" in text for text in calls)


# --- WO-P1-679 review repair P2: case-insensitive signal fail-closed --------


def test_lowercase_legacy_launcher_fails_closed() -> None:
    source = _legacy_wait_process_launcher().lower()

    classified, state = _classify_start_script_runtime_forensics(source)

    assert classified == source
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_lowercase_hardened_launcher_fails_closed() -> None:
    source = _hardened_wait_process_launcher().lower()

    classified, state = _classify_start_script_runtime_forensics(source)

    assert classified == source
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


@pytest.mark.parametrize(
    "marker_line",
    (
        'Write-Log ("TUNNEL_START_FAILED: Tunnel client exited with code {0}; exit_code={0}" -f $RuntimeExitCode)',
        "New-Item -ItemType Directory -Force -Path $RuntimeArchiveDir | Out-Null",
        "$ArchiveStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'",
        "foreach ($RuntimeLog in @($RuntimeStdout, $RuntimeStderr)) {",
        "if (Test-Path -LiteralPath $RuntimeLog -PathType Leaf) {",
        "$Leaf = [System.IO.Path]::GetFileName($RuntimeLog)",
        "$Archived = Join-Path $RuntimeArchiveDir ($ArchiveStamp + '-' + $Leaf)",
    ),
    ids=[
        "tunnel-start-failed",
        "new-item-archive",
        "archive-stamp",
        "foreach-header",
        "test-path-header",
        "leaf",
        "archived",
    ],
)
def test_standalone_distinctive_marker_fails_closed(marker_line: str) -> None:
    source = marker_line + "\n$ProfileTemplate = 'unchanged-generic-reference'\n"

    classified, state = _classify_start_script_runtime_forensics(source)

    assert classified == source
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


# --- WO-P1-679 round 3: expandable interpolation bound (lexical provenance) -


def _hardened_wait() -> str:
    return _hardened_wait_process_launcher()


def _hardened_method() -> str:
    return _hardened_method_wait_launcher()


_STARTING_LINE = 'Write-Log "STARTING: health=$HealthListenAddress project=$ProjectPath"'
_ARCHIVE_LINE = "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'"


def _insert_between_markers(payload_line: str) -> str:
    hardened = _hardened_wait()
    assert _ARCHIVE_LINE in hardened and _STARTING_LINE in hardened
    return hardened.replace(
        _ARCHIVE_LINE, _ARCHIVE_LINE + "\n" + payload_line, 1
    )


def _with_starting_payload(payload: str) -> str:
    hardened = _hardened_wait()
    assert _STARTING_LINE in hardened
    return hardened.replace(
        _STARTING_LINE, 'Write-Log "STARTING: ' + payload + '"', 1
    )


_SUBEXPRESSION_PAYLOADS = (
    "$(exit 0)",
    "$(throw 'stop')",
    "$(return)",
    "$(break)",
    "$(continue)",
    "$(Write-Output x)",
    '$("$nested")',
    "$(Get-Date `\n        -Format x)",
)


@pytest.mark.parametrize(
    "payload",
    _SUBEXPRESSION_PAYLOADS,
    ids=["exit", "throw", "return", "break", "continue", "write-output", "nested", "multiline"],
)
@pytest.mark.parametrize(
    "builder",
    (
        lambda payload: '$Probe = "' + payload + '"\n' + _hardened_wait(),
        lambda payload: _insert_between_markers('$Probe = "' + payload + '"'),
        lambda payload: _with_starting_payload(payload),
    ),
    ids=["prefix", "between-markers", "starting-payload"],
)
def test_active_subexpression_in_expandable_string_refuses(payload: str, builder) -> None:
    source = builder(payload)

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS
    assert classified == source


@pytest.mark.parametrize(
    "here_literal",
    (
        "$Probe = @\"\n$(exit 0)\n\"@\n",
        '$Probe = @"' + "\n" + "$(Get-Date `\n        -Format x)" + "\n" + '"@' + "\n",
        '$Probe = "$(exit 0)"\n$Other = @"\n$(throw \'stop\')\n"@\n',
    ),
    ids=["herestring-exit", "herestring-multiline", "string-plus-herestring"],
)
def test_active_subexpression_in_expandable_herestring_refuses(here_literal: str) -> None:
    source = _hardened_wait() + here_literal

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS
    assert classified == source


def test_subexpression_in_literal_herestring_stays_inert() -> None:
    source = _hardened_wait() + "$Probe = @'\n$(exit 0)\n'@\n"

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED
    assert classified == source


def test_backtick_escaped_subexpression_stays_inert() -> None:
    source = _hardened_wait() + '$Probe = "`$(exit 0)"\n'

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED
    assert classified == source


def test_double_backtick_keeps_subexpression_active() -> None:
    source = _hardened_wait() + '$Probe = "``$(exit 0)"\n'

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS
    assert classified == source


def test_generated_variable_interpolation_stays_already_hardened() -> None:
    source = _hardened_wait()
    assert "$HealthListenAddress" in source and "$(" not in source

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED
    assert classified == source


def test_exact_legacy_subexpression_still_transforms() -> None:
    source = _legacy_method_wait_launcher()
    assert "$($RuntimeProcess.ExitCode)" in source

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.TRANSFORMED
    assert "$($RuntimeProcess.ExitCode)" not in classified
    again, again_state = _classify_start_script_runtime_forensics(classified)
    assert again_state is _RuntimeForensicsHardeningState.ALREADY_HARDENED
    assert again == classified


def test_marker_lines_inside_multiline_string_are_not_structural() -> None:
    decoy = (
        "$Note = 'plan:\n"
        "exit $RuntimeExitCode\n"
        "Write-Log \"STOPPED: tunnel-client exit_code=0\"\n"
        "'\n"
    )
    source = _hardened_wait() + decoy

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED
    assert classified == source


def test_pure_decoy_multiline_string_is_generic_passthrough() -> None:
    source = (
        "$Note = 'plan:\n"
        "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'\n"
        "$RuntimeProcess.WaitForExit()\n"
        "exit $RuntimeExitCode\n"
        "'\n"
        "$ProfileTemplate = 'unchanged-generic-reference'\n"
    )

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.PASSTHROUGH_UNRECOGNIZED
    assert classified == source


# --- WO-P1-679 round 3: helper body contract -------------------------------


def _wizard_start_script(tmp_path: Path) -> str:
    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    wizard_target = _wizard_reference(instances_root)
    return (wizard_target / "start.ps1").read_text(encoding="utf-8-sig")


_WIZARD_WRITE_LOG_HEADER = "function Write-Log([string]$Message) {"
_WIZARD_FAIL_HEADER = "function Fail([string]$Code, [string]$Message) {"
_WIZARD_WRITE_LOG_BODY = (
    "$line = ('{0} [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $InstanceName, $Message)\n"
    "Write-Host $line\n"
    "Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8\n"
)
_WIZARD_FAIL_BODY = (
    'Write-Log ("{0}: {1}" -f $Code, $Message)\n'
    "exit 1\n"
)


def _mutate_wizard_body(source: str, header: str, mutation) -> str:
    """Apply `mutation(body_text) -> body_text` to the helper after `header`, proving location."""
    start = source.index(header)
    open_brace = source.index("{", start)
    close_brace = source.index("\n}", open_brace) + 1
    body = source[open_brace + 1 : close_brace]
    mutated = mutation(body)
    assert mutated != body
    return source[: open_brace + 1] + mutated + source[close_brace:]


@pytest.mark.parametrize(
    "header, mutation",
    (
        (_WIZARD_WRITE_LOG_HEADER, lambda b: b + "    exit 0\n"),
        (_WIZARD_WRITE_LOG_HEADER, lambda b: b + "    throw 'stop'\n"),
        (_WIZARD_WRITE_LOG_HEADER, lambda b: b + "    return\n"),
        (_WIZARD_WRITE_LOG_HEADER, lambda b: b + "    # injected comment\n"),
        (_WIZARD_WRITE_LOG_HEADER, lambda b: b.replace("    Write-Host $line\n", "")),
        (
            _WIZARD_WRITE_LOG_HEADER,
            lambda b: b.replace(
                "Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8",
                "Add-Content -LiteralPath $LogFile -Value $line -Encoding ASCII",
            ),
        ),
        (_WIZARD_FAIL_HEADER, lambda b: b + "    return\n"),
        (_WIZARD_FAIL_HEADER, lambda b: b.replace("exit 1", "exit 2")),
        (_WIZARD_FAIL_HEADER, lambda b: b.replace("    exit 1\n", "")),
        (_WIZARD_FAIL_HEADER, lambda b: b.replace("    exit 1\n", "    exit 1 ; exit 1\n")),
        (
            _WIZARD_FAIL_HEADER,
            lambda b: b.replace(
                'Write-Log ("{0}: {1}" -f $Code, $Message)',
                'Write-Log ("{0}-{1}" -f $Code, $Message)',
            ),
        ),
    ),
    ids=[
        "writelog-exit",
        "writelog-throw",
        "writelog-return",
        "writelog-comment",
        "writelog-op-removed",
        "writelog-op-altered",
        "fail-return-added",
        "fail-exit-changed",
        "fail-exit-deleted",
        "fail-exit-duplicated",
        "fail-args-altered",
    ],
)
def test_mutated_helper_body_refuses(tmp_path: Path, header: str, mutation) -> None:
    source = _wizard_start_script(tmp_path)

    mutated = _mutate_wizard_body(source, header, mutation)

    _, state = _classify_start_script_runtime_forensics(mutated)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_duplicate_helper_function_refuses(tmp_path: Path) -> None:
    source = _wizard_start_script(tmp_path)
    start = source.index(_WIZARD_WRITE_LOG_HEADER)
    close = source.index("\n}", start) + 2
    duplicated = source + "\n" + source[start:close] + "\n"
    assert duplicated.count(_WIZARD_WRITE_LOG_HEADER) == 2

    _, state = _classify_start_script_runtime_forensics(duplicated)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_nested_helper_function_refuses(tmp_path: Path) -> None:
    source = _wizard_start_script(tmp_path)
    start = source.index(_WIZARD_WRITE_LOG_HEADER)
    close = source.index("\n}", start) + 2
    block = source[start:close]
    indented = "\n".join(
        ("    " + line if line.strip() else line) for line in block.splitlines()
    )
    nested = source[:start] + "if ($true) {\n" + indented + "\n}\n" + source[close:]
    assert _WIZARD_WRITE_LOG_HEADER in nested

    _, state = _classify_start_script_runtime_forensics(nested)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_statement_after_helper_close_refuses(tmp_path: Path) -> None:
    source = _wizard_start_script(tmp_path)
    start = source.index(_WIZARD_FAIL_HEADER)
    close = source.index("\n}", start) + 2
    mutated = source[:close] + " exit 0" + source[close:]
    assert "} exit 0" in mutated

    _, state = _classify_start_script_runtime_forensics(mutated)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def _helper_bodies_crlf(source: str) -> str:
    for header in (_WIZARD_WRITE_LOG_HEADER, _WIZARD_FAIL_HEADER):
        start = source.index(header)
        close = source.index("\n}", start) + 2
        source = source[:start] + source[start:close].replace("\n", "\r\n") + source[close:]
    return source


@pytest.mark.parametrize(
    "formatting",
    (
        lambda s: s,
        _helper_bodies_crlf,
        lambda s: "\n".join(
            ("        " + line if line.strip() and line.startswith("    ") else line)
            for line in s.split("\n")
        ),
    ),
    ids=["exact", "helper-bodies-crlf", "deeper-indent"],
)
def test_supported_helper_formatting_variants_accept(tmp_path: Path, formatting) -> None:
    source = formatting(_wizard_start_script(tmp_path))

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED


# --- WO-P1-679 round 3: try/finally adjacency ------------------------------


def _with_finally_gap(filler: str) -> str:
    method = _hardened_method()
    head, separator, tail = method.partition("finally {")
    assert separator == "finally {"
    return head + filler + "finally {" + tail


@pytest.mark.parametrize(
    "filler",
    (
        "$x = 1\n",
        "Get-Date\n",
        '"lit"\n',
        "'lit'\n",
        '@"live"\n"@\n',
        "@'literal'\n'@\n",
        ";\n",
        "Get-Date `\n",
        "$null | Out-Null\n",
    ),
    ids=[
        "assignment",
        "command",
        "double-quoted",
        "single-quoted",
        "expandable-herestring",
        "literal-herestring",
        "semicolon",
        "backtick-continuation",
        "pipeline",
    ],
)
def test_statement_between_try_and_finally_refuses(filler: str) -> None:
    source = _with_finally_gap(filler)

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS
    assert classified == source


@pytest.mark.parametrize(
    "trivia",
    ("\n\n", "# comment\n", "<# note #>\n", "   \n\t\n"),
    ids=["blank-lines", "line-comment", "block-comment", "whitespace"],
)
def test_trivia_between_try_and_finally_accepts(trivia: str) -> None:
    source = _with_finally_gap(trivia)

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED
    assert classified == source


@pytest.mark.parametrize(
    "malformed",
    (
        lambda: _hardened_wait() + "finally {\n}\n",
        lambda: _hardened_method().split("finally {")[0],
        lambda: _hardened_method().replace("finally {", "try {"),
        lambda: _hardened_wait() + "try {\n}\ntry {\n}\nfinally {\n}\n",
        lambda: _hardened_method().replace("finally {", "finally {\n}\nfinally {\n"),
    ),
    ids=["dangling", "missing", "replaced", "crossed", "double-finally"],
)
def test_try_finally_pairing_malformed_refuses(malformed) -> None:
    source = malformed()

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


@pytest.mark.parametrize(
    "trailing",
    ('$Probe = "unterminated\n', "<#\n", '$Probe = @"\n', "'\n"),
    ids=["unterminated-string", "unterminated-block-comment", "unterminated-herestring", "unterminated-single"],
)
def test_trailing_unterminated_lexis_blocks_positive_verdict(trailing: str) -> None:
    source = _hardened_wait() + trailing

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


# --- WO-P1-679 round 3: operation-level attacks, zero materialization -------


def _launcher_reference_with(extra_line: str) -> str:
    return (
        "$ProfileTemplate = Join-Path $ProfilesDir 'serena-wastewater.yaml.template'\n"
        "$RuntimeProfile = Join-Path $RunDir 'serena-wastewater.yaml'\n"
        "$LogFile = Join-Path $LogsDir ('wastewater-' + $day)\n"
        + _legacy_wait_process_launcher()
        + extra_line
    )


def _count_target_writes(monkeypatch, target_name: str) -> list[str]:
    calls: list[str] = []
    real_mkdir = __import__("pathlib").Path.mkdir
    real_write = __import__("pathlib").Path.write_text

    def spy_mkdir(self, *args, **kwargs):
        calls.append("mkdir:" + self.name)
        return real_mkdir(self, *args, **kwargs)

    def spy_write(self, *args, **kwargs):
        calls.append("write:" + self.name)
        return real_write(self, *args, **kwargs)

    monkeypatch.setattr(__import__("pathlib").Path, "mkdir", spy_mkdir)
    monkeypatch.setattr(__import__("pathlib").Path, "write_text", spy_write)
    return calls


@pytest.mark.parametrize(
    "extra_line",
    (
        '$Probe = "$(exit 0)"\n',
        '$Probe = "``$(throw \'stop\')"\n',
        '$Probe = @"\n$(return)\n"@\n',
    ),
    ids=["interpolation-string", "double-backtick", "interpolation-herestring"],
)
def test_create_instance_refuses_interpolation_attack_before_materialization(
    sandbox, monkeypatch, extra_line: str
) -> None:
    instances_root, ref, project = sandbox
    (ref / "start.ps1").write_text(_launcher_reference_with(extra_line), encoding="utf-8")
    calls = _count_target_writes(monkeypatch, "interpolated")

    with pytest.raises(InstanceCreateError) as raised:
        create_instance(
            instances_root,
            "interpolated",
            project,
            health_port=48114,
            reference_root=ref,
        )

    assert raised.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "interpolated").exists()
    assert not [c for c in calls if "interpolated" in c]


def test_create_instance_refuses_helper_body_attack_before_materialization(
    tmp_path: Path, monkeypatch
) -> None:
    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    wizard_target = _wizard_reference(instances_root)
    source = (wizard_target / "start.ps1").read_text(encoding="utf-8-sig")
    mutated = _mutate_wizard_body(
        source, _WIZARD_WRITE_LOG_HEADER, lambda b: b + "    exit 0\n"
    )
    (wizard_target / "start.ps1").write_text(mutated, encoding="utf-8-sig")
    project = tmp_path / "proj"
    project.mkdir()
    calls = _count_target_writes(monkeypatch, "helperattacked")

    with pytest.raises(InstanceCreateError) as raised:
        create_instance(
            instances_root,
            "helperattacked",
            project,
            health_port=18015,
            reference_root=wizard_target,
        )

    assert raised.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "helperattacked").exists()
    assert not [c for c in calls if "helperattacked" in c]


def test_create_instance_refuses_finally_gap_attack_before_materialization(
    sandbox, monkeypatch
) -> None:
    instances_root, ref, project = sandbox
    gapped = _with_finally_gap("$x = 1\n")
    profiled = (
        "$ProfileTemplate = Join-Path $ProfilesDir 'serena-wastewater.yaml.template'\n"
        "$RuntimeProfile = Join-Path $RunDir 'serena-wastewater.yaml'\n"
        "$LogFile = Join-Path $LogsDir ('wastewater-' + $day)\n" + gapped
    )
    (ref / "start.ps1").write_text(profiled, encoding="utf-8")
    calls = _count_target_writes(monkeypatch, "gapattack")

    with pytest.raises(InstanceCreateError) as raised:
        create_instance(
            instances_root, "gapattack", project, health_port=48114, reference_root=ref
        )

    assert raised.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "gapattack").exists()
    assert not [c for c in calls if "gapattack" in c]


def test_written_start_script_is_exactly_the_validated_snapshot(sandbox) -> None:
    from a_conductor.instance_create import _substitute_reference_literals

    instances_root, ref, project = sandbox
    (ref / "start.ps1").write_text(_launcher_reference_with(""), encoding="utf-8")

    created = create_instance(
        instances_root, "snapshot", project, health_port=48114, reference_root=ref
    )

    written = (created / "start.ps1").read_text(encoding="utf-8")
    reference_text = (ref / "start.ps1").read_text(encoding="utf-8")
    substituted = _substitute_reference_literals(
        reference_text, "wastewater", "serena-snapshot", "snapshot"
    )
    classified, state = _classify_start_script_runtime_forensics(substituted)
    assert state is _RuntimeForensicsHardeningState.TRANSFORMED
    assert written == classified


# --- WO-P1-679 round 4: PowerShell comment/herestring/smart-quote semantics -


def test_block_comment_does_not_nest_first_closer_wins(tmp_path: Path) -> None:
    source = _wizard_start_script(tmp_path) + "<#\n<#\n#>\nexit 5\n#>\n"

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS
    assert classified == source


def test_herestring_closer_with_trailing_tokens_is_live_code(tmp_path: Path) -> None:
    source = (
        _wizard_start_script(tmp_path)
        + '$hidden = @"\ndata\n"@ | Out-Null\nexit 5\n"@\nx\n# "\n'
    )

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS
    assert classified == source


def test_legacy_hidden_behind_trailing_token_closer_never_passes_through() -> None:
    source = (
        "$RuntimeStdout = Join-Path $LogsDir 'runtime.stdout.log'\n"
        "$RuntimeStderr = Join-Path $LogsDir 'runtime.stderr.log'\n"
        'Write-Log "STARTING: health=$HealthListenAddress project=$ProjectPath"\n'
        '$hidden = @"\ndata\n"@ | Out-Null\n'
        "$RuntimeProcess = Start-Process -FilePath $TunnelClientPath -PassThru\n"
        "Wait-Process -Id $RuntimeProcess.Id\n"
    )

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.TRANSFORMED
    assert "Wait-Process -Id $RuntimeProcess.Id" not in classified


def test_smart_quote_wrapped_wizard_text_earns_no_positive_verdict(tmp_path: Path) -> None:
    wizard = _wizard_start_script(tmp_path)
    source = "$Note = @\u201c\n" + wizard + "\u201d@\n"

    _, state = _classify_start_script_runtime_forensics(source)

    assert state is not _RuntimeForensicsHardeningState.ALREADY_HARDENED
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_smart_quoted_inline_string_earns_no_positive_verdict() -> None:
    source = _hardened_wait() + "$Note = \u201cplain data\u201d\n"

    _, state = _classify_start_script_runtime_forensics(source)

    assert state is not _RuntimeForensicsHardeningState.ALREADY_HARDENED
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_crlf_hardened_text_direct_api_classifies_already_hardened() -> None:
    source = _hardened_wait().replace("\n", "\r\n")

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED
    assert classified == source


def test_crlf_legacy_wait_direct_api_transforms() -> None:
    source = _legacy_wait_process_launcher().replace("\n", "\r\n")

    classified, state = _classify_start_script_runtime_forensics(source)

    assert state is _RuntimeForensicsHardeningState.TRANSFORMED
    assert classified != source
    again, again_state = _classify_start_script_runtime_forensics(classified)
    assert again_state is _RuntimeForensicsHardeningState.ALREADY_HARDENED


def test_transform_outputs_byte_identical_to_frozen_candidate() -> None:
    import hashlib
    import json
    import subprocess
    import sys

    old_src = "/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo293-repair/src"
    if not Path(old_src, "a_conductor", "instance_create.py").is_file():
        pytest.skip("frozen old worktree not present on this host")
    launcher = (
        "import json, sys\n"
        f"sys.path.insert(0, {old_src!r})\n"
        "from test_instance_create_launchers import payload\n"
        "from a_conductor.instance_create import _harden_start_script_runtime_forensics\n"
        "print(json.dumps(_harden_start_script_runtime_forensics(payload)))\n"
    )
    for legacy in (
        _legacy_wait_process_launcher(),
        _legacy_method_wait_launcher(),
    ):
        probe = Path(tempfile.gettempdir()) / "test_instance_create_launchers.py"
        probe.write_text("payload = " + repr(legacy), encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, "-c", launcher],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(probe.parent),
            )
        finally:
            probe.unlink(missing_ok=True)
        assert result.returncode == 0, result.stderr
        frozen_output = json.loads(result.stdout)
        ours = _harden_start_script_runtime_forensics(legacy)
        assert (
            hashlib.sha256(ours.encode("utf-8")).hexdigest()
            == hashlib.sha256(frozen_output.encode("utf-8")).hexdigest()
        )
        assert ours == frozen_output


# --- WO-P1-679 round 5: spec single-quote-character smart codepoints --------


@pytest.mark.parametrize("codepoint", ("\u201a", "\u201b"))
def test_low_smart_quote_wrapped_wizard_text_earns_no_positive_verdict(
    tmp_path: Path, codepoint: str
) -> None:
    wizard = _wizard_start_script(tmp_path)
    source = "$Note = @" + codepoint + "\n" + wizard + codepoint + "@\n"

    _, state = _classify_start_script_runtime_forensics(source)

    assert state is not _RuntimeForensicsHardeningState.ALREADY_HARDENED
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


@pytest.mark.parametrize("codepoint", ("\u201a", "\u201b"))
def test_create_instance_refuses_low_smart_quote_reference_before_materialization(
    sandbox, monkeypatch, codepoint: str
) -> None:
    instances_root, ref, project = sandbox
    (ref / "start.ps1").write_text(
        _hardened_wait() + "$Note = @" + codepoint + "\ndata\n" + codepoint + "@\n",
        encoding="utf-8",
    )
    calls = _count_target_writes(monkeypatch, "lowsq")

    with pytest.raises(InstanceCreateError) as raised:
        create_instance(
            instances_root, "lowsq", project, health_port=48114, reference_root=ref
        )

    assert raised.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "lowsq").exists()
    assert not [c for c in calls if "lowsq" in c]


# --- WO-P1-679 round 7 A: runtime launch-sequence completeness -------------

_LAUNCH_LINE = "$RuntimeProcess = Start-Process -FilePath $TunnelClientPath -PassThru"


def test_removed_runtime_launch_refuses() -> None:
    source = _hardened_wait().replace(_LAUNCH_LINE + "\n", "")
    assert _LAUNCH_LINE not in source

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_commented_runtime_launch_refuses() -> None:
    source = _hardened_wait().replace(_LAUNCH_LINE, "# " + _LAUNCH_LINE)
    assert ("# " + _LAUNCH_LINE) in source

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_string_hidden_runtime_launch_refuses() -> None:
    hardened = _hardened_wait().replace(_LAUNCH_LINE + "\n", "")
    source = (
        hardened
        + '$note = "ordinary multiline data\n'
        + _LAUNCH_LINE
        + '\nmore"\n'
    )

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_duplicate_runtime_launch_refuses() -> None:
    source = _hardened_wait() + _LAUNCH_LINE + "\n"

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_guard_wrapped_runtime_launch_refuses() -> None:
    source = _hardened_wait().replace(
        _LAUNCH_LINE, "if ($false) {\n    " + _LAUNCH_LINE + "\n}"
    )

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_create_instance_refuses_launchless_reference_before_materialization(
    sandbox, monkeypatch
) -> None:
    instances_root, ref, project = sandbox
    (ref / "start.ps1").write_text(
        _launcher_reference_with("").replace(_LAUNCH_LINE + "\n", ""),
        encoding="utf-8",
    )
    calls = _count_target_writes(monkeypatch, "nolaunch")

    with pytest.raises(InstanceCreateError) as raised:
        create_instance(
            instances_root, "nolaunch", project, health_port=48114, reference_root=ref
        )

    assert raised.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "nolaunch").exists()
    assert not [c for c in calls if "nolaunch" in c]


def test_wizard_multi_line_launch_template_stays_already_hardened(
    tmp_path: Path,
) -> None:
    source = _wizard_start_script(tmp_path)
    assert "Start-Process -FilePath $TunnelClientPath `" in source

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED


# --- WO-P1-679 round 7 B: Fail-call placement + guard body contracts --------


def test_toplevel_fail_call_prefix_refuses(tmp_path: Path) -> None:
    source = _wizard_start_script(tmp_path) + "Fail 'STOP' 'early termination'\n"

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_mid_body_fail_call_refuses() -> None:
    hardened = _hardened_method_wait_launcher()
    source = hardened.replace(
        "$RuntimeProcess.WaitForExit()",
        "Fail 'STOP' 'mid body'\n$RuntimeProcess.WaitForExit()",
        1,
    )

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_injected_guard_body_call_refuses(tmp_path: Path) -> None:
    source = _wizard_start_script(tmp_path)
    marker = "    Fail 'CONFIG_NOT_FOUND' \"tunnel-client not found: $TunnelClientPath\""
    assert marker in source
    mutated = source.replace(
        marker, marker + "\n    Get-Date", 1
    )

    _, state = _classify_start_script_runtime_forensics(mutated)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_reforged_preflight_guard_refuses(tmp_path: Path) -> None:
    source = _wizard_start_script(tmp_path)
    original = "if (-not (Test-Path -LiteralPath $TunnelIdPath -PathType Leaf)) {"
    assert original in source
    mutated = source.replace(
        original,
        "if (-not (Test-Path -LiteralPath $ProjectPath -PathType Leaf)) {",
        1,
    )

    _, state = _classify_start_script_runtime_forensics(mutated)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_create_instance_refuses_toplevel_fail_attack_before_materialization(
    tmp_path: Path, monkeypatch
) -> None:
    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    wizard_target = _wizard_reference(instances_root)
    source = (wizard_target / "start.ps1").read_text(encoding="utf-8-sig")
    mutated = source + "Fail 'STOP' 'early termination'\n"
    (wizard_target / "start.ps1").write_text(mutated, encoding="utf-8-sig")
    project = tmp_path / "proj"
    project.mkdir()
    calls = _count_target_writes(monkeypatch, "failattack")

    with pytest.raises(InstanceCreateError) as raised:
        create_instance(
            instances_root,
            "failattack",
            project,
            health_port=18016,
            reference_root=wizard_target,
        )

    assert raised.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "failattack").exists()
    assert not [c for c in calls if "failattack" in c]


# --- WO-P1-679 round 7 B: archive-block completeness ------------------------


@pytest.mark.parametrize(
    "archive_line",
    (
        "New-Item -ItemType Directory -Force -Path $RuntimeArchiveDir | Out-Null",
        "$ArchiveStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'",
        "foreach ($RuntimeLog in @($RuntimeStdout, $RuntimeStderr)) {",
        "if (Test-Path -LiteralPath $RuntimeLog -PathType Leaf) {",
        "$Leaf = [System.IO.Path]::GetFileName($RuntimeLog)",
        "$Archived = Join-Path $RuntimeArchiveDir ($ArchiveStamp + '-' + $Leaf)",
    ),
    ids=["new-item", "archive-stamp", "foreach", "test-path", "leaf", "archived"],
)
def test_missing_archive_operation_refuses(archive_line: str) -> None:
    source = _hardened_wait().replace(archive_line + "\n", "")
    assert archive_line not in source

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


# --- WO-P1-679 round 7 C: parse-only PowerShell oracle ----------------------

_PARSE_ORACLE_PROBE = r"""
param([string]$ArtifactPath)
$ErrorActionPreference = 'Stop'
$text = [System.IO.File]::ReadAllText($ArtifactPath, [System.Text.Encoding]::UTF8)
$tokens = $null
$errors = $null
[System.Management.Automation.Language.Parser]::ParseInput($text, [ref]$tokens, [ref]$errors) | Out-Null
$result = [ordered]@{
    engine      = $PSVersionTable.PSVersion.ToString()
    error_count = @($errors).Count
    first_error = if (@($errors).Count -gt 0) { @($errors)[0].Message } else { $null }
}
[Console]::Out.Write(($result | ConvertTo-Json -Compress))
"""


def _resolve_parse_oracle_engines() -> list[str]:
    """Engine discovery for the parse oracle with Windows-mandatory presence.

    On Windows a green parse gate requires at least one real engine, so missing
    all engines FAILS there; on other platforms an engine-less host takes an
    explicit skip at the call site. No installation or shell probing beyond
    shutil.which.
    """
    import shutil
    import sys

    engines = []
    for name in ("pwsh", "powershell"):
        path = shutil.which(name)
        if path:
            engines.append(path)
    if not engines and sys.platform == "win32":
        pytest.fail(
            "parse oracle engines are mandatory on Windows: neither pwsh nor powershell was found"
        )
    return engines


def _available_powershell_engines() -> list[str]:
    return _resolve_parse_oracle_engines()


def _run_parse_oracle(engine: str, artifact: Path, tmp_path: Path) -> dict:
    import json
    import subprocess

    probe = tmp_path / "parse_probe.ps1"
    probe.write_text(_PARSE_ORACLE_PROBE, encoding="utf-8-sig", newline="\r\n")
    try:
        completed = subprocess.run(
            [
                engine,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(probe),
                str(artifact),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        probe.unlink(missing_ok=True)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip(), "parse oracle produced empty output"
    payload = json.loads(completed.stdout)
    assert isinstance(payload.get("error_count"), int), payload
    return payload


def _write_parse_artifact(tmp_path: Path, name: str, text: str) -> Path:
    artifact = tmp_path / name
    artifact.write_bytes(text.encode("utf-8"))
    return artifact


_ORACLE_NEGATIVES = {
    "unbalanced-brace": "if ($true) {\n$X = 1\n",
    "try-without-finally": "try {\n$X = 1\n}\n$Y = 2\n",
    "unclosed-function": "function Broken() {\n",
}


def test_parse_oracle_valid_generated_scripts(tmp_path: Path) -> None:
    engines = _available_powershell_engines()
    if not engines:
        pytest.skip("no PowerShell engine available for parse oracle (pwsh/powershell)")

    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    wizard_target = _wizard_reference(instances_root)
    wizard_text = (wizard_target / "start.ps1").read_text(encoding="utf-8-sig")
    project = tmp_path / "proj"
    project.mkdir()
    created = create_instance(
        instances_root,
        "oracle",
        project,
        health_port=18017,
        reference_root=wizard_target,
    )
    clone_text = (created / "start.ps1").read_text(encoding="utf-8")
    fixtures = {
        "wizard": wizard_text,
        "legacy-wait-transformed": _harden_start_script_runtime_forensics(
            _legacy_wait_process_launcher()
        ),
        "legacy-method-transformed": _harden_start_script_runtime_forensics(
            _legacy_method_wait_launcher()
        ),
        "final-substituted-clone": clone_text,
    }
    for engine in engines:
        for name, text in fixtures.items():
            artifact = _write_parse_artifact(tmp_path, f"{name}.ps1", text)
            payload = _run_parse_oracle(engine, artifact, tmp_path)
            assert payload["error_count"] == 0, (engine, name, payload)


def test_parse_oracle_negatives_prove_not_inert(tmp_path: Path) -> None:
    engines = _available_powershell_engines()
    if not engines:
        pytest.skip("no PowerShell engine available for parse oracle (pwsh/powershell)")

    for engine in engines:
        for name, text in _ORACLE_NEGATIVES.items():
            artifact = _write_parse_artifact(tmp_path, f"neg-{name}.ps1", text)
            payload = _run_parse_oracle(engine, artifact, tmp_path)
            assert payload["error_count"] >= 1, (engine, name, payload)


# --- WO-P1-679 round 8: case/midline/invocation Fail-token authority ---------

_FAIL_ATTACKS = (
    "FAIL 'EVIL' 'terminating before launch'",
    "fAiL 'EVIL' 'terminating before launch'",
    "Write-Log 'note'; Fail 'EVIL' 'terminating before launch'",
    "& Fail 'EVIL' 'terminating before launch'",
    "F`ail 'EVIL' 'terminating before launch'",
)


def _wizard_with_fail_attack(tmp_path: Path, attack: str) -> str:
    source = _wizard_start_script(tmp_path)
    marker = 'Write-Log "STARTING: health=$HealthListenAddress project=$ProjectPath"'
    assert marker in source
    mutated = source.replace(marker, marker + "\n" + attack, 1)
    assert attack in mutated
    return mutated


@pytest.mark.parametrize(
    "attack",
    _FAIL_ATTACKS,
    ids=["upper", "mixed-case", "midline-semicolon", "call-operator", "backtick-escaped"],
)
def test_wizard_fail_token_attacks_refuse(tmp_path: Path, attack: str) -> None:
    source = _wizard_with_fail_attack(tmp_path, attack)

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_hardened_legacy_fail_token_attack_refuses() -> None:
    source = _hardened_wait() + "FAIL 'EVIL' 'terminating before launch'\n"

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_create_instance_refuses_fail_token_attack_before_materialization(
    tmp_path: Path, monkeypatch
) -> None:
    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    wizard_target = _wizard_reference(instances_root)
    source = (wizard_target / "start.ps1").read_text(encoding="utf-8-sig")
    marker = 'Write-Log "STARTING: health=$HealthListenAddress project=$ProjectPath"'
    assert marker in source
    mutated = source.replace(
        marker,
        marker + "\nFAIL 'EVIL' 'terminating before launch'",
        1,
    )
    (wizard_target / "start.ps1").write_text(mutated, encoding="utf-8-sig")
    project = tmp_path / "proj"
    project.mkdir()
    calls = _count_target_writes(monkeypatch, "failtoken")

    with pytest.raises(InstanceCreateError) as raised:
        create_instance(
            instances_root,
            "failtoken",
            project,
            health_port=18018,
            reference_root=wizard_target,
        )

    assert raised.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "failtoken").exists()
    assert not [c for c in calls if "failtoken" in c]


def test_literal_fail_slug_stays_legal(sandbox) -> None:
    instances_root, ref, project = sandbox
    (ref / "start.ps1").write_text(
        "$ProfileTemplate = Join-Path $ProfilesDir 'serena-wastewater.yaml.template'\n"
        "$RuntimeProfile = Join-Path $RunDir 'serena-wastewater.yaml'\n"
        "$LogFile = Join-Path $LogsDir ('wastewater-' + $day)\n"
        + _legacy_wait_process_launcher(),
        encoding="utf-8",
    )

    created = create_instance(
        instances_root, "fail", project, health_port=48114, reference_root=ref
    )

    start = (created / "start.ps1").read_text(encoding="utf-8")
    assert "serena-fail.yaml.template" in start
    _, state = _classify_start_script_runtime_forensics(start)
    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED


# --- WO-P1-679 round 9: launch-template exact single-backtick continuations ---

_WIZARD_CONTINUATION_LINES = (
    "$RuntimeProcess = Start-Process -FilePath $TunnelClientPath `",
    "    -ArgumentList @('run', '--profile-file', $RuntimeProfile, '--pid.file', $PidFile) `",
    "    -NoNewWindow -PassThru `",
    "    -RedirectStandardOutput $RuntimeStdout `",
)


def _wizard_with_continuation_backticks(
    tmp_path: Path, line_index: int, count: int
) -> str:
    source = _wizard_start_script(tmp_path)
    original = _WIZARD_CONTINUATION_LINES[line_index]
    assert original in source
    mutated_line = original[:-1] + ("`" * count)
    mutated = source.replace(original, mutated_line, 1)
    assert mutated_line in mutated
    return mutated


@pytest.mark.parametrize("line_index", range(4), ids=["file", "args", "flags", "stdout"])
@pytest.mark.parametrize("count", (2, 3), ids=["double-backtick", "triple-backtick"])
def test_noncanonical_continuation_backticks_refuse(
    tmp_path: Path, line_index: int, count: int
) -> None:
    source = _wizard_with_continuation_backticks(tmp_path, line_index, count)

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS


def test_create_instance_refuses_double_backtick_launch_before_materialization(
    tmp_path: Path, monkeypatch
) -> None:
    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    wizard_target = _wizard_reference(instances_root)
    source = (wizard_target / "start.ps1").read_text(encoding="utf-8-sig")
    original = _WIZARD_CONTINUATION_LINES[0]
    mutated = source.replace(original, original[:-1] + "``", 1)
    (wizard_target / "start.ps1").write_text(mutated, encoding="utf-8-sig")
    project = tmp_path / "proj"
    project.mkdir()
    calls = _count_target_writes(monkeypatch, "dbtick")

    with pytest.raises(InstanceCreateError) as raised:
        create_instance(
            instances_root,
            "dbtick",
            project,
            health_port=18019,
            reference_root=wizard_target,
        )

    assert raised.value.code == "REFERENCE_START_SCRIPT_UNSAFE"
    assert not (instances_root / "dbtick").exists()
    assert not [c for c in calls if "dbtick" in c]


def test_single_backtick_canonical_launch_stays_accepted(tmp_path: Path) -> None:
    source = _wizard_start_script(tmp_path)
    for line in _WIZARD_CONTINUATION_LINES:
        assert line in source

    _, state = _classify_start_script_runtime_forensics(source)
    assert state is _RuntimeForensicsHardeningState.ALREADY_HARDENED


# --- WO-P1-679 round 9: engine-presence gating mandatory on Windows ----------


def test_windows_missing_all_engines_fails_not_skips(monkeypatch) -> None:
    import sys

    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr(sys, "platform", "win32")

    with pytest.raises(pytest.fail.Exception):
        _resolve_parse_oracle_engines()


def test_windows_available_engine_proceeds(monkeypatch) -> None:
    import sys

    monkeypatch.setattr(
        "shutil.which", lambda name: r"C:\pwsh\pwsh.exe" if name == "pwsh" else None
    )
    monkeypatch.setattr(sys, "platform", "win32")

    engines = _resolve_parse_oracle_engines()
    assert engines == [r"C:\pwsh\pwsh.exe"]


def test_non_windows_missing_engines_returns_empty(monkeypatch) -> None:
    import sys

    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr(sys, "platform", "darwin")

    assert _resolve_parse_oracle_engines() == []
