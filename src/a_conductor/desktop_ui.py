"""Tkinter desktop adapter for the A-Conductor Control Center.

The desktop layer consumes only the application-service snapshot/actions. It
contains no process, tunnel, Git, or persistence implementation.
"""

from __future__ import annotations

from concurrent.futures import Executor, Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .control_center import ControlCenterError, ControlCenterSnapshot
from .domain import WorkerState
from .lifecycle_coordinator import LifecycleCoordinatorError
from .lifecycle_executor import LifecycleExecutionResult
from .runtime_setup import RuntimeSetupError, SetupReadiness, WorkerSetupDraft
from .worker_serena_settings import LanguageBackend, WorkerSerenaSettings


class ControlCenterUIService(Protocol):
    def snapshot(self) -> ControlCenterSnapshot: ...

    def register_project(
        self,
        root_path,
        *,
        display_name: str | None = None,
        project_id: str | None = None,
    ): ...

    def assign_project(
        self,
        worker_id: str,
        project_id: str,
        *,
        mutation_allowed: bool = True,
    ): ...

    def release_worker(self, worker_id: str): ...


@dataclass(frozen=True, slots=True)
class DesktopTheme:
    background: str = "#0c1015"
    panel: str = "#121820"
    panel_alt: str = "#171f29"
    border: str = "#263241"
    foreground: str = "#d7e0ea"
    muted: str = "#7f8c9a"
    accent: str = "#5cc8d7"
    ready: str = "#62d394"
    warning: str = "#e6b85c"
    error: str = "#ee6b73"
    idle: str = "#87929d"
    selection: str = "#20394a"
    monospace_font: str = "Cascadia Mono"
    sans_font: str = "Segoe UI"
    base_font_size: int = 10


class AConductorDesktopApp:
    def __init__(
        self,
        root: tk.Tk,
        *,
        service: ControlCenterUIService,
        theme: DesktopTheme | None = None,
        directory_picker: Callable[[], str] | None = None,
        error_handler: Callable[[str], None] | None = None,
        background_executor: Executor | None = None,
    ) -> None:
        self.root = root
        self.service = service
        self.theme = theme or DesktopTheme()
        self._directory_picker = directory_picker or filedialog.askdirectory
        self._error_handler = error_handler or self._show_error
        self._background_executor = background_executor or ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="a-conductor-ui"
        )
        self._owns_background_executor = background_executor is None
        self._project_ids: list[str] = []
        self._worker_ids: dict[str, str] = {}
        self._setup_entries: dict[str, ttk.Entry] = {}
        self._setup_draft: WorkerSetupDraft | None = None

        self._configure_root()
        self._configure_styles()
        self._build_layout()
        self.root.bind_all("<Control-k>", self._on_palette_shortcut)
        self.root.bind_all("<Control-K>", self._on_palette_shortcut)
        self.refresh()

    def _configure_root(self) -> None:
        self.root.title("A-Conductor")
        self.root.configure(background=self.theme.background)
        self.root.geometry("1080x680")
        self.root.minsize(860, 520)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "AConductor.TButton",
            background=self.theme.panel_alt,
            foreground=self.theme.foreground,
            bordercolor=self.theme.border,
            focusthickness=1,
            focuscolor=self.theme.accent,
            padding=(9, 5),
            font=(self.theme.sans_font, self.theme.base_font_size),
        )
        style.map(
            "AConductor.TButton",
            background=[("active", self.theme.selection), ("disabled", self.theme.panel)],
            foreground=[("disabled", self.theme.muted)],
        )
        style.configure(
            "Workers.Treeview",
            background=self.theme.panel,
            fieldbackground=self.theme.panel,
            foreground=self.theme.foreground,
            bordercolor=self.theme.border,
            rowheight=28,
            font=(self.theme.monospace_font, self.theme.base_font_size),
        )
        style.configure(
            "Workers.Treeview.Heading",
            background=self.theme.panel_alt,
            foreground=self.theme.muted,
            bordercolor=self.theme.border,
            font=(self.theme.sans_font, self.theme.base_font_size, "bold"),
        )
        style.map(
            "Workers.Treeview",
            background=[("selected", self.theme.selection)],
            foreground=[("selected", self.theme.foreground)],
        )

    def _build_layout(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        top = tk.Frame(
            self.root,
            bg=self.theme.panel,
            highlightthickness=1,
            highlightbackground=self.theme.border,
        )
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        top.grid_columnconfigure(1, weight=1)
        tk.Label(
            top,
            text="A-CONDUCTOR",
            bg=self.theme.panel,
            fg=self.theme.foreground,
            font=(self.theme.monospace_font, 14, "bold"),
            padx=12,
            pady=9,
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            top,
            text="Ctrl+K  COMMAND PALETTE",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        ).grid(row=0, column=1, sticky="e", padx=12)
        self.connection_label = tk.Label(
            top,
            text="● ONLINE",
            bg=self.theme.panel,
            fg=self.theme.ready,
            font=(self.theme.monospace_font, 10, "bold"),
            padx=12,
        )
        self.connection_label.grid(row=0, column=2, sticky="e")

        body = tk.Frame(self.root, bg=self.theme.background)
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=0)
        body.grid_columnconfigure(0, weight=0, minsize=280)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        project_panel = self._panel(body, "PROJECTS")
        project_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        project_panel.grid_rowconfigure(1, weight=1)
        project_panel.grid_columnconfigure(0, weight=1)
        self.project_list = tk.Listbox(
            project_panel,
            bg=self.theme.panel,
            fg=self.theme.foreground,
            selectbackground=self.theme.selection,
            selectforeground=self.theme.foreground,
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            exportselection=False,
            font=(self.theme.monospace_font, self.theme.base_font_size),
        )
        self.project_list.grid(row=1, column=0, sticky="nsew", padx=9, pady=(0, 9))

        worker_panel = self._panel(body, "WORKERS")
        worker_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        worker_panel.grid_rowconfigure(1, weight=1)
        worker_panel.grid_columnconfigure(0, weight=1)
        columns = ("worker", "state", "project", "path")
        self.worker_tree = ttk.Treeview(
            worker_panel,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Workers.Treeview",
        )
        headings = {
            "worker": ("WORKER", 130),
            "state": ("STATE", 100),
            "project": ("PROJECT", 180),
            "path": ("PATH", 320),
        }
        for name, (label, width) in headings.items():
            self.worker_tree.heading(name, text=label, anchor="w")
            self.worker_tree.column(name, width=width, minwidth=80, anchor="w")
        self.worker_tree.grid(row=1, column=0, sticky="nsew", padx=9, pady=(0, 5))
        self.worker_tree.bind("<<TreeviewSelect>>", lambda _event: self._update_lifecycle_buttons())
        self.worker_tree.tag_configure("ready", foreground=self.theme.ready)
        self.worker_tree.tag_configure("warning", foreground=self.theme.warning)
        self.worker_tree.tag_configure("error", foreground=self.theme.error)
        self.worker_tree.tag_configure("idle", foreground=self.theme.idle)

        actions = tk.Frame(worker_panel, bg=self.theme.panel)
        actions.grid(row=2, column=0, sticky="ew", padx=9, pady=(4, 9))
        self.add_button = self._button(actions, "Add Project", self.add_project)
        self.assign_button = self._button(actions, "Assign", self.assign_selected)
        self.release_button = self._button(actions, "Release", self.release_selected)
        self.refresh_button = self._button(actions, "Refresh", self.refresh)
        self.start_button = self._button(actions, "Start", self.start_selected)
        self.stop_button = self._button(actions, "Stop", self.stop_selected)
        self.restart_button = self._button(actions, "Restart", self.restart_selected)
        self.setup_button = self._button(actions, "Setup", self.open_runtime_setup)
        self.config_button = self._button(actions, "Config", self.open_worker_config)
        for index, button in enumerate(
            (
                self.add_button,
                self.assign_button,
                self.release_button,
                self.refresh_button,
                self.start_button,
                self.stop_button,
                self.restart_button,
                self.setup_button,
                self.config_button,
            )
        ):
            button.grid(row=0, column=index, padx=(0, 6))
        self.start_button.state(["disabled"])
        self.stop_button.state(["disabled"])
        self.restart_button.state(["disabled"])
        self.setup_button.state(["disabled"])
        self.config_button.state(["disabled"])

        activity_panel = self._panel(self.root, "ACTIVITY / LOG")
        activity_panel.grid(row=2, column=0, sticky="nsew", padx=10, pady=(6, 10))
        activity_panel.grid_rowconfigure(1, weight=1)
        activity_panel.grid_columnconfigure(0, weight=1)
        self.activity_text = tk.Text(
            activity_panel,
            height=9,
            bg=self.theme.background,
            fg=self.theme.foreground,
            insertbackground=self.theme.accent,
            borderwidth=0,
            highlightthickness=0,
            wrap="none",
            state="disabled",
            font=(self.theme.monospace_font, self.theme.base_font_size),
        )
        self.activity_text.grid(row=1, column=0, sticky="nsew", padx=9, pady=(0, 9))
        self.log_activity("Control Center ready")

    def _panel(self, parent, title: str) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=self.theme.panel,
            highlightthickness=1,
            highlightbackground=self.theme.border,
        )
        tk.Label(
            frame,
            text=title,
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9, "bold"),
            anchor="w",
            padx=9,
            pady=8,
        ).grid(row=0, column=0, sticky="ew")
        return frame

    def _button(self, parent, text: str, command) -> ttk.Button:
        return ttk.Button(
            parent,
            text=text,
            command=command,
            style="AConductor.TButton",
        )

    @staticmethod
    def _state_tag(state: WorkerState) -> str:
        if state is WorkerState.READY:
            return "ready"
        if state in {WorkerState.STARTING, WorkerState.BUSY, WorkerState.STOPPING}:
            return "warning"
        if state is WorkerState.ERROR:
            return "error"
        return "idle"

    def refresh(self) -> None:
        snapshot = self.service.snapshot()
        self.connection_label.configure(
            text="● ONLINE" if snapshot.online else "● OFFLINE",
            fg=self.theme.ready if snapshot.online else self.theme.error,
        )

        selected_project = self.selected_project_id()
        self.project_list.delete(0, "end")
        self._project_ids.clear()
        for project in snapshot.projects:
            self._project_ids.append(project.project_id)
            self.project_list.insert("end", f"> {project.display_name}\n  {project.root_path}")
        if selected_project in self._project_ids:
            index = self._project_ids.index(selected_project)
            self.project_list.selection_set(index)

        selected_worker = self.selected_worker_id()
        for item in self.worker_tree.get_children():
            self.worker_tree.delete(item)
        self._worker_ids.clear()
        for worker in snapshot.workers:
            project_name = worker.project_display_name or "—"
            project_path = worker.project_root_path or "—"
            item = self.worker_tree.insert(
                "",
                "end",
                values=(
                    worker.worker_id,
                    worker.state.value,
                    project_name,
                    project_path,
                ),
                tags=(self._state_tag(worker.state),),
            )
            self._worker_ids[item] = worker.worker_id
            if selected_worker == worker.worker_id:
                self.worker_tree.selection_set(item)
                self.worker_tree.focus(item)
        self._update_lifecycle_buttons()

    def selected_project_id(self) -> str | None:
        selected = self.project_list.curselection()
        if not selected:
            return None
        index = int(selected[0])
        return self._project_ids[index] if index < len(self._project_ids) else None

    def selected_worker_id(self) -> str | None:
        selected = self.worker_tree.selection()
        if not selected:
            return None
        return self._worker_ids.get(selected[0])

    def add_project(self) -> None:
        selected = self._directory_picker()
        if not selected:
            return
        try:
            self.service.register_project(Path(selected))
        except ControlCenterError as exc:
            self._handle_error(exc.code)
            return
        self.log_activity(f"Add Project  {Path(selected).name}")
        self.refresh()

    def assign_selected(self) -> None:
        project_id = self.selected_project_id()
        worker_id = self.selected_worker_id()
        if project_id is None:
            self._handle_error("SELECT_PROJECT")
            return
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return
        try:
            self.service.assign_project(worker_id, project_id, mutation_allowed=True)
        except ControlCenterError as exc:
            self._handle_error(exc.code)
            return
        self.log_activity(f"Assign       {worker_id} <- {project_id}")
        self.refresh()

    def release_selected(self) -> None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return
        try:
            self.service.release_worker(worker_id)
        except ControlCenterError as exc:
            self._handle_error(exc.code)
            return
        self.log_activity(f"Release      {worker_id}")
        self.refresh()

    @staticmethod
    def _set_enabled(button: ttk.Button, enabled: bool) -> None:
        button.state(["!disabled"] if enabled else ["disabled"])

    def _selected_worker_row(self):
        worker_id = self.selected_worker_id()
        if worker_id is None:
            return None
        return next(
            (row for row in self.service.snapshot().workers if row.worker_id == worker_id),
            None,
        )

    def _has_lifecycle_service(self) -> bool:
        return all(
            callable(getattr(self.service, name, None))
            for name in ("start_worker", "stop_worker", "restart_worker")
        )

    def _has_setup_service(self) -> bool:
        return all(
            callable(getattr(self.service, name, None))
            for name in ("worker_setup", "save_worker_setup")
        )

    def _has_settings_service(self) -> bool:
        return all(
            callable(getattr(self.service, name, None))
            for name in ("worker_settings", "save_worker_settings")
        )

    def _readiness(self, worker_id: str) -> SetupReadiness:
        fn = getattr(self.service, "lifecycle_readiness", None)
        if not callable(fn):
            return SetupReadiness(True, "READY")
        try:
            result = fn(worker_id)
        except RuntimeSetupError as exc:
            return SetupReadiness(False, exc.code)
        except Exception:
            return SetupReadiness(False, "SETUP_READINESS_FAILED")
        return result if isinstance(result, SetupReadiness) else SetupReadiness(False, "SETUP_READINESS_INVALID")

    def _update_lifecycle_buttons(self) -> None:
        row = self._selected_worker_row()
        has_lifecycle = self._has_lifecycle_service()
        has_setup = self._has_setup_service()
        self._set_enabled(self.setup_button, row is not None and has_setup)
        self._set_enabled(
            self.config_button, row is not None and self._has_settings_service()
        )
        if row is None or not has_lifecycle or row.assignment_id is None:
            self._set_enabled(self.start_button, False)
            self._set_enabled(self.stop_button, False)
            self._set_enabled(self.restart_button, False)
            return

        ready = self._readiness(row.worker_id).ready
        self._set_enabled(
            self.start_button,
            row.state is WorkerState.STOPPED and ready,
        )
        self._set_enabled(
            self.stop_button,
            row.state in {WorkerState.READY, WorkerState.BUSY, WorkerState.STARTING},
        )
        self._set_enabled(
            self.restart_button,
            row.state is WorkerState.READY and ready,
        )

    def _submit_lifecycle(self, action: str, worker_id: str, command) -> None:
        self.log_activity(f"{action:<12} {worker_id} QUEUED")
        self._set_enabled(self.start_button, False)
        self._set_enabled(self.stop_button, False)
        self._set_enabled(self.restart_button, False)
        future = self._background_executor.submit(command, worker_id)
        self.root.after(0, self._poll_lifecycle_future, action, worker_id, future)

    def _poll_lifecycle_future(
        self,
        action: str,
        worker_id: str,
        future: Future,
    ) -> None:
        if not future.done():
            self.root.after(25, self._poll_lifecycle_future, action, worker_id, future)
            return
        try:
            result = future.result()
        except LifecycleCoordinatorError as exc:
            self._handle_error(exc.code)
            self._update_lifecycle_buttons()
            return
        except Exception:
            self._handle_error("LIFECYCLE_COMMAND_FAILED")
            self._update_lifecycle_buttons()
            return

        if not isinstance(result, LifecycleExecutionResult):
            self._handle_error("LIFECYCLE_RESULT_INVALID")
            self._update_lifecycle_buttons()
            return
        self.log_activity(
            f"{action:<12} {worker_id} {result.state.value} {result.reason_code}"
        )
        self.refresh()

    def _run_selected_lifecycle(self, action: str, method_name: str) -> None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return
        command = getattr(self.service, method_name, None)
        if not callable(command):
            self._handle_error("LIFECYCLE_NOT_WIRED")
            return
        self._submit_lifecycle(action, worker_id, command)

    def start_selected(self) -> None:
        self._run_selected_lifecycle("START", "start_worker")

    def stop_selected(self) -> None:
        self._run_selected_lifecycle("STOP", "stop_worker")

    def restart_selected(self) -> None:
        self._run_selected_lifecycle("RESTART", "restart_worker")

    def open_runtime_setup(self) -> tk.Toplevel | None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return None
        worker_setup = getattr(self.service, "worker_setup", None)
        if not callable(worker_setup):
            self._handle_error("RUNTIME_SETUP_NOT_AVAILABLE")
            return None
        try:
            draft = worker_setup(worker_id)
        except RuntimeSetupError as exc:
            self._handle_error(exc.code)
            return None
        except Exception:
            self._handle_error("RUNTIME_SETUP_FAILED")
            return None
        if not isinstance(draft, WorkerSetupDraft):
            self._handle_error("RUNTIME_SETUP_RESULT_INVALID")
            return None

        self._setup_draft = draft
        dialog = tk.Toplevel(self.root)
        dialog.title(f"A-Conductor — Runtime Setup — {worker_id}")
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text=f"> RUNTIME SETUP  {worker_id}  {'CONFIGURED' if draft.configured else 'UNCONFIGURED'}",
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        fields = (
            ("instance_root", "Instance root", draft.instance_root),
            ("serena_home", "SERENA_HOME", draft.serena_home),
            ("run_dir", "Run directory", draft.run_dir),
            ("log_dir", "Log directory", draft.log_dir),
            ("health_host", "Health host", draft.health_host),
            ("health_port", "Health port", str(draft.health_port)),
            ("runtime_executable", "Runtime executable", draft.runtime_executable_ref),
            ("profile_template", "Profile template", draft.profile_template_ref),
            ("tunnel_reference_id", "Tunnel ref ID", draft.tunnel_binding_ref or ""),
            ("tunnel_reference_file", "Tunnel ref file", draft.reference_file_path or ""),
            ("tunnel_reference_root", "Tunnel ref allowed root", draft.reference_allowed_root or ""),
            ("serena_config_source", "Serena config source", ""),
        )
        self._setup_entries = {}
        for row_index, (key, label, value) in enumerate(fields, start=1):
            tk.Label(
                frame,
                text=label,
                bg=self.theme.panel,
                fg=self.theme.muted,
                font=(self.theme.monospace_font, 9),
                anchor="w",
            ).grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=2)
            entry = ttk.Entry(frame, width=72)
            entry.insert(0, value)
            entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", pady=2)
            self._setup_entries[key] = entry

        button_row = len(fields) + 1
        self._button(frame, "Save", lambda: self.save_runtime_setup(dialog)).grid(
            row=button_row, column=0, sticky="w", pady=(12, 0)
        )
        self._button(frame, "Capture Exact Git", self.capture_exact_identity).grid(
            row=button_row, column=1, sticky="w", pady=(12, 0)
        )
        self._button(frame, "No Git", self.save_no_git_identity).grid(
            row=button_row, column=2, sticky="w", pady=(12, 0)
        )
        return dialog

    def save_runtime_setup(self, dialog: tk.Toplevel | None = None) -> None:
        draft = self._setup_draft
        save = getattr(self.service, "save_worker_setup", None)
        if draft is None or not callable(save):
            self._handle_error("RUNTIME_SETUP_NOT_AVAILABLE")
            return
        try:
            health_port = int(self._setup_entries["health_port"].get().strip())
        except (KeyError, ValueError):
            self._handle_error("HEALTH_PORT_INVALID")
            return

        def value(key: str) -> str:
            return self._setup_entries[key].get().strip()

        updated = WorkerSetupDraft(
            worker_id=draft.worker_id,
            configured=draft.configured,
            instance_root=value("instance_root"),
            serena_home=value("serena_home"),
            run_dir=value("run_dir"),
            log_dir=value("log_dir"),
            health_host=value("health_host"),
            health_port=health_port,
            runtime_executable_ref=value("runtime_executable"),
            profile_template_ref=value("profile_template"),
            tunnel_binding_ref=value("tunnel_reference_id") or None,
            reference_file_path=value("tunnel_reference_file") or None,
            reference_allowed_root=value("tunnel_reference_root") or None,
            startup_timeout_seconds=draft.startup_timeout_seconds,
            stop_timeout_seconds=draft.stop_timeout_seconds,
        )
        source = value("serena_config_source") or None
        try:
            saved = save(updated, serena_config_source=source)
        except RuntimeSetupError as exc:
            self._handle_error(exc.code)
            return
        except Exception:
            self._handle_error("RUNTIME_SETUP_SAVE_FAILED")
            return
        if not isinstance(saved, WorkerSetupDraft):
            self._handle_error("RUNTIME_SETUP_RESULT_INVALID")
            return
        self._setup_draft = saved
        self.log_activity(f"Setup        {saved.worker_id} SAVED")
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
        self.refresh()

    def capture_exact_identity(self) -> None:
        self._run_identity_action("EXACT", "capture_exact_project_identity")

    def save_no_git_identity(self) -> None:
        self._run_identity_action("NO_GIT", "save_no_git_project_identity")

    def _run_identity_action(self, label: str, method_name: str) -> None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return
        command = getattr(self.service, method_name, None)
        if not callable(command):
            self._handle_error("RUNTIME_SETUP_NOT_AVAILABLE")
            return
        try:
            command(worker_id)
        except RuntimeSetupError as exc:
            self._handle_error(exc.code)
            return
        except Exception:
            self._handle_error("PROJECT_IDENTITY_SAVE_FAILED")
            return
        self.log_activity(f"Identity     {worker_id} {label}")
        self._update_lifecycle_buttons()

    def _handle_error(self, code: str) -> None:
        self.log_activity(f"ERROR        {code}")
        self._error_handler(code)

    def _show_error(self, code: str) -> None:
        messagebox.showerror("A-Conductor", code, parent=self.root)

    def log_activity(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.activity_text.configure(state="normal")
        self.activity_text.insert("end", f"{stamp}  {text}\n")
        self.activity_text.see("end")
        self.activity_text.configure(state="disabled")

    def _on_palette_shortcut(self, _event=None):
        self.open_command_palette()
        return "break"

    def open_command_palette(self) -> tk.Toplevel:
        palette = tk.Toplevel(self.root)
        palette.title("A-Conductor — Command Palette")
        palette.configure(bg=self.theme.panel)
        palette.transient(self.root)
        palette.resizable(False, False)
        frame = tk.Frame(palette, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text="> COMMAND PALETTE",
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 11, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        commands = (
            ("Add Project", self.add_project),
            ("Assign Selected", self.assign_selected),
            ("Release Worker", self.release_selected),
            ("Runtime Setup", self.open_runtime_setup),
            ("Worker Config", self.open_worker_config),
            ("Start Worker", self.start_selected),
            ("Stop Worker", self.stop_selected),
            ("Restart Worker", self.restart_selected),
            ("Refresh", self.refresh),
        )
        for label, command in commands:
            button = ttk.Button(
                frame,
                text=label,
                style="AConductor.TButton",
                command=lambda fn=command: self._run_palette_command(palette, fn),
            )
            button.pack(fill="x", pady=2)
        palette.bind("<Escape>", lambda _event: palette.destroy())
        palette.grab_set()
        return palette

    @staticmethod
    def _run_palette_command(palette: tk.Toplevel, command) -> None:
        palette.destroy()
        command()

    def open_worker_config(self) -> tk.Toplevel | None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return None
        load = getattr(self.service, "worker_settings", None)
        save = getattr(self.service, "save_worker_settings", None)
        if not callable(load) or not callable(save):
            self._handle_error("SETTINGS_NOT_AVAILABLE")
            return None
        try:
            settings = load(worker_id)
        except Exception:
            self._handle_error("SETTINGS_LOAD_FAILED")
            return None
        if not isinstance(settings, WorkerSerenaSettings):
            self._handle_error("SETTINGS_RESULT_INVALID")
            return None

        row = self._selected_worker_row()
        bound_project = row.project_root_path if row is not None else ""

        dialog = tk.Toplevel(self.root)
        dialog.title(f"A-Conductor — Worker Config — {worker_id}")
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text=f"> WORKER CONFIG  {worker_id}",
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        self._config_worker_id = worker_id
        self._config_entries: dict[str, ttk.Entry | ttk.Combobox] = {}

        backend_box = ttk.Combobox(
            frame,
            values=[backend.value for backend in LanguageBackend],
            state="readonly",
            width=30,
        )
        backend_box.set(settings.language_backend.value)
        backend_box.grid(row=1, column=1, sticky="ew", pady=2)
        self._config_entries["language_backend"] = backend_box
        tk.Label(
            frame,
            text="Language backend",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        ).grid(row=1, column=0, sticky="w", padx=(0, 10))

        fields = (
            ("tool_timeout", "Tool timeout (s)", str(settings.tool_timeout)),
            ("excluded_tools", "Excluded tools (comma)", ",".join(settings.excluded_tools)),
            ("included_optional_tools", "Included optional tools", ",".join(settings.included_optional_tools)),
            ("fixed_tools", "Fixed tools (exclusive)", ",".join(settings.fixed_tools)),
            ("base_modes", "Base modes (comma)", ",".join(settings.base_modes)),
            ("bound_project", "Bound project (via Assign)", bound_project or ""),
        )
        for row_index, (key, label, value) in enumerate(fields, start=2):
            tk.Label(
                frame,
                text=label,
                bg=self.theme.panel,
                fg=self.theme.muted,
                font=(self.theme.monospace_font, 9),
            ).grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=2)
            entry = ttk.Entry(frame, width=56)
            entry.insert(0, value)
            entry.grid(row=row_index, column=1, sticky="ew", pady=2)
            if key == "bound_project":
                entry.state(["disabled"])
            self._config_entries[key] = entry

        self._config_status = tk.Label(
            frame,
            text="Values apply on next worker start.",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        )
        self._config_status.grid(row=len(fields) + 2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        button_row = len(fields) + 3
        self._button(frame, "Save", lambda: self.save_worker_config(dialog)).grid(
            row=button_row, column=0, sticky="w", pady=(12, 0)
        )
        self._button(frame, "Cancel", lambda: dialog.destroy() if dialog.winfo_exists() else None).grid(
            row=button_row, column=1, sticky="w", pady=(12, 0)
        )
        return dialog

    @staticmethod
    def _csv_field(entry) -> tuple[str, ...]:
        return tuple(part.strip() for part in entry.get().split(",") if part.strip())

    def save_worker_config(self, dialog: tk.Toplevel | None = None) -> None:
        worker_id = getattr(self, "_config_worker_id", None)
        entries = getattr(self, "_config_entries", None)
        save = getattr(self.service, "save_worker_settings", None)
        if worker_id is None or not entries or not callable(save):
            self._handle_error("SETTINGS_NOT_AVAILABLE")
            return

        try:
            backend = LanguageBackend(str(entries["language_backend"].get()).strip())
        except ValueError:
            self._handle_error("SETTINGS_LANGUAGE_BACKEND_INVALID")
            return
        try:
            timeout = int(str(entries["tool_timeout"].get()).strip())
        except ValueError:
            self._handle_error("SETTINGS_TOOL_TIMEOUT_INVALID")
            return

        try:
            settings = WorkerSerenaSettings(
                worker_id=worker_id,
                language_backend=backend,
                excluded_tools=self._csv_field(entries["excluded_tools"]),
                included_optional_tools=self._csv_field(entries["included_optional_tools"]),
                fixed_tools=self._csv_field(entries["fixed_tools"]),
                base_modes=self._csv_field(entries["base_modes"]),
                tool_timeout=timeout,
            )
        except ValueError as exc:
            status = getattr(self, "_config_status", None)
            if status is not None and status.winfo_exists():
                status.configure(text=f"ERROR  {exc}", fg=self.theme.error)
            self._handle_error("SETTINGS_INVALID")
            return

        try:
            saved = save(settings)
        except Exception:
            self._handle_error("SETTINGS_SAVE_FAILED")
            return
        if not isinstance(saved, WorkerSerenaSettings):
            self._handle_error("SETTINGS_RESULT_INVALID")
            return
        self.log_activity(f"Config       {saved.worker_id} SAVED (applies on next start)")
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
