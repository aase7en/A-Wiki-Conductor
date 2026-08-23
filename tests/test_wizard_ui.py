"""Setup Wizard UI: step navigation, first-run detection."""

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


def make_app(root, tmp_path: Path):
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    instances_root = tmp_path / "instances"
    instances_root.mkdir(exist_ok=True)
    service = DesktopControlService.open(
        tmp_path / "cc.sqlite", instances_root=instances_root
    )
    return AConductorDesktopApp(root, service=service)


def test_wizard_opens_with_welcome_step(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    dialog = app.open_setup_wizard()
    try:
        assert app._wiz_step == 0
        assert dialog.winfo_exists()
    finally:
        dialog.destroy()


def test_wizard_advance_and_back(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    dialog = app.open_setup_wizard()
    try:
        app._wizard_advance()
        assert app._wiz_step == 1
        app._wizard_back()
        assert app._wiz_step == 0
    finally:
        dialog.destroy()


def test_wizard_renders_all_steps(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    dialog = app.open_setup_wizard()
    try:
        for step in range(6):
            app._wiz_step = step
            app._render_wizard_step()
            # each step has some widgets in the frame
            children = app._wiz_frame.winfo_children()
            assert len(children) > 0, f"step {step} has no widgets"
    finally:
        dialog.destroy()


def test_i18n_wizard_keys_exist() -> None:
    from a_conductor.i18n import STRINGS, set_language, tr

    for key in ("wiz.title", "wiz.welcome", "wiz.check", "wiz.install",
                "wiz.instance", "wiz.credentials", "wiz.finish", "wiz.next", "wiz.back"):
        assert key in STRINGS, key
        assert STRINGS[key]["th"].strip()
        assert STRINGS[key]["en"].strip()
