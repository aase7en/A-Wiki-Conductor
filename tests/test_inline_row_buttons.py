"""WO-P1-066 — inline per-row actions: EDIT column + empty-state add rows.

Rows that hold data expose an ``Edit`` affordance in a trailing EDIT
column; a table with no records at all shows a ``+ Add ...`` row that
opens the matching add dialog anywhere it is clicked.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

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


def make_app(root, tmp_path: Path, assign: bool = True, executor=None):
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    instances_root = tmp_path / "instances"
    instances_root.mkdir(exist_ok=True)
    service = DesktopControlService.open(
        tmp_path / "ui.sqlite", instances_root=instances_root
    )
    if assign:
        project = service.register_project(tmp_path)
        service.assign_project("a-worker-01", project.project_id)
    kwargs = {}
    if executor is not None:
        kwargs["background_executor"] = executor
    return AConductorDesktopApp(root, service=service, **kwargs)


def _children(tree):
    return tree.get_children()


# --- column presence -------------------------------------------------------


def test_workers_tree_has_edit_column_and_cells(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    assert "edit" in app.worker_tree["columns"]
    assert app.worker_tree.heading("edit", "text") == "EDIT"
    items = _children(app.worker_tree)
    assert items, "seeded workers expected"
    for item in items:
        if item == "__add_worker__":
            continue
        values = app.worker_tree.item(item, "values")
        assert values[-1] == "Edit"
        assert len(values) == 6


def test_connectors_tree_has_edit_column(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    assert "edit" in app.instance_tree["columns"]
    assert app.instance_tree.heading("edit", "text") == "EDIT"


def test_projects_panel_is_treeview_with_edit_column(root, tmp_path: Path) -> None:
    from tkinter import ttk

    app = make_app(root, tmp_path)
    assert isinstance(app.project_list, ttk.Treeview)
    assert "edit" in app.project_list["columns"]
    assert app.project_list.heading("edit", "text") == "EDIT"
    # Two-line rows (name + path) need a taller rowheight; Treeview never
    # auto-sizes, so the dedicated style must carry it.
    style = app.project_list.winfo_toplevel().tk.call(
        "ttk::style", "lookup", "Projects.Treeview", "-rowheight"
    )
    assert int(style) >= 40
    items = [i for i in _children(app.project_list) if i != "__add_project__"]
    assert len(items) == 1
    assert app.project_list.item(items[0], "values")[-1] == "Edit"


def test_selected_project_id_survives_conversion(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    items = [i for i in _children(app.project_list) if i != "__add_project__"]
    app.project_list.selection_set(items[0])
    root.update_idletasks()
    assert app.selected_project_id() == items[0]


# --- empty-state add rows --------------------------------------------------


def test_empty_projects_show_add_row_and_it_disappears(root, tmp_path: Path) -> None:
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    instances_root = tmp_path / "instances"
    instances_root.mkdir(exist_ok=True)
    service = DesktopControlService.open(
        tmp_path / "empty.sqlite", instances_root=instances_root
    )
    app = AConductorDesktopApp(root, service=service)
    children = _children(app.project_list)
    assert children == ("__add_project__",)
    values = app.project_list.item("__add_project__", "values")
    assert values[0] == "+ Add Project"

    service.register_project(tmp_path)
    app.refresh()
    root.update_idletasks()
    assert "__add_project__" not in _children(app.project_list)


def test_workers_add_row_appears_only_when_empty(root, tmp_path: Path) -> None:
    # No assignment here so every seeded worker is deletable.
    app = make_app(root, tmp_path, assign=False)
    assert "__add_worker__" not in _children(app.worker_tree)

    for worker in list(app.service.snapshot().workers):
        app.service.delete_worker(worker.worker_id)
    app.refresh()
    root.update_idletasks()
    children = _children(app.worker_tree)
    assert "__add_worker__" in children
    assert app.worker_tree.item("__add_worker__", "values")[0] == "+ Add Worker"


def test_empty_connectors_show_add_row(root, tmp_path: Path) -> None:
    from test_instance_manage import ImmediateExecutor

    app = make_app(root, tmp_path, executor=ImmediateExecutor())
    app.refresh_instances()
    root.update()
    children = _children(app.instance_tree)
    assert "__add_instance__" in children
    assert app.instance_tree.item("__add_instance__", "values")[0] == "+ Add Connector"


# --- click routing ---------------------------------------------------------


def test_inline_click_add_row_opens_add_dialog(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    app.worker_tree.delete(*app.worker_tree.get_children())
    app.worker_tree.insert(
        "", "end", iid="__add_worker__",
        values=("+ Add Worker", "", "", "", "", ""), tags=("row-add",),
    )
    calls = []
    app.open_add_worker_dialog = lambda: calls.append("add")
    result = app._handle_inline_click(
        app.worker_tree,
        "__add_worker__",
        "#1",
        app._worker_edit_column,
        lambda: calls.append("edit"),
        app.open_add_worker_dialog,
    )
    assert calls == ["add"]
    assert result == "break"


def test_inline_click_edit_cell_selects_row_and_opens_editor(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    calls = []
    app.open_rename_worker_dialog = lambda: calls.append("edit")
    row = _children(app.worker_tree)[0]
    result = app._handle_inline_click(
        app.worker_tree,
        row,
        app._worker_edit_column,
        app._worker_edit_column,
        app.open_rename_worker_dialog,
        lambda: calls.append("add"),
    )
    assert calls == ["edit"]
    assert app.worker_tree.selection() == (row,)
    assert result == "break"


def test_inline_click_other_column_keeps_default(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    calls = []
    row = _children(app.worker_tree)[0]
    result = app._handle_inline_click(
        app.worker_tree,
        row,
        "#1",
        app._worker_edit_column,
        lambda: calls.append("edit"),
        lambda: calls.append("add"),
    )
    assert calls == []
    assert result is None


def test_project_edit_cell_routes_to_assign(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    calls = []
    app.assign_selected = lambda: calls.append("assign")
    row = [i for i in _children(app.project_list) if i != "__add_project__"][0]
    app._handle_inline_click(
        app.project_list,
        row,
        app._project_edit_column,
        app._project_edit_column,
        app.assign_selected,
        lambda: calls.append("add"),
    )
    assert calls == ["assign"]


# --- Edit Connector dialog --------------------------------------------------


def _fake_instance_row(app, root, name="sunday-test", project="A:/proj/x"):
    item = app.instance_tree.insert(
        "", "end", values=(name, "18099", "STOPPED", project, "-", "-", "Edit")
    )
    app._instance_rows[name] = item
    app._monitor_instances[name] = SimpleNamespace(
        name=name, project_path=project, tunnel_configured=False
    )
    app.instance_tree.selection_set(item)
    return item


def test_edit_connector_dialog_prefills_name_and_project(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    _fake_instance_row(app, root)
    dialog = app.open_edit_instance_dialog()
    assert dialog is not None
    try:
        assert app._edit_name_entry.get() == "sunday-test"
        assert app._edit_project_entry.get() == "A:/proj/x"
        assert app._tunnel_entry.get() == ""
    finally:
        dialog.destroy()


def test_edit_connector_save_applies_only_changed_fields(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    _fake_instance_row(app, root)
    calls: list[tuple] = []
    app.service.rename_instance = lambda n, v: calls.append(("rename", n, v)) or "renamed-display"
    app.service.set_instance_tunnel_id = lambda n, v: calls.append(("tunnel", n, v))
    app.service.rebind_instance = lambda n, v: calls.append(("rebind", n, v)) or "REBOUND"
    app.refresh_instances = lambda: calls.append(("refresh",))

    dialog = app.open_edit_instance_dialog()
    app._edit_name_entry.delete(0, "end")
    app._edit_name_entry.insert(0, "renamed-display")
    app._tunnel_entry.insert(0, "tunnel_" + "a1" * 16)
    app._edit_project_entry.delete(0, "end")
    app._edit_project_entry.insert(0, "A:/proj/y")
    dialog.destroy()
    app._save_edit_instance_dialog_values(
        "sunday-test", "sunday-test", "A:/proj/x",
        "renamed-display", "tunnel_" + "a1" * 16, "A:/proj/y",
    )

    kinds = [c[0] for c in calls]
    assert kinds == ["tunnel", "rebind", "rename", "refresh"]
    assert ("rename", "sunday-test", "renamed-display") in calls


def test_edit_connector_save_ignores_unchanged_fields(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    _fake_instance_row(app, root)
    calls: list[tuple] = []
    app.service.rename_instance = lambda n, v: calls.append(("rename", n, v))
    app.service.set_instance_tunnel_id = lambda n, v: calls.append(("tunnel", n, v))
    app.service.rebind_instance = lambda n, v: calls.append(("rebind", n, v))
    app.refresh_instances = lambda: None
    dialog = app.open_edit_instance_dialog()
    dialog.destroy()
    app._save_edit_instance_dialog_values(
        "sunday-test", "sunday-test", "A:/proj/x", "sunday-test", "", "A:/proj/x"
    )
    assert calls == []


def test_edit_connector_requires_selection(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    errors = []
    app._handle_error = lambda code: errors.append(code)
    result = app.open_edit_instance_dialog()
    assert result is None
    assert errors == ["SELECT_INSTANCE"]


# --- language contract ------------------------------------------------------


def test_inline_action_labels_are_english(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    labels = [app.worker_tree.heading("edit", "text"), app.instance_tree.heading("edit", "text")]
    for item in _children(app.worker_tree):
        labels.append(app.worker_tree.item(item, "values")[-1])
    for label in labels:
        assert label
        for ch in label:
            assert not ("\u0e00" <= ch <= "\u0e7f") and not ("\u4e00" <= ch <= "\u9fff")


def test_version_still_pinned(root, tmp_path: Path) -> None:
    assert APP_VERSION == "0.6.0"
