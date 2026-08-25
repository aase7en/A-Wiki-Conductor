"""MONITOR panel: per-instance runtime status without any CMD window."""

from __future__ import annotations

from concurrent.futures import Future
from datetime import datetime
from pathlib import Path

import pytest

from a_conductor.instance_monitor import (
    latest_log_path,
    monitor_report,
    process_memory_mb,
    read_pid,
    scan_errors,
    tail_lines,
)


def make_instance(root: Path, *, slug: str = "sunday-worker-1", day: str | None = None) -> Path:
    instance = root / slug
    (instance / "logs").mkdir(parents=True)
    (instance / "run").mkdir()
    (instance / "config").mkdir()
    (instance / "instance.ps1").write_text(
        "\n".join(
            [
                "# Sunday-Worker-1 instance configuration",
                "$InstanceName = 'Sunday-Worker-1'",
                "$ProjectPath = 'A:\\GitHub\\demo'",
                f"$SerenaHome = '{instance / 'serena-home'}'",
                "$HealthListenAddress = '127.0.0.1:18901'",
                "$TunnelProfileName = 'serena-sunday-worker-1'",
                "$TunnelClientPath = 'C:\\AI\\tunnel\\tunnel-client.exe'",
                "$LegacySecretPath = 'C:\\AI\\tunnel\\secret.dpapi'",
            ]
        ),
        encoding="utf-8",
    )
    day = day or datetime.now().strftime("%Y%m%d")
    (instance / "logs" / f"{slug}-{day}.log").write_text(
        "line1\nline2 ERROR boom\nline3\n", encoding="utf-8"
    )
    return instance


def test_read_pid_parses_run_file(tmp_path: Path) -> None:
    instance = make_instance(tmp_path)
    assert read_pid(instance) is None
    (instance / "run" / "tunnel-client.pid").write_text("4242\n", encoding="utf-8")
    assert read_pid(instance) == 4242


def test_latest_log_path_prefers_today(tmp_path: Path) -> None:
    instance = make_instance(tmp_path, day="20260101")
    (instance / "logs" / "sunday-worker-1-20260102.log").write_text("x", encoding="utf-8")
    found = latest_log_path(instance)
    assert found is not None and found.name.endswith("20260102.log")


def test_tail_lines_returns_last_n(tmp_path: Path) -> None:
    instance = make_instance(tmp_path)
    log = latest_log_path(instance)
    assert log is not None
    lines = tail_lines(log, 2)
    assert lines == ["line2 ERROR boom", "line3"]


def test_scan_errors_flags_error_lines() -> None:
    assert scan_errors(["ok", "x ERROR bad", "TUNNEL_START_FAILED: y", "fine"]) == [
        "x ERROR bad",
        "TUNNEL_START_FAILED: y",
    ]


def test_process_memory_mb_with_injected_runner() -> None:
    def fake_runner(argv):
        return 0, "123456789\n", ""

    assert process_memory_mb(1, runner=fake_runner) == pytest.approx(117.74, abs=0.1)


def test_monitor_report_combines_everything(tmp_path: Path) -> None:
    instance = make_instance(tmp_path)
    (instance / "run" / "tunnel-client.pid").write_text("99\n", encoding="utf-8")
    report = monitor_report(instance, state="READY")
    assert report["state"] == "READY"
    assert report["pid"] == 99
    assert report["errors"] == ["line2 ERROR boom"]
    assert report["tail"] == ["line1", "line2 ERROR boom", "line3"]
    assert report["log_file"].endswith(".log")


# --- UI ------------------------------------------------------------------


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
    from test_instance_manage import ImmediateExecutor

    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp
    from a_conductor.local_instances import InstanceHealthState, LocalInstance

    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    instance_root = instances_root / "sunday-worker-1"
    (instance_root / "logs").mkdir(parents=True)
    (instance_root / "run").mkdir()
    (instance_root / "config").mkdir()
    (instance_root / "logs" / "sunday-worker-1-20260101.log").write_text(
        "line1\nline2 ERROR boom\nline3\n", encoding="utf-8"
    )
    instance = LocalInstance(
        name="Sunday-Worker-1",
        project_path=str(tmp_path / "project"),
        health_address="127.0.0.1:18901",
        instance_root=instance_root,
        tunnel_configured=False,
    )
    service = DesktopControlService.open(tmp_path / "ui.sqlite", instances_root=instances_root)
    service.instances = lambda: (instance,)
    service.instance_states = lambda: ((instance, InstanceHealthState.STOPPED),)
    return AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )


def test_monitor_panel_exists_and_shows_hint(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    assert app.monitor_text is not None
    content = app.monitor_text.get("1.0", "end")
    assert "MONITOR" in content


def test_monitor_updates_on_selection(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    app.refresh_instances()
    root.update()
    children = app.instance_tree.get_children()
    assert children
    app.instance_tree.selection_clear()
    app.instance_tree.selection_set(children[0])
    app._update_monitor_now()
    content = app.monitor_text.get("1.0", "end")
    assert "Sunday-Worker-1" in content


class PendingExecutor:
    def __init__(self) -> None:
        self.submissions: list[tuple] = []

    def submit(self, fn, *args, **kwargs):
        future = Future()
        self.submissions.append((fn, args, kwargs, future))
        return future

    def shutdown(self, wait=False, cancel_futures=False):
        return None


def test_monitor_refresh_coalesces_while_one_sample_is_in_flight(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    app.refresh_instances()
    root.update()
    item = app.instance_tree.get_children()[0]
    app.instance_tree.selection_set(item)
    pending = PendingExecutor()
    app._background_executor = pending

    app._refresh_monitor_async()
    app._refresh_monitor_async()
    app._refresh_monitor_async()

    assert len(pending.submissions) == 1
    assert app._monitor_future is pending.submissions[0][3]
    assert app._monitor_poll_after_id is not None


def test_instance_refresh_replaces_monitor_cache_and_preserves_ready_total_header(
    root, tmp_path: Path
) -> None:
    app = make_app(root, tmp_path)
    app._monitor_instances["stale-instance"] = object()

    app.refresh_instances()
    root.update()
    app.refresh()

    assert set(app._monitor_instances) == {"Sunday-Worker-1"}
    assert "CONNECTORS 0/1" in str(app.header_runtime_label.cget("text"))
