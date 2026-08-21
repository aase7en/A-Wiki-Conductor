from __future__ import annotations

from pathlib import Path

from a_conductor.memory_presence import (
    MemoryPresenceState,
    inspect_memory_presence,
)


def test_no_project(tmp_path: Path) -> None:
    result = inspect_memory_presence(tmp_path / "missing")
    assert result.state is MemoryPresenceState.NO_PROJECT
    assert result.total_files == 0


def test_no_memories_dir(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    result = inspect_memory_presence(project)
    assert result.state is MemoryPresenceState.NO_MEMORIES
    assert result.total_files == 0


def test_empty_dir(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    (project / ".serena" / "memories").mkdir(parents=True)
    result = inspect_memory_presence(project)
    assert result.state is MemoryPresenceState.EMPTY


def test_maintenance_only(tmp_path: Path) -> None:
    memories = tmp_path / "proj" / ".serena" / "memories"
    memories.mkdir(parents=True)
    (memories / "memory_maintenance.md").write_text("seeded", encoding="utf-8")
    result = inspect_memory_presence(tmp_path / "proj")
    assert result.state is MemoryPresenceState.MAINTENANCE_ONLY
    assert result.total_files == 1
    assert result.maintenance_only is True


def test_has_memories(tmp_path: Path) -> None:
    memories = tmp_path / "proj" / ".serena" / "memories"
    memories.mkdir(parents=True)
    (memories / "memory_maintenance.md").write_text("seeded", encoding="utf-8")
    (memories / "architecture.md").write_text("notes", encoding="utf-8")
    (memories / "global_rules.md").write_text("rules", encoding="utf-8")
    result = inspect_memory_presence(tmp_path / "proj")
    assert result.state is MemoryPresenceState.HAS_MEMORIES
    assert result.total_files == 3
    assert result.maintenance_only is False


def test_read_only(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    inspect_memory_presence(project)
    inspect_memory_presence(tmp_path / "elsewhere")
    assert list(project.iterdir()) == []
