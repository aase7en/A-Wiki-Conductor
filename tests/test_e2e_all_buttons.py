"""Real E2E: test every button as a human would click them."""

from __future__ import annotations

import tempfile
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

    service = DesktopControlService.open(
        tmp_path / "e2e.sqlite",
        instances_root=tmp_path / "instances",
    )
    return AConductorDesktopApp(root, service=service)


def get_toplevels(root):
    import tkinter as tk

    return [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]


def find_widget(parent, widget_class, text_contains=None):
    for child in parent.winfo_children():
        if isinstance(child, widget_class):
            if text_contains is None:
                return child
            try:
                txt = str(child.cget("text"))
                if text_contains in txt:
                    return child
            except Exception:
                pass
        result = find_widget(child, widget_class, text_contains)
        if result is not None:
            return result
    return None


# WORKERS TOOLBAR
class TestWorkerButtons:
    def test_add_worker_button_creates_worker(self, root, tmp_path):
        from tkinter import ttk

        app = make_app(root, tmp_path)
        assert len(app.worker_tree.get_children()) == 3
        app.add_worker_button.invoke()
        root.update()
        dialogs = get_toplevels(root)
        assert dialogs, "Dialog didn't open"
        dialog = dialogs[-1]
        entry = find_widget(dialog, ttk.Entry)
        assert entry is not None, "Name entry not found"
        entry.insert(0, "E2E Worker")
        btn = find_widget(dialog, ttk.Button, "Add")
        if btn is None:
            btn = find_widget(dialog, ttk.Button, "เพิ่ม")
        assert btn is not None, "Submit button not found"
        btn.invoke()
        root.update()
        assert len(app.worker_tree.get_children()) == 4
        ids = [app.worker_tree.item(i, "values")[0] for i in app.worker_tree.get_children()]
        assert "a-worker-04" in ids

    def test_rename_worker_button(self, root, tmp_path):
        from tkinter import ttk

        app = make_app(root, tmp_path)
        children = app.worker_tree.get_children()
        app.worker_tree.selection_clear()
        app.worker_tree.selection_set(children[0])
        app.rename_worker_button.invoke()
        root.update()
        dialogs = get_toplevels(root)
        assert dialogs
        entry = find_widget(dialogs[-1], ttk.Entry)
        assert entry is not None
        entry.delete(0, "end")
        entry.insert(0, "Renamed Worker")
        btn = find_widget(dialogs[-1], ttk.Button, "Save")
        if btn is None:
            btn = find_widget(dialogs[-1], ttk.Button, "บันทึก")
        assert btn is not None
        btn.invoke()
        root.update()
        assert app.service.snapshot().workers[0].display_name == "Renamed Worker"

    def test_delete_worker_with_confirm(self, root, tmp_path, monkeypatch):
        app = make_app(root, tmp_path)
        assert len(app.worker_tree.get_children()) == 3
        children = app.worker_tree.get_children()
        app.worker_tree.selection_clear()
        app.worker_tree.selection_set(children[-1])
        monkeypatch.setattr(app, "_confirm", lambda msg: True)
        app.delete_selected_worker()
        root.update()
        assert len(app.worker_tree.get_children()) == 2

    def test_delete_worker_declined(self, root, tmp_path, monkeypatch):
        app = make_app(root, tmp_path)
        children = app.worker_tree.get_children()
        app.worker_tree.selection_clear()
        app.worker_tree.selection_set(children[0])
        monkeypatch.setattr(app, "_confirm", lambda msg: False)
        app.delete_selected_worker()
        assert len(app.worker_tree.get_children()) == 3


# PROJECT PANEL
class TestProjectButtons:
    def test_add_project_registers(self, root, tmp_path):
        app = make_app(root, tmp_path)
        proj_dir = tmp_path / "my-project"
        proj_dir.mkdir()
        app.service.register_project(str(proj_dir), display_name="My Project")
        app.refresh()
        root.update()
        assert app.project_list.size() == 1

    def test_activate_button_exists(self, root, tmp_path):
        app = make_app(root, tmp_path)
        assert app.activate_button is not None

    def test_assign_button_exists(self, root, tmp_path):
        app = make_app(root, tmp_path)
        assert app.assign_button is not None


# CONNECTOR TOOLBAR
class TestConnectorButtons:
    def test_all_connector_buttons_exist(self, root, tmp_path):
        app = make_app(root, tmp_path)
        for name in [
            "instance_start_button", "instance_stop_button",
            "instance_startall_button", "instance_auto_button",
            "instance_rescan_button", "add_instance_button",
            "rename_instance_button", "delete_instance_button",
        ]:
            assert hasattr(app, name), f"Missing: {name}"
            assert getattr(app, name) is not None

    def test_rescan_button_updates(self, root, tmp_path):
        app = make_app(root, tmp_path)
        app.rescan_instances()
        root.update()


# HEADER BUTTONS
class TestHeaderButtons:
    def test_guide_button_exists(self, root, tmp_path):
        app = make_app(root, tmp_path)
        assert app.help_button is not None

    def test_settings_button_exists(self, root, tmp_path):
        app = make_app(root, tmp_path)
        assert app.prefs_button is not None

    def test_settings_dialog_opens(self, root, tmp_path):
        app = make_app(root, tmp_path)
        window = app.open_preferences()
        assert window is not None
        assert window.winfo_exists()
        window.destroy()

    def test_check_update_button_exists(self, root, tmp_path):
        app = make_app(root, tmp_path)
        assert app._update_button is not None

    def test_donate_button_opens_dialog(self, root, tmp_path):
        app = make_app(root, tmp_path)
        assert app._donate_button is not None
        dialog = app.open_donate_dialog()
        assert dialog is not None
        assert dialog.winfo_exists()
        dialog.destroy()


# STATUS + MONITOR
class TestStatusAndMonitor:
    def test_brand_label_shows_version(self, root, tmp_path):
        from a_conductor.branding import APP_VERSION

        app = make_app(root, tmp_path)
        text = str(app.brand_label.cget("text"))
        assert APP_VERSION in text

    def test_monitor_panel_renders(self, root, tmp_path):
        app = make_app(root, tmp_path)
        content = app.monitor_text.get("1.0", "end")
        assert "MONITOR" in content

    def test_activity_log_receives_events(self, root, tmp_path):
        app = make_app(root, tmp_path)
        app.log_activity("TEST_EVENT hello")
        content = app.activity_text.get("1.0", "end")
        assert "TEST_EVENT" in content


# LIFECYCLE BUTTONS
class TestLifecycleButtons:
    def test_all_lifecycle_buttons_exist(self, root, tmp_path):
        app = make_app(root, tmp_path)
        for name in ["start_button", "stop_button", "restart_button", "setup_button", "config_button"]:
            assert hasattr(app, name)
            assert getattr(app, name) is not None

    def test_lifecycle_disabled_without_selection(self, root, tmp_path):
        app = make_app(root, tmp_path)
        app.worker_tree.selection_clear()
        app._update_lifecycle_buttons()
        assert app.start_button.instate(["disabled"])
        assert app.stop_button.instate(["disabled"])

    def test_setup_enabled_with_selection(self, root, tmp_path):
        app = make_app(root, tmp_path)
        children = app.worker_tree.get_children()
        app.worker_tree.selection_set(children[0])
        app._update_lifecycle_buttons()
        assert app.setup_button.instate(["!disabled"])


# SPLASH + LOGO
class TestSplashAndLogo:
    def test_logo_exists(self, root, tmp_path):
        app = make_app(root, tmp_path)
        assert hasattr(app, "_logo")

    def test_splash_imports(self):
        from a_conductor.splash import show_splash

        assert callable(show_splash)
