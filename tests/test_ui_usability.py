"""WO: usability — horizontal scroll, full-path hover tooltip, copy, version."""

from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.branding import APP_NAME, APP_VERSION


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

    service = DesktopControlService.open(tmp_path / "ui.sqlite")
    project = service.register_project(tmp_path)
    service.assign_project("a-worker-01", project.project_id)
    return AConductorDesktopApp(root, service=service)


def test_window_title_shows_version(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    assert root.title() == f"{APP_NAME} v{APP_VERSION}"
    assert APP_VERSION == "0.5.0"


def test_worker_tree_has_horizontal_scroll(root, tmp_path: Path) -> None:
    from tkinter import ttk

    app = make_app(root, tmp_path)
    assert isinstance(app.worker_xscroll, ttk.Scrollbar)
    assert app.worker_tree.cget("xscrollcommand")


def test_instance_tree_has_horizontal_scroll(root, tmp_path: Path) -> None:
    from tkinter import ttk

    app = make_app(root, tmp_path)
    assert isinstance(app.instance_xscroll, ttk.Scrollbar)
    assert app.instance_tree.cget("xscrollcommand")


def test_tree_row_path_returns_full_path(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    items = app.worker_tree.get_children()
    assert items
    path = app._tree_row_path(app.worker_tree, items[0], column=3)
    assert path is not None
    assert str(tmp_path) in path.replace("/", "\\")


def test_copy_path_to_clipboard(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    app._copy_path_to_clipboard(r"A:\GitHub\very-long\project-path")
    root.update()
    assert root.clipboard_get() == r"A:\GitHub\very-long\project-path"


def test_row_tooltip_provider_returns_path(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    items = app.worker_tree.get_children()
    provider = app._row_path_tip_providers[app.worker_tree]
    assert callable(provider)
    assert provider(items[0]) == app._tree_row_path(app.worker_tree, items[0], column=3)
