from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.worker_serena_settings import (
    LanguageBackend,
    WorkerSerenaSettings,
    apply_worker_serena_settings,
)


def base_settings(**overrides) -> WorkerSerenaSettings:
    values = {
        "worker_id": "a-worker-01",
        "language_backend": LanguageBackend.LSP,
        "excluded_tools": ("find_file",),
        "included_optional_tools": (),
        "fixed_tools": (),
        "base_modes": ("interactive", "editing"),
        "tool_timeout": 300,
    }
    values.update(overrides)
    return WorkerSerenaSettings(**values)


def test_default_settings_render_core_lines(tmp_path: Path) -> None:
    settings = WorkerSerenaSettings(worker_id="a-worker-02")

    text = settings.render_serena_config(project_path=r"A:\GitHub\env-wastewater-webapp")

    assert "language_backend: LSP" in text
    assert "tool_timeout: 240" in text
    assert "excluded_tools: []" in text
    assert "fixed_tools: []" in text
    assert "projects:" in text
    assert r"'A:\GitHub\env-wastewater-webapp'" in text


def test_custom_values_render_lists_and_backend(tmp_path: Path) -> None:
    settings = base_settings()

    text = settings.render_serena_config(project_path=r"A:\GitHub\demo")

    assert "language_backend: LSP" in text
    assert "tool_timeout: 300" in text
    assert text.count("- find_file") == 1
    assert "- interactive" in text
    assert "- editing" in text


def test_jetbrains_backend_renders(tmp_path: Path) -> None:
    settings = base_settings(language_backend=LanguageBackend.JETBRAINS)

    assert "language_backend: JetBrains" in settings.render_serena_config(project_path="A:/x")


def test_fixed_tools_are_exclusive_with_other_tool_lists() -> None:
    with pytest.raises(ValueError) as exc:
        base_settings(fixed_tools=("read_file",), excluded_tools=("find_file",))
    assert "FIXED_TOOLS_EXCLUSIVE" in str(exc.value)
    with pytest.raises(ValueError):
        base_settings(fixed_tools=("read_file",), included_optional_tools=("create_memory",))


def test_fixed_tools_alone_is_valid() -> None:
    settings = base_settings(
        fixed_tools=("read_file", "execute_shell"),
        excluded_tools=(),
        included_optional_tools=(),
    )
    text = settings.render_serena_config(project_path="A:/x")
    assert "- read_file" in text
    assert "- execute_shell" in text


def test_invalid_tool_names_and_duplicates_rejected() -> None:
    with pytest.raises(ValueError):
        base_settings(excluded_tools=("bad name",))
    with pytest.raises(ValueError):
        base_settings(excluded_tools=("",))
    with pytest.raises(ValueError):
        base_settings(excluded_tools=("find_file", "find_file"))
    with pytest.raises(ValueError):
        base_settings(base_modes=("interactive", "interactive"))
    with pytest.raises(ValueError):
        base_settings(base_modes=("",))


def test_tool_timeout_bounds_and_worker_id_pattern() -> None:
    with pytest.raises(ValueError):
        base_settings(tool_timeout=0)
    with pytest.raises(ValueError):
        base_settings(tool_timeout=86401)
    with pytest.raises(ValueError):
        WorkerSerenaSettings(worker_id="../escape")
    with pytest.raises(ValueError):
        WorkerSerenaSettings(worker_id="Worker 01")


def test_applier_writes_confined_serena_config(tmp_path: Path) -> None:
    root = tmp_path / "instances"
    root.mkdir()
    settings = base_settings(worker_id="a-worker-03")

    written = apply_worker_serena_settings(
        settings,
        instances_root=root,
        project_path=r"A:\GitHub\env-wastewater-webapp",
    )

    expected = (root / "a-worker-03" / "serena-home" / "serena_config.yml").resolve()
    assert written == expected
    text = written.read_text(encoding="utf-8")
    assert "tool_timeout: 300" in text
    assert "- find_file" in text
    assert r"'A:\GitHub\env-wastewater-webapp'" in text


def test_applier_overwrites_on_reapply(tmp_path: Path) -> None:
    root = tmp_path / "instances"
    root.mkdir()
    first = apply_worker_serena_settings(
        base_settings(),
        instances_root=root,
        project_path="A:/one",
    )
    second = apply_worker_serena_settings(
        base_settings(tool_timeout=999),
        instances_root=root,
        project_path="A:/two",
    )
    assert first == second
    text = second.read_text(encoding="utf-8")
    assert "tool_timeout: 999" in text
    assert "A:/one" not in text


def test_applier_requires_existing_root(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError) as exc:
        apply_worker_serena_settings(
            base_settings(),
            instances_root=tmp_path / "missing",
            project_path="A:/x",
        )
    assert "INSTANCES_ROOT_NOT_FOUND" in str(exc.value)


def test_render_round_trip_key_values(tmp_path: Path) -> None:
    settings = base_settings(
        excluded_tools=("find_file", "restart_language_server"),
        included_optional_tools=("create_memory",),
        base_modes=("editing",),
        tool_timeout=120,
    )
    text = settings.render_serena_config(project_path=r"A:\GitHub\A-Wiki-Conductor")

    for fragment in (
        "language_backend: LSP",
        "tool_timeout: 120",
        "- find_file",
        "- restart_language_server",
        "- create_memory",
        "- editing",
        r"'A:\GitHub\A-Wiki-Conductor'",
        "excluded_tools:",
        "included_optional_tools:",
        "base_modes:",
        "line_ending: native",
        "web_dashboard: false",
    ):
        assert fragment in text


def test_store_round_trip_settings(tmp_path: Path) -> None:
    from a_conductor.serena_config_store import (
        SerenaConfigStoreError,
        SQLiteSerenaConfigStore,
    )

    store = SQLiteSerenaConfigStore(tmp_path / "settings.sqlite")
    store.initialize()
    assert store.get_worker_settings("a-worker-01") is None

    settings = base_settings()
    store.save_worker_settings(settings)
    assert store.get_worker_settings("a-worker-01") == settings

    updated = base_settings(tool_timeout=999, excluded_tools=())
    store.save_worker_settings(updated)
    assert store.get_worker_settings("a-worker-01") == updated
    assert store.get_worker_settings("a-worker-02") is None

    try:
        store.save_worker_settings("not-settings")
    except SerenaConfigStoreError as exc:
        assert "SETTINGS_INVALID" in str(exc)
    else:
        raise AssertionError("non-settings value was accepted")


def test_desktop_control_settings_facade_defaults_and_save(tmp_path: Path) -> None:
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.serena_config_store import (
        SerenaConfigStoreError,
        SQLiteSerenaConfigStore,
    )

    store = SQLiteSerenaConfigStore(tmp_path / "facade.sqlite")
    service = DesktopControlService(
        control_center=object(),
        lifecycle=object(),
        settings_store=store,
    )

    default = service.worker_settings("a-worker-01")
    assert default == WorkerSerenaSettings(worker_id="a-worker-01")

    saved = service.save_worker_settings(base_settings())
    assert saved == base_settings()
    assert service.worker_settings("a-worker-01") == base_settings()

    try:
        service.save_worker_settings("not-settings")
    except SerenaConfigStoreError as exc:
        assert "SETTINGS_INVALID" in str(exc)
    else:
        raise AssertionError("facade accepted invalid settings")

    unavailable = DesktopControlService(control_center=object(), lifecycle=object())
    try:
        unavailable.worker_settings("a-worker-01")
    except SerenaConfigStoreError as exc:
        assert "SETTINGS_STORE_NOT_AVAILABLE" in str(exc)
    else:
        raise AssertionError("missing store was not reported")


def test_settings_v2_languages_and_project_validation() -> None:
    ok = base_settings(
        enabled_languages=("python", "html", "markdown"),
        project_path=r"A:\GitHub\demo",
    )
    text = ok.render_serena_config()
    assert "  typescript: 0" in text
    assert "  rust: 0" in text
    assert "  python: 0" not in text
    assert r"'A:\GitHub\demo'" in text

    with pytest.raises(ValueError):
        base_settings(enabled_languages=("python", "python"))
    with pytest.raises(ValueError):
        base_settings(enabled_languages=("klingon",))
    with pytest.raises(ValueError):
        base_settings(project_path="   ")


def test_settings_v2_empty_languages_render_plain_priorities() -> None:
    text = base_settings().render_serena_config(project_path="A:/x")
    assert "ls_priorities:" in text
    assert ": 0" not in text


def test_settings_v2_no_project_renders_empty_projects() -> None:
    text = WorkerSerenaSettings(worker_id="a-worker-01").render_serena_config()
    assert "projects: []" in text


def test_settings_v2_param_overrides_project_field() -> None:
    settings = base_settings(project_path=r"A:\GitHub\field")
    text = settings.render_serena_config(project_path=r"A:\GitHub\param")
    assert r"'A:\GitHub\param'" in text
    assert r"'A:\GitHub\field'" not in text


def test_store_migration_adds_v2_columns(tmp_path: Path) -> None:
    import sqlite3

    from a_conductor.serena_config_store import SQLiteSerenaConfigStore

    database = tmp_path / "legacy.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE serena_config_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE serena_worker_settings (
            worker_id TEXT PRIMARY KEY,
            language_backend TEXT NOT NULL,
            excluded_tools TEXT NOT NULL,
            included_optional_tools TEXT NOT NULL,
            fixed_tools TEXT NOT NULL,
            base_modes TEXT NOT NULL,
            tool_timeout INTEGER NOT NULL
        );
        INSERT INTO serena_worker_settings VALUES(
            'a-worker-01', 'LSP', '[]', '[]', '[]', '[]', 240
        );
        """
    )
    connection.commit()
    connection.close()

    store = SQLiteSerenaConfigStore(database)
    store.initialize()
    migrated = store.get_worker_settings("a-worker-01")
    assert migrated is not None
    assert migrated.tool_timeout == 240
    assert migrated.project_path is None
    assert migrated.enabled_languages == ()

    updated = base_settings(
        enabled_languages=("python", "markdown"),
        project_path=r"A:\GitHub\demo",
    )
    store.save_worker_settings(updated)
    reloaded = store.get_worker_settings("a-worker-01")
    assert reloaded == updated
    assert reloaded.enabled_languages == ("python", "markdown")


def test_brain_settings_validation() -> None:
    ok = base_settings(
        brain_folders=(r"A:\GitHub\A-Wiki",),
        brain_entry_files=(r"A:\GitHub\A-Wiki\AGENTS.md", r"A:\GitHub\A-Wiki\wiki\context\wiki-overview.md"),
    )
    assert ok.brain_folders == (r"A:\GitHub\A-Wiki",)

    with pytest.raises(ValueError):
        base_settings(brain_folders=(r"A:\GitHub\A", r"A:\GitHub\B", r"A:\GitHub\C"))
    with pytest.raises(ValueError):
        base_settings(brain_folders=("relative/path",))
    with pytest.raises(ValueError):
        base_settings(brain_folders=("",))
    with pytest.raises(ValueError):
        base_settings(brain_folders=(r"A:\X", r"A:\X"))
    with pytest.raises(ValueError):
        base_settings(brain_entry_files=("not/absolute.md",))
    with pytest.raises(ValueError):
        base_settings(brain_entry_files=(r"A:\X\a.md", r"A:\X\b.md", r"A:\X\c.md"))


def test_brain_render_injects_system_prompt_index_only() -> None:
    settings = base_settings(
        brain_folders=(r"A:\GitHub\A-Wiki",),
        brain_entry_files=(r"A:\GitHub\A-Wiki\AGENTS.md",),
    )
    text = settings.render_serena_config(project_path="A:/x")

    assert "system_prompt: |" in text
    assert "[A-CONDUCTOR SECOND BRAIN]" in text
    assert r"A:\GitHub\A-Wiki" in text
    assert r"A:\GitHub\A-Wiki\AGENTS.md" in text
    assert "BEFORE starting the task" in text
    assert "read_file" in text
    # Index-only mandate: the brain block stays compact (no file contents).
    start = text.index("system_prompt: |")
    end = text.index("language_backend:")
    block = text[start:end] if start < end else text[start : start + 2000]
    assert len(block) < 1600


def test_brain_absent_renders_no_system_prompt() -> None:
    text = base_settings().render_serena_config(project_path="A:/x")
    assert "system_prompt" not in text


def test_brain_store_migration_and_round_trip(tmp_path: Path) -> None:
    import sqlite3

    from a_conductor.serena_config_store import SQLiteSerenaConfigStore

    database = tmp_path / "legacy2.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE serena_config_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE serena_worker_settings (
            worker_id TEXT PRIMARY KEY,
            language_backend TEXT NOT NULL,
            excluded_tools TEXT NOT NULL,
            included_optional_tools TEXT NOT NULL,
            fixed_tools TEXT NOT NULL,
            base_modes TEXT NOT NULL,
            tool_timeout INTEGER NOT NULL,
            project_path TEXT,
            enabled_languages TEXT
        );
        """
    )
    connection.commit()
    connection.close()

    store = SQLiteSerenaConfigStore(database)
    store.initialize()

    settings = base_settings(
        brain_folders=(r"A:\GitHub\A-Wiki",),
        brain_entry_files=(r"A:\GitHub\A-Wiki\AGENTS.md",),
    )
    store.save_worker_settings(settings)
    loaded = store.get_worker_settings(settings.worker_id)
    assert loaded == settings
    assert loaded.brain_folders == (r"A:\GitHub\A-Wiki",)


def test_apply_brain_to_serena_home_append_guard_idempotent(tmp_path: Path) -> None:
    from a_conductor.worker_serena_settings import apply_brain_to_serena_home

    home = tmp_path / "serena-home"
    home.mkdir()
    config = home / "serena_config.yml"
    config.write_text(
        "language_backend: LSP\ntool_timeout: 240\n", encoding="utf-8"
    )
    profile = base_settings(
        brain_folders=(r"A:\GitHub\A-Wiki",),
        brain_entry_files=(r"A:\GitHub\A-Wiki\AGENTS.md",),
    )

    first = apply_brain_to_serena_home(profile, home)
    text_one = config.read_text(encoding="utf-8")

    assert first == "APPLIED"
    assert "language_backend: LSP" in text_one
    assert "system_prompt: |" in text_one
    assert "[A-CONDUCTOR SECOND BRAIN]" in text_one

    updated_profile = base_settings(
        brain_folders=(r"A:\GitHub\Other",),
        brain_entry_files=(r"A:\GitHub\Other\rules.md",),
    )
    second = apply_brain_to_serena_home(updated_profile, home)
    text_two = config.read_text(encoding="utf-8")

    assert second == "APPLIED"
    assert text_two.count("system_prompt: |") == 1
    assert r"A:\GitHub\Other" in text_two
    assert r"A:\GitHub\A-Wiki\AGENTS.md" not in text_two


def test_apply_brain_skip_cases(tmp_path: Path) -> None:
    from a_conductor.worker_serena_settings import apply_brain_to_serena_home

    empty_home = tmp_path / "empty"
    empty_home.mkdir()
    assert apply_brain_to_serena_home(base_settings(), empty_home) == "SKIPPED_NO_CONFIG"

    home = tmp_path / "home"
    home.mkdir()
    config = home / "serena_config.yml"
    config.write_text("language_backend: LSP\n", encoding="utf-8")
    assert apply_brain_to_serena_home(base_settings(), home) == "SKIPPED_NO_BRAIN"

    config.write_text(
        "system_prompt: |\n  pre-existing owner prompt\n", encoding="utf-8"
    )
    brainy = base_settings(brain_folders=(r"A:\GitHub\A-Wiki",))
    assert apply_brain_to_serena_home(brainy, home) == "SKIPPED_SYSTEM_PROMPT_PRESENT"
    assert "SECOND BRAIN" not in config.read_text(encoding="utf-8")
