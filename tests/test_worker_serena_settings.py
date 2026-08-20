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
