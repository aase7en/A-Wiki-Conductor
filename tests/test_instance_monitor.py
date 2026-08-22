"""MONITOR panel: per-instance runtime status without any CMD window."""

from __future__ import annotations

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
                "$HealthListenAddress = '127.0.0.1:18011'",
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

    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    make_instance(instances_root)
    service = DesktopControlService.open(tmp_path / "ui.sqlite", instances_root=instances_root)
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
