"""WO-P1-068 — connector clarity & safety after the Rescan incident.

Covers: close-time confirm before stopping RUNNING connectors, Rescan
result summary, live 15s connectors-state refresh, masked tunnel-ID
suffix in the table and the Edit dialog, and discovery-level suffix
extraction. (Incident: chats died at app close; Rescan only revealed
it — see WO-P1-068 for the full write-up.)
"""

from __future__ import annotations

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


def make_app(root, tmp_path: Path, state="READY", tunnel_suffix: str = ""):
    from test_instance_manage import ImmediateExecutor

    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp
    from a_conductor.local_instances import InstanceHealthState, LocalInstance

    instances_root = tmp_path / "instances"
    instances_root.mkdir(exist_ok=True)
    instance_root = instances_root / "sunday-worker-1"
    (instance_root / "logs").mkdir(parents=True, exist_ok=True)
    instance = LocalInstance(
        name="Sunday-Worker-1",
        project_path=str(tmp_path / "project"),
        health_address="127.0.0.1:18901",
        instance_root=instance_root,
        tunnel_configured=bool(tunnel_suffix),
        tunnel_suffix=tunnel_suffix,
    )
    service = DesktopControlService.open(tmp_path / "ui.sqlite", instances_root=instances_root)
    service.instances = lambda: (instance,)
    states = {
        "READY": InstanceHealthState.READY,
        "STOPPED": InstanceHealthState.STOPPED,
    }
    service.instance_states = lambda: ((instance, states[state]),)
    # refresh_instances prefers the cancellable variant; route it through the
    # stub so tests do not probe live loopback ports.
    service.instance_states_cancellable = lambda cancel_check: service.instance_states()
    return AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )


# --- 1+2: close-time confirm -------------------------------------------------


def test_close_asks_before_stopping_running_connectors(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path, state="READY")
    app.refresh_instances()
    root.update()

    asked: list[str] = []
    stopped: list[str] = []
    app._confirm = lambda message: (asked.append(message), False)[1]
    app.service.stop_all_instances = lambda: stopped.append("called") or []
    app.service.get_preference = lambda key: True if key == "shutdown_stops_instances" else None

    app._on_close_request()

    assert len(asked) == 1
    assert "1" in asked[0]  # mentions the RUNNING count
    assert stopped == []  # user declined -> nothing stopped


def test_close_without_running_connectors_does_not_ask(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path, state="STOPPED")
    app.refresh_instances()
    root.update()

    asked: list[str] = []
    stopped: list[str] = []
    app._confirm = lambda message: (asked.append(message), True)[1]
    app.service.stop_all_instances = lambda: stopped.append("called") or []
    app.service.get_preference = lambda key: True if key == "shutdown_stops_instances" else None

    app._on_close_request()

    assert asked == []  # nothing READY -> silent path unchanged
    assert stopped == ["called"]


# --- 2: rescan summary -------------------------------------------------------


def test_rescan_logs_found_summary(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path, state="READY")
    lines: list[str] = []
    app.log_activity = lambda text: lines.append(str(text))

    app.rescan_instances()
    root.update()

    joined = "\n".join(lines)
    assert "RESCAN" in joined
    assert "พบ 1 ตัวเชื่อม" in joined
    assert "1 READY" in joined and "0 STOPPED" in joined


# --- 4: masked tunnel suffix in the table ------------------------------------


def test_instance_table_shows_masked_tunnel_suffix(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path, state="READY", tunnel_suffix="e3f1")
    app.refresh_instances()
    root.update()

    row = app.instance_tree.get_children()[0]
    values = app.instance_tree.item(row, "values")
    assert values[4] == "...e3f1"  # TUNNEL column


def test_instance_table_shows_dash_without_tunnel(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path, state="STOPPED", tunnel_suffix="")
    app.refresh_instances()
    root.update()

    row = app.instance_tree.get_children()[0]
    values = app.instance_tree.item(row, "values")
    assert values[4] == "-"


# --- 5: discovery-level suffix extraction ------------------------------------


def test_discovery_reads_tunnel_suffix(tmp_path: Path) -> None:
    from a_conductor.local_instances import discover_local_instances

    tunnel_id = "tunnel_" + "ab12" * 8  # ends with ab12
    instance_root = tmp_path / "instances" / "sunday-worker-9"
    (instance_root / "config").mkdir(parents=True)
    (instance_root / "run").mkdir()
    (instance_root / "config" / "tunnel-id.txt").write_text(tunnel_id + "\n", encoding="utf-8")
    (instance_root / "instance.ps1").write_text(
        "\n".join(
            [
                "$InstanceName = 'Sunday-Worker-9'",
                "$ProjectPath = 'A:\\proj'",
                "$HealthListenAddress = '127.0.0.1:18909'",
            ]
        ),
        encoding="utf-8",
    )

    instances = discover_local_instances(tmp_path / "instances")
    assert len(instances) == 1
    assert instances[0].tunnel_configured is True
    assert instances[0].tunnel_suffix == "ab12"


# --- 6: edit dialog shows the current tunnel masked ---------------------------


def test_edit_connector_dialog_shows_current_tunnel_masked(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path, state="READY", tunnel_suffix="e3f1")
    row = app.instance_tree.insert(
        "", "end", values=("Sunday-Worker-1", "18901", "READY", "p", "...e3f1", "-", "Edit")
    )
    app._instance_rows["Sunday-Worker-1"] = row
    instance = next(iter(app.service.instances()))
    app._monitor_instances["Sunday-Worker-1"] = instance
    app.instance_tree.selection_set(row)

    dialog = app.open_edit_instance_dialog()
    try:
        assert dialog is not None
        hint = str(app._edit_tunnel_current.cget("text"))
        assert "...e3f1" in hint
        assert "tunnel_" not in hint  # never the full ID
    finally:
        dialog.destroy()


# --- 3: periodic live refresh -------------------------------------------------


def test_periodic_instance_refresh_scheduled_and_cancelled_on_close(
    root, tmp_path: Path
) -> None:
    app = make_app(root, tmp_path, state="READY")
    app.start_background_operations()
    root.update()
    assert app._instance_refresh_after_id is not None  # scheduled at startup

    app._confirm = lambda message: True
    app._on_close_request()
    assert app._instance_refresh_after_id is None  # cancelled cleanly
