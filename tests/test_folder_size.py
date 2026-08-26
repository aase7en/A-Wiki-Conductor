"""WO-P1-070 — project folder size display (data-only, no subprocess)."""

from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.folder_size import (
    disk_particle_levels,
    folder_size_bytes,
    format_size,
    project_disk_display,
)


def test_folder_size_sums_files(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"x" * 100)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_bytes(b"y" * 200)
    assert folder_size_bytes(tmp_path) == 300


def test_empty_folder_is_zero(tmp_path: Path) -> None:
    assert folder_size_bytes(tmp_path) == 0


def test_missing_path_is_zero(tmp_path: Path) -> None:
    assert folder_size_bytes(tmp_path / "nonexistent") == 0


def test_format_bytes() -> None:
    assert format_size(0) == "0 B"
    assert format_size(500) == "500 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(1024 * 1024) == "1.0 MB"
    assert format_size(1024 * 1024 * 1024) == "1.0 GB"


def test_format_large_sizes() -> None:
    assert format_size(1536 * 1024 * 1024) == "1.5 GB"
    assert format_size(5 * 1024 * 1024) == "5.0 MB"


def test_display_none_path() -> None:
    assert project_disk_display(None) == "—"


def test_display_real_path(tmp_path: Path) -> None:
    (tmp_path / "f.bin").write_bytes(b"z" * 2048)
    assert project_disk_display(tmp_path) == "2.0 KB"


def test_cancelled_scan_returns_none_before_walk(tmp_path: Path, monkeypatch) -> None:
    import a_conductor.folder_size as fs

    def explode(_root):
        raise AssertionError("os.walk must not run after cancellation")

    monkeypatch.setattr(fs.os, "walk", explode)
    assert fs.folder_size_bytes(tmp_path, cancel_check=lambda: True) is None
    assert fs.project_disk_display(tmp_path, cancel_check=lambda: True) is None


def test_never_spawns_subprocess() -> None:
    """WO-P1-070: verify no subprocess import in the module."""
    import a_conductor.folder_size as fs
    assert not hasattr(fs, "subprocess"), "folder_size must not import subprocess"
    assert not hasattr(fs, "Popen"), "folder_size must not use Popen"


def test_disk_particle_levels_are_monotonic_log_magnitude() -> None:
    samples = ["1.0 KB", "1.0 MB", "1.0 GB", "1.0 TB"]
    lit = [sum(level > 0 for level in disk_particle_levels(value)) for value in samples]
    assert lit == sorted(lit)
    assert len(set(lit)) == len(lit)
    assert lit[-1] == 24


def test_disk_particle_levels_are_visual_only_and_fail_closed() -> None:
    assert disk_particle_levels("—") == (0.0,) * 24
    assert disk_particle_levels("…") == (0.0,) * 24
    assert disk_particle_levels("not-a-size") == (0.0,) * 24
    levels = disk_particle_levels("1.0 GB")
    active = [level for level in levels if level > 0]
    assert active
    assert active == sorted(active)
    assert all(0.0 <= level <= 1.0 for level in levels)
