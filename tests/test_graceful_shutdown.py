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
    from types import SimpleNamespace

    import a_conductor.local_instances as local_instances
    from a_conductor.local_instances import InstanceHealthState, InstanceResultCode

    service = make_service(tmp_path)
    monkeypatch.setattr(
        local_instances, "instance_health_state", lambda _i: InstanceHealthState.READY
    )
    stopped: list[str] = []

    def fake_stop(name, action):
        assert action == "stop"
        stopped.append(name)
        return SimpleNamespace(result_code=InstanceResultCode.STOPPED)

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
    from types import SimpleNamespace

    import a_conductor.local_instances as local_instances
    from a_conductor.local_instances import InstanceHealthState, InstanceResultCode

    service = make_service(tmp_path)
    states = {"Sunday-Worker-1": InstanceHealthState.READY, "Sunday-Worker-2": InstanceHealthState.STOPPED}
    monkeypatch.setattr(
        local_instances,
        "instance_health_state",
        lambda instance: states[instance.name],
    )
    stopped: list[str] = []
    monkeypatch.setattr(
        service,
        "instance_action",
        lambda name, action: (
            stopped.append(name)
            or SimpleNamespace(result_code=InstanceResultCode.STOPPED)
        ),
    )
    monkeypatch.setattr(service, "instances", lambda: tuple(
        type("I", (), {"name": name, "instance_root": tmp_path / name})()
        for name in states
    ))

    results = service.stop_all_instances()

    assert stopped == ["Sunday-Worker-1"]
    assert results == [("Sunday-Worker-1", True)]


def test_stop_all_continues_after_failure(tmp_path: Path, monkeypatch) -> None:
    from types import SimpleNamespace

    import a_conductor.local_instances as local_instances
    from a_conductor.local_instances import InstanceHealthState, InstanceResultCode

    service = make_service(tmp_path)
    monkeypatch.setattr(
        local_instances, "instance_health_state", lambda _i: InstanceHealthState.READY
    )

    def flaky_stop(name, action):
        if name == "Sunday-Worker-2":
            raise RuntimeError("boom")
        return SimpleNamespace(result_code=InstanceResultCode.STOPPED)

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


def test_stop_all_reports_failed_stop_outcome_truthfully(
    tmp_path: Path, monkeypatch
) -> None:
    from types import SimpleNamespace

    import a_conductor.local_instances as local_instances
    from a_conductor.local_instances import InstanceHealthState, InstanceResultCode

    service = make_service(tmp_path)
    monkeypatch.setattr(
        local_instances, "instance_health_state", lambda _i: InstanceHealthState.READY
    )
    monkeypatch.setattr(
        service,
        "instances",
        lambda: (
            SimpleNamespace(name="Sunday-Worker-1", instance_root=tmp_path / "w1"),
        ),
    )
    monkeypatch.setattr(
        service,
        "instance_action",
        lambda name, action: SimpleNamespace(
            result_code=InstanceResultCode.STOP_FAILED
        ),
    )

    assert service.stop_all_instances() == [("Sunday-Worker-1", False)]


@pytest.mark.parametrize(
    "start_result",
    ["START_CANCELLED", "STARTED_NOT_READY"],
)
def test_stop_all_forces_stop_of_launched_unready_start(
    tmp_path: Path, monkeypatch, start_result: str
) -> None:
    import a_conductor.local_instances as local_instances
    from a_conductor.local_instances import (
        InstanceHealthState,
        InstanceOrchestrationOutcome,
        InstanceResultCode,
        LocalInstance,
    )

    service = make_service(tmp_path)
    instance = LocalInstance(
        name="Sunday-Worker-1",
        project_path="A:/GitHub/demo",
        health_address="127.0.0.1:18011",
        instance_root=tmp_path / "instances" / "sunday-worker-1",
    )
    monkeypatch.setattr(service, "instances", lambda: (instance,))
    health_probes: list[str] = []

    def health_state(target):
        health_probes.append(target.name)
        return InstanceHealthState.STOPPED

    monkeypatch.setattr(local_instances, "instance_health_state", health_state)
    forced: list[bool] = []

    class Orchestrator:
        def start(self, target, *, cancel_check=None):
            return InstanceOrchestrationOutcome(
                action="start",
                result_code=InstanceResultCode(start_result),
                process_launched=True,
            )

        def stop(self, target, *, force=False):
            forced.append(force)
            return InstanceOrchestrationOutcome(
                action="stop", result_code=InstanceResultCode.STOPPED
            )

    service._instance_orchestrator = Orchestrator()

    service.instance_action_cancellable(
        instance.name, "start", cancel_check=lambda: True
    )
    results = service.stop_all_instances()

    assert forced == [True]
    assert health_probes == []
    assert results == [(instance.name, True)]


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
    assert app._background_cancel_event.is_set()


def test_close_cooperatively_cancels_inflight_autostart(
    root, tmp_path: Path, monkeypatch
) -> None:
    from threading import Event
    from types import SimpleNamespace

    from a_conductor.local_instances import InstanceResultCode

    service = make_service(tmp_path)
    service.set_preference("shutdown_stops_instances", False)
    monkeypatch.setattr(
        service,
        "autostart_instance_names",
        lambda: ("Sunday-Worker-1",),
    )
    started = Event()
    released = Event()

    def cancellable_action(name, action, *, cancel_check):
        assert (name, action) == ("Sunday-Worker-1", "start")
        started.set()
        assert released.wait(0.01) is False
        while not cancel_check():
            released.wait(0.01)
        released.set()
        return SimpleNamespace(result_code=InstanceResultCode.START_CANCELLED)

    monkeypatch.setattr(
        service,
        "instance_action_cancellable",
        cancellable_action,
        raising=False,
    )
    app = make_app(root, service)

    app._autostart_flagged_instances()
    assert started.wait(1.0)

    app._on_close_request()

    assert released.wait(1.0)
    assert app._background_cancel_event.is_set()


def test_close_waits_for_cancelled_start_before_stopping_connectors(
    root, tmp_path: Path, monkeypatch
) -> None:
    import time
    from threading import Event
    from types import SimpleNamespace

    from a_conductor.local_instances import InstanceResultCode

    service = make_service(tmp_path)
    monkeypatch.setattr(
        service,
        "autostart_instance_names",
        lambda: ("Sunday-Worker-1",),
    )
    started = Event()
    released = Event()

    def cancellable_action(name, action, *, cancel_check):
        started.set()
        while not cancel_check():
            time.sleep(0.005)
        time.sleep(0.2)
        released.set()
        return SimpleNamespace(result_code=InstanceResultCode.START_CANCELLED)

    monkeypatch.setattr(
        service,
        "instance_action_cancellable",
        cancellable_action,
        raising=False,
    )
    stop_observations: list[bool] = []
    monkeypatch.setattr(
        service,
        "stop_all_instances",
        lambda: stop_observations.append(released.is_set()) or [],
    )
    app = make_app(root, service)

    app._autostart_flagged_instances()
    assert started.wait(1.0)

    app._on_close_request()

    assert stop_observations == [True]


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
