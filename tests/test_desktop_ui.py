from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk
from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path

import pytest

from a_conductor.control_center import (
    ControlCenterSnapshot,
    WorkerScreenRow,
)
from a_conductor.desktop_app import default_database_path, run_smoke
from a_conductor.desktop_ui import AConductorDesktopApp, DesktopTheme
from a_conductor.domain import Project, WorkerState
from a_conductor.lifecycle import LifecycleAction
from a_conductor.lifecycle_coordinator import LifecycleCoordinatorError
from a_conductor.lifecycle_executor import LifecycleExecutionResult, LifecycleExecutionState
from a_conductor.runtime_setup import SetupReadiness, WorkerSetupDraft
from a_conductor.worker_serena_settings import WorkerSerenaSettings
from a_conductor.local_instances import (
    InstanceHealthState,
    InstanceResultCode,
    LocalInstance,
)


class FakeService:
    def __init__(self, snapshot: ControlCenterSnapshot) -> None:
        self.current = snapshot
        self.assign_calls: list[tuple[str, str]] = []
        self.release_calls: list[str] = []
        self.register_calls: list[tuple[Path, str | None]] = []

    def snapshot(self) -> ControlCenterSnapshot:
        return self.current

    def assign_project(self, worker_id: str, project_id: str, *, mutation_allowed: bool = True):
        self.assign_calls.append((worker_id, project_id))
        return object()

    def release_worker(self, worker_id: str):
        self.release_calls.append(worker_id)
        return object()

    def register_project(self, root_path, *, display_name=None, project_id=None):
        self.register_calls.append((Path(root_path), display_name))
        return object()


def sample_snapshot() -> ControlCenterSnapshot:
    project = Project("project-1", "A-Wiki", r"A:\GitHub\A-Wiki")
    workers = (
        WorkerScreenRow(
            "a-worker-01",
            "A-Worker 1",
            WorkerState.READY,
            "runtime-01",
            "assignment-1",
            project.project_id,
            project.display_name,
            project.root_path,
            True,
        ),
        WorkerScreenRow(
            "a-worker-02",
            "A-Worker 2",
            WorkerState.STOPPED,
            "runtime-02",
            None,
            None,
            None,
            None,
            None,
        ),
        WorkerScreenRow(
            "a-worker-03",
            "A-Worker 3",
            WorkerState.STOPPED,
            "runtime-03",
            None,
            None,
            None,
            None,
            None,
        ),
    )
    return ControlCenterSnapshot(projects=(project,), workers=workers, online=True)


@pytest.fixture
def root():
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


def test_default_theme_is_dark_compact_and_semantic() -> None:
    theme = DesktopTheme()
    assert theme.background.startswith("#")
    assert theme.panel.startswith("#")
    assert theme.ready != theme.error != theme.warning
    assert theme.monospace_font
    assert theme.base_font_size <= 12


def test_default_database_path_uses_localappdata_when_available(tmp_path: Path) -> None:
    path = default_database_path({"LOCALAPPDATA": str(tmp_path)})
    assert path == tmp_path / "A-Conductor" / "control-center.sqlite"


def test_default_database_path_falls_back_to_home(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    path = default_database_path({})
    assert path == tmp_path / ".a-conductor" / "control-center.sqlite"


def test_app_renders_projects_workers_and_disabled_lifecycle_controls(root) -> None:
    service = FakeService(sample_snapshot())
    app = AConductorDesktopApp(root, service=service)
    root.update_idletasks()

    assert root.title() == "A-Sunday Conductor v0.2.1"
    assert app.project_list.size() == 1
    assert len(app.worker_tree.get_children()) == 3
    assert app.start_button.instate(["disabled"])
    assert app.stop_button.instate(["disabled"])
    assert app.restart_button.instate(["disabled"])
    assert "ONLINE" in app.connection_label.cget("text")


def test_refresh_projects_worker_assignment_and_state(root) -> None:
    app = AConductorDesktopApp(root, service=FakeService(sample_snapshot()))
    app.refresh()
    rows = app.worker_tree.get_children()
    values = app.worker_tree.item(rows[0], "values")
    assert "READY" in values
    assert "A-Wiki" in values
    assert "a-worker-01" in values


def test_assign_selected_delegates_to_service(root) -> None:
    service = FakeService(sample_snapshot())
    app = AConductorDesktopApp(root, service=service)
    app.project_list.selection_set(0)
    worker_item = app.worker_tree.get_children()[1]
    app.worker_tree.selection_set(worker_item)
    app.worker_tree.focus(worker_item)

    app.assign_selected()

    assert service.assign_calls == [("a-worker-02", "project-1")]
    assert "Assign" in app.activity_text.get("1.0", "end")


def test_release_selected_delegates_to_service(root) -> None:
    service = FakeService(sample_snapshot())
    app = AConductorDesktopApp(root, service=service)
    worker_item = app.worker_tree.get_children()[0]
    app.worker_tree.selection_set(worker_item)
    app.worker_tree.focus(worker_item)

    app.release_selected()

    assert service.release_calls == ["a-worker-01"]


def test_add_project_uses_injected_directory_picker(root, tmp_path: Path) -> None:
    project = tmp_path / "new-project"
    project.mkdir()
    service = FakeService(sample_snapshot())
    app = AConductorDesktopApp(
        root,
        service=service,
        directory_picker=lambda: str(project),
    )

    app.add_project()

    assert service.register_calls == [(project, None)]


def test_guide_button_opens_bundled_user_guide(root) -> None:
    from a_conductor.desktop_ui import find_user_guide_path

    opened: list[Path] = []
    app = AConductorDesktopApp(
        root,
        service=FakeService(sample_snapshot()),
        background_executor=ImmediateExecutor(),
        guide_opener=opened.append,
    )

    assert find_user_guide_path() is not None
    app.open_guide()

    assert len(opened) == 1
    assert opened[0].name == "USER-GUIDE.md"


def test_smoke_constructs_real_service_ui_without_mainloop(tmp_path: Path) -> None:
    try:
        code, summary = run_smoke(tmp_path / "control-center.sqlite")
    except tk.TclError as exc:
        pytest.skip(f"Tk display unavailable: {exc}")
    assert code == 0
    assert summary == "A-CONDUCTOR_SMOKE_OK projects=0 workers=3"


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except BaseException as exc:
            future.set_exception(exc)
        return future

    def shutdown(self, wait=False, cancel_futures=False):
        return None


class FakeLifecycleService(FakeService):
    def __init__(self, snapshot: ControlCenterSnapshot) -> None:
        super().__init__(snapshot)
        self.lifecycle_calls: list[tuple[str, str]] = []
        self.raise_error: BaseException | None = None

    def _run(self, action: LifecycleAction, worker_id: str):
        self.lifecycle_calls.append((action.value, worker_id))
        if self.raise_error is not None:
            raise self.raise_error
        return LifecycleExecutionResult(
            transaction_id=f"tx-ui-{action.value.lower()}",
            state=LifecycleExecutionState.NOOP,
            reason_code="TEST_NOOP",
        )

    def start_worker(self, worker_id: str):
        return self._run(LifecycleAction.START, worker_id)

    def stop_worker(self, worker_id: str):
        return self._run(LifecycleAction.STOP, worker_id)

    def restart_worker(self, worker_id: str):
        return self._run(LifecycleAction.RESTART, worker_id)


def lifecycle_snapshot() -> ControlCenterSnapshot:
    base = sample_snapshot()
    project = base.projects[0]
    workers = list(base.workers)
    workers[1] = replace(
        workers[1],
        assignment_id="assignment-2",
        project_id=project.project_id,
        project_display_name=project.display_name,
        project_root_path=project.root_path,
        mutation_allowed=True,
    )
    return ControlCenterSnapshot(projects=base.projects, workers=tuple(workers), online=True)


def test_lifecycle_capable_service_enables_state_aware_controls(root) -> None:
    service = FakeLifecycleService(lifecycle_snapshot())
    app = AConductorDesktopApp(root, service=service, background_executor=ImmediateExecutor())

    stopped_item = app.worker_tree.get_children()[1]
    app.worker_tree.selection_set(stopped_item)
    app.worker_tree.focus(stopped_item)
    app._update_lifecycle_buttons()
    assert app.start_button.instate(["!disabled"])
    assert app.stop_button.instate(["disabled"])
    assert app.restart_button.instate(["disabled"])

    ready_item = app.worker_tree.get_children()[0]
    app.worker_tree.selection_set(ready_item)
    app.worker_tree.focus(ready_item)
    app._update_lifecycle_buttons()
    assert app.start_button.instate(["disabled"])
    assert app.stop_button.instate(["!disabled"])
    assert app.restart_button.instate(["!disabled"])


def test_start_selected_runs_through_background_executor_and_logs_result(root) -> None:
    service = FakeLifecycleService(lifecycle_snapshot())
    app = AConductorDesktopApp(root, service=service, background_executor=ImmediateExecutor())
    item = app.worker_tree.get_children()[1]
    app.worker_tree.selection_set(item)
    app.worker_tree.focus(item)
    app._update_lifecycle_buttons()

    app.start_selected()
    root.update()

    assert service.lifecycle_calls == [("START", "a-worker-02")]
    activity = app.activity_text.get("1.0", "end")
    assert "START" in activity
    assert "TEST_NOOP" in activity


def test_known_lifecycle_error_logs_code_only(root) -> None:
    service = FakeLifecycleService(lifecycle_snapshot())
    service.raise_error = LifecycleCoordinatorError("WORKER_STATE_PERSISTENCE_FAILED")
    app = AConductorDesktopApp(
        root,
        service=service,
        background_executor=ImmediateExecutor(),
        error_handler=lambda _code: None,
    )
    item = app.worker_tree.get_children()[1]
    app.worker_tree.selection_set(item)
    app.worker_tree.focus(item)

    app.start_selected()
    root.update()

    activity = app.activity_text.get("1.0", "end")
    assert "WORKER_STATE_PERSISTENCE_FAILED" in activity


def test_unknown_lifecycle_exception_never_logs_raw_secret_text(root) -> None:
    service = FakeLifecycleService(lifecycle_snapshot())
    service.raise_error = RuntimeError("super-secret-runtime-detail")
    app = AConductorDesktopApp(
        root,
        service=service,
        background_executor=ImmediateExecutor(),
        error_handler=lambda _code: None,
    )
    item = app.worker_tree.get_children()[1]
    app.worker_tree.selection_set(item)
    app.worker_tree.focus(item)

    app.start_selected()
    root.update()

    activity = app.activity_text.get("1.0", "end")
    assert "LIFECYCLE_COMMAND_FAILED" in activity
    assert "super-secret-runtime-detail" not in activity


class FakeSetupLifecycleService(FakeLifecycleService):
    def __init__(self, snapshot: ControlCenterSnapshot, draft: WorkerSetupDraft) -> None:
        super().__init__(snapshot)
        self.draft = draft
        self.readiness = SetupReadiness(False, "WORKER_CONFIG_MISSING")
        self.saved = []
        self.identity_calls: list[tuple[str, str]] = []

    def worker_setup(self, worker_id: str):
        return self.draft

    def save_worker_setup(self, draft, *, serena_config_source=None):
        self.saved.append((draft, serena_config_source))
        self.draft = replace(draft, configured=True)
        return self.draft

    def capture_exact_project_identity(self, worker_id: str):
        self.identity_calls.append(("EXACT", worker_id))
        return object()

    def save_no_git_project_identity(self, worker_id: str):
        self.identity_calls.append(("NO_GIT", worker_id))
        return object()

    def lifecycle_readiness(self, worker_id: str):
        return self.readiness


def setup_draft(tmp_path: Path) -> WorkerSetupDraft:
    root_path = (tmp_path / "worker").resolve()
    return WorkerSetupDraft(
        worker_id="a-worker-02",
        configured=False,
        instance_root=str(root_path),
        serena_home=str(root_path / "serena-home"),
        run_dir=str(root_path / "run"),
        log_dir=str(root_path / "logs"),
        health_host="127.0.0.1",
        health_port=18012,
        runtime_executable_ref="",
        profile_template_ref="",
        tunnel_binding_ref=None,
        reference_file_path=None,
        reference_allowed_root=None,
        startup_timeout_seconds=15,
        stop_timeout_seconds=10,
    )


def test_setup_readiness_gates_start_for_stopped_worker(root, tmp_path: Path) -> None:
    service = FakeSetupLifecycleService(lifecycle_snapshot(), setup_draft(tmp_path))
    app = AConductorDesktopApp(root, service=service, background_executor=ImmediateExecutor())
    item = app.worker_tree.get_children()[1]
    app.worker_tree.selection_set(item)
    app.worker_tree.focus(item)

    app._update_lifecycle_buttons()
    assert app.start_button.instate(["disabled"])

    service.readiness = SetupReadiness(True, "READY")
    app._update_lifecycle_buttons()
    assert app.start_button.instate(["!disabled"])


def test_setup_dialog_contains_paths_refs_but_no_secret_value_fields(root, tmp_path: Path) -> None:
    service = FakeSetupLifecycleService(lifecycle_snapshot(), setup_draft(tmp_path))
    app = AConductorDesktopApp(root, service=service, background_executor=ImmediateExecutor())
    item = app.worker_tree.get_children()[1]
    app.worker_tree.selection_set(item)
    app.worker_tree.focus(item)

    dialog = app.open_runtime_setup()
    root.update_idletasks()

    assert isinstance(dialog, tk.Toplevel)
    keys = set(app._setup_entries)
    assert "tunnel_reference_id" in keys
    assert "tunnel_reference_file" in keys
    assert "serena_config_source" in keys
    assert all(
        forbidden not in key
        for key in keys
        for forbidden in ("api_key", "token_value", "secret_value", "tunnel_id_value")
    )
    dialog.destroy()


def test_setup_dialog_save_delegates_non_secret_draft(root, tmp_path: Path) -> None:
    service = FakeSetupLifecycleService(lifecycle_snapshot(), setup_draft(tmp_path))
    app = AConductorDesktopApp(
        root,
        service=service,
        background_executor=ImmediateExecutor(),
        error_handler=lambda _code: None,
    )
    item = app.worker_tree.get_children()[1]
    app.worker_tree.selection_set(item)
    app.worker_tree.focus(item)
    dialog = app.open_runtime_setup()
    app._setup_entries["runtime_executable"].insert(0, str(tmp_path / "tunnel-client.exe"))
    app._setup_entries["profile_template"].insert(0, str(tmp_path / "runtime.yaml.template"))
    app._setup_entries["serena_config_source"].insert(0, str(tmp_path / "serena_config.yml"))

    app.save_runtime_setup(dialog)

    assert len(service.saved) == 1
    saved, source = service.saved[0]
    assert saved.worker_id == "a-worker-02"
    assert saved.runtime_executable_ref.endswith("tunnel-client.exe")
    assert str(source).endswith("serena_config.yml")


def test_setup_capture_identity_actions_delegate(root, tmp_path: Path) -> None:
    service = FakeSetupLifecycleService(lifecycle_snapshot(), setup_draft(tmp_path))
    app = AConductorDesktopApp(
        root,
        service=service,
        background_executor=ImmediateExecutor(),
        error_handler=lambda _code: None,
    )
    item = app.worker_tree.get_children()[1]
    app.worker_tree.selection_set(item)
    app.worker_tree.focus(item)

    app.capture_exact_identity()
    app.save_no_git_identity()

    assert service.identity_calls == [
        ("EXACT", "a-worker-02"),
        ("NO_GIT", "a-worker-02"),
    ]


class SettingsFakeService(FakeService):
    def __init__(self, snapshot: ControlCenterSnapshot) -> None:
        super().__init__(snapshot)
        self.saved: list[WorkerSerenaSettings] = []

    def worker_settings(self, worker_id: str) -> WorkerSerenaSettings:
        return WorkerSerenaSettings(worker_id=worker_id)

    def save_worker_settings(self, settings: WorkerSerenaSettings) -> WorkerSerenaSettings:
        self.saved.append(settings)
        return settings


def _select_first_worker(app: AConductorDesktopApp, root: tk.Tk) -> None:
    worker_item = app.worker_tree.get_children()[0]
    app.worker_tree.selection_set(worker_item)
    app.worker_tree.focus(worker_item)
    app._update_lifecycle_buttons()
    root.update_idletasks()


def test_worker_config_dialog_prefills_and_saves(root) -> None:
    service = SettingsFakeService(sample_snapshot())
    codes: list[str] = []
    app = AConductorDesktopApp(root, service=service, error_handler=codes.append)
    _select_first_worker(app, root)

    dialog = app.open_worker_config()

    assert dialog is not None
    assert app._config_entries["tool_timeout"].get() == "240"
    assert app._config_entries["language_backend"].get() == "LSP"
    assert app._config_entries["project_path"].get().endswith("A-Wiki")
    assert app._config_tool_vars["find_file"].get() is True
    assert len(app._config_tool_vars) >= 20
    assert len(app._config_lang_vars) >= 20
    assert app._config_lang_vars["python"].get() is True
    app._config_tool_vars["find_file"].set(False)
    app._config_lang_vars["rust"].set(False)
    app._config_lang_vars["go"].set(False)
    app._config_entries["tool_timeout"].delete(0, "end")
    app._config_entries["tool_timeout"].insert(0, "300")
    app._config_entries["base_modes"].insert(0, "editing")
    app._config_entries["project_path"].delete(0, "end")
    app._config_entries["project_path"].insert(0, r"A:\GitHub\env-wastewater-webapp")

    app.save_worker_config(dialog)

    assert codes == []
    assert len(service.saved) == 1
    saved = service.saved[0]
    assert saved.worker_id == "a-worker-01"
    assert saved.excluded_tools == ("find_file",)
    assert saved.base_modes == ("editing",)
    assert saved.tool_timeout == 300
    assert saved.project_path == r"A:\GitHub\env-wastewater-webapp"
    assert "python" in saved.enabled_languages
    assert "html" in saved.enabled_languages
    assert "rust" not in saved.enabled_languages
    assert "go" not in saved.enabled_languages
    assert not dialog.winfo_exists()


def test_worker_config_invalid_combination_blocks_save(root) -> None:
    service = SettingsFakeService(sample_snapshot())
    codes: list[str] = []
    app = AConductorDesktopApp(root, service=service, error_handler=codes.append)
    _select_first_worker(app, root)
    dialog = app.open_worker_config()
    assert dialog is not None
    app._config_entries["fixed_tools"].insert(0, "read_file")
    app._config_tool_vars["find_file"].set(False)

    app.save_worker_config(dialog)

    assert service.saved == []
    assert codes == ["SETTINGS_INVALID"]
    assert dialog.winfo_exists()
    dialog.destroy()


def test_config_button_requires_settings_service_and_selection(root) -> None:
    plain_app = AConductorDesktopApp(root, service=FakeService(sample_snapshot()))
    assert plain_app.config_button.instate(["disabled"])
    _select_first_worker(plain_app, root)
    assert plain_app.config_button.instate(["disabled"])

    settings_app = AConductorDesktopApp(root, service=SettingsFakeService(sample_snapshot()))
    _select_first_worker(settings_app, root)
    assert not settings_app.config_button.instate(["disabled"])


class FakeInstanceService(FakeService):
    def __init__(self, snapshot: ControlCenterSnapshot) -> None:
        super().__init__(snapshot)
        from types import SimpleNamespace

        self._simple = SimpleNamespace
        self.instance_actions: list[tuple[str, str]] = []
        self.autostart: dict[str, bool] = {"Serena-Beta": True}
        self.states = {
            "Serena-Alpha": InstanceHealthState.READY,
            "Serena-Beta": InstanceHealthState.STOPPED,
        }
        self._instances = tuple(
            LocalInstance(
                name=name,
                project_path=f"A:/GitHub/{name.lower()}",
                health_address=f"127.0.0.1:{18010 + index}",
                instance_root=Path("C:/AI/serena-instances") / name.lower(),
            )
            for index, name in enumerate(self.states)
        )

    def instances(self):
        return self._instances

    def instance_states(self):
        return tuple((item, self.states[item.name]) for item in self._instances)

    def instance_action(self, name, action):
        self.instance_actions.append((name, action))
        code = InstanceResultCode.RUNNING if action == "start" else InstanceResultCode.STOPPED
        return self._simple(result_code=code)

    def instance_autostart(self, name):
        return self.autostart.get(name, False)

    def set_instance_autostart(self, name, enabled):
        self.autostart[name] = enabled

    def autostart_instance_names(self):
        return tuple(name for name, value in self.autostart.items() if value)


def test_instance_panel_lists_states_and_autostarts_flagged(root) -> None:
    service = FakeInstanceService(sample_snapshot())
    app = AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )
    app.start_background_operations()
    root.update()

    rows = app.instance_tree.get_children()
    assert len(rows) == 2
    alpha_values = app.instance_tree.item(rows[0], "values")
    beta_values = app.instance_tree.item(rows[1], "values")
    assert alpha_values[0] == "Serena-Alpha"
    assert "READY" in alpha_values[2]
    assert alpha_values[4] == "-"
    assert "STOPPED" in beta_values[2]
    assert beta_values[4] == "-"   # TUNNEL column (fake: not configured)
    assert beta_values[5] == "ON"  # AUTO column

    assert ("Serena-Beta", "start") in service.instance_actions
    assert app.instance_start_button.instate(["!disabled"])


def test_instance_start_selected_delegates_to_service(root) -> None:
    service = FakeInstanceService(sample_snapshot())
    app = AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )
    app.start_background_operations()
    root.update()
    beta_row = app._instance_rows["Serena-Beta"]
    app.instance_tree.selection_set(beta_row)
    app.instance_tree.focus(beta_row)

    app.start_selected_instance()
    root.update()

    assert ("Serena-Beta", "start") in service.instance_actions


def test_instance_toggle_auto_persists_through_service(root) -> None:
    service = FakeInstanceService(sample_snapshot())
    app = AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )
    app.start_background_operations()
    root.update()
    alpha_row = app._instance_rows["Serena-Alpha"]
    app.instance_tree.selection_set(alpha_row)
    app.instance_tree.focus(alpha_row)

    app.toggle_instance_autostart()
    root.update()

    assert service.autostart["Serena-Alpha"] is True
    assert app.instance_tree.item(alpha_row, "values")[4] == "ON"


def test_instance_panel_disabled_without_instance_service(root) -> None:
    app = AConductorDesktopApp(
        root, service=FakeService(sample_snapshot()), background_executor=ImmediateExecutor()
    )
    root.update()

    assert app.instance_start_button.instate(["disabled"])
    assert len(app.instance_tree.get_children()) == 0


def test_second_brain_dialog_saves_global_profile(root) -> None:
    service = SettingsFakeService(sample_snapshot())
    codes: list[str] = []
    app = AConductorDesktopApp(
        root,
        service=service,
        background_executor=ImmediateExecutor(),
        error_handler=codes.append,
        directory_picker=lambda: r"C:\picked\brain",
    )

    dialog = app.open_brain_config()
    assert dialog is not None
    app._brain_entries["brain_folder_1"].insert(0, r"A:\GitHub\A-Wiki")
    app._brain_entries["brain_entry_1"].insert(0, r"A:\GitHub\A-Wiki\AGENTS.md")

    app.save_brain_config(dialog)

    assert codes == []
    saved = [s for s in service.saved if s.worker_id == "global-brain"]
    assert len(saved) == 1
    assert saved[0].brain_folders == (r"A:\GitHub\A-Wiki",)
    assert saved[0].brain_entry_files == (r"A:\GitHub\A-Wiki\AGENTS.md",)
    assert not dialog.winfo_exists()


def test_second_brain_defaults_button_fills_awiki(root) -> None:
    service = SettingsFakeService(sample_snapshot())
    app = AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )
    dialog = app.open_brain_config()
    assert dialog is not None

    app._fill_brain_defaults()
    app.save_brain_config(dialog)

    saved = [s for s in service.saved if s.worker_id == "global-brain"][0]
    assert saved.brain_folders == (r"A:\GitHub\A-Wiki",)
    assert saved.brain_entry_files == (
        r"A:\GitHub\A-Wiki\AGENTS.md",
        r"A:\GitHub\A-Wiki\wiki\context\wiki-overview.md",
    )


def test_second_brain_invalid_path_blocked(root) -> None:
    service = SettingsFakeService(sample_snapshot())
    codes: list[str] = []
    app = AConductorDesktopApp(
        root,
        service=service,
        background_executor=ImmediateExecutor(),
        error_handler=codes.append,
    )
    dialog = app.open_brain_config()
    app._brain_entries["brain_folder_1"].insert(0, "relative/not/absolute")

    app.save_brain_config(dialog)

    assert codes == ["SETTINGS_INVALID"]
    assert not [s for s in service.saved if s.worker_id == "global-brain"]
    assert dialog.winfo_exists()
    dialog.destroy()


def test_guide_opens_in_app_window_by_default(root) -> None:
    app = AConductorDesktopApp(
        root, service=FakeService(sample_snapshot()), background_executor=ImmediateExecutor()
    )

    window = app.open_guide()

    assert window is not None
    assert "คู่มือ" in window.title()
    text_widget = None
    for child in window.grid_slaves(row=0, column=0):
        text_widget = child
    assert isinstance(text_widget, tk.Text)
    content = text_widget.get("1.0", "end")
    assert "A-Sunday Conductor" in content
    assert "เริ่มต้น" in content or "คู่มือ" in content
    window.destroy()


def test_all_primary_buttons_have_tooltips(root) -> None:
    app = AConductorDesktopApp(
        root, service=FakeService(sample_snapshot()), background_executor=ImmediateExecutor()
    )
    for name in (
        "add_button", "assign_button", "release_button", "refresh_button",
        "start_button", "stop_button", "restart_button", "setup_button",
        "config_button", "activate_button", "help_button",
    ):
        button = getattr(app, name)
        tip = getattr(button, "_acond_tooltip", None)
        assert tip is not None, name
        assert tip.text.strip(), name


def test_add_and_assign_live_in_projects_panel(root) -> None:
    app = AConductorDesktopApp(
        root, service=FakeService(sample_snapshot()), background_executor=ImmediateExecutor()
    )

    def panel_of(widget):
        parent = widget.nametowidget(widget.winfo_parent())
        return parent

    add_panel = panel_of(panel_of(app.add_button))   # project_actions -> PROJECTS panel
    list_panel = panel_of(app.project_list)
    release_panel = panel_of(panel_of(app.release_button))

    activate_panel = panel_of(panel_of(app.activate_button))

    assert add_panel is list_panel
    assert activate_panel is list_panel
    assert release_panel is not list_panel


def test_activate_helper_copies_selected_project_prompt(root) -> None:
    app = AConductorDesktopApp(
        root, service=FakeService(sample_snapshot()), background_executor=ImmediateExecutor()
    )
    app.project_list.selection_set(0)

    app.copy_activation_prompt()

    copied = root.clipboard_get()
    assert copied == (
        "Activate the current dir as project using serena\n"
        r"Project path: A:\GitHub\A-Wiki"
    )
    assert "Copy Activate" in app.activity_text.get("1.0", "end")


def test_activate_helper_requires_selected_project(root) -> None:
    captured: list[str] = []
    app = AConductorDesktopApp(
        root,
        service=FakeService(sample_snapshot()),
        background_executor=ImmediateExecutor(),
        error_handler=captured.append,
    )

    app.copy_activation_prompt()

    assert captured == ["SELECT_PROJECT"]


def test_worker_start_routes_to_matching_connector(root) -> None:
    service = FakeInstanceService(sample_snapshot())
    service.worker_start_path = lambda worker_id: (
        "connector",
        "Serena-Alpha" if worker_id == "a-worker-01" else None,
    )
    app = AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )
    root.update()
    app.refresh()
    root.update()
    worker_item = app.worker_tree.get_children()[0]
    app.worker_tree.selection_set(worker_item)
    app.worker_tree.focus(worker_item)
    app._update_lifecycle_buttons()

    # CONNECTOR column shows the matching instance name
    assert "Serena-Alpha" in app.worker_tree.item(worker_item, "values")

    # Start is enabled WITHOUT any lifecycle service (connector path)
    assert not app.start_button.instate(["disabled"])

    app.start_selected()
    root.update()

    assert ("Serena-Alpha", "start-w") in service.instance_actions


def test_worker_start_blocked_without_connector_or_setup(root) -> None:
    service = FakeInstanceService(sample_snapshot())
    service.worker_start_path = lambda worker_id: ("blocked", "SETUP_REQUIRED")
    app = AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )
    root.update()
    worker_item = app.worker_tree.get_children()[0]
    app.worker_tree.selection_set(worker_item)
    app.worker_tree.focus(worker_item)
    app._update_lifecycle_buttons()

    assert app.start_button.instate(["disabled"])
    assert app.worker_tree.item(worker_item, "values")[4] == "-"


class TunnelFakeService(FakeInstanceService):
    def __init__(self, snapshot: ControlCenterSnapshot) -> None:
        super().__init__(snapshot)
        self.tunnel_writes: list[tuple[str, str]] = []
        self._tunnel_flags = {"Serena-Alpha": True, "Serena-Beta": False}
        for item in self._instances:
            object.__setattr__(
                item, "tunnel_configured", self._tunnel_flags.get(item.name, False)
            )

    def set_instance_tunnel_id(self, instance_name, tunnel_id):
        from a_conductor.serena_config_store import SerenaConfigStoreError
        import re as _re

        if not _re.fullmatch(r"tunnel_[0-9a-f]{32}", (tunnel_id or "").strip()):
            raise SerenaConfigStoreError("TUNNEL_ID_INVALID")
        self.tunnel_writes.append((instance_name, tunnel_id.strip()))
        return Path("C:/nowhere") / f"{instance_name}.txt"


def test_tunnel_column_reflects_configuration(root) -> None:
    service = TunnelFakeService(sample_snapshot())
    app = AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )
    app.refresh_instances()
    root.update()

    values = {
        app.instance_tree.item(item, "values")[0]: app.instance_tree.item(item, "values")[4]
        for item in app.instance_tree.get_children()
    }
    assert values["Serena-Alpha"] == "Y"
    assert values["Serena-Beta"] == "-"


def test_tunnel_dialog_validates_and_saves(root) -> None:
    service = TunnelFakeService(sample_snapshot())
    codes: list[str] = []
    app = AConductorDesktopApp(
        root,
        service=service,
        background_executor=ImmediateExecutor(),
        error_handler=codes.append,
    )
    app.refresh_instances()
    root.update()
    beta_row = app._instance_rows["Serena-Beta"]
    app.instance_tree.selection_set(beta_row)
    app.instance_tree.focus(beta_row)

    dialog = app.open_tunnel_id_dialog()
    assert dialog is not None

    valid_id = "tunnel_" + "9f8e7d6c" * 4
    app._tunnel_entry.delete(0, "end")
    app._tunnel_entry.insert(0, valid_id)
    app._validate_tunnel_entry()
    assert "ถูกต้อง" in app._tunnel_status.cget("text")

    # click save via invoking the button command
    def find_button(parent, label):
        for child in parent.winfo_children():
            if isinstance(child, ttk.Button) and child.cget("text") == label:
                return child
            nested = find_button(child, label)
            if nested is not None:
                return nested
        return None

    save_button = find_button(dialog, "บันทึก")
    assert save_button is not None
    save_button.invoke()

    assert ("Serena-Beta", valid_id) in service.tunnel_writes
    assert not dialog.winfo_exists()

    # invalid input path: reopen and try bad id
    dialog2 = app.open_tunnel_id_dialog()
    app._tunnel_entry.delete(0, "end")
    app._tunnel_entry.insert(0, "bad-id")
    find_button(dialog2, "บันทึก").invoke()
    assert codes == ["TUNNEL_ID_INVALID"]
    assert not any(name == "Serena-Beta" and value == "bad-id" for name, value in service.tunnel_writes)
    if dialog2.winfo_exists():
        dialog2.destroy()


def test_guide_viewer_marks_urls_as_links(root) -> None:
    from a_conductor.desktop_ui import link_url_spans

    spans = link_url_spans("อ่าน https://oraios.github.io/serena/ และ https://a.b/c)")
    assert (spans[0][1] - spans[0][0]) == len("https://oraios.github.io/serena/")
    assert spans[1][1] - spans[1][0] == len("https://a.b/c")

    app = AConductorDesktopApp(
        root, service=FakeService(sample_snapshot()), background_executor=ImmediateExecutor()
    )
    window = app.open_guide()
    assert window is not None
    text_widget = None
    for child in window.grid_slaves(row=0, column=0):
        text_widget = child
    assert isinstance(text_widget, tk.Text)
    content = text_widget.get("1.0", "end")
    assert "เชื่อมต่อ AI แต่ละค่าย" in content
    assert text_widget.tag_ranges("link")
    window.destroy()


def test_error_popup_is_themed_and_teaches(root) -> None:
    from a_conductor.desktop_ui import ERROR_EXPLANATIONS

    window = None
    app = AConductorDesktopApp(
        root,
        service=FakeService(sample_snapshot()),
        background_executor=ImmediateExecutor(),
    )

    # every code the UI raises must have a Thai teaching entry
    import re as _re
    from pathlib import Path as _Path
    source = _Path("src/a_conductor/desktop_ui.py").read_text(encoding="utf-8")
    used = set(_re.findall(r'_handle_error\("([A-Z_]+)"', source))
    missing = sorted(used - set(ERROR_EXPLANATIONS))
    assert not missing, missing

    # the default handler (bypass injected capture) shows the themed window
    app._error_handler = app._show_error
    window = app._show_error("SELECT_WORKER")
    assert window is not None
    labels = [w for w in window.winfo_children()[0].winfo_children() if isinstance(w, tk.Label)]
    texts = [str(l.cget("text")) for l in labels]
    assert any("ยังไม่ได้เลือก Worker" in t for t in texts)
    assert any("SELECT_WORKER" in t for t in texts)
    assert any("คู่มือ" in t for t in texts)
    window.destroy()


def test_status_pulse_toggles_online_color(root) -> None:
    app = AConductorDesktopApp(
        root, service=FakeService(sample_snapshot()), background_executor=ImmediateExecutor()
    )
    first = str(app.connection_label.cget("fg"))
    app._start_status_pulse()
    second = str(app.connection_label.cget("fg"))
    app._start_status_pulse()
    third = str(app.connection_label.cget("fg"))
    assert {second, third} == {app.theme.ready, app.theme.ready_dim}
    assert first in (second, third)
    assert second != third


def test_memory_status_reflects_selected_project(root, tmp_path) -> None:
    snapshot = sample_snapshot()
    has_memories = tmp_path / "with-memories"
    (has_memories / ".serena" / "memories").mkdir(parents=True)
    (has_memories / ".serena" / "memories" / "notes.md").write_text("x", encoding="utf-8")
    no_memories = tmp_path / "fresh"
    no_memories.mkdir()
    from dataclasses import replace as _replace

    projects = (
        Project("project-mem", "WithMem", str(has_memories)),
        Project("project-fresh", "Fresh", str(no_memories)),
    )
    service = FakeService(_replace(snapshot, projects=projects))
    app = AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )

    # nothing selected -> neutral
    app.project_list.selection_clear(0, "end")
    app._refresh_memory_status()
    assert "เลือกโปรเจกต์" in app.memory_status_label.cget("text")

    # select project with memories
    app.project_list.selection_set(0)
    app._refresh_memory_status()
    assert "พร้อม (1 ไฟล์)" in app.memory_status_label.cget("text")

    # select fresh project -> onboarding nudge (click replaces selection)
    app.project_list.selection_clear(0, "end")
    app.project_list.selection_set(1)
    app._refresh_memory_status()
    text = app.memory_status_label.cget("text")
    assert "ยังไม่มีความจำ" in text
    assert "เริ่มบทสนทนาใหม่" in text


class PrefsFakeService(FakeService):
    def __init__(self, snapshot: ControlCenterSnapshot) -> None:
        super().__init__(snapshot)
        self.preferences: dict[str, bool] = {}

    def get_preference(self, key):
        return self.preferences.get(key)

    def set_preference(self, key, value):
        self.preferences[key] = value


def test_preferences_dialog_toggle_persists_immediately(root) -> None:
    service = PrefsFakeService(sample_snapshot())
    codes: list[str] = []
    app = AConductorDesktopApp(
        root,
        service=service,
        background_executor=ImmediateExecutor(),
        error_handler=codes.append,
    )

    window = app.open_preferences()
    assert window is not None

    # find the supervised checkbox and flip it off then on
    def find_checkbutton(parent):
        for child in parent.winfo_children():
            if isinstance(child, tk.Checkbutton):
                return child
            nested = find_checkbutton(child)
            if nested is not None:
                return nested
        return None

    box = find_checkbutton(window)
    assert box is not None
    assert hasattr(box, "_acond_tooltip")

    box.invoke()
    root.update()
    assert service.preferences["supervised"] is False
    box.invoke()
    root.update()
    assert service.preferences["supervised"] is True
    assert codes == []
    window.destroy()


def test_preferences_button_in_header_gated(root) -> None:
    plain = AConductorDesktopApp(
        root, service=FakeService(sample_snapshot()), background_executor=ImmediateExecutor()
    )
    assert plain.prefs_button.instate(["disabled"])

    wired = AConductorDesktopApp(
        root,
        service=PrefsFakeService(sample_snapshot()),
        background_executor=ImmediateExecutor(),
    )
    assert not wired.prefs_button.instate(["disabled"])


class RebindFakeService(FakeInstanceService):
    def __init__(self, snapshot):
        super().__init__(snapshot)
        self.rebinds: list[tuple[str, str]] = []

    def rebind_instance(self, name, new_root):
        self.rebinds.append((name, new_root))
        return "REBOUND"


def test_rebind_dialog_success_and_blocked(root, tmp_path) -> None:
    service = RebindFakeService(sample_snapshot())
    codes: list[str] = []
    app = AConductorDesktopApp(
        root,
        service=service,
        background_executor=ImmediateExecutor(),
        error_handler=codes.append,
        directory_picker=lambda: str(tmp_path / "newp"),
    )
    app.refresh_instances()
    root.update()
    row = app._instance_rows["Serena-Alpha"]
    app.instance_tree.selection_set(row)
    app.instance_tree.focus(row)

    dialog = app.open_rebind_dialog()
    assert dialog is not None
    app._rebind_entry.insert(0, str(tmp_path / "newp"))

    def find_btn(parent, label):
        for c in parent.winfo_children():
            if isinstance(c, ttk.Button) and c.cget("text") == label:
                return c
            n = find_btn(c, label)
            if n is not None:
                return n
        return None

    find_btn(dialog, "เปลี่ยนเลย").invoke()
    assert ("Serena-Alpha", str(tmp_path / "newp")) in service.rebinds
    assert not dialog.winfo_exists()

    # blocked case (same project)
    service.rebind_instance = lambda n, r: "SKIPPED_SAME_PROJECT"
    dialog2 = app.open_rebind_dialog()
    app._rebind_entry.insert(0, str(tmp_path / "same"))
    find_btn(dialog2, "เปลี่ยนเลย").invoke()
    assert "SKIPPED_SAME_PROJECT" in app._rebind_status.cget("text")
    assert dialog2.winfo_exists()
    dialog2.destroy()


def test_config_dialog_every_surface_has_explanation(root) -> None:
    from a_conductor.config_blurbs import (
        FIELD_BLURBS,
        LANGUAGE_BACKEND_BLURBS,
        LANGUAGE_BLURBS,
        MODE_BLURBS,
        TOOL_BLURBS,
    )
    from a_conductor.worker_serena_settings import (
        ENGINE_TOOLS,
        KNOWN_LANGUAGES,
        LanguageBackend,
    )

    # blurb catalogs cover every catalogued surface
    for tool in ENGINE_TOOLS:
        assert tool in TOOL_BLURBS, tool
    for language in KNOWN_LANGUAGES:
        assert language in LANGUAGE_BLURBS, language
    for backend in LanguageBackend:
        assert backend.value in LANGUAGE_BACKEND_BLURBS, backend.value
    for field in ("tool_timeout", "project_path", "included_optional_tools", "fixed_tools", "base_modes"):
        assert field in FIELD_BLURBS, field
    assert "interactive" in MODE_BLURBS

    # dialog actually attaches tooltips to toggle checkboxes and field blurbs render
    service = SettingsFakeService(sample_snapshot())
    app = AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )
    worker_item = app.worker_tree.get_children()[0]
    app.worker_tree.selection_set(worker_item)
    app.worker_tree.focus(worker_item)

    dialog = app.open_worker_config()
    assert dialog is not None
    boxes = []

    def collect(parent):
        for c in parent.winfo_children():
            if isinstance(c, tk.Checkbutton):
                boxes.append(c)
            collect(c)

    collect(dialog)
    with_tip = [b for b in boxes if hasattr(b, "_acond_tooltip")]
    assert len(boxes) > 40          # tools + languages grids
    assert len(with_tip) == len(boxes)  # every checkbox has a tooltip

    # backend blurb shows on open
    assert "LSP" in str(app._backend_blurb.cget("text")) or app._backend_blurb.cget("text")
    assert app._backend_blurb.cget("text")
    dialog.destroy()


def test_upstream_button_opens_dialog_with_data(root, monkeypatch) -> None:
    from a_conductor.upstream_check import UpstreamStatus

    app = AConductorDesktopApp(
        root, service=FakeService(sample_snapshot()), background_executor=ImmediateExecutor()
    )
    assert not app.upstream_button.instate(["disabled"])
    assert hasattr(app.upstream_button, "_acond_tooltip")

    captured = []

    monkeypatch.setattr(
        "a_conductor.desktop_ui.fetch_upstream_status",
        lambda: captured.append(1)
        or UpstreamStatus(
            latest_release_tag="v9.9.9",
            latest_release_url="https://github.com/oraios/serena/releases/v9.9.9",
            latest_commit_sha="abc123def456",
            latest_commit_date="2026-08-22T00:00:00Z",
            repo_url="https://github.com/oraios/serena",
        ),
    )

    app.check_upstream()
    root.update()

    # a themed dialog exists and contains the fetched data + clickable repo link
    tops = [w for w in app.root.winfo_children() if isinstance(w, tk.Toplevel) and w.winfo_exists()]
    assert tops, "upstream dialog did not open"
    dialog = tops[-1]
    texts = []
    for w in dialog.winfo_children():
        for c in w.winfo_children():
            if isinstance(c, tk.Text):
                texts.append(c.get("1.0", "end"))
    assert texts and "v9.9.9" in texts[0]
    assert "https://github.com/oraios/serena" in texts[0]
    assert not app.upstream_button.instate(["disabled"])
    dialog.destroy()
