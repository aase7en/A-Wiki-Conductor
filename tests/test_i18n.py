"""Bilingual UI: string table integrity, error coverage, language preference."""

from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor import i18n
from a_conductor.i18n import STRINGS, get_language, set_language, tr


def test_default_language_is_thai() -> None:
    set_language("th")
    assert tr("btn.guide") == "คู่มือ"


def test_switch_to_english() -> None:
    set_language("en")
    assert tr("btn.guide") == "Guide"
    set_language("th")


def test_unknown_key_falls_back_to_key() -> None:
    assert tr("no.such.key") == "no.such.key"


def test_every_entry_has_both_languages() -> None:
    for key, entry in STRINGS.items():
        assert entry.get("th", "").strip(), key
        assert entry.get("en", "").strip(), key


def test_english_error_explanations_cover_every_thai_code() -> None:
    from a_conductor.desktop_ui import ERROR_EXPLANATIONS
    from a_conductor.error_explanations_en import ERROR_EXPLANATIONS_EN

    missing = sorted(set(ERROR_EXPLANATIONS) - set(ERROR_EXPLANATIONS_EN))
    assert not missing, missing
    for code, (title, lines) in ERROR_EXPLANATIONS_EN.items():
        assert title.strip(), code
        assert all(line.strip() for line in lines), code


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
        set_language("th")


def make_app(root, tmp_path: Path, language: bool | None = None):
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    service = DesktopControlService.open(tmp_path / "ui.sqlite")
    if language is not None:
        service.set_preference("language", language)
    app = AConductorDesktopApp(root, service=service)
    root.update()
    return app


def test_app_opens_in_english_when_preference_set(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path, language=True)
    assert get_language() == "en"
    assert app.help_button.cget("text") == "Guide"
    assert app.prefs_button.cget("text") == "Settings"


def test_app_opens_in_thai_by_default(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    assert get_language() == "th"
    assert app.help_button.cget("text") == "คู่มือ"


def test_error_popup_uses_english_when_switched(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path, language=True)
    window = app._show_error("SELECT_WORKER")
    try:
        assert "Notice" in window.title()
        texts = [
            str(child.cget("text"))
            for child in window.winfo_children()[0].winfo_children()
            if hasattr(child, "cget")
        ]
        assert any("No Worker selected" in text for text in texts)
    finally:
        window.destroy()


def test_connector_button_labels_follow_language(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path, language=True)
    assert app.add_instance_button.cget("text") == "+ Connector"
    assert app.rename_instance_button.cget("text") == "Rename"
    assert app.delete_instance_button.cget("text") == "Delete"


def test_preferences_language_switch_toggles_preference(root, tmp_path: Path) -> None:
    import tkinter as tk

    app = make_app(root, tmp_path, language=False)
    window = app.open_preferences()
    try:
        boxes = [
            child
            for child in window.winfo_children()[0].winfo_children()
            if isinstance(child, tk.Checkbutton)
        ]
        assert len(boxes) == 2
        boxes[1].invoke()
        assert app.service.get_preference("language") is True
        assert get_language() == "en"
        boxes[1].invoke()
        assert app.service.get_preference("language") is False
        assert get_language() == "th"
    finally:
        window.destroy()
