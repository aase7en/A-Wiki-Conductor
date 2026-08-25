"""WO: C2 + I1 — generated .ps1 must carry a UTF-8 BOM (Thai paths survive
Windows PowerShell 5.1), and every substituted ``--project`` path must be
double-quoted so spaces cannot split the command line."""

from __future__ import annotations

from pathlib import Path

from test_instance_create import make_reference

from a_conductor.instance_create import create_instance
from a_conductor.instance_rebind import rebind_instance_project
from a_conductor.local_instances import discover_local_instances


def _sandbox(tmp_path: Path, project_name: str = "ไทย ทดสอบ"):
    instances_root = tmp_path / "instances"
    instances_root.mkdir(exist_ok=True)
    project = tmp_path / project_name
    project.mkdir(exist_ok=True)
    return instances_root, make_reference(instances_root), project


def test_add_connector_ps1_carries_utf8_bom(tmp_path: Path) -> None:
    instances_root, ref, project = _sandbox(tmp_path)
    created = create_instance(
        instances_root, "thai-test", project, health_port=48200, reference_root=ref
    )
    raw = (created / "instance.ps1").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "instance.ps1 missing UTF-8 BOM"


def test_created_template_quotes_project_path_with_spaces(tmp_path: Path) -> None:
    instances_root, ref, project = _sandbox(tmp_path, "My Project")
    created = create_instance(
        instances_root, "spacey", project, health_port=48201, reference_root=ref
    )
    templates = list((created / "profiles").glob("*.yaml.template"))
    assert templates, "expected a rendered profile template"
    text = templates[0].read_text(encoding="utf-8")
    assert '--project "' in text, "space-containing project path must be quoted"


def test_wizard_ps1_files_carry_utf8_bom(tmp_path: Path) -> None:
    from a_conductor.setup_wizard import FirstInstanceCreator

    project = tmp_path / "โปรเจกต์ wizard"
    project.mkdir()
    tc = tmp_path / "tc" / "tunnel-client.exe"
    tc.parent.mkdir(parents=True, exist_ok=True)
    tc.write_bytes(b"MZ")
    key = tmp_path / "tc" / "config" / "api-key.dpapi"
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_bytes(b"x")
    created = FirstInstanceCreator(instances_root=tmp_path / "inst").create(
        name="wiz-thai",
        project_path=project,
        health_port=48202,
        tunnel_client_path=tc,
        api_key_file=key,
    )
    for name in ("instance.ps1", "start.ps1", "stop.ps1"):
        raw = (created / name).read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf"), f"{name} missing UTF-8 BOM"
    template = next((created / "profiles").glob("*.yaml.template"))
    assert '--project "' in template.read_text(encoding="utf-8")


def test_rebind_rewrites_template_with_quotes_and_keeps_bom(tmp_path: Path) -> None:
    instances_root, ref, project = _sandbox(tmp_path, "proj one")
    create_instance(
        instances_root, "rebind-q", project, health_port=48203, reference_root=ref
    )
    second = tmp_path / "proj two"
    second.mkdir()
    (target := instances_root / "rebind-q").exists()
    instance = next(
        i for i in discover_local_instances(instances_root) if i.name == "Serena-Rebind-Q"
    )
    result = rebind_instance_project(instance, instances_root, str(second))
    assert result == "REBOUND"
    template = next((target / "profiles").glob("*.yaml.template"))
    text = template.read_text(encoding="utf-8")
    assert '--project "' in text
    assert (target / "instance.ps1").read_bytes().startswith(b"\xef\xbb\xbf")
