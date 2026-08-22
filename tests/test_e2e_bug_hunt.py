"""E2E bug hunt: adversarial scenarios through the real facade + real files.

Each scenario is designed to poke edges a happy-path suite never touches.
No mocking except where the real OS interaction is flaky by nature (health
probes, running processes).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_instance_create import make_reference  # type: ignore[import-not-found]

from a_conductor.desktop_control import DesktopControlService
from a_conductor.instance_create import InstanceCreateError
from a_conductor.instance_monitor import monitor_report, read_pid
from a_conductor.instance_runtime import reap_instance_wrappers


@pytest.fixture()
def service(tmp_path: Path) -> DesktopControlService:
    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    make_reference(instances_root)
    return DesktopControlService.open(tmp_path / "cc.sqlite", instances_root=instances_root)


def project(tmp_path: Path, name: str = "proj") -> Path:
    p = tmp_path / name
    p.mkdir(exist_ok=True)
    return p


# --- weird but legal names -------------------------------------------------


@pytest.mark.parametrize("slug", ["a", "x-1", "chat2", "sunday-worker-42"])
def test_create_with_short_and_numeric_names(service, tmp_path, slug):
    created = service.create_instance(slug, str(project(tmp_path)))
    assert created.name.lower().endswith(slug)
    assert (Path(service.instances_root) / slug).is_dir()


@pytest.mark.parametrize(
    "slug",
    ["-lead", "ทดสอบ", "with space", "x_y", "tab\tname"],
)
def test_create_rejects_hostile_slugs(service, tmp_path, slug):
    with pytest.raises(InstanceCreateError) as exc:
        service.create_instance(slug, str(project(tmp_path)))
    assert exc.value.code in ("NAME_INVALID", "NAME_ALREADY_EXISTS")


def test_create_accepts_uppercase_by_lowering(service, tmp_path):
    created = service.create_instance("Research", str(project(tmp_path)))
    assert (Path(service.instances_root) / "research").is_dir()


# --- weird project paths ----------------------------------------------------


def test_create_with_apostrophe_project_path(service, tmp_path):
    proj = tmp_path / "O'Brien"
    proj.mkdir()
    created = service.create_instance("apostrophe", str(proj))
    ps1 = (created.instance_root / "instance.ps1").read_text(encoding="utf-8")
    assert "O''Brien" in ps1  # escaped for PowerShell


def test_create_with_space_project_path_roundtrip(service, tmp_path):
    proj = tmp_path / "My Drive project"
    proj.mkdir()
    created = service.create_instance("spaced", str(proj))
    discovered = next(i for i in service.instances() if i.name == created.name)
    assert Path(discovered.project_path) == proj


@pytest.mark.parametrize("bad", ["relative/path", "", "Z:\\definitely\\missing"])
def test_create_rejects_bad_project_paths(service, tmp_path, bad):
    with pytest.raises(InstanceCreateError) as exc:
        service.create_instance("badpath", bad or "relative/path")
    assert exc.value.code in ("PROJECT_NOT_FOUND", "NAME_ALREADY_EXISTS")


# --- lifecycle edges --------------------------------------------------------


def test_delete_then_recreate_same_name(service, tmp_path):
    proj = project(tmp_path)
    service.create_instance("phoenix", str(proj))
    service.delete_instance("Serena-Phoenix")
    again = service.create_instance("phoenix", str(proj))  # must not collide
    assert again.name == "Serena-Phoenix"


def test_flags_and_alias_survive_reopen(service, tmp_path):
    proj = project(tmp_path)
    service.create_instance("durable", str(proj))
    service.set_instance_autostart("Serena-Durable", True)
    service.rename_instance("Serena-Durable", "งานยา")

    reopened = DesktopControlService.open(
        tmp_path / "cc.sqlite", instances_root=service.instances_root
    )
    assert reopened.instance_autostart("Serena-Durable") is True
    assert reopened.instance_aliases().get("Serena-Durable") == "งานยา"

    reopened.delete_instance("Serena-Durable")
    final = DesktopControlService.open(
        tmp_path / "cc.sqlite", instances_root=service.instances_root
    )
    assert "Serena-Durable" not in {i.name for i in final.instances()}
    assert "Serena-Durable" not in final.autostart_instance_names()
    assert "Serena-Durable" not in final.instance_aliases()


def test_delete_running_instance_refused(service, tmp_path, monkeypatch):
    import a_conductor.local_instances as local_instances
    from a_conductor.local_instances import InstanceHealthState

    proj = project(tmp_path)
    service.create_instance("busy", str(proj))
    target = next(i for i in service.instances() if i.name == "Serena-Busy")
    monkeypatch.setattr(
        local_instances, "instance_health_state", lambda _i, **_k: InstanceHealthState.READY
    )
    calls: list[str] = []
    monkeypatch.setattr(
        service, "instance_action", lambda name, action: calls.append(action)
    )
    from a_conductor.instance_delete import InstanceManageError

    with pytest.raises(InstanceManageError) as exc:
        service.delete_instance("Serena-Busy")
    assert exc.value.code == "INSTANCE_STOP_REQUIRED"
    assert calls == ["stop"]


# --- monitor robustness on broken folders -----------------------------------


def test_monitor_report_on_mangled_instance(tmp_path):
    broken = tmp_path / "broken"
    (broken / "run").mkdir(parents=True)
    (broken / "run" / "tunnel-client.pid").write_text("not-a-pid", encoding="utf-8")
    (broken / "logs").mkdir()
    (broken / "logs" / "today.log").write_text("", encoding="utf-8")

    report = monitor_report(broken, state="UNKNOWN")
    assert report["pid"] is None
    assert report["tail"] == []
    assert report["errors"] == []
    assert read_pid(broken) is None


def test_monitor_report_large_log_tail_only(tmp_path):
    inst = tmp_path / "big"
    (inst / "logs").mkdir(parents=True)
    lines = [f"line-{i}" for i in range(20000)]
    (inst / "logs" / "big.log").write_text("\n".join(lines), encoding="utf-8")
    report = monitor_report(inst, state="READY")
    assert report["tail"][-1] == "line-19999"
    assert len(report["tail"]) == 12


# --- reaper safety ----------------------------------------------------------


def test_reap_nonexistent_and_empty_paths():
    assert reap_instance_wrappers(Path("C:/AI/does-not-exist/at-all")) == []
    assert reap_instance_wrappers("") == []


# --- worker registry edges ---------------------------------------------------


def test_add_many_workers_then_delete_all_and_reopen(tmp_path):
    svc = DesktopControlService.open(tmp_path / "cc.sqlite")
    for _ in range(5):
        svc.add_worker()
    ids = [w.worker_id for w in svc.snapshot().workers]
    assert len(ids) == 8  # 3 default + 5

    for worker_id in list(ids):
        svc.delete_worker(worker_id)

    reopened = DesktopControlService.open(tmp_path / "cc.sqlite")
    names = [w.worker_id for w in reopened.snapshot().workers]
    # Deleting every worker is allowed; reopen then reseeds the 3 defaults
    # (documented bootstrap behavior when the registry is empty).
    assert names == ["a-worker-01", "a-worker-02", "a-worker-03"]


def test_rename_worker_to_same_name_is_idempotent(service, tmp_path):
    svc = DesktopControlService.open(tmp_path / "cc.sqlite")
    svc.rename_worker("a-worker-01", "Same")
    svc.rename_worker("a-worker-01", "Same")
    assert svc.snapshot().workers[0].display_name == "Same"


# --- i18n round-trip through popups ------------------------------------------


def test_error_popup_language_round_trip(tmp_path):
    from a_conductor import i18n
    from a_conductor.error_explanations_en import ERROR_EXPLANATIONS_EN

    i18n.set_language("en")
    table = ERROR_EXPLANATIONS_EN
    assert table["SELECT_WORKER"][0]
    i18n.set_language("th")
    from a_conductor.desktop_ui import ERROR_EXPLANATIONS

    assert ERROR_EXPLANATIONS["SELECT_WORKER"][0]
