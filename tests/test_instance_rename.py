"""WO: rename a connector instance's real backend identity (folder + scripts)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_instance_create import make_reference  # type: ignore[import-not-found]

from a_conductor.instance_create import create_instance
from a_conductor.instance_rename import (
    InstanceRenameError,
    rename_instance_backend,
)
from a_conductor.local_instances import discover_local_instances


@pytest.fixture()
def sandbox(tmp_path: Path):
    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    make_reference(instances_root)
    project = tmp_path / "proj"
    project.mkdir()
    return instances_root, project


def test_rename_moves_everything(sandbox) -> None:
    instances_root, project = sandbox
    create_instance(
        instances_root, "research", project, health_port=18014
    )

    new_root = rename_instance_backend(
        instances_root, "research", "sunday-worker-9", work_number=9
    )

    assert new_root.name == "sunday-worker-9"
    assert not (instances_root / "research").exists()

    ps1 = (new_root / "instance.ps1").read_text(encoding="utf-8")
    assert "$InstanceName = 'Sunday-Worker-9'" in ps1
    assert "$TunnelProfileName = 'serena-sunday-worker-9'" in ps1
    assert "sunday-worker-9\\serena-home" in ps1  # SerenaHome follows the folder
    assert "18014" in ps1  # port unchanged

    start = (new_root / "start.ps1").read_text(encoding="utf-8")
    assert "serena-sunday-worker-9.yaml.template" in start
    assert "serena-sunday-worker-9.yaml" in start
    assert "'sunday-worker-9-'" in start
    assert "research" not in start

    templates = list((new_root / "profiles").glob("*.template"))
    assert [t.name for t in templates] == ["serena-sunday-worker-9.yaml.template"]

    assert (new_root / "Start-Sunday-Worker-9.cmd").is_file()
    cmd = (new_root / "Start-Sunday-Worker-9.cmd").read_text(encoding="utf-8")
    assert "title Sunday-works 9 - Sunday-Worker-9" in cmd
    assert (new_root / "Stop-Sunday-Worker-9.cmd").is_file()


def test_rename_preserves_discovery(sandbox) -> None:
    instances_root, project = sandbox
    create_instance(instances_root, "research", project, health_port=18014)
    rename_instance_backend(instances_root, "research", "sunday-worker-9", work_number=9)

    instances = discover_local_instances(instances_root)
    by_name = {i.name: i for i in instances}
    assert "Sunday-Worker-9" in by_name
    renamed = by_name["Sunday-Worker-9"]
    assert renamed.health_address.endswith("18014")
    assert Path(renamed.project_path) == project


def test_rename_guards(sandbox) -> None:
    instances_root, project = sandbox
    create_instance(instances_root, "research", project, health_port=18014)
    create_instance(instances_root, "other", project, health_port=18015)

    with pytest.raises(InstanceRenameError) as exc:
        rename_instance_backend(instances_root, "missing", "sunday-worker-9")
    assert exc.value.code == "INSTANCE_NOT_FOUND"

    with pytest.raises(InstanceRenameError) as exc:
        rename_instance_backend(instances_root, "research", "other")
    assert exc.value.code == "TARGET_EXISTS"

    with pytest.raises(InstanceRenameError) as exc:
        rename_instance_backend(instances_root, "research", "Bad Slug!")
    assert exc.value.code == "SLUG_INVALID"

    # untouched on failure
    assert (instances_root / "research").exists()


def test_rename_removes_stale_run_profile(sandbox) -> None:
    instances_root, project = sandbox
    create_instance(instances_root, "research", project, health_port=18014)
    (instances_root / "research" / "run" / "serena-research.yaml").write_text(
        "stale", encoding="utf-8"
    )
    new_root = rename_instance_backend(
        instances_root, "research", "sunday-worker-9", work_number=9
    )
    assert not (new_root / "run" / "serena-research.yaml").exists()
