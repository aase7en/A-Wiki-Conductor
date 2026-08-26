from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
import inspect
import time
import tkinter as tk

import pytest

from a_conductor.control_center import ControlCenterSnapshot
from a_conductor.desktop_ui import AConductorDesktopApp
from a_conductor.domain import Project


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


class ManualExecutor:
    def __init__(self) -> None:
        self.futures: list[Future] = []
        self.calls: list[tuple[object, tuple, dict]] = []
        self.shutdown_calls: list[tuple[bool, bool]] = []

    def submit(self, fn, *args, **kwargs):
        future = Future()
        future.set_running_or_notify_cancel()
        self.futures.append(future)
        self.calls.append((fn, args, kwargs))
        return future

    def shutdown(self, wait=False, cancel_futures=False):
        self.shutdown_calls.append((wait, cancel_futures))


class FakeService:
    def __init__(self, projects: tuple[Project, ...]) -> None:
        self._snapshot = ControlCenterSnapshot(projects=projects, workers=(), online=True)

    def snapshot(self) -> ControlCenterSnapshot:
        return self._snapshot


def test_app_exposes_dedicated_disk_executor_injection_seam() -> None:
    assert "disk_executor" in inspect.signature(AConductorDesktopApp.__init__).parameters


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


def _select_project(app: AConductorDesktopApp, project_id: str) -> None:
    app.project_list.selection_set(project_id)
    app.project_list.focus(project_id)


def _wait_until(root: tk.Tk, predicate, *, timeout_seconds: float = 0.5) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        root.update()
        if predicate():
            return
        time.sleep(0.005)
    root.update()
    assert predicate(), "condition did not become true before timeout"


def test_project_disk_scan_is_submitted_without_running_on_ui_thread(root, tmp_path: Path) -> None:
    project = Project("p1", "One", str(tmp_path / "one"))
    disk_executor = ManualExecutor()
    app = AConductorDesktopApp(
        root,
        service=FakeService((project,)),
        background_executor=ImmediateExecutor(),
        disk_executor=disk_executor,
    )

    _select_project(app, "p1")
    app._refresh_project_disk()

    assert app.overview_disk_value.cget("text") == "…"
    assert len(disk_executor.calls) == 1
    assert not disk_executor.futures[0].done()


def test_stale_disk_result_cannot_overwrite_new_selection(root, tmp_path: Path) -> None:
    projects = (
        Project("p1", "One", str(tmp_path / "one")),
        Project("p2", "Two", str(tmp_path / "two")),
    )
    disk_executor = ManualExecutor()
    app = AConductorDesktopApp(
        root,
        service=FakeService(projects),
        background_executor=ImmediateExecutor(),
        disk_executor=disk_executor,
    )

    _select_project(app, "p1")
    app._refresh_project_disk()
    first = disk_executor.futures[0]

    _select_project(app, "p2")
    app._refresh_project_disk()
    second = disk_executor.futures[1]

    first.set_result("99.0 GB")
    root.update()
    assert app.overview_disk_value.cget("text") != "99.0 GB"

    second.set_result("2.0 GB")
    _wait_until(root, lambda: app.overview_disk_value.cget("text") == "2.0 GB")


def test_completed_project_disk_value_is_cached(root, tmp_path: Path) -> None:
    project = Project("p1", "One", str(tmp_path / "one"))
    disk_executor = ManualExecutor()
    app = AConductorDesktopApp(
        root,
        service=FakeService((project,)),
        background_executor=ImmediateExecutor(),
        disk_executor=disk_executor,
    )

    _select_project(app, "p1")
    app._refresh_project_disk()
    disk_executor.futures[0].set_result("3.0 GB")
    _wait_until(root, lambda: app.overview_disk_value.cget("text") == "3.0 GB")

    app._refresh_project_disk()
    assert app.overview_disk_value.cget("text") == "3.0 GB"
    assert len(disk_executor.calls) == 1


def test_shutdown_cancels_disk_scan_and_owned_executor(root, tmp_path: Path) -> None:
    project = Project("p1", "One", str(tmp_path / "one"))
    disk_executor = ManualExecutor()
    app = AConductorDesktopApp(
        root,
        service=FakeService((project,)),
        background_executor=ImmediateExecutor(),
        disk_executor=disk_executor,
    )

    _select_project(app, "p1")
    app._refresh_project_disk()
    cancel_event = app._project_disk_cancel_event
    assert cancel_event is not None and not cancel_event.is_set()

    app._shutdown_ui_resources()

    assert cancel_event.is_set()
    # Injected executors are not owned by the app and must not be shut down.
    assert disk_executor.shutdown_calls == []
