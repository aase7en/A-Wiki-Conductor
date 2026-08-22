"""Loop B-1: platform layer — OS-aware roots and process flags."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from a_conductor.platform_support import (
    default_instances_root,
    is_windows,
    process_creation_flags,
)


def test_is_windows_matches_sys_platform(monkeypatch) -> None:
    monkeypatch.setattr("a_conductor.platform_support.sys.platform", "win32")
    assert is_windows() is True
    monkeypatch.setattr("a_conductor.platform_support.sys.platform", "linux")
    assert is_windows() is False


def test_windows_root_is_c_ai(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("a_conductor.platform_support.sys.platform", "win32")
    assert default_instances_root() == Path("C:/AI/serena-instances")


def test_posix_root_is_home_ai(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("a_conductor.platform_support.sys.platform", "linux")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert default_instances_root() == tmp_path / "AI" / "serena-instances"


def test_env_override_wins_all_platforms(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("A_CONDUCTOR_INSTANCES_ROOT", str(tmp_path / "custom"))
    assert default_instances_root() == tmp_path / "custom"
    monkeypatch.setattr("a_conductor.platform_support.sys.platform", "linux")
    assert default_instances_root() == tmp_path / "custom"


def test_creation_flags_windows_use_create_no_window(monkeypatch) -> None:
    monkeypatch.setattr("a_conductor.platform_support.sys.platform", "win32")
    flags = process_creation_flags()
    assert flags  # truthy on Windows (CREATE_NO_WINDOW bit)


def test_creation_flags_posix_zero(monkeypatch) -> None:
    monkeypatch.setattr("a_conductor.platform_support.sys.platform", "darwin")
    assert process_creation_flags() == 0


def test_local_instances_default_root_follows_platform(monkeypatch, tmp_path: Path) -> None:
    import a_conductor.local_instances as local_instances

    monkeypatch.setenv("A_CONDUCTOR_INSTANCES_ROOT", str(tmp_path / "from-env"))
    # The resolver honors the env at call time (the module constant is an
    # import-time snapshot only).
    assert Path(local_instances.default_instances_root()) == tmp_path / "from-env"


def test_launcher_on_posix_spawns_direct_shell(monkeypatch, tmp_path: Path) -> None:
    """On POSIX the launcher runs the .sh entry directly (no cmd.exe)."""
    import a_conductor.local_instances as local_instances

    monkeypatch.setattr(local_instances.sys, "platform", "linux")
    captured: dict = {}

    class FakePopen:
        def __init__(self, argv, **kwargs):
            captured["argv"] = argv
            captured["kwargs"] = kwargs

    monkeypatch.setattr(local_instances.subprocess, "Popen", FakePopen)
    script = tmp_path / "start.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    local_instances._default_launcher(script, tmp_path)
    argv = captured["argv"]
    assert argv[0] in ("/bin/sh", "sh")
    assert str(script) in argv
    assert captured["kwargs"].get("start_new_session") is True
