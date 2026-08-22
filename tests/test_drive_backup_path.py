"""Instance-delete backups prefer the A-Wiki-Data Drive layer when present."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_instance_create import make_reference  # type: ignore[import-not-found]

from a_conductor.desktop_control import DesktopControlService
from a_conductor.desktop_control import default_backup_dir


def test_default_backup_dir_prefers_drive_layer(tmp_path: Path, monkeypatch) -> None:
    drive_backup = tmp_path / "drive" / "A-Wiki-Data" / "backups" / "a-conductor-instances"
    drive_backup.mkdir(parents=True)
    monkeypatch.setattr(
        "a_conductor.desktop_control.A_WIKI_DATA_BACKUP_DIR", drive_backup
    )
    assert default_backup_dir() == drive_backup


def test_default_backup_dir_falls_back_to_localappdata(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "a_conductor.desktop_control.A_WIKI_DATA_BACKUP_DIR",
        tmp_path / "drive" / "missing",
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    assert default_backup_dir() == tmp_path / "local" / "A-Conductor" / "instance-backups"


def test_delete_instance_writes_zip_into_drive_layer(tmp_path: Path, monkeypatch) -> None:
    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    make_reference(instances_root)
    project = tmp_path / "proj"
    project.mkdir()
    service = DesktopControlService.open(
        tmp_path / "cc.sqlite", instances_root=instances_root
    )
    service.create_instance("Research", str(project))

    drive_backup = tmp_path / "drive" / "backups" / "a-conductor-instances"
    drive_backup.mkdir(parents=True)
    monkeypatch.setattr(
        "a_conductor.desktop_control.A_WIKI_DATA_BACKUP_DIR", drive_backup
    )

    zipped = service.delete_instance("Serena-Research")

    assert zipped.parent == drive_backup
    assert zipped.is_file()
