"""Loop A-1: bilingual config blurbs + MODE grid wiring."""

from __future__ import annotations

from pathlib import Path

import pytest


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
    finally:
        from a_conductor import i18n

        i18n.set_language("th")


def test_blurbs_en_mirror_every_thai_dict() -> None:
    from a_conductor import config_blurbs as th
    from a_conductor import config_blurbs_en as en

    for name in (
        "LANGUAGE_BACKEND_BLURBS",
        "TOOL_BLURBS",
        "MODE_BLURBS",
        "LANGUAGE_BLURBS",
        "FIELD_BLURBS",
    ):
        th_dict = getattr(th, name)
        en_dict = getattr(en, name)
        assert set(th_dict) == set(en_dict), name
        assert all(value.strip() for value in en_dict.values()), name


def test_active_blurbs_follow_language() -> None:
    from a_conductor import config_blurbs
    from a_conductor.i18n import set_language

    set_language("en")
    assert "agent inspects" in config_blurbs.active_blurbs().TOOL_BLURBS["read_file"]

    set_language("th")
    assert "อ่านไฟล์" in config_blurbs.active_blurbs().TOOL_BLURBS["read_file"]


def test_config_dialog_has_mode_checkboxes(root, tmp_path: Path) -> None:
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    service = DesktopControlService.open(tmp_path / "cc.sqlite")
    app = AConductorDesktopApp(root, service=service)
    app.worker_tree.selection_clear()
    app.worker_tree.selection_set(app.worker_tree.get_children()[0])
    dialog = app.open_worker_config()
    try:
        assert hasattr(app, "_config_mode_vars")
        assert len(app._config_mode_vars) == 8
        # fresh settings carry no modes -> all unchecked; check one and save
        assert all(var.get() is False for var in app._config_mode_vars.values())
        app._config_mode_vars["interactive"].set(True)
        app._config_mode_vars["editing"].set(True)
        app.save_worker_config()
        saved = service.worker_settings("a-worker-01")
        assert set(saved.base_modes) == {"interactive", "editing"}
    finally:
        if dialog.winfo_exists():
            dialog.destroy()
