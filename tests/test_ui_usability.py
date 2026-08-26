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

    instances_root = tmp_path / "instances"
    instances_root.mkdir(exist_ok=True)
    service = DesktopControlService.open(
        tmp_path / "ui.sqlite", instances_root=instances_root
    )
    project = service.register_project(tmp_path)
    service.assign_project("a-worker-01", project.project_id)
    return AConductorDesktopApp(root, service=service)


def test_window_title_shows_version(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    assert root.title() == f"{APP_NAME} v{APP_VERSION}"
    assert APP_VERSION == "0.7.0"


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
    assert texts == [
        "Add Project",
        "Assign Worker",
        "Add Worker",
        "Start Worker",
        "Stop Worker",
        "Restart Worker",
        "Release Worker",
        "Copy Activate",
        "Refresh",
    ]


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
    app.project_list.selection_set()
    app.project_list.selection_set(second.project_id)
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

    workflow_parent.event_generate("<Configure>", width=900, height=60)
    assert {int(b.grid_info()["row"]) for b in app.workflow_buttons} == {0}

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


@pytest.mark.parametrize(
    ("width", "height"),
    ((700, 680), (900, 680), (700, 760), (900, 760), (1280, 820), (1600, 900)),
)
def test_real_window_action_controls_stay_inside_available_width(
    root, tmp_path: Path, width: int, height: int
) -> None:
    app = make_app(root, tmp_path)
    root.deiconify()
    root.geometry(f"{width}x{height}+20+20")
    root.update_idletasks()
    root.update()

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
    for parent, buttons in (
        (app._workflow_frame, app.workflow_buttons),
        (app.add_instance_button.master, connector_buttons),
    ):
        parent_right = parent.winfo_rootx() + parent.winfo_width()
        clip_container = parent.master
        parent_bottom = clip_container.winfo_rooty() + clip_container.winfo_height()
        for button in buttons:
            assert button.winfo_ismapped(), str(button.cget("text"))
            assert (
                button.winfo_rootx() + button.winfo_width() <= parent_right
            ), f"{width}px clips {button.cget('text')}"
            assert (
                button.winfo_rooty() + button.winfo_height() <= parent_bottom
            ), f"{width}px hides {button.cget('text')} below its action area"

    workflow_rows = {int(button.grid_info()["row"]) for button in app.workflow_buttons}
    if width < 900:
        assert len(workflow_rows) > 1
    else:
        assert workflow_rows == {0}


@pytest.mark.parametrize(
    ("width", "height"),
    (
        (700, 680),
        (900, 680),
        (1080, 680),
        (700, 760),
        (900, 760),
        (1280, 820),
        (1600, 900),
    ),
)
def test_real_window_keeps_all_operational_panes_visible(
    root, tmp_path: Path, width: int, height: int
) -> None:
    app = make_app(root, tmp_path)
    root.deiconify()
    root.geometry(f"{width}x{height}+20+20")
    root.update_idletasks()
    root.update()

    for widget in (
        app.worker_tree,
        app.instance_tree,
        app.monitor_text,
        app.activity_text,
    ):
        assert widget.winfo_ismapped(), f"{width}x{height}: {widget} is hidden"
        assert widget.winfo_height() >= 24, (
            f"{width}x{height}: {widget} collapsed to {widget.winfo_height()}px"
        )


def test_window_minimum_height_keeps_operational_surfaces_reachable(
    root, tmp_path: Path
) -> None:
    app = make_app(root, tmp_path)
    root.deiconify()
    root.geometry("700x500+20+20")
    root.update_idletasks()
    root.update()

    assert root.winfo_height() >= 680
    for widget in (
        app.worker_tree,
        app.instance_tree,
        app.monitor_text,
        app.activity_text,
    ):
        assert widget.winfo_ismapped()
        assert widget.winfo_height() >= 24


@pytest.mark.parametrize("width", (700, 900, 1080))
def test_default_height_exposes_selectable_rows_and_two_console_lines(
    root, tmp_path: Path, width: int
) -> None:
    from test_instance_monitor import make_app as make_monitor_app

    app = make_monitor_app(root, tmp_path)
    app._logo.stop()
    app.refresh_instances()
    root.deiconify()
    root.geometry(f"{width}x680+20+20")
    # Startup work may log before the PanedWindow reaches its final height.
    app.log_activity("Geometry probe second line")
    root.update_idletasks()
    root.update()

    connector = app.instance_tree.get_children()[0]
    app.instance_tree.selection_set(connector)
    app._update_monitor_now()
    root.update_idletasks()

    for tree in (app.worker_tree, app.instance_tree):
        item = tree.get_children()[0]
        bbox = tree.bbox(item)
        assert bbox, f"{width}px: first row has no visible bbox"
        _x, y, _row_width, row_height = bbox
        assert y + row_height <= tree.winfo_height(), (
            f"{width}px: first row is clipped at {y + row_height}px "
            f"inside {tree.winfo_height()}px"
        )

    for text_widget in (app.monitor_text, app.activity_text):
        first_visible = text_widget.index("@0,0 linestart")
        second_visible = text_widget.index(f"{first_visible} +1line linestart")
        console_name = "MONITOR" if text_widget is app.monitor_text else "ACTIVITY"
        for index in (first_visible, second_visible):
            line = text_widget.dlineinfo(index)
            assert line is not None, f"{width}px {console_name}: {index} is not visible"
            _x, y, _line_width, line_height, _baseline = line
            assert y >= 0, (
                f"{width}px {console_name}: {index} begins {abs(y)}px above the visible console"
            )
            assert y + line_height <= text_widget.winfo_height(), (
                f"{width}px: {index} is clipped at {y + line_height}px "
                f"inside {text_widget.winfo_height()}px"
            )


def test_terminal_command_center_header_contract(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    root.update_idletasks()
    assert app.title_label.cget("text") == "A-CONDUCTOR"
    assert "Orchestrate" in app.tagline_label.cget("text")
    assert app.brain_button.master is app._header_frame
    assert app._logo.frame.master is app._header_frame
    assert int(app._logo.frame.grid_info()["column"]) < int(app.title_label.master.grid_info()["column"])


def test_activity_view_realigns_to_complete_recent_lines_after_resize(
    root, tmp_path: Path
) -> None:
    app = make_app(root, tmp_path)
    root.deiconify()
    root.geometry("900x680+20+20")
    root.update_idletasks()
    root.update()
    app.log_activity("Geometry probe second line")
    app.activity_text.yview_moveto(1.0)

    app.activity_text.event_generate("<Configure>")
    root.update()
    root.update_idletasks()

    first = app.activity_text.index("@0,0 linestart")
    second = app.activity_text.index(f"{first} +1line linestart")
    for index in (first, second):
        line = app.activity_text.dlineinfo(index)
        assert line is not None
        _x, y, _line_width, line_height, _baseline = line
        assert y >= 0
        assert y + line_height <= app.activity_text.winfo_height()


def test_system_overview_uses_real_snapshot_counts(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    root.update_idletasks()
    assert app._overview_frame.winfo_exists()
    assert app.overview_projects_value.cget("text") == "1"
    assert app.overview_workers_value.cget("text") == "0 / 0"
    assert "3 registered" in str(app.registry_status_label.cget("text"))


def test_terminal_theme_is_near_black_and_restrained() -> None:
    from a_conductor.desktop_ui import DesktopTheme

    theme = DesktopTheme()
    assert theme.background.lower() == "#080b0f"
    assert theme.panel.lower() == "#0d1117"
    assert theme.border.lower() == "#242b35"

    def luminance(color: str) -> float:
        channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
            for value in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    bright = luminance(theme.ready_dim)
    dark = luminance(theme.background)
    assert (bright + 0.05) / (dark + 0.05) >= 4.5


def test_master_family_asset_is_preferred() -> None:
    from a_conductor.desktop_ui import find_particle_image_path

    path = find_particle_image_path()
    assert path is not None
    assert path.name == "sunday-family-particle.png"

def test_compact_header_actions_do_not_overflow(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    root.geometry("700x700")
    root.update_idletasks()
    root.update()
    assert app.prefs_button.winfo_x() + app.prefs_button.winfo_width() <= app._header_frame.winfo_width()
    assert app.help_button.winfo_manager() == "grid"
    assert app.prefs_button.winfo_manager() == "grid"


def test_system_overview_reflows_without_clipping_at_compact_width(
    root, tmp_path: Path
) -> None:
    app = make_app(root, tmp_path)
    root.deiconify()
    root.geometry("700x680+20+20")
    root.update_idletasks()
    root.update()

    values = (
        app.overview_projects_value,
        app.overview_workers_value,
        app.overview_connectors_value,
        app.overview_state_value,
    )
    cells = tuple(value.master for value in values)
    metrics = cells[0].master
    right_edge = metrics.winfo_rootx() + metrics.winfo_width()

    assert {int(cell.grid_info()["row"]) for cell in cells} == {0}
    for cell in cells:
        assert cell.winfo_rootx() + cell.winfo_reqwidth() <= right_edge
    assert [str(cell.winfo_children()[0].cget("text")) for cell in cells] == [
        "PROJECTS",
        "SLOTS",
        "DRIFT",
        "STATE",
    ]

    root.geometry("900x680+20+20")
    root.update_idletasks()
    root.update()
    assert {int(cell.grid_info()["row"]) for cell in cells} == {0}
    assert [str(cell.winfo_children()[0].cget("text")) for cell in cells] == [
        "PROJECTS",
        "AI SLOTS LIVE",
        "ACTIVE DRIFT",
        "CONTROLLER",
    ]


def test_real_system_metrics_render_in_overview(root, tmp_path: Path) -> None:
    from a_conductor.system_metrics import SystemMetrics

    app = make_app(root, tmp_path)

    class FakeSampler:
        def sample(self):
            return SystemMetrics(
                cpu_percent=18.2,
                memory_used_bytes=int(6.2 * 1024**3),
                memory_total_bytes=32 * 1024**3,
                uptime_seconds=2 * 86400 + 14 * 3600 + 37 * 60,
            )

    app._system_metrics_sampler = FakeSampler()
    app._update_system_metrics_now()
    assert app.overview_cpu_value.cget("text") == "18%"
    assert app.overview_memory_value.cget("text") == "6.2 / 32.0 GB"
    assert app.overview_uptime_value.cget("text") == "2d 14h 37m"
    assert list(app._cpu_history)[-1] == pytest.approx(18.2)


def test_system_monitor_history_is_bounded_and_unavailable_is_honest(root, tmp_path: Path) -> None:
    from a_conductor.system_metrics import SystemMetrics

    app = make_app(root, tmp_path)

    class FakeSampler:
        def sample(self):
            return SystemMetrics(None, None, None, 5.0)

    app._system_metrics_sampler = FakeSampler()
    for _ in range(app.SYSTEM_METRIC_HISTORY_LIMIT + 10):
        app._update_system_metrics_now()
    assert len(app._cpu_history) <= app.SYSTEM_METRIC_HISTORY_LIMIT
    assert app.overview_cpu_value.cget("text") == "—"
    assert app.overview_memory_value.cget("text") == "—"
    assert app.overview_uptime_value.cget("text") == "00:00:05"


def test_system_monitor_callback_is_cancelled_cleanly(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    app._start_system_monitor()
    assert app._system_metric_after_id is not None
    app._stop_system_monitor()
    assert app._system_metric_after_id is None


def test_confirmation_dialog_supports_focus_escape_and_return(root, tmp_path: Path) -> None:
    import tkinter as tk

    app = make_app(root, tmp_path)
    root.deiconify()
    root.update()
    observed: list[tuple[bool, bool]] = []

    def dismiss_with_escape() -> None:
        dialog = next(
            child for child in root.winfo_children() if isinstance(child, tk.Toplevel)
        )
        focused = dialog.focus_get()
        observed.append((bool(dialog.bind("<Escape>")), focused is not None))
        dialog.event_generate("<Escape>")
        dialog.after(20, lambda: dialog.destroy() if dialog.winfo_exists() else None)

    root.after(40, dismiss_with_escape)
    assert app._confirm("Keyboard-safe confirmation?") is False
    assert observed == [(True, True)]

    def accept_with_return() -> None:
        dialog = next(
            child for child in root.winfo_children() if isinstance(child, tk.Toplevel)
        )
        observed.append((bool(dialog.bind("<Return>")), dialog.focus_get() is not None))
        dialog.event_generate("<Return>")
        dialog.after(20, lambda: dialog.destroy() if dialog.winfo_exists() else None)

    root.after(40, accept_with_return)
    assert app._confirm("Keyboard-safe confirmation?") is True
    assert observed[-1] == (True, True)
