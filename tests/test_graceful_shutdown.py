"""Closing the app stops every running connector and cleans up."""

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


def make_service(tmp_path: Path):
    from a_conductor.desktop_control import DesktopControlService

    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    return DesktopControlService.open(tmp_path / "cc.sqlite", instances_root=instances_root)


def test_stop_all_instances_stops_each_running_one(tmp_path: Path, monkeypatch) -> None:
    import a_conductor.local_instances as local_instances
    from a_conductor.local_instances import InstanceHealthState

    service = make_service(tmp_path)
    monkeypatch.setattr(
        local_instances, "instance_health_state", lambda _i: InstanceHealthState.READY
    )
    stopped: list[str] = []

    def fake_stop(name, action):
        assert action == "stop"
        stopped.append(name)

    monkeypatch.setattr(service, "instance_action", fake_stop)
    monkeypatch.setattr(
        service,
        "instances",
        lambda: tuple(
            type("I", (), {"name": f"Sunday-Worker-{n}", "instance_root": tmp_path / f"w{n}"})()
            for n in (1, 2, 3)
        ),
    )

    results = service.stop_all_instances()

    assert stopped == ["Sunday-Worker-1", "Sunday-Worker-2", "Sunday-Worker-3"]
    assert [name for name, _ok in results] == [
        "Sunday-Worker-1",
        "Sunday-Worker-2",
        "Sunday-Worker-3",
    ]


def test_stop_all_skips_stopped_instances(tmp_path: Path, monkeypatch) -> None:
    import a_conductor.local_instances as local_instances
    from a_conductor.local_instances import InstanceHealthState

    service = make_service(tmp_path)
    states = {"Sunday-Worker-1": InstanceHealthState.READY, "Sunday-Worker-2": InstanceHealthState.STOPPED}
    monkeypatch.setattr(
        local_instances,
        "instance_health_state",
        lambda instance: states[instance.name],
    )
    stopped: list[str] = []
    monkeypatch.setattr(service, "instance_action", lambda name, action: stopped.append(name))
    monkeypatch.setattr(service, "instances", lambda: tuple(
        type("I", (), {"name": name, "instance_root": tmp_path / name})()
        for name in states
    ))

    results = service.stop_all_instances()

    assert stopped == ["Sunday-Worker-1"]
    assert results == [("Sunday-Worker-1", True)]


def test_stop_all_continues_after_failure(tmp_path: Path, monkeypatch) -> None:
    import a_conductor.local_instances as local_instances
    from a_conductor.local_instances import InstanceHealthState

    service = make_service(tmp_path)
    monkeypatch.setattr(
        local_instances, "instance_health_state", lambda _i: InstanceHealthState.READY
    )

    def flaky_stop(name, action):
        if name == "Sunday-Worker-2":
            raise RuntimeError("boom")

    monkeypatch.setattr(service, "instance_action", flaky_stop)
    monkeypatch.setattr(service, "instances", lambda: tuple(
        type("I", (), {"name": f"Sunday-Worker-{n}", "instance_root": tmp_path / f"w{n}"})()
        for n in (1, 2, 3)
    ))

    results = service.stop_all_instances()
    assert dict(results) == {
        "Sunday-Worker-1": True,
        "Sunday-Worker-2": False,
        "Sunday-Worker-3": True,
    }


def make_app(root, service):
    from a_conductor.desktop_ui import AConductorDesktopApp

    return AConductorDesktopApp(root, service=service)


def test_close_request_stops_all_then_destroys(root, tmp_path: Path, monkeypatch) -> None:
    service = make_service(tmp_path)
    app = make_app(root, service)
    calls: list[str] = []
    monkeypatch.setattr(service, "stop_all_instances", lambda: calls.append("stop_all") or [])
    monkeypatch.setattr(app.root, "destroy", lambda: calls.append("destroy"))

    app._on_close_request()

    assert calls == ["stop_all", "destroy"]


def test_close_request_without_stop_preference_skips_stopping(
    root, tmp_path: Path, monkeypatch
) -> None:
    service = make_service(tmp_path)
    service.set_preference("shutdown_stops_instances", False)
    app = make_app(root, service)
    calls: list[str] = []
    monkeypatch.setattr(service, "stop_all_instances", lambda: calls.append("stop_all") or [])
    monkeypatch.setattr(app.root, "destroy", lambda: calls.append("destroy"))

    app._on_close_request()

    assert calls == ["destroy"]


def test_close_request_stops_ui_callbacks_logo_and_owned_executor(
    root, tmp_path: Path, monkeypatch
) -> None:
    service = make_service(tmp_path)
    service.set_preference("shutdown_stops_instances", False)
    app = make_app(root, service)
    logo_calls: list[str] = []
    shutdown_calls: list[tuple[bool, bool]] = []

    class Logo:
        def destroy(self) -> None:
            logo_calls.append("destroy")

    app._logo = Logo()
    monkeypatch.setattr(
        app._background_executor,
        "shutdown",
        lambda *, wait, cancel_futures: shutdown_calls.append((wait, cancel_futures)),
    )
    monkeypatch.setattr(app.root, "destroy", lambda: None)

    app._on_close_request()

    assert logo_calls == ["destroy"]
    assert shutdown_calls == [(False, True)]
    assert app._status_pulse_after_id is None
    assert app._monitor_tick_after_id is None
    assert app._monitor_poll_after_id is None
    assert app._system_metric_after_id is None
    assert not app._scheduled_after_ids


def test_direct_root_destroy_cancels_every_scheduled_ui_callback(tmp_path: Path) -> None:
    """Destroy-before-idle must not leave Tcl callbacks targeting dead widgets."""
    import tkinter as tk

    service = make_service(tmp_path)
    root = tk.Tk()
    root.withdraw()
    app = make_app(root, service)

    root.destroy()

    assert app._scheduled_after_ids == set()
    assert root.tk.call("after", "info") == ""
