"""Tkinter desktop adapter for the A-Conductor Control Center.

The desktop layer consumes only the application-service snapshot/actions. It
contains no process, tunnel, Git, or persistence implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .control_center import ControlCenterError, ControlCenterSnapshot
from .domain import WorkerState


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
    ) -> None:
        self.root = root
        self.service = service
        self.theme = theme or DesktopTheme()
        self._directory_picker = directory_picker or filedialog.askdirectory
        self._error_handler = error_handler or self._show_error
        self._project_ids: list[str] = []
        self._worker_ids: dict[str, str] = {}

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
        self.start_button = self._button(actions, "Start", self._lifecycle_not_wired)
        self.stop_button = self._button(actions, "Stop", self._lifecycle_not_wired)
        self.restart_button = self._button(actions, "Restart", self._lifecycle_not_wired)
        for index, button in enumerate(
            (
                self.add_button,
                self.assign_button,
                self.release_button,
                self.refresh_button,
                self.start_button,
                self.stop_button,
                self.restart_button,
            )
        ):
            button.grid(row=0, column=index, padx=(0, 6))
        self.start_button.state(["disabled"])
        self.stop_button.state(["disabled"])
        self.restart_button.state(["disabled"])

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

    def _lifecycle_not_wired(self) -> None:
        self._handle_error("LIFECYCLE_NOT_WIRED")

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
