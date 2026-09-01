from __future__ import annotations

import tkinter as tk
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace

import pytest

from a_conductor.control_center import ControlCenterSnapshot
from a_conductor.desktop_ui import AConductorDesktopApp
from a_conductor.i18n import get_language, set_language


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


class ControlledExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.futures: list[Future] = []
    def submit(self, fn, *args, **kwargs):
        future = Future()
        self.calls.append((fn, args, kwargs))
        self.futures.append(future)
        return future

    def shutdown(self, wait=False, cancel_futures=False):
        return None


class FakeService:
    def __init__(self, rows=(), error: Exception | None = None) -> None:
        self.rows = tuple(rows)
        self.error = error
        self.provider_calls = 0
        self.preferences = {"supervised": True, "shutdown_stops_instances": True}

    def snapshot(self) -> ControlCenterSnapshot:
        return ControlCenterSnapshot(projects=(), workers=(), online=True)

    def get_preference(self, name: str):
        return self.preferences.get(name)

    def set_preference(self, name: str, value) -> None:
        self.preferences[name] = value

    def provider_operator_rows(self):
        self.provider_calls += 1
        if self.error is not None:
            raise self.error
        return self.rows

class TypedProviderError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def make_row(**overrides):
    data = dict(
        provider_id="glm-primary",
        display_name="GLM 5.3",
        provider_type="anthropic-compatible",
        enabled=True,
        configured=True,
        runtime_ready=True,
        readiness_reason="READY",
        task_authorization="NOT_EVALUATED",
        models=(),
        harness_strategies=(),
        trust_class=SimpleNamespace(value="UNKNOWN"),
        egress_boundary=SimpleNamespace(value="UNKNOWN"),
        max_concurrency=2,
        configuration_generation=7,
        health=SimpleNamespace(value="AVAILABLE"),
        observed_at=None,
        observation_age_seconds=12.5,
        provenance="PROBE",
        latency_ms=123,
        quota=None,
    )
    data.update(overrides)
    return SimpleNamespace(**data)

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


def make_app(root, service, executor):
    return AConductorDesktopApp(
        root,
        service=service,
        background_executor=executor,
        disk_executor=ImmediateExecutor(),
    )


def panel_text(app) -> str:
    widget = app._models_agents_text
    return widget.get("1.0", "end").strip()

def test_models_agents_empty_state_is_explicit(root) -> None:
    service = FakeService()
    app = make_app(root, service, ImmediateExecutor())
    window = app.open_preferences()
    root.update()

    assert window is not None
    assert service.provider_calls == 1
    assert "NO PROVIDERS" in panel_text(app).upper()


def test_models_agents_ready_row_keeps_authorization_separate_and_secret_free(root) -> None:
    sentinel = "https://secret.example/api?key=TOPSECRET"
    service = FakeService((make_row(provenance="PROBE"),))
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences()
    root.update()

    text = panel_text(app)
    assert "GLM 5.3" in text
    assert "CONFIGURED" in text
    assert "READY" in text
    assert "NOT_EVALUATED" in text
    assert "UNKNOWN" in text
    assert sentinel not in text
    assert "endpoint" not in text.casefold()
    assert "credential" not in text.casefold()

def test_models_agents_typed_error_does_not_collapse_to_empty(root) -> None:
    service = FakeService(error=TypedProviderError("PROVIDER_CONFIGURATION_CORRUPT"))
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences()
    root.update()

    text = panel_text(app)
    assert "PROVIDER_CONFIGURATION_CORRUPT" in text
    assert "NO PROVIDERS" not in text.upper()


def test_models_agents_refresh_is_single_flight(root) -> None:
    service = FakeService((make_row(),))
    executor = ControlledExecutor()
    app = make_app(root, service, executor)
    app.open_preferences()
    root.update()

    assert len(executor.calls) == 1
    app._refresh_models_agents_panel()
    app._refresh_models_agents_panel()
    assert len(executor.calls) == 1

    executor.futures[0].set_result(service.provider_operator_rows())
    app._poll_models_agents_future(app._models_agents_request_id, executor.futures[0])
    root.update()
    assert "GLM 5.3" in panel_text(app)

def test_models_agents_delayed_result_after_preferences_close_is_ignored(root) -> None:
    service = FakeService((make_row(),))
    executor = ControlledExecutor()
    app = make_app(root, service, executor)
    window = app.open_preferences()
    root.update()

    assert window is not None
    window.destroy()
    root.update()
    executor.futures[0].set_result(service.provider_operator_rows())
    root.update()

    assert app._preferences_window is None
    assert app._models_agents_refresh_pending is False


def test_models_agents_formatter_preserves_zero_generation_and_disabled_reason(root) -> None:
    service = FakeService((make_row(
        enabled=False,
        configured=False,
        runtime_ready=False,
        readiness_reason="PROVIDER_GENERATION_INVALID",
        configuration_generation=0,
        health=SimpleNamespace(value="RATE_LIMITED"),
    ),))
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences()
    root.update()

    text = panel_text(app)
    assert "DISABLED" in text
    assert "NOT CONFIGURED" in text
    assert "NOT READY" in text
    assert "PROVIDER_GENERATION_INVALID" in text
    assert "RATE_LIMITED" in text
    assert "generation=0" in text

def test_models_agents_formatter_shows_quota_without_policy_inference(root) -> None:
    quota = SimpleNamespace(remaining=17, reset_in_seconds=3600, reset_at=None)
    service = FakeService((make_row(quota=quota),))
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences()
    root.update()

    text = panel_text(app)
    assert "remaining=17" in text
    assert "reset=3600s" in text
    assert "AUTH=NOT_EVALUATED" in text


def test_models_agents_missing_service_method_is_typed_error(root) -> None:
    service = FakeService()
    service.provider_operator_rows = None
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences()
    root.update()

    assert "PROVIDER_STORE_NOT_AVAILABLE" in panel_text(app)

def test_models_agents_delayed_read_stays_loading_without_second_submit(root) -> None:
    service = FakeService((make_row(),))
    executor = ControlledExecutor()
    app = make_app(root, service, executor)
    app.open_preferences()
    root.update()

    assert "provider" in panel_text(app).casefold()
    assert app._models_agents_refresh_pending is True
    assert len(executor.calls) == 1


def test_models_agents_language_refresh_rerenders_panel_state(root) -> None:
    previous_language = get_language()
    service = FakeService()
    app = make_app(root, service, ImmediateExecutor())
    try:
        app.open_preferences()
        root.update()
        before = panel_text(app)

        app._language_combo.set("English")
        app._language_combo.event_generate("<<ComboboxSelected>>")
        root.update()

        assert panel_text(app) != before
        assert "NO PROVIDERS" in panel_text(app)
    finally:
        set_language(previous_language)
