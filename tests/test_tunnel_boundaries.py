from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from a_conductor.owned_process import OwnedProcessSpec, build_owned_child_environment
from a_conductor.serena_lifecycle_backend import SerenaOperationResult
from a_conductor.serena_materializer import SerenaMaterializedRuntime
from a_conductor.serena_runtime import (
    ProjectIdentityPolicy,
    SerenaProjectBinding,
    SerenaWorkerConfig,
)
from a_conductor.tunnel_boundaries import (
    LocalFileReferenceStore,
    LocalTunnelOwnershipGuard,
    ReferenceResolutionError,
    ReferenceBackedSerenaTokenProvider,
    StrictTunnelClientPreflightService,
)


def make_worker(tmp_path: Path, *, template_text: str = "tunnel: __TUNNEL_ID__\n") -> SerenaWorkerConfig:
    root = tmp_path / "worker"
    external = tmp_path / "external"
    external.mkdir(parents=True, exist_ok=True)
    executable = external / "tunnel-client.exe"
    executable.write_bytes(b"test")
    template = external / "runtime.yaml.template"
    template.write_text(template_text, encoding="utf-8")
    return SerenaWorkerConfig(
        worker_id="a-worker-test",
        runtime_id="runtime-test",
        instance_root=str(root),
        serena_home=str(root / "serena-home"),
        health_host="127.0.0.1",
        health_port=18121,
        tunnel_binding_ref="tunnel-ref",
        credential_ref="credential-ref",
        runtime_executable_ref=str(executable),
        profile_template_ref=str(template),
        run_dir=str(root / "run"),
        log_dir=str(root / "logs"),
        startup_timeout_seconds=5,
        stop_timeout_seconds=5,
    )


def make_binding(tmp_path: Path) -> SerenaProjectBinding:
    project = tmp_path / "project"
    project.mkdir(parents=True, exist_ok=True)
    return SerenaProjectBinding(
        project_id="project-test",
        worktree_path=str(project),
        identity_policy=ProjectIdentityPolicy.EXACT,
        expected_branch="main",
        expected_head="abc123",
        mutation_allowed=True,
    )


def make_store(tmp_path: Path, value: str = "tunnel-value") -> LocalFileReferenceStore:
    refs = tmp_path / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    tunnel_file = refs / "tunnel-id.txt"
    tunnel_file.write_text(value, encoding="utf-8")
    return LocalFileReferenceStore(
        {"tunnel-ref": tunnel_file},
        allowed_roots=(refs,),
    )


def make_materialized(tmp_path: Path) -> SerenaMaterializedRuntime:
    root = tmp_path / "worker"
    run = root / "run"
    logs = root / "logs"
    home = root / "serena-home"
    run.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    executable = tmp_path / "tunnel-client.exe"
    executable.write_bytes(b"test")
    profile = run / "runtime-profile.yaml"
    profile.write_text("profile\n", encoding="utf-8")
    spec = OwnedProcessSpec(
        allowed_root=root,
        cwd=run,
        pid_path=run / "runtime.pid",
        stdout_path=logs / "stdout.log",
        stderr_path=logs / "stderr.log",
        command=(str(executable), "run", "--profile-file", str(profile)),
        expected_executable_name="tunnel-client.exe",
        expected_profile_marker=str(profile),
        environment_overrides=(("SERENA_HOME", str(home)),),
    )
    return SerenaMaterializedRuntime(
        profile_path=profile.resolve(),
        serena_home=home.resolve(),
        health_url="http://127.0.0.1:18121/readyz",
        process_spec=spec,
    )


def test_reference_store_reads_trimmed_single_line_value(tmp_path: Path) -> None:
    store = make_store(tmp_path, "  tunnel-value  \n")
    assert store.read_text("tunnel-ref") == "tunnel-value"


@pytest.mark.parametrize("value", ["", "   ", "one\ntwo", "bad\x00value"])
def test_reference_store_rejects_invalid_values_without_echo(tmp_path: Path, value: str) -> None:
    store = make_store(tmp_path, value)
    with pytest.raises(ReferenceResolutionError) as exc_info:
        store.read_text("tunnel-ref")
    assert exc_info.value.code == "REFERENCE_VALUE_INVALID"
    if value:
        assert value not in str(exc_info.value)


def test_reference_store_unknown_ref_fails_without_path_guessing(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(ReferenceResolutionError) as exc_info:
        store.read_text("unknown-ref")
    assert exc_info.value.code == "REFERENCE_NOT_FOUND"


def test_reference_store_rejects_mapping_outside_allowed_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("value", encoding="utf-8")
    with pytest.raises(ValueError, match="allowed root"):
        LocalFileReferenceStore(
            {"tunnel-ref": outside},
            allowed_roots=(allowed,),
        )


def test_token_provider_returns_only_placeholders_requested_by_template(tmp_path: Path) -> None:
    worker = make_worker(
        tmp_path,
        template_text="tunnel: __TUNNEL_ID__\nproject: __PROJECT_PATH__\n",
    )
    binding = make_binding(tmp_path)
    provider = ReferenceBackedSerenaTokenProvider(make_store(tmp_path))

    values = provider.resolve(worker, binding)

    assert values == {
        "__TUNNEL_ID__": "tunnel-value",
        "__PROJECT_PATH__": str(Path(binding.worktree_path).resolve()),
    }
    assert "__SERENA_HOME__" not in values


def test_token_provider_supports_derived_non_secret_tokens(tmp_path: Path) -> None:
    worker = make_worker(
        tmp_path,
        template_text=(
            "worker: __WORKER_ID__\n"
            "home: __SERENA_HOME__\n"
            "health: __HEALTH_LISTEN_ADDRESS__\n"
        ),
    )
    binding = make_binding(tmp_path)
    provider = ReferenceBackedSerenaTokenProvider(make_store(tmp_path))

    values = provider.resolve(worker, binding)

    assert values == {
        "__WORKER_ID__": worker.worker_id,
        "__SERENA_HOME__": str(Path(worker.serena_home).resolve()),
        "__HEALTH_LISTEN_ADDRESS__": f"{worker.health_host}:{worker.health_port}",
    }


def test_token_provider_unknown_placeholder_fails_closed(tmp_path: Path) -> None:
    worker = make_worker(tmp_path, template_text="x: __UNSUPPORTED_SECRET__\n")
    provider = ReferenceBackedSerenaTokenProvider(make_store(tmp_path))
    with pytest.raises(ReferenceResolutionError) as exc_info:
        provider.resolve(worker, make_binding(tmp_path))
    assert exc_info.value.code == "PROFILE_TOKEN_UNSUPPORTED"


def test_token_provider_requires_tunnel_reference_when_template_requests_it(tmp_path: Path) -> None:
    worker = make_worker(tmp_path)
    data = {name: getattr(worker, name) for name in worker.__dataclass_fields__}
    data["tunnel_binding_ref"] = None
    worker_without_ref = SerenaWorkerConfig(**data)
    provider = ReferenceBackedSerenaTokenProvider(make_store(tmp_path))

    with pytest.raises(ReferenceResolutionError) as exc_info:
        provider.resolve(worker_without_ref, make_binding(tmp_path))
    assert exc_info.value.code == "TUNNEL_REFERENCE_REQUIRED"


def test_tunnel_guard_detects_collision_and_owned_state(tmp_path: Path) -> None:
    worker = make_worker(tmp_path)
    guard = LocalTunnelOwnershipGuard(
        {
            "tunnel-ref": "other-worker",
        }
    )
    collision = guard.verify_available(worker)
    assert collision == SerenaOperationResult(success=False, error_code="TUNNEL_COLLISION")

    owned = LocalTunnelOwnershipGuard({"tunnel-ref": worker.worker_id})
    available = owned.verify_available(worker)
    assert available.success is True
    released = owned.verify_released(worker)
    assert released == SerenaOperationResult(
        success=False,
        error_code="TUNNEL_STILL_OWNED",
        recovery_required=True,
    )


def test_tunnel_guard_no_ref_is_free() -> None:
    class Worker:
        worker_id = "worker"
        tunnel_binding_ref = None

    guard = LocalTunnelOwnershipGuard({})
    assert guard.verify_available(Worker()).success is True  # type: ignore[arg-type]
    assert guard.verify_released(Worker()).success is True  # type: ignore[arg-type]


def test_shared_child_environment_builder_filters_parent_secrets(tmp_path: Path) -> None:
    materialized = make_materialized(tmp_path)
    source = {
        "Path": r"C:\Tools",
        "SYSTEMROOT": r"C:\Windows",
        "OPENAI_API_KEY": "parent-secret",
        "CUSTOM_SECRET": "secret",
        "SERENA_HOME": "wrong",
    }
    env = build_owned_child_environment(materialized.process_spec, source)
    assert env["Path"] == source["Path"]
    assert env["SYSTEMROOT"] == source["SYSTEMROOT"]
    assert env["SERENA_HOME"] == str(materialized.serena_home)
    assert "OPENAI_API_KEY" not in env
    assert "CUSTOM_SECRET" not in env


def test_preflight_uses_fixed_doctor_argv_safe_env_and_redacts_output(tmp_path: Path, monkeypatch) -> None:
    materialized = make_materialized(tmp_path)
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout="sensitive doctor output",
            stderr="sensitive stderr",
        )

    monkeypatch.setattr("a_conductor.tunnel_boundaries.subprocess.run", fake_run)
    service = StrictTunnelClientPreflightService(
        timeout_seconds=4,
        environment_source={
            "Path": r"C:\Tools",
            "SYSTEMROOT": r"C:\Windows",
            "OPENAI_API_KEY": "parent-secret",
        },
    )

    result = service.run(materialized)

    assert result == SerenaOperationResult(success=True)
    argv, kwargs = calls[0]
    assert argv == [
        materialized.process_spec.command[0],
        "doctor",
        "--profile-file",
        str(materialized.profile_path),
        "--explain",
    ]
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 4
    assert "OPENAI_API_KEY" not in kwargs["env"]
    assert kwargs["env"]["SERENA_HOME"] == str(materialized.serena_home)
    assert "sensitive doctor output" not in repr(result)


def test_preflight_nonzero_exit_is_redacted_failure(tmp_path: Path, monkeypatch) -> None:
    materialized = make_materialized(tmp_path)

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 2, stdout="secret", stderr="secret")

    monkeypatch.setattr("a_conductor.tunnel_boundaries.subprocess.run", fake_run)
    result = StrictTunnelClientPreflightService().run(materialized)
    assert result == SerenaOperationResult(
        success=False,
        error_code="TUNNEL_PREFLIGHT_FAILED",
    )


def test_preflight_timeout_is_redacted_failure(tmp_path: Path, monkeypatch) -> None:
    materialized = make_materialized(tmp_path)

    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output="secret")

    monkeypatch.setattr("a_conductor.tunnel_boundaries.subprocess.run", fake_run)
    result = StrictTunnelClientPreflightService().run(materialized)
    assert result == SerenaOperationResult(
        success=False,
        error_code="TUNNEL_PREFLIGHT_TIMEOUT",
    )
