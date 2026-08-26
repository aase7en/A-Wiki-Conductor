"""WO-P1-069 — singleton dialogs + version bump to 0.7.0.

Pressing Donate/Guide/Edit repeatedly must never stack duplicate windows.
Every dialog-opening method now goes through a shared singleton guard
that lifts the existing window to front instead of creating a new one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.branding import APP_VERSION


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
    from test_instance_manage import ImmediateExecutor
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    instances_root = tmp_path / "instances"
    instances_root.mkdir(exist_ok=True)
    service = DesktopControlService.open(
        tmp_path / "ui.sqlite", instances_root=instances_root
    )
    project = service.register_project(tmp_path)
    service.assign_project("a-worker-01", project.project_id)
    return AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )


def test_version_is_070() -> None:
    assert APP_VERSION == "0.7.0"


def test_donate_dialog_is_singleton(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    d1 = app.open_donate_dialog()
    assert d1 is not None
    d2 = app.open_donate_dialog()
    assert d2 is d1  # same window, not a new one
    d1.destroy()


def test_preferences_dialog_is_singleton(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    d1 = app.open_preferences()
    d2 = app.open_preferences()
    assert d2 is d1
    d1.destroy()


def test_add_worker_dialog_is_singleton(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    app.open_add_worker_dialog()
    # open_add_worker_dialog returns None but stores in _add_worker_dialog
    d1 = getattr(app, "_add_worker_dialog", None)
    assert d1 is not None and d1.winfo_exists()
    app.open_add_worker_dialog()
    d2 = getattr(app, "_add_worker_dialog", None)
    assert d2 is d1
    d1.destroy()


def test_brain_config_is_singleton(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    d1 = app.open_brain_config()
    assert d1 is not None
    d2 = app.open_brain_config()
    assert d2 is d1
    d1.destroy()


def test_singleton_dialogs_lift_existing(root, tmp_path: Path) -> None:
    """Re-open must return the SAME window object (not create a new one)."""
    app = make_app(root, tmp_path)
    d1 = app.open_donate_dialog()
    assert d1 is not None
    root.update()
    d2 = app.open_donate_dialog()
    assert d2 is d1  # same Toplevel — no stacking
    d1.destroy()
