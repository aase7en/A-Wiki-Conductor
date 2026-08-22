"""WO-P1-060 PR-B: materialize a new connector instance from a reference."""

from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.instance_create import (
    InstanceCreateError,
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
                "$HealthListenAddress = '127.0.0.1:18013'",
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
        "server:\n  listen_addr: 127.0.0.1:18013\nargs:\n  - --project A:/GitHub/demo-old\ntunnel_id: __TUNNEL_ID__\n",
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
        health_port=18014,
        reference_root=ref,
        work_number=4,
    )

    assert (created / "instance.ps1").is_file()
    ps1 = (created / "instance.ps1").read_text(encoding="utf-8")
    assert "$InstanceName = 'Serena-Research'" in ps1
    assert "$HealthListenAddress = '127.0.0.1:18014'" in ps1
    assert str(project) in ps1
    assert "tunnel-client.exe" in ps1  # shared paths carried from reference

    start = (created / "start.ps1").read_text(encoding="utf-8")
    assert "serena-research.yaml.template" in start
    assert "serena-research.yaml" in start
    assert "'research-'" in start
    assert "wastewater" not in start

    start_cmd = (created / "Start-Serena-Research.cmd").read_text(encoding="utf-8")
    assert "title Sunday-works 4 - Research" in start_cmd

    template = (created / "profiles" / "serena-research.yaml.template").read_text(
        encoding="utf-8"
    )
    assert "127.0.0.1:18014" in template
    assert f"--project {project.as_posix()}" in template
    assert "__TUNNEL_ID__" in template

    config = (created / "serena-home" / "serena_config.yml").read_text(encoding="utf-8")
    assert f"projects:\n- '{project}'" in config

    assert (created / "run").is_dir()
    assert (created / "logs").is_dir()


def test_created_instance_is_discoverable(sandbox) -> None:
    instances_root, ref, project = sandbox
    create_instance(
        instances_root, "Research", project, health_port=18014, reference_root=ref
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
        health_port=18014,
        tunnel_id=tunnel,
        reference_root=ref,
    )
    assert (created / "config" / "tunnel-id.txt").read_text(encoding="utf-8").strip() == tunnel


def test_create_instance_guards(sandbox) -> None:
    instances_root, ref, project = sandbox
    create_instance(
        instances_root, "Research", project, health_port=18014, reference_root=ref
    )
    with pytest.raises(InstanceCreateError) as exc:
        create_instance(
            instances_root, "research", project, health_port=18015, reference_root=ref
        )
    assert exc.value.code == "NAME_ALREADY_EXISTS"

    with pytest.raises(InstanceCreateError) as exc:
        create_instance(
            instances_root, "Bad Name!", project, health_port=18015, reference_root=ref
        )
    assert exc.value.code == "NAME_INVALID"

    with pytest.raises(InstanceCreateError) as exc:
        create_instance(
            instances_root,
            "Other",
            instances_root / "missing",
            health_port=18015,
            reference_root=ref,
        )
    assert exc.value.code == "PROJECT_NOT_FOUND"

    with pytest.raises(InstanceCreateError) as exc:
        create_instance(
            instances_root,
            "Other",
            project,
            health_port=18015,
            tunnel_id="nope",
            reference_root=ref,
        )
    assert exc.value.code == "TUNNEL_ID_INVALID"

    empty_root = instances_root.parent / "empty-instances"
    empty_root.mkdir()
    with pytest.raises(InstanceCreateError) as exc:
        create_instance(empty_root, "Other", project, health_port=18015)
    assert exc.value.code == "REFERENCE_MISSING"


def test_create_instance_auto_reference_and_work_number(sandbox) -> None:
    instances_root, _ref, project = sandbox
    created = create_instance(instances_root, "Research", project, health_port=18014)
    cmd = (created / "Start-Serena-Research.cmd").read_text(encoding="utf-8")
    # sandbox has exactly one reference instance -> next window number is 2
    assert "title Sunday-works 2 - Research" in cmd


def test_next_health_port_is_max_plus_one(sandbox) -> None:
    instances_root, ref, project = sandbox
    create_instance(
        instances_root, "Research", project, health_port=18100, reference_root=ref
    )
    instances = discover_local_instances(instances_root)
    assert next_health_port(instances) == 18101


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
