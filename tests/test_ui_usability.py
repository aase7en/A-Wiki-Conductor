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


def test_responsive_column_count_uses_available_width() -> None:
    from a_conductor.desktop_ui import responsive_column_count

    assert responsive_column_count(1400, 9) == 9
    assert 1 < responsive_column_count(500, 9) < 9
    assert responsive_column_count(80, 9) == 1


def test_primary_workflow_buttons_follow_action_order(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    texts = [button.cget("text") for button in app.workflow_buttons]
    assert texts[:6] == ["Add Project", "Assign", "Add Worker", "Start", "Stop", "Restart"]


def test_monitor_and_activity_share_horizontal_lower_pane(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    assert str(app._lower_pane.cget("orient")) == "horizontal"
    panes = app._lower_pane.panes()
    assert len(panes) == 2


def test_brain_is_in_header_and_donate_is_visible(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    assert app.brain_button.master is app._header_frame
    assert app._donate_button.winfo_manager() == "pack"
    assert app._update_button.winfo_manager() == "pack"


def test_typewriter_teaching_surface_exists(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    assert app._teaching_label.winfo_exists()
    assert app._teaching_messages


def test_main_view_buttons_are_english_only(root, tmp_path: Path) -> None:
    import re
    from tkinter import ttk

    app = make_app(root, tmp_path)
    root.update_idletasks()

    def walk(widget):
        for child in widget.winfo_children():
            yield child
            yield from walk(child)

    texts = [str(w.cget("text")) for w in walk(root) if isinstance(w, ttk.Button)]
    assert texts
    for text in texts:
        assert not re.search(r"[\u0E00-\u0E7F\u4E00-\u9FFF]", text), text


def test_activity_log_supports_copy_all(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    app.log_activity("Diagnostic line for copy")
    copied = app.copy_text_widget_all(app.activity_text)
    assert "Diagnostic line for copy" in copied
    assert "Diagnostic line for copy" in root.clipboard_get()
    assert str(app.activity_text.cget("state")) == "disabled"


def test_monitor_supports_copy_all(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    copied = app.copy_text_widget_all(app.monitor_text)
    assert isinstance(copied, str)
    assert str(app.monitor_text.cget("state")) == "disabled"


def test_connector_column_has_help_and_add_connector_visible(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    assert app.add_instance_button.cget("text") == "Add Connector"
    help_text = app.connector_help_text()
    assert "Connector" in help_text and "-" in help_text and "Add Connector" in help_text


def test_assign_replacement_confirms_and_switches_project(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    second_dir = tmp_path / "second-project"
    second_dir.mkdir()
    second = app.service.register_project(second_dir, display_name="Second Project")
    app.refresh()
    project_index = app._project_ids.index(second.project_id)
    app.project_list.selection_clear(0, "end")
    app.project_list.selection_set(project_index)
    worker_item = next(item for item, worker_id in app._worker_ids.items() if worker_id == "a-worker-01")
    app.worker_tree.selection_set(worker_item)
    messages = []
    app._confirm = lambda message: messages.append(message) or True
    app.assign_selected()
    row = next(w for w in app.service.snapshot().workers if w.worker_id == "a-worker-01")
    assert row.project_id == second.project_id
    assert messages and "Current:" in messages[0] and "New:" in messages[0]


def test_add_connector_button_is_managed_by_layout(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    root.update_idletasks()
    assert app.add_instance_button.winfo_manager() == "grid"


def test_desktop_ui_buttons_cannot_bypass_canonical_factory() -> None:
    source = Path("src/a_conductor/desktop_ui.py").read_text(encoding="utf-8")
    assert source.count("ttk.Button(") == 1
    assert "tk.Button(" not in source.replace("ttk.Button(", "")
    assert "text=canonical_button_label(text)" in source


def test_responsive_action_grids_reflow_at_compact_and_wide_widths(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    workflow_parent = app.add_button.master
    connector_parent = app.add_instance_button.master
    connector_buttons = (
        app.instance_start_button,
        app.instance_stop_button,
        app.instance_startall_button,
        app.instance_auto_button,
        app.instance_rescan_button,
        app.add_instance_button,
        app.rename_instance_button,
        app.delete_instance_button,
        app.tunnel_button,
        app.rebind_button,
        app.upstream_button,
    )

    workflow_parent.event_generate("<Configure>", width=1280, height=60)
    connector_parent.event_generate("<Configure>", width=1280, height=60)
    assert {int(b.grid_info()["row"]) for b in app.workflow_buttons} == {0}
    assert {int(b.grid_info()["row"]) for b in connector_buttons} == {0}

    workflow_parent.event_generate("<Configure>", width=700, height=60)
    connector_parent.event_generate("<Configure>", width=700, height=60)
    assert len({int(b.grid_info()["row"]) for b in app.workflow_buttons}) > 1
    assert len({int(b.grid_info()["row"]) for b in connector_buttons}) > 1
    assert all(
        b.winfo_manager() == "grid"
        for b in app.workflow_buttons + connector_buttons
    )
