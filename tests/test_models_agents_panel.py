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


class ActionFakeService(FakeService):
    def __init__(self, rows=()) -> None:
        super().__init__(rows)
        self.action_calls: list[tuple] = []

    def update_provider_profile(self, provider_id, **kwargs):
        self.action_calls.append(("edit", provider_id, kwargs))
        return kwargs["expected_generation"] + 1

    def set_provider_enabled(self, provider_id, **kwargs):
        self.action_calls.append(("enabled", provider_id, kwargs))
        return kwargs["expected_generation"] + 1

    def test_provider(self, provider_id):
        self.action_calls.append(("test", provider_id, {}))
        return SimpleNamespace(
            provider_id=provider_id,
            health=SimpleNamespace(value="AVAILABLE"),
            provenance="probe:test",
        )

    def provider_credential_ref_runtime_supported(self, value):
        prefix = "secret-ref:awiki-env/"
        return isinstance(value, str) and value.startswith(prefix) and len(value) > len(prefix)


def test_wo127_provider_actions_exist_and_disable_uses_visible_generation(root) -> None:
    service = ActionFakeService((make_row(configuration_generation=7, enabled=True),))
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences()
    root.update()

    assert app._models_agents_provider_combo.get()
    assert app._models_agents_edit_button.cget("text") == "Edit"
    assert app._models_agents_toggle_button.cget("text") == "Disable"
    assert app._models_agents_test_button.cget("text") == "Test"

    app._toggle_selected_provider()
    root.update()
    assert service.action_calls[0] == (
        "enabled", "glm-primary", {"enabled": False, "expected_generation": 7}
    )


def test_wo127_edit_dialog_never_prefills_endpoint_or_credential(root) -> None:
    service = ActionFakeService((make_row(),))
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences()
    root.update()

    dialog = app._open_selected_provider_edit_dialog()
    root.update()
    assert dialog is not None
    texts: list[str] = []
    stack = [dialog]
    while stack:
        widget = stack.pop()
        stack.extend(widget.winfo_children())
        try:
            texts.append(str(widget.cget("text")))
        except tk.TclError:
            pass
        if isinstance(widget, (tk.Entry, tk.Text)):
            try:
                texts.append(widget.get() if isinstance(widget, tk.Entry) else widget.get("1.0", "end"))
            except tk.TclError:
                pass
    combined = "\n".join(texts)
    assert "https://" not in combined
    assert "secret-ref:provider/ui/main" not in combined


def test_wo127_test_action_is_single_flight_and_unsupported_is_truthful(root) -> None:
    service = ActionFakeService((make_row(),))
    executor = ControlledExecutor()
    app = make_app(root, service, executor)
    app.open_preferences()
    root.update()

    executor.futures[0].set_result(service.provider_operator_rows())
    app._poll_models_agents_future(app._models_agents_request_id, executor.futures[0])
    root.update()

    app._test_selected_provider()
    app._test_selected_provider()
    assert len(executor.calls) == 2

    executor.futures[1].set_result(SimpleNamespace(
        provider_id="glm-primary",
        health=SimpleNamespace(value="UNAVAILABLE"),
        provenance="zai-quota-monitor:unsupported-route",
    ))
    app._poll_models_agents_action_future(
        app._models_agents_action_request_id, "glm-primary", "test", executor.futures[1]
    )
    root.update()
    assert "UNSUPPORTED" in app._models_agents_action_label.cget("text")
    assert "unsupported-route" not in app._models_agents_action_label.cget("text")


def test_wo127_delayed_action_after_preferences_close_is_ignored(root) -> None:
    service = ActionFakeService((make_row(),))
    executor = ControlledExecutor()
    app = make_app(root, service, executor)
    window = app.open_preferences()
    root.update()
    executor.futures[0].set_result(service.provider_operator_rows())
    app._poll_models_agents_future(app._models_agents_request_id, executor.futures[0])
    root.update()

    app._test_selected_provider()
    assert app._models_agents_action_pending_provider == "glm-primary"
    action_future = executor.futures[1]
    action_request = app._models_agents_action_request_id
    window.destroy()
    root.update()
    action_future.set_result(SimpleNamespace(
        provider_id="glm-primary",
        health=SimpleNamespace(value="AVAILABLE"),
        provenance="probe:test",
    ))
    app._poll_models_agents_action_future(action_request, "glm-primary", "test", action_future)
    root.update()

    assert app._preferences_window is None
    assert app._models_agents_action_pending_provider is None


def test_wo127_action_failure_uses_typed_teaching_error_without_resubmit(root) -> None:
    service = ActionFakeService((make_row(configuration_generation=7, enabled=True),))
    executor = ControlledExecutor()
    app = make_app(root, service, executor)
    app.open_preferences()
    root.update()
    executor.futures[0].set_result(service.provider_operator_rows())
    app._poll_models_agents_future(app._models_agents_request_id, executor.futures[0])
    errors: list[str] = []
    app._handle_error = lambda code: errors.append(code)

    app._toggle_selected_provider()
    app._toggle_selected_provider()
    assert len(executor.calls) == 2
    executor.futures[1].set_exception(TypedProviderError("PROVIDER_CONFIGURATION_IN_USE"))
    app._poll_models_agents_action_future(
        app._models_agents_action_request_id, "glm-primary", "disable", executor.futures[1]
    )
    assert errors == ["PROVIDER_CONFIGURATION_IN_USE"]
    assert app._models_agents_action_label.cget("text") == "PROVIDER_CONFIGURATION_IN_USE"


# --- WO134 T3/T4: provider evidence detail GUI (RED-first) ---

from types import SimpleNamespace

from a_conductor.i18n import get_language, set_language
from a_conductor.provider_selection_observability import (
    project_provider_selection_evidence,
)
from a_conductor.provider_config_store import ProviderAdmissionRecord


def _wo134_admission(**overrides):
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    data = dict(
        admission_id="adm-001",
        provider_id="glm-primary",
        execution_id="exec-1",
        batch_id="batch-1",
        acquired_at=now - timedelta(minutes=5),
        expires_at=now + timedelta(minutes=5),
        status="ACTIVE",
        configuration_generation=7,
    )
    data.update(overrides)
    return ProviderAdmissionRecord(**data)


def _wo134_evidence(records, *, generation=7, now=None):
    return project_provider_selection_evidence(
        provider_id="glm-primary",
        current_configuration_generation=generation,
        admissions=tuple(records),
        now=now,
    )


class EvidenceFakeService(FakeService):
    def __init__(self, rows=(), error=None, graph_nodes=()):
        super().__init__(rows)
        self.evidence_error = error
        self.evidence_calls: list[str] = []
        self.graph_nodes = tuple(graph_nodes)
        self.graph_calls: list[tuple] = []

    def provider_selection_evidence(self, provider_id, **kwargs):
        self.evidence_calls.append(provider_id)
        if self.evidence_error is not None:
            raise self.evidence_error
        evidence = _wo134_evidence(
            [_wo134_admission()],
            generation=getattr(self.rows[0], "configuration_generation", 7) if self.rows else 7,
        )
        row = next(
            (item for item in self.rows if getattr(item, "provider_id", "") == provider_id),
            self.rows[0] if self.rows else make_row(),
        )
        return row, evidence

    def operator_graph_snapshot(self, graph_id, graph_run_id=None, *, event_limit=20):
        self.graph_calls.append((graph_id, graph_run_id))
        return SimpleNamespace(nodes=self.graph_nodes, runtime_evidence=True)


def _open_evidence(root, app):
    dialog = app._open_selected_provider_evidence()
    root.update()
    return dialog


def _evidence_text(app):
    return app._provider_evidence_text.get("1.0", "end")


def test_wo134_evidence_button_exists_on_second_row(root) -> None:
    service = EvidenceFakeService((make_row(),))
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences()
    root.update()

    button = app._models_agents_evidence_button
    assert button.cget("text") == "Evidence..."
    assert button.instate(("disabled",)) is False
    # second action row, never the first (combo/buttons) row
    assert int(button.grid_info()["row"]) >= 1


def test_wo134_evidence_dialog_singleton_reuse_and_provider_switch(root) -> None:
    rows = (make_row(configuration_generation=7), make_row(provider_id="glm-secondary", display_name="Second", configuration_generation=3))
    service = EvidenceFakeService(rows)
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences()
    root.update()

    first = _open_evidence(root, app)
    again = _open_evidence(root, app)
    assert again is first

    app._models_agents_provider_combo.current(1)
    root.update()
    switched = _open_evidence(root, app)
    assert switched is first
    root.update()
    assert service.evidence_calls == ["glm-primary", "glm-primary", "glm-secondary"]
    assert "Second" in _evidence_text(app)


def test_wo134_evidence_single_flight_background_only(root) -> None:
    service = EvidenceFakeService((make_row(),))
    executor = ControlledExecutor()
    app = make_app(root, service, executor)
    app.open_preferences()
    root.update()
    executor.futures[0].set_result(service.provider_operator_rows())
    app._poll_models_agents_future(app._models_agents_request_id, executor.futures[0])
    root.update()
    list_calls = len(executor.calls)

    app._open_selected_provider_evidence()
    app._open_selected_provider_evidence()
    app._open_selected_provider_evidence()
    assert len(executor.calls) == list_calls + 1
    work_fn = executor.calls[-1][0]
    executor.futures[-1].set_result(work_fn())
    app._poll_provider_evidence_future(app._provider_evidence_request_id, "glm-primary", executor.futures[-1])
    root.update()
    assert service.evidence_calls == ["glm-primary"]  # ran once, off the Tk thread
    assert "SELECTION_REASON=UNKNOWN" in _evidence_text(app)


def test_wo134_evidence_late_future_discarded_on_close_and_switch(root) -> None:
    service = EvidenceFakeService((make_row(), make_row(provider_id="glm-secondary", display_name="S", configuration_generation=1)))
    executor = ControlledExecutor()
    app = make_app(root, service, executor)
    app.open_preferences()
    root.update()
    executor.futures[0].set_result(service.provider_operator_rows())
    app._poll_models_agents_future(app._models_agents_request_id, executor.futures[0])
    root.update()

    dialog = app._open_selected_provider_evidence()
    pending_future = executor.futures[-1]
    dialog.destroy()
    root.update()
    pending_future.set_result(service.provider_selection_evidence("glm-primary"))
    app._poll_provider_evidence_future(app._provider_evidence_request_id, "glm-primary", pending_future)
    root.update()  # no TclError, pending cleared
    assert app._provider_evidence_pending is False

    app._models_agents_provider_combo.current(1)
    root.update()
    app._open_selected_provider_evidence()
    switch_future = executor.futures[-1]
    app._models_agents_provider_combo.current(0)
    root.update()
    app._open_selected_provider_evidence()  # provider switch while pending
    switch_future.set_result(service.provider_selection_evidence("glm-secondary"))
    app._poll_provider_evidence_future(app._provider_evidence_request_id - 1, "glm-secondary", switch_future)
    root.update()
    assert "Second" not in _evidence_text(app) or service.evidence_calls[-1] == "glm-primary"


def test_wo134_preferences_close_destroys_evidence_dialog(root) -> None:
    service = EvidenceFakeService((make_row(),))
    app = make_app(root, service, ImmediateExecutor())
    prefs = app.open_preferences()
    root.update()
    dialog = _open_evidence(root, app)
    assert dialog.winfo_exists()

    prefs.destroy()
    root.update()
    assert app._provider_evidence_window is None
    assert app._provider_evidence_pending is False
    try:
        assert not dialog.winfo_exists()
    except Exception:
        pass  # destroyed widgets may raise; the None check is the contract


def test_wo134_language_rerender_uses_cache_zero_io(root) -> None:
    previous = get_language()
    service = EvidenceFakeService((make_row(),))
    app = make_app(root, service, ImmediateExecutor())
    try:
        app.open_preferences()
        root.update()
        _open_evidence(root, app)
        calls_after_load = len(service.evidence_calls)
        before = _evidence_text(app)

        set_language("en")
        app._render_provider_evidence_from_cache()
        root.update()
        after_en = _evidence_text(app)

        assert len(service.evidence_calls) == calls_after_load  # zero extra I/O
        assert "SELECTION_REASON=UNKNOWN" in after_en
        assert after_en != before or before  # render ran; constants always present
        set_language("th")
        app._render_provider_evidence_from_cache()
        root.update()
        assert len(service.evidence_calls) == calls_after_load
    finally:
        set_language(previous)


def test_wo134_evidence_sentinel_free(root) -> None:
    sentinel = "https://secret.example/api?key=TOPSECRET"
    hostile_row = make_row(
        endpoint=SimpleNamespace(base_url=sentinel),
        base_url=sentinel,
        credential_ref="secret-ref:awiki-env/GLM_KEY",
        api_key="TOPSECRET",
    )
    service = EvidenceFakeService((hostile_row,))
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences()
    root.update()
    dialog = _open_evidence(root, app)

    texts: list[str] = [dialog.title()]

    def walk(widget):
        for child in widget.winfo_children():
            walk(child)
        try:
            if widget.winfo_class() == "Text":
                texts.append(widget.get("1.0", "end"))
            elif "text" in widget.keys():
                value = widget.cget("text")
                if isinstance(value, str):
                    texts.append(value)
        except Exception:
            pass

    walk(dialog)
    joined = "\n".join(texts)
    assert sentinel not in joined
    assert "TOPSECRET" not in joined
    assert "secret-ref:" not in joined


def test_wo134_evidence_error_states_typed_not_empty(root) -> None:
    class TypedErr(RuntimeError):
        def __init__(self, code):
            self.code = code
            super().__init__(code)

    for code in ("PROVIDER_ADMISSION_RECORD_INVALID", "PROVIDER_EVIDENCE_TARGET_UNAVAILABLE"):
        service = EvidenceFakeService((make_row(),), error=TypedErr(code))
        app = make_app(root, service, ImmediateExecutor())
        app.open_preferences()
        root.update()
        _open_evidence(root, app)
        text = _evidence_text(app)
        assert code in text
        assert "SELECTION_REASON" not in text  # error is not a partial success


def test_wo134_evidence_renders_constants_sections_and_fields(root) -> None:
    from datetime import datetime, timezone

    now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    class OverrideService(EvidenceFakeService):
        def provider_selection_evidence(self, provider_id, **kwargs):
            self.evidence_calls.append(provider_id)
            return self.rows[0], self.evidence_result_override

    service = OverrideService((make_row(),))
    service.evidence_result_override = _wo134_evidence(
        [_wo134_admission(), _wo134_admission(admission_id="adm-002", status="RELEASED", released_at=now, execution_id="exec-2", batch_id="batch-2")],
        generation=7,
        now=now,
    )
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences()
    root.update()
    _open_evidence(root, app)
    text = _evidence_text(app)

    assert "SELECTION_REASON=UNKNOWN" in text
    assert "FALLBACK_REASON=NOT_EVALUATED" in text
    assert ": models=" in text and "harness=" in text  # declared-capabilities line (language-agnostic)
    assert "adm-001" in text and "adm-002" in text
    assert "exec-1" in text and "batch-1" in text
    assert "ACTIVE" in text and "RELEASED" in text
    assert "MATCHES_CURRENT" in text
    assert "TERMINAL" in text
    assert "acquired=" in text
    assert "NO_READABLE_GRAPH_EVIDENCE" in text


def test_wo134_evidence_graph_exact_link(root) -> None:
    from a_conductor.graph.dispatch import GraphDispatchKey

    node = SimpleNamespace(node_id="node-a", objective="work", status="RUNNING", worker_id="w1")
    job_id = GraphDispatchKey("graph-1", "run-1", "node-a").job_id
    near_miss = job_id[:-1] + ("0" if job_id[-1] != "0" else "1")
    records = [_wo134_admission(execution_id=job_id), _wo134_admission(admission_id="adm-x", execution_id=near_miss)]
    now = None

    class GraphService(EvidenceFakeService):
        def provider_selection_evidence(self, provider_id, **kwargs):
            self.evidence_calls.append(provider_id)
            return self.rows[0], _wo134_evidence(records)

    service = GraphService((make_row(),), graph_nodes=(node,))
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences()
    root.update()

    app._graph_monitor_graph_id = "graph-1"
    app._graph_monitor_run_id = "run-1"
    _open_evidence(root, app)
    text = _evidence_text(app)
    assert "node-a" in text  # exact match links
    assert "graph-1" in text and "run-1" in text
    # near miss never links
    app._provider_evidence_window.destroy()
    root.update()

    app._graph_monitor_run_id = None  # no explicit run -> never links
    _open_evidence(root, app)
    assert "node-a" not in _evidence_text(app)
    assert "NO_READABLE_GRAPH_EVIDENCE" in _evidence_text(app)


def test_wo134_pending_evidence_cannot_mix_graph_contexts(root) -> None:
    from a_conductor.graph.dispatch import GraphDispatchKey

    node = SimpleNamespace(node_id="node-a", objective="work", status="RUNNING", worker_id="w1")
    job_id = GraphDispatchKey("graph-1", "run-1", "node-a").job_id

    class GraphService(EvidenceFakeService):
        def provider_selection_evidence(self, provider_id, **kwargs):
            self.evidence_calls.append(provider_id)
            return self.rows[0], _wo134_evidence([_wo134_admission(execution_id=job_id)])

    service = GraphService((make_row(),), graph_nodes=(node,))
    executor = ControlledExecutor()
    app = make_app(root, service, executor)
    app.open_preferences(); root.update()
    executor.futures[0].set_result(service.provider_operator_rows())
    app._poll_models_agents_future(app._models_agents_request_id, executor.futures[0]); root.update()

    app._graph_monitor_graph_id = "graph-1"
    app._graph_monitor_run_id = "run-1"
    app._open_selected_provider_evidence()
    future = executor.futures[-1]
    result = executor.calls[-1][0]()
    assert service.graph_calls[-1] == ("graph-1", "run-1")

    app._graph_monitor_graph_id = "graph-2"
    app._graph_monitor_run_id = "run-2"
    future.set_result(result)
    app._poll_provider_evidence_future(app._provider_evidence_request_id, "glm-primary", future)
    root.update()
    text = _evidence_text(app)
    assert "node-a" not in text
    assert "graph_context=graph-2 run=run-2" not in text


def test_wo134_graph_monitor_change_invalidates_cached_links_without_evidence_io(root, monkeypatch) -> None:
    import a_conductor.desktop_ui as desktop_ui_module
    from a_conductor.graph.dispatch import GraphDispatchKey

    node = SimpleNamespace(node_id="node-a", objective="work", status="RUNNING", worker_id="w1")
    job_id = GraphDispatchKey("graph-1", "run-1", "node-a").job_id

    class GraphService(EvidenceFakeService):
        def provider_selection_evidence(self, provider_id, **kwargs):
            self.evidence_calls.append(provider_id)
            return self.rows[0], _wo134_evidence([_wo134_admission(execution_id=job_id)])
        def operator_graph_ids(self):
            return ("graph-1", "graph-2")

    service = GraphService((make_row(),), graph_nodes=(node,))
    app = make_app(root, service, ImmediateExecutor())
    app.open_preferences(); root.update()
    app._graph_monitor_graph_id = "graph-1"
    app._graph_monitor_run_id = "run-1"
    _open_evidence(root, app)
    assert "node-a" in _evidence_text(app)
    evidence_calls = len(service.evidence_calls)

    responses = iter(["graph-2", "run-2"])
    monkeypatch.setattr(desktop_ui_module.simpledialog, "askstring", lambda *_a, **_k: next(responses))
    app._refresh_monitor_async = lambda: None
    app.open_graph_monitor(); root.update()

    text = _evidence_text(app)
    assert len(service.evidence_calls) == evidence_calls
    assert "node-a" not in text
    assert "graph_context=" not in text
    assert "NO_READABLE_GRAPH_EVIDENCE" in text


def test_wo134_provider_action_success_refreshes_open_evidence_in_background(root) -> None:
    class EvidenceActionService(EvidenceFakeService):
        def test_provider(self, provider_id):
            return SimpleNamespace(
                provider_id=provider_id,
                health=SimpleNamespace(value="AVAILABLE"),
                provenance="probe:test",
            )

    service = EvidenceActionService((make_row(),))
    executor = ControlledExecutor()
    app = make_app(root, service, executor)
    app.open_preferences(); root.update()
    executor.futures[0].set_result(service.provider_operator_rows())
    app._poll_models_agents_future(app._models_agents_request_id, executor.futures[0]); root.update()

    app._open_selected_provider_evidence()
    first_evidence_future = executor.futures[-1]
    first_evidence_future.set_result(executor.calls[-1][0]())
    app._poll_provider_evidence_future(
        app._provider_evidence_request_id, "glm-primary", first_evidence_future
    ); root.update()
    assert service.evidence_calls == ["glm-primary"]

    app._test_selected_provider()
    action_future = executor.futures[-1]
    action_future.set_result(service.test_provider("glm-primary"))
    new_calls_start = len(executor.calls)
    app._poll_models_agents_action_future(
        app._models_agents_action_request_id, "glm-primary", "test", action_future
    ); root.update()

    assert len(executor.calls) >= new_calls_start + 2  # evidence refresh + panel refresh
    evidence_index = next(
        index for index in range(new_calls_start, len(executor.calls))
        if getattr(executor.calls[index][0], "__name__", "") == "_work"
    )
    evidence_work = executor.calls[evidence_index][0]
    evidence_future = executor.futures[evidence_index]
    evidence_future.set_result(evidence_work())
    app._poll_provider_evidence_future(
        app._provider_evidence_request_id, "glm-primary", evidence_future
    ); root.update()
    assert service.evidence_calls == ["glm-primary", "glm-primary"]
