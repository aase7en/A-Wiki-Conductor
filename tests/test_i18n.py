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

    instances_root = tmp_path / "instances"
    instances_root.mkdir(exist_ok=True)
    service = DesktopControlService.open(
        tmp_path / "ui.sqlite", instances_root=instances_root
    )
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
    # Action labels stay canonical English; hover help follows Thai.
    assert app.help_button.cget("text") == "Guide"
    provider = app.help_button._acond_tooltip.text
    assert callable(provider)
    assert "คู่มือ" in provider()


def test_row_copy_menu_label_provider_changes_language_live(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    provider = app._row_path_menu_label_providers[app.worker_tree]

    set_language("th")
    thai = provider()
    expected_thai = tr("menu.copy.path")
    set_language("zh-CN")
    chinese = provider()
    expected_chinese = tr("menu.copy.path")
    set_language("en")
    expected_english = tr("menu.copy.path")

    assert thai == expected_thai
    assert chinese == expected_chinese
    assert provider() == expected_english
    assert thai != provider()
    assert chinese != provider()


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


def test_chinese_session_uses_english_error_fallback_not_thai(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    set_language("zh-CN")
    window = app._show_error("SELECT_WORKER")
    try:
        texts = [
            str(child.cget("text"))
            for child in window.winfo_children()[0].winfo_children()
            if hasattr(child, "cget")
        ]
        assert any("No Worker selected" in text for text in texts)
        assert not any(any("\u0e00" <= char <= "\u0e7f" for char in text) for text in texts)
    finally:
        window.destroy()


def test_connector_button_labels_are_canonical_english(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path, language=True)
    assert app.add_instance_button.cget("text") == "Add Connector"
    assert app.rename_instance_button.cget("text") == "Rename"
    assert app.delete_instance_button.cget("text") == "Delete"


def test_preferences_language_switch_persists_three_languages(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path, language=False)
    window = app.open_preferences()
    try:
        combo = app._language_combo
        combo.set("中文")
        combo.event_generate("<<ComboboxSelected>>")
        root.update()
        assert get_language() == "zh-CN"
        assert app.service.get_preference("language_zh") is True
        assert app.service.get_preference("language") is False

        combo.set("English")
        combo.event_generate("<<ComboboxSelected>>")
        root.update()
        assert get_language() == "en"
        assert app.service.get_preference("language_zh") is False
        assert app.service.get_preference("language") is True

        combo.set("Thai")
        combo.event_generate("<<ComboboxSelected>>")
        root.update()
        assert get_language() == "th"
        assert app.service.get_preference("language_zh") is False
        assert app.service.get_preference("language") is False
    finally:
        window.destroy()


def test_chinese_switch_refreshes_open_settings_and_monitor_without_thai(
    root, tmp_path: Path
) -> None:
    app = make_app(root, tmp_path, language=False)
    window = app.open_preferences()
    try:
        app._language_combo.set("中文")
        app._language_combo.event_generate("<<ComboboxSelected>>")
        app._render_monitor(None, None)
        root.update()

        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)

        visible_text = []
        for widget in walk(window):
            try:
                text = str(widget.cget("text"))
            except Exception:
                continue
            if text:
                visible_text.append(text)
        visible_text.append(app.monitor_text.get("1.0", "end"))
        assert visible_text
        assert not any(
            any("\u0e00" <= char <= "\u0e7f" for char in text)
            for text in visible_text
        )
    finally:
        window.destroy()


def test_preferences_dialog_is_single_instance(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)

    first = app.open_preferences()
    second = app.open_preferences()

    assert first is not None
    assert second is first
    first.destroy()


def test_switch_to_chinese_localized_help() -> None:
    set_language("zh-CN")
    assert "工作槽" in tr("tip.add.worker") or "工作" in tr("tip.add.worker")
    set_language("th")


def test_canonical_button_labels_are_always_english() -> None:
    from a_conductor.i18n import canonical_button_label

    assert canonical_button_label("คู่มือ") == "Guide"
    assert canonical_button_label("ตั้งค่า") == "Settings"
    assert canonical_button_label("บันทึก") == "Save"
    assert canonical_button_label("ยกเลิก") == "Cancel"
    assert canonical_button_label("เปิดไฟล์ภายนอก") == "Open External File"
    assert canonical_button_label("เลือกโฟลเดอร์...") == "Browse Folder..."


def test_tooltip_provider_changes_language_live(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    provider = app.start_button._acond_tooltip.text
    assert callable(provider)
    set_language("th")
    thai = provider()
    set_language("zh-CN")
    chinese = provider()
    set_language("en")
    english = provider()
    assert thai != chinese != english
    assert "启动" in chinese
    assert "Start" in english


def test_wo127_models_agents_action_keys_cover_all_three_languages() -> None:
    keys = (
        "prefs.models_agents.edit", "prefs.models_agents.disable", "prefs.models_agents.enable",
        "prefs.models_agents.test", "prefs.models_agents.save", "prefs.models_agents.cancel",
        "prefs.models_agents.edit.help", "prefs.models_agents.toggle.help", "prefs.models_agents.test.help",
        "prefs.models_agents.credential.label", "prefs.models_agents.credential.help",
        "prefs.models_agents.unsupported_credential",
    )
    for key in keys:
        entry = STRINGS[key]
        assert entry.get("th", "").strip(), key
        assert entry.get("en", "").strip(), key
        set_language("zh-CN")
        assert tr(key).strip() and tr(key) != key, key
    set_language("th")


def test_wo127_provider_teaching_errors_have_no_mojibake() -> None:
    from a_conductor.desktop_ui import ERROR_EXPLANATIONS

    codes = ("PROVIDER_PROFILE_INVALID", "CONFIG_STORE_UNAVAILABLE", "CONFIG_STORE_SCHEMA_UNAVAILABLE", "CONFIG_STORE_READ_FAILED")
    for code in codes:
        title, lines = ERROR_EXPLANATIONS[code]
        text = " ".join((title, *lines))
        assert "??" not in text, code
        assert "\ufffd" not in text, code
    assert ERROR_EXPLANATIONS["CONFIG_STORE_UNAVAILABLE"][0] == "เปิดฐานข้อมูล Provider ไม่ได้"
    assert "ไม่ผ่าน validation" in ERROR_EXPLANATIONS["PROVIDER_PROFILE_INVALID"][1][0]
    assert "เปิดแอป" in ERROR_EXPLANATIONS["CONFIG_STORE_SCHEMA_UNAVAILABLE"][1][1]
