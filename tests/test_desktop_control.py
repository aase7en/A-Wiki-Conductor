from __future__ import annotations

from pathlib import Path

from a_conductor.control_center import ControlCenterService
from a_conductor.desktop_control import DesktopControlService
from a_conductor.lifecycle import LifecycleAction
from a_conductor.lifecycle_executor import LifecycleExecutionResult, LifecycleExecutionState
from a_conductor.persistence import SQLiteRegistryStore


class FakeCoordinator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, LifecycleAction]] = []

    def execute(self, worker_id: str, action: LifecycleAction) -> LifecycleExecutionResult:
        self.calls.append((worker_id, action))
        return LifecycleExecutionResult(
            transaction_id=f"tx-{action.value.lower()}",
            state=LifecycleExecutionState.NOOP,
            reason_code="TEST_NOOP",
        )


def test_facade_delegates_lifecycle_actions(tmp_path: Path) -> None:
    control = ControlCenterService.open(SQLiteRegistryStore(tmp_path / "control.sqlite"))
    coordinator = FakeCoordinator()
    service = DesktopControlService(control_center=control, lifecycle=coordinator)

    assert service.start_worker("a-worker-01").state is LifecycleExecutionState.NOOP
    assert service.stop_worker("a-worker-01").state is LifecycleExecutionState.NOOP
    assert service.restart_worker("a-worker-01").state is LifecycleExecutionState.NOOP
    assert coordinator.calls == [
        ("a-worker-01", LifecycleAction.START),
        ("a-worker-01", LifecycleAction.STOP),
        ("a-worker-01", LifecycleAction.RESTART),
    ]


def test_facade_delegates_control_center_snapshot_and_project_actions(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    control = ControlCenterService.open(SQLiteRegistryStore(database))
    service = DesktopControlService(control_center=control, lifecycle=FakeCoordinator())
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    project = service.register_project(project_dir, display_name="Project")
    assignment = service.assign_project("a-worker-01", project.project_id)

    assert assignment.worker_id == "a-worker-01"
    assert service.snapshot() == control.snapshot()
    assert service.release_worker("a-worker-01").assignment_id is None


def test_open_uses_same_control_center_instance_for_coordinator_builder(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    captured = {}
    coordinator = FakeCoordinator()

    def builder(path, *, service):
        captured["path"] = Path(path)
        captured["service"] = service
        return coordinator

    desktop = DesktopControlService.open(database, coordinator_builder=builder)

    assert captured["path"] == database
    assert captured["service"] is desktop.control_center
    assert desktop.lifecycle is coordinator
    assert len(desktop.snapshot().workers) == 3


def _worker_config_for(root, worker_id="a-worker-01"):
    from a_conductor.serena_runtime import SerenaWorkerConfig

    return SerenaWorkerConfig(
        worker_id=worker_id,
        runtime_id="runtime-1",
        instance_root=str(root / "instance"),
        serena_home=str(root / "instance" / "serena-home"),
        health_host="127.0.0.1",
        health_port=18201,
        tunnel_binding_ref=None,
        credential_ref=None,
        runtime_executable_ref=str(root / "engine.exe"),
        profile_template_ref=str(root / "profile.yaml"),
        run_dir=str(root / "instance" / "run"),
        log_dir=str(root / "instance" / "logs"),
    )


class _FakeControlCenter:
    def __init__(self, project_root=None):
        self._project_root = project_root

    def snapshot(self):
        from a_conductor.control_center import ControlCenterSnapshot, WorkerScreenRow
        from a_conductor.domain import WorkerState

        return ControlCenterSnapshot(
            projects=(),
            workers=(
                WorkerScreenRow(
                    worker_id="a-worker-01",
                    display_name="A-Worker 1",
                    state=WorkerState.STOPPED,
                    runtime_id="runtime-1",
                    assignment_id="assignment-1" if self._project_root else None,
                    project_id="project-1" if self._project_root else None,
                    project_display_name="P" if self._project_root else None,
                    project_root_path=self._project_root,
                    mutation_allowed=True,
                ),
            ),
            online=True,
        )


class _FakeLifecycle:
    def __init__(self):
        self.calls = []

    def execute(self, worker_id, action):
        self.calls.append((worker_id, action.value))
        return object()


def test_apply_worker_settings_to_home_applied(tmp_path):
    from a_conductor.serena_config_store import SQLiteSerenaConfigStore
    from a_conductor.worker_serena_settings import WorkerSerenaSettings

    config_store = SQLiteSerenaConfigStore(tmp_path / "control.sqlite")
    config_store.save_worker_config(_worker_config_for(tmp_path))
    config_store.save_worker_settings(
        WorkerSerenaSettings(
            worker_id="a-worker-01",
            tool_timeout=777,
            project_path=r"A:\GitHub\demo",
            brain_folders=(r"A:\GitHub\A-Wiki",),
        )
    )
    service = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=_FakeLifecycle(),
        settings_store=config_store,
    )

    result = service.apply_worker_settings_to_home("a-worker-01")

    written = tmp_path / "instance" / "serena-home" / "serena_config.yml"
    assert result == "APPLIED"
    text = written.read_text(encoding="utf-8")
    assert "tool_timeout: 777" in text
    assert "A:\GitHub\demo" in text
    assert "[A-CONDUCTOR SECOND BRAIN]" in text


def test_apply_worker_settings_project_fallback_from_assignment(tmp_path):
    from a_conductor.serena_config_store import SQLiteSerenaConfigStore
    from a_conductor.worker_serena_settings import WorkerSerenaSettings

    config_store = SQLiteSerenaConfigStore(tmp_path / "control.sqlite")
    config_store.save_worker_config(_worker_config_for(tmp_path))
    config_store.save_worker_settings(
        WorkerSerenaSettings(worker_id="a-worker-01")
    )
    service = DesktopControlService(
        control_center=_FakeControlCenter(project_root=r"A:\GitHub\assigned"),
        lifecycle=_FakeLifecycle(),
        settings_store=config_store,
    )

    result = service.apply_worker_settings_to_home("a-worker-01")

    assert result == "APPLIED"
    text = (tmp_path / "instance" / "serena-home" / "serena_config.yml").read_text(encoding="utf-8")
    assert r"A:\GitHub\assigned" in text


def test_apply_worker_settings_skip_codes(tmp_path):
    from a_conductor.serena_config_store import SQLiteSerenaConfigStore
    from a_conductor.worker_serena_settings import WorkerSerenaSettings

    empty_store = SQLiteSerenaConfigStore(tmp_path / "empty.sqlite")
    service = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=_FakeLifecycle(),
        settings_store=empty_store,
    )
    from a_conductor.worker_serena_settings import WorkerSerenaSettings as _W

    empty_store.save_worker_settings(_W(worker_id="a-worker-01"))
    assert service.apply_worker_settings_to_home("a-worker-01") == "SKIPPED_NOT_CONFIGURED"

    config_store = SQLiteSerenaConfigStore(tmp_path / "cfg.sqlite")
    config_store.save_worker_config(_worker_config_for(tmp_path / "c"))
    service2 = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=_FakeLifecycle(),
        settings_store=config_store,
    )
    assert service2.apply_worker_settings_to_home("a-worker-01") == "SKIPPED_NO_SETTINGS"

    config_store.save_worker_settings(WorkerSerenaSettings(worker_id="a-worker-01"))

    # A rogue config that escapes its instance root cannot even be persisted by
    # the store (its own validation rejects it), so prove the facade guard with
    # a stub store that hands out an unsafe config directly.
    from dataclasses import replace as _replace

    rogue_config = _replace(
        _worker_config_for(tmp_path / "c"), serena_home=str(tmp_path / "elsewhere")
    )

    class _RogueStore:
        def get_worker_settings(self, worker_id):
            return WorkerSerenaSettings(worker_id=worker_id)

        def get_worker_config(self, worker_id):
            return rogue_config

    service3 = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=_FakeLifecycle(),
        settings_store=_RogueStore(),
    )
    assert service3.apply_worker_settings_to_home("a-worker-01") == "SKIPPED_TARGET_UNSAFE"


def test_start_worker_applies_settings_before_lifecycle(tmp_path):
    from a_conductor.serena_config_store import SQLiteSerenaConfigStore
    from a_conductor.worker_serena_settings import WorkerSerenaSettings

    config_store = SQLiteSerenaConfigStore(tmp_path / "control.sqlite")
    config_store.save_worker_config(_worker_config_for(tmp_path))
    config_store.save_worker_settings(
        WorkerSerenaSettings(worker_id="a-worker-01", tool_timeout=555)
    )
    lifecycle = _FakeLifecycle()
    service = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=lifecycle,
        settings_store=config_store,
    )

    service.start_worker("a-worker-01")

    assert lifecycle.calls == [("a-worker-01", "START")]
    text = (tmp_path / "instance" / "serena-home" / "serena_config.yml").read_text(encoding="utf-8")
    assert "tool_timeout: 555" in text


def test_open_job_control_honors_supervised_preference(tmp_path, monkeypatch):
    from a_conductor.serena_config_store import SQLiteSerenaConfigStore
    from a_conductor.native_operations import NativeOperationDefinition, NativeOperationKind

    config_store = SQLiteSerenaConfigStore(tmp_path / "jc.sqlite")
    service = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=_FakeLifecycle(),
        settings_store=config_store,
    )
    operations = (
        NativeOperationDefinition(
            operation_ref="op:pytest",
            kind=NativeOperationKind.PYTEST,
            paths=("tests",),
            timeout_seconds=60,
        ),
    )

    captured = {}
    import a_conductor.desktop_control as dc

    class _RecordingJobControl:
        def __init__(self, *, supervised, **kwargs):
            captured["supervised"] = supervised

        @classmethod
        def open(cls, *args, **kwargs):
            return cls(**kwargs)

    import a_conductor.job_control as jc

    monkeypatch.setattr(jc, "DurableJobControlService", _RecordingJobControl)

    jobs = service.open_job_control(tmp_path / "jc.sqlite", operations)
    assert isinstance(jobs, _RecordingJobControl)
    assert captured["supervised"] is True  # default ON per user decision

    config_store.set_preference("supervised", False)
    service.open_job_control(tmp_path / "jc.sqlite", operations)
    assert captured["supervised"] is False


def test_open_job_control_requires_settings_store(tmp_path):
    from a_conductor.serena_config_store import SerenaConfigStoreError

    service = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=_FakeLifecycle(),
    )
    try:
        service.open_job_control(tmp_path / "x.sqlite", ())
    except SerenaConfigStoreError as exc:
        assert "SETTINGS_STORE_NOT_AVAILABLE" in str(exc)
    else:
        raise AssertionError("missing store accepted")


def test_wo125_open_canonicalizes_one_control_database_identity(tmp_path, monkeypatch) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    monkeypatch.chdir(first)
    captured: dict[str, Path] = {}

    def builder(path, *, service):
        captured["path"] = Path(path)
        return FakeCoordinator()

    desktop = DesktopControlService.open("control.sqlite", coordinator_builder=builder)
    expected = (first / "control.sqlite").resolve(strict=False)

    assert captured["path"] == expected
    assert desktop.settings_store.database_path == expected
    assert desktop._provider_store.database_path == expected
    monkeypatch.chdir(second)
    assert desktop.settings_store.database_path == expected
    assert desktop._provider_store.database_path == expected


def test_wo125_provider_operator_rows_requires_retained_store() -> None:
    import pytest
    from a_conductor.provider_config_store import ProviderConfigStoreError

    service = DesktopControlService(control_center=_FakeControlCenter(), lifecycle=_FakeLifecycle())
    with pytest.raises(ProviderConfigStoreError) as exc:
        service.provider_operator_rows()
    assert exc.value.code == "PROVIDER_STORE_NOT_AVAILABLE"
    assert str(exc.value) == "PROVIDER_STORE_NOT_AVAILABLE"


def test_wo125_direct_facade_refuses_mismatched_control_database_authorities(tmp_path) -> None:
    import pytest
    from a_conductor.provider_config_store import SQLiteProviderConfigStore
    from a_conductor.serena_config_store import SQLiteSerenaConfigStore

    settings = SQLiteSerenaConfigStore(tmp_path / "settings.sqlite")
    provider = SQLiteProviderConfigStore(tmp_path / "provider.sqlite")
    settings.initialize()
    provider.initialize()

    with pytest.raises(ValueError, match="CONTROL_DATABASE_IDENTITY_MISMATCH"):
        DesktopControlService(
            control_center=_FakeControlCenter(),
            lifecycle=_FakeLifecycle(),
            settings_store=settings,
            provider_store=provider,
        )


def _wo125_profile():
    from a_conductor.provider_configuration import (
        EgressBoundary, HarnessStrategy, ProtocolFamily, ProviderConfiguration,
        ProviderModelConfiguration, ProviderTrustClass,
    )
    return ProviderConfiguration(
        provider_id="provider-ui",
        display_name="Provider UI",
        provider_type="cloud-proxy",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="provider-config:ui/base-url",
        credential_ref="secret-ref:provider/ui/main",
        trust_class=ProviderTrustClass.UNKNOWN,
        egress_boundary=EgressBoundary.UNKNOWN,
        harness_strategies=(HarnessStrategy.CLAUDE_CODE_CLI,),
        max_concurrency=1,
        models=(ProviderModelConfiguration(model_id="model-ui", display_name="Model UI"),),
        enabled=True,
    )


def test_wo125_provider_operator_rows_reuses_store_and_sees_fresh_commits(tmp_path) -> None:
    from datetime import datetime, timezone
    from a_conductor.provider_config_store import SQLiteProviderConfigStore
    from a_conductor.provider_configuration import ProviderEndpointConfig, ProviderHealth, ProviderObservation

    now = datetime(2026, 9, 1, 13, 0, tzinfo=timezone.utc)
    database = tmp_path / "control.sqlite"
    provider_store = SQLiteProviderConfigStore(database)
    profile = _wo125_profile()
    provider_store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    provider_store.save_provider(profile)
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(),
        provider_store=provider_store,
        clock=lambda: now,
    )

    first = service.provider_operator_rows()
    assert len(first) == 1
    assert first[0].runtime_ready is False
    assert first[0].task_authorization == "NOT_EVALUATED"

    provider_store.save_observation(
        ProviderObservation(
            provider_id=profile.provider_id,
            health=ProviderHealth.AVAILABLE,
            observed_at=now,
            provenance="probe:desktop-control-test",
            configuration_generation=1,
        )
    )
    second = service.provider_operator_rows()
    assert second[0].runtime_ready is True
    assert second[0].task_authorization == "NOT_EVALUATED"
    assert second[0].provenance == "PROBE"


def test_wo125_provider_store_bootstraps_once_not_on_operator_refresh(tmp_path, monkeypatch) -> None:
    from a_conductor.provider_config_store import SQLiteProviderConfigStore

    calls = 0
    original = SQLiteProviderConfigStore.initialize

    def counted_initialize(self):
        nonlocal calls
        calls += 1
        return original(self)

    monkeypatch.setattr(SQLiteProviderConfigStore, "initialize", counted_initialize)
    service = DesktopControlService.open(
        tmp_path / "control.sqlite",
        coordinator_builder=lambda path, *, service: FakeCoordinator(),
    )

    assert calls == 1
    assert service.provider_operator_rows() == ()
    assert service.provider_operator_rows() == ()
    assert calls == 1


def test_wo127_update_provider_profile_preserves_identity_and_cas(tmp_path) -> None:
    from a_conductor.provider_config_store import SQLiteProviderConfigStore
    from a_conductor.provider_configuration import ProviderEndpointConfig

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = _wo125_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    store.save_provider(profile)
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(), provider_store=store,
    )

    generation = service.update_provider_profile(
        profile.provider_id,
        expected_generation=1,
        display_name="Provider Renamed",
        max_concurrency=3,
    )

    saved = store.get_provider(profile.provider_id)
    assert generation == 2
    assert saved is not None
    assert saved.display_name == "Provider Renamed"
    assert saved.max_concurrency == 3
    assert saved.provider_id == profile.provider_id
    assert saved.endpoint_ref == profile.endpoint_ref
    assert saved.credential_ref == profile.credential_ref


def test_wo127_update_provider_profile_stale_generation_fails_without_overwrite(tmp_path) -> None:
    import pytest
    from a_conductor.provider_config_store import ProviderConfigStoreError, SQLiteProviderConfigStore
    from a_conductor.provider_configuration import ProviderEndpointConfig

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = _wo125_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    store.save_provider(profile)
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(), provider_store=store,
    )
    service.update_provider_profile(profile.provider_id, expected_generation=1, display_name="Winner")

    with pytest.raises(ProviderConfigStoreError) as exc:
        service.update_provider_profile(profile.provider_id, expected_generation=1, display_name="Loser")

    assert exc.value.code == "PROVIDER_GENERATION_STALE"
    assert store.get_provider(profile.provider_id).display_name == "Winner"


def test_wo127_disable_and_reenable_preserve_configured_profile(tmp_path) -> None:
    from a_conductor.provider_config_store import SQLiteProviderConfigStore
    from a_conductor.provider_configuration import ProviderEndpointConfig

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = _wo125_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    store.save_provider(profile)
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(), provider_store=store,
    )
    gen2 = service.set_provider_enabled(profile.provider_id, enabled=False, expected_generation=1)
    disabled = store.get_provider(profile.provider_id)
    assert gen2 == 2
    assert disabled is not None and disabled.enabled is False
    assert service.provider_operator_rows()[0].configured is True
    assert service.provider_operator_rows()[0].runtime_ready is False
    assert service.provider_operator_rows()[0].readiness_reason == "PROVIDER_DISABLED"

    gen3 = service.set_provider_enabled(profile.provider_id, enabled=True, expected_generation=2)
    enabled = store.get_provider(profile.provider_id)
    assert gen3 == 3
    assert enabled is not None and enabled.enabled is True


def test_wo127_invalid_profile_update_maps_to_typed_error(tmp_path) -> None:
    import pytest
    from a_conductor.provider_config_store import ProviderConfigStoreError, SQLiteProviderConfigStore
    from a_conductor.provider_configuration import ProviderEndpointConfig

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = _wo125_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    store.save_provider(profile)
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(), provider_store=store,
    )

    with pytest.raises(ProviderConfigStoreError) as exc:
        service.update_provider_profile(profile.provider_id, expected_generation=1, display_name="")
    assert exc.value.code == "PROVIDER_PROFILE_INVALID"
    assert store.get_provider(profile.provider_id).display_name == profile.display_name


def test_wo127_test_provider_uses_canonical_runtime_refresh_and_maps_missing(tmp_path, monkeypatch) -> None:
    import pytest
    from datetime import datetime, timezone
    from a_conductor.provider_config_store import ProviderConfigStoreError, SQLiteProviderConfigStore
    from a_conductor.provider_configuration import ProviderEndpointConfig, ProviderHealth, ProviderObservation
    import a_conductor.provider_runtime_assembly as runtime_assembly

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = _wo125_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    store.save_provider(profile)
    now = datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc)
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(), provider_store=store, clock=lambda: now,
    )
    calls = []

    def fake_refresh(**kwargs):
        calls.append(kwargs)
        return ProviderObservation(
            provider_id=profile.provider_id, health=ProviderHealth.AVAILABLE,
            observed_at=now, provenance="probe:test", configuration_generation=1,
        )

    monkeypatch.setattr(runtime_assembly, "refresh_zai_provider_observation", fake_refresh)
    result = service.test_provider(profile.provider_id)
    assert result.health is ProviderHealth.AVAILABLE
    assert calls[0]["database_path"] == store.database_path.resolve(strict=False)
    assert calls[0]["provider_id"] == profile.provider_id
    assert calls[0]["clock"] is service._clock

    monkeypatch.setattr(runtime_assembly, "refresh_zai_provider_observation", lambda **kwargs: None)
    with pytest.raises(ProviderConfigStoreError) as exc:
        service.test_provider("provider-missing")
    assert exc.value.code == "PROVIDER_TEST_TARGET_UNAVAILABLE"


def test_wo127_update_refused_while_provider_admission_is_active(tmp_path) -> None:
    import pytest
    from datetime import datetime, timezone
    from a_conductor.provider_config_store import ProviderConfigStoreError, SQLiteProviderConfigStore
    from a_conductor.provider_configuration import ProviderEndpointConfig

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = _wo125_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    store.save_provider(profile)
    now = datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc)
    acquired = store.acquire_admission(
        provider_id=profile.provider_id, execution_id="exec-active", batch_id="batch-active",
        expected_max_concurrency=1, now=now, ttl_seconds=300,
        expected_configuration_generation=1,
    )
    assert acquired.admission is not None
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(), provider_store=store,
    )

    with pytest.raises(ProviderConfigStoreError) as exc:
        service.update_provider_profile(profile.provider_id, expected_generation=1, display_name="Blocked")
    assert exc.value.code == "PROVIDER_CONFIGURATION_IN_USE"
    assert store.load_provider_snapshot(profile.provider_id).generation == 1


def test_wo127_missing_provider_never_resurrects_on_edit(tmp_path) -> None:
    import pytest
    from a_conductor.provider_config_store import ProviderConfigStoreError, SQLiteProviderConfigStore

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    store.initialize()
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(), provider_store=store,
    )

    with pytest.raises(ProviderConfigStoreError) as exc:
        service.update_provider_profile("provider-ui", expected_generation=1, display_name="No resurrection")
    assert exc.value.code == "PROVIDER_GENERATION_STALE"
    assert store.get_provider("provider-ui") is None


def test_wo127_test_provider_propagates_generation_stale_without_retry(tmp_path, monkeypatch) -> None:
    import pytest
    from a_conductor.provider_config_store import ProviderConfigStoreError, SQLiteProviderConfigStore
    import a_conductor.provider_runtime_assembly as runtime_assembly

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    store.initialize()
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(), provider_store=store,
    )
    calls = 0
    def stale(**kwargs):
        nonlocal calls
        calls += 1
        raise ProviderConfigStoreError("PROVIDER_OBSERVATION_GENERATION_STALE")
    monkeypatch.setattr(runtime_assembly, "refresh_zai_provider_observation", stale)

    with pytest.raises(ProviderConfigStoreError) as exc:
        service.test_provider("provider-ui")
    assert exc.value.code == "PROVIDER_OBSERVATION_GENERATION_STALE"
    assert calls == 1


def test_wo127_invalid_patch_fails_before_provider_store_read() -> None:
    import pytest
    from a_conductor.provider_config_store import ProviderConfigStoreError

    class ExplodingStore:
        database_path = Path("never-open.sqlite")
        calls = 0

        def get_provider(self, provider_id):
            self.calls += 1
            raise AssertionError("store read must not happen")

    store = ExplodingStore()
    service = DesktopControlService(
        control_center=_FakeControlCenter(), lifecycle=_FakeLifecycle(), provider_store=store,
    )
    for kwargs in ({"display_name": ""}, {"max_concurrency": 0}, {"models": ()}):
        with pytest.raises(ProviderConfigStoreError) as exc:
            service.update_provider_profile("provider-ui", expected_generation=1, **kwargs)
        assert exc.value.code == "PROVIDER_PROFILE_INVALID"
    assert store.calls == 0


def test_wo127_credential_repoint_is_verbatim_and_runtime_support_is_declared(tmp_path) -> None:
    from a_conductor.provider_config_store import SQLiteProviderConfigStore
    from a_conductor.provider_configuration import ProviderEndpointConfig

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = _wo125_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    store.save_provider(profile)
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(), provider_store=store,
    )
    supported = "secret-ref:awiki-env/KEY_X"
    unsupported = "secret-ref:other/x"
    assert service.provider_credential_ref_runtime_supported(supported) is True
    assert service.provider_credential_ref_runtime_supported(unsupported) is False
    assert service.provider_credential_ref_runtime_supported("secret-ref:awiki-env/9BAD") is False
    assert service.update_provider_profile(profile.provider_id, expected_generation=1, credential_ref=supported) == 2
    assert store.get_provider(profile.provider_id).credential_ref == supported
    assert service.update_provider_profile(profile.provider_id, expected_generation=2, credential_ref=unsupported) == 3
    assert store.get_provider(profile.provider_id).credential_ref == unsupported


def test_wo127_expired_admission_still_fences_provider_edit(tmp_path) -> None:
    import sqlite3
    import pytest
    from datetime import datetime, timezone
    from a_conductor.provider_config_store import ProviderConfigStoreError, SQLiteProviderConfigStore
    from a_conductor.provider_configuration import ProviderEndpointConfig

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = _wo125_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    store.save_provider(profile)
    acquired = store.acquire_admission(
        provider_id=profile.provider_id, execution_id="exec-expired", batch_id="batch-expired",
        expected_max_concurrency=1, now=datetime(2026, 9, 2, tzinfo=timezone.utc),
        ttl_seconds=1, expected_configuration_generation=1,
    )
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE provider_admissions SET status='EXPIRED' WHERE admission_id=?", (acquired.admission.admission_id,))
    service = DesktopControlService(control_center=ControlCenterService.open(SQLiteRegistryStore(database)), lifecycle=FakeCoordinator(), provider_store=store)
    with pytest.raises(ProviderConfigStoreError) as exc:
        service.update_provider_profile(profile.provider_id, expected_generation=1, display_name="Blocked")
    assert exc.value.code == "PROVIDER_CONFIGURATION_IN_USE"
    assert store.load_provider_snapshot(profile.provider_id).generation == 1


def test_wo127_disabled_provider_refuses_new_admission(tmp_path) -> None:
    import pytest
    from datetime import datetime, timezone
    from a_conductor.provider_config_store import ProviderConfigStoreError, SQLiteProviderConfigStore
    from a_conductor.provider_configuration import ProviderEndpointConfig

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = _wo125_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    store.save_provider(profile)
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)), lifecycle=FakeCoordinator(), provider_store=store,
    )
    service.set_provider_enabled(profile.provider_id, enabled=False, expected_generation=1)
    with pytest.raises(ProviderConfigStoreError) as exc:
        store.acquire_admission(
            provider_id=profile.provider_id, execution_id="exec-disabled", batch_id="batch-disabled",
            expected_max_concurrency=1, now=datetime(2026, 9, 2, tzinfo=timezone.utc), ttl_seconds=60,
            expected_configuration_generation=2,
        )
    assert exc.value.code == "PROVIDER_ADMISSION_PROVIDER_DISABLED"
    row = service.provider_operator_rows()[0]
    assert row.configured is True and row.readiness_reason == "PROVIDER_DISABLED"


def test_wo127_real_sqlite_test_provider_persists_generation_bound_quota(tmp_path) -> None:
    from dataclasses import replace
    from datetime import datetime, timezone
    from a_conductor.provider_config_store import SQLiteProviderConfigStore
    from a_conductor.provider_configuration import ProviderEndpointConfig, ProviderHealth

    class FakeQuotaTransport:
        def __init__(self):
            self.calls = []
        def get_json(self, url, *, authorization, timeout_seconds):
            self.calls.append((url, authorization, timeout_seconds))
            return 200, {"data": {"limits": [{
                "type": "TOKENS_LIMIT", "usage": 100, "currentValue": 40,
                "remaining": 60, "nextResetTime": 1788084000000,
            }]}}

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = replace(_wo125_profile(), credential_ref="secret-ref:awiki-env/ANTHROPIC_API_KEY")
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.z.ai/api/anthropic"))
    store.save_provider(profile)
    drive = tmp_path / "A-Wiki-Data"
    (drive / "secrets").mkdir(parents=True)
    (drive / "secrets" / "global.env").write_text("ANTHROPIC_API_KEY=test-only-secret\n", encoding="utf-8")
    now = datetime(2026, 8, 30, 5, 0, tzinfo=timezone.utc)
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(), provider_store=store, clock=lambda: now,
    )
    transport = FakeQuotaTransport()
    observed = service.test_provider(profile.provider_id, transport=transport, drive_root=drive)
    assert observed.health is ProviderHealth.AVAILABLE
    assert observed.configuration_generation == 1
    assert observed.quota is not None and observed.quota.remaining == 60
    assert store.get_observation(profile.provider_id) == observed
    assert transport.calls and transport.calls[0][1] == "test-only-secret"
    assert "test-only-secret" not in observed.provenance


# --- WO134 T2: provider selection evidence facade (RED-first) ---

from dataclasses import replace as _wo134_replace

from a_conductor.provider_config_store import (
    ProviderConfigStoreError,
    SQLiteProviderConfigStore,
)


class _WO134CallOrderStore(SQLiteProviderConfigStore):
    def __init__(self, database):
        super().__init__(database)
        self.wo134_calls: list[str] = []

    def list_provider_admissions(self, **kwargs):
        self.wo134_calls.append("admissions")
        return super().list_provider_admissions(**kwargs)

    def list_provider_snapshots(self):
        self.wo134_calls.append("snapshots")
        return super().list_provider_snapshots()


class _WO134RacingStore(SQLiteProviderConfigStore):
    """Applies a generation-2 edit AFTER admissions read, BEFORE snapshot read."""

    def __init__(self, database, profile):
        super().__init__(database)
        self._profile = profile
        self._edited = False

    def list_provider_snapshots(self):
        if not self._edited:
            self._edited = True
            self.save_provider(
                _wo134_replace(self._profile, display_name="gen-2 edit"),
                expected_generation=1,
            )
        return super().list_provider_snapshots()


def _wo134_service(tmp_path, store=None):
    database = tmp_path / "control.sqlite"
    store = store or SQLiteProviderConfigStore(database)
    store.initialize()
    return DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(),
        provider_store=store,
    )


def test_wo134_evidence_reads_admissions_before_snapshots(tmp_path) -> None:
    import pytest
    from a_conductor.provider_configuration import ProviderEndpointConfig

    database = tmp_path / "control.sqlite"
    store = _WO134CallOrderStore(database)
    store.save_endpoint(ProviderEndpointConfig("provider-config:test/base-url", "https://api.example.test/v1"))
    profile = _wo125_profile()
    store.save_provider(profile)
    service = _wo134_service(tmp_path, store)

    row, evidence = service.provider_selection_evidence(profile.provider_id)

    assert store.wo134_calls == ["admissions", "snapshots"]
    assert evidence.selection_reason == "UNKNOWN"
    assert evidence.fallback_reason == "NOT_EVALUATED"
    assert row.provider_id == profile.provider_id
    assert evidence.admissions == ()


def test_wo134_released_generation_race_is_stale_not_matches(tmp_path) -> None:
    from datetime import datetime, timezone
    from a_conductor.provider_configuration import ProviderEndpointConfig

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    store.save_endpoint(ProviderEndpointConfig("provider-config:test/base-url", "https://api.example.test/v1"))
    profile = _wo125_profile()
    store.save_provider(profile)
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    acquired = store.acquire_admission(
        provider_id=profile.provider_id, execution_id="exec-race", batch_id="batch-race",
        expected_max_concurrency=1, now=now, ttl_seconds=600,
        expected_configuration_generation=1,
    )
    store.release_admission(
        acquired.admission.admission_id, provider_id=profile.provider_id,
        execution_id="exec-race", batch_id="batch-race", now=now,
    )
    racing = _WO134RacingStore(database, profile)
    service = _wo134_service(tmp_path, racing)

    _row, evidence = service.provider_selection_evidence(profile.provider_id)

    assert len(evidence.admissions) == 1
    assert evidence.current_configuration_generation == 2
    assert evidence.admissions[0].configuration_generation == 1
    assert evidence.admissions[0].generation_relation == "STALE_VS_CURRENT"


def test_wo134_missing_target_and_invalid_inputs_fail_typed(tmp_path) -> None:
    import pytest

    service = _wo134_service(tmp_path / "missing" / "sub" / None if False else tmp_path)
    with pytest.raises(ProviderConfigStoreError) as exc:
        service.provider_selection_evidence("provider-not-there")
    assert exc.value.code == "PROVIDER_EVIDENCE_TARGET_UNAVAILABLE"

    with pytest.raises(ProviderConfigStoreError) as exc:
        service.provider_selection_evidence("   ")
    assert exc.value.code == "PROVIDER_ADMISSION_FILTER_INVALID"
    with pytest.raises(ProviderConfigStoreError) as exc:
        service.provider_selection_evidence(_wo125_profile().provider_id, admissions_limit=0)
    assert exc.value.code == "PROVIDER_ADMISSION_LIST_LIMIT_INVALID"


def test_wo134_corrupt_admission_is_typed_never_partial(tmp_path) -> None:
    import sqlite3
    import pytest
    from datetime import datetime, timezone
    from a_conductor.provider_configuration import ProviderEndpointConfig

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    store.save_endpoint(ProviderEndpointConfig("provider-config:test/base-url", "https://api.example.test/v1"))
    profile = _wo125_profile()
    store.save_provider(profile)
    store.acquire_admission(
        provider_id=profile.provider_id, execution_id="exec-x", batch_id="b",
        expected_max_concurrency=1, now=datetime(2026, 9, 2, tzinfo=timezone.utc), ttl_seconds=600,
    )
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE provider_admissions SET acquired_at='garbage' WHERE execution_id='exec-x'")
        connection.commit()
    service = _wo134_service(tmp_path, store)

    with pytest.raises(ProviderConfigStoreError) as exc:
        service.provider_selection_evidence(profile.provider_id)
    assert exc.value.code == "PROVIDER_ADMISSION_RECORD_INVALID"


def test_wo134_constants_invariant_under_healthy_and_failing_fixtures(tmp_path) -> None:
    import sqlite3
    from datetime import datetime, timedelta, timezone
    from a_conductor.provider_configuration import (
        ProviderEndpointConfig, ProviderHealth, ProviderObservation,
    )

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = _wo125_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    store.save_provider(profile)
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    store.save_observation(ProviderObservation(
        provider_id=profile.provider_id, health=ProviderHealth.AVAILABLE,
        observed_at=now, provenance="probe:test", configuration_generation=1,
    ))
    active = store.acquire_admission(
        provider_id=profile.provider_id, execution_id="exec-live", batch_id="b1",
        expected_max_concurrency=1, now=now, ttl_seconds=600,
        expected_configuration_generation=1,
    )
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(), provider_store=store, clock=lambda: now,
    )
    healthy = service.provider_selection_evidence(profile.provider_id)
    assert healthy[0].runtime_ready is True
    assert healthy[1].selection_reason == "UNKNOWN" and healthy[1].fallback_reason == "NOT_EVALUATED"

    # failing fixture: quota-exhausted health + expired admission + drift
    store.save_observation(ProviderObservation(
        provider_id=profile.provider_id, health=ProviderHealth.QUOTA_EXHAUSTED,
        observed_at=now, provenance="probe:test", configuration_generation=1,
    ))
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE provider_admissions SET status='EXPIRED' WHERE admission_id=?", (active.admission.admission_id,))
        connection.commit()
    failing = service.provider_selection_evidence(profile.provider_id)
    assert failing[0].runtime_ready is False
    assert failing[1].selection_reason == "UNKNOWN" and failing[1].fallback_reason == "NOT_EVALUATED"
    assert failing[1].admissions[0].expiry_observation == "PAST_EXPIRY_RECONCILE_REQUIRED"


def test_wo134_single_provider_api_no_cross_provider_surface() -> None:
    import inspect

    signature = inspect.signature(DesktopControlService.provider_selection_evidence)
    assert "provider_id" in signature.parameters
    assert not any("providers" in name for name in signature.parameters)


def test_wo134_real_sqlite_e2e_statuses_drift_and_relation(tmp_path) -> None:
    import sqlite3
    from datetime import datetime, timedelta, timezone
    from a_conductor.provider_configuration import ProviderEndpointConfig

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    store.save_endpoint(ProviderEndpointConfig("provider-config:test/base-url", "https://api.example.test/v1"))
    profile = _wo125_profile()
    store.save_provider(profile)
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    first = store.acquire_admission(
        provider_id=profile.provider_id, execution_id="exec-1", batch_id="b1",
        expected_max_concurrency=1, now=now - timedelta(minutes=10), ttl_seconds=60,
        expected_configuration_generation=1,
    )
    store.release_admission(first.admission.admission_id, provider_id=profile.provider_id,
                            execution_id="exec-1", batch_id="b1", now=now - timedelta(minutes=9))
    second = store.acquire_admission(
        provider_id=profile.provider_id, execution_id="exec-2", batch_id="b2",
        expected_max_concurrency=1, now=now, ttl_seconds=600,
        expected_configuration_generation=1,
    )
    store.release_admission(second.admission.admission_id, provider_id=profile.provider_id,
                            execution_id="exec-2", batch_id="b2", now=now)
    store.save_provider(_wo134_replace(profile, display_name="gen 2"), expected_generation=1)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE provider_admissions SET status='EXPIRED' WHERE execution_id='exec-2'")
        connection.commit()
    service = DesktopControlService(
        control_center=ControlCenterService.open(SQLiteRegistryStore(database)),
        lifecycle=FakeCoordinator(), provider_store=store, clock=lambda: now,
    )
    row, evidence = service.provider_selection_evidence(profile.provider_id)

    assert [item.status for item in evidence.admissions] == ["EXPIRED", "RELEASED"]
    assert all(item.generation_relation == "STALE_VS_CURRENT" for item in evidence.admissions)
    assert evidence.admissions[0].expiry_observation == "PAST_EXPIRY_RECONCILE_REQUIRED"
    assert evidence.admissions[1].expiry_observation == "TERMINAL"
    assert evidence.admissions[1].released_at is not None
    assert row.configuration_generation == 2
