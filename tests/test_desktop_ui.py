from __future__ import annotations

import os
import tkinter as tk
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

    assert root.title() == "A-Conductor"
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
    assert beta_values[4] == "ON"

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
    assert "A-Conductor" in content
    assert "เริ่มต้น" in content or "คู่มือ" in content
    window.destroy()


def test_all_primary_buttons_have_tooltips(root) -> None:
    app = AConductorDesktopApp(
        root, service=FakeService(sample_snapshot()), background_executor=ImmediateExecutor()
    )
    for name in (
        "add_button", "assign_button", "release_button", "refresh_button",
        "start_button", "stop_button", "restart_button", "setup_button",
        "config_button", "help_button",
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

    assert add_panel is list_panel
    assert release_panel is not list_panel
