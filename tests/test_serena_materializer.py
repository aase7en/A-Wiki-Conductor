from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from a_conductor.serena_materializer import (
    SerenaMaterializationError,
    SerenaMaterializedRuntime,
    SerenaRuntimeMaterializer,
)
from a_conductor.serena_runtime import (
    ProjectIdentityPolicy,
    SerenaProjectBinding,
    SerenaWorkerConfig,
)


def worker(tmp_path: Path, *, health_host: str = "127.0.0.1") -> SerenaWorkerConfig:
    root = tmp_path / "worker-root"
    external = tmp_path / "external"
    external.mkdir(parents=True, exist_ok=True)
    executable = external / "tunnel-client.exe"
    executable.write_bytes(b"test-executable-placeholder")
    template = external / "runtime.yaml.template"
    template.write_text(
        "tunnel: __TUNNEL_ID__\nproject: __PROJECT_PATH__\n",
        encoding="utf-8",
    )
    return SerenaWorkerConfig(
        worker_id="a-worker-test",
        runtime_id="runtime-test",
        instance_root=str(root),
        serena_home=str(root / "serena-home"),
        health_host=health_host,
        health_port=18031,
        tunnel_binding_ref="binding-ref",
        credential_ref="credential-ref",
        runtime_executable_ref=str(executable),
        profile_template_ref=str(template),
        run_dir=str(root / "run"),
        log_dir=str(root / "logs"),
        startup_timeout_seconds=5,
        stop_timeout_seconds=7,
    )


def binding(tmp_path: Path) -> SerenaProjectBinding:
    return SerenaProjectBinding(
        project_id="project-test",
        worktree_path=str(tmp_path / "project"),
        identity_policy=ProjectIdentityPolicy.EXACT,
        expected_branch="main",
        expected_head="abc123",
        mutation_allowed=True,
    )


def tokens(tmp_path: Path) -> dict[str, str]:
    return {
        "__TUNNEL_ID__": "tunnel-test-id",
        "__PROJECT_PATH__": str(tmp_path / "project"),
    }


def test_materialize_renders_profile_and_builds_owned_process_spec(tmp_path: Path) -> None:
    config = worker(tmp_path)
    result = SerenaRuntimeMaterializer().materialize(
        config,
        binding(tmp_path),
        tokens(tmp_path),
    )

    assert isinstance(result, SerenaMaterializedRuntime)
    assert result.profile_path == Path(config.run_dir).resolve() / "runtime-profile.yaml"
    assert result.serena_home == Path(config.serena_home).resolve()
    assert result.health_url == "http://127.0.0.1:18031/readyz"
    assert result.profile_path.read_text(encoding="utf-8") == (
        f"tunnel: tunnel-test-id\nproject: {tmp_path / 'project'}\n"
    )

    spec = result.process_spec
    assert spec.allowed_root == Path(config.instance_root).resolve()
    assert spec.cwd == Path(config.run_dir).resolve()
    assert spec.pid_path == Path(config.run_dir).resolve() / "runtime.pid"
    assert spec.stdout_path == Path(config.log_dir).resolve() / "runtime.stdout.log"
    assert spec.stderr_path == Path(config.log_dir).resolve() / "runtime.stderr.log"
    assert spec.command == (
        str(Path(config.runtime_executable_ref).resolve()),
        "run",
        "--profile-file",
        str(result.profile_path),
    )
    assert "--pid.file" not in spec.command
    assert spec.expected_executable_name == "tunnel-client.exe"
    assert spec.expected_profile_marker == str(result.profile_path)
    assert spec.stop_timeout_seconds == config.stop_timeout_seconds


def test_public_result_does_not_store_token_values(tmp_path: Path) -> None:
    sensitive_value = "very-sensitive-tunnel-value"
    values = tokens(tmp_path)
    values["__TUNNEL_ID__"] = sensitive_value

    result = SerenaRuntimeMaterializer().materialize(
        worker(tmp_path),
        binding(tmp_path),
        values,
    )

    assert sensitive_value not in repr(result)
    assert not hasattr(result, "token_values")


@pytest.mark.parametrize(
    ("values", "expected_code"),
    [
        ({"__TUNNEL_ID__": "id-only"}, "PROFILE_TOKEN_MISMATCH"),
        (
            {
                "__TUNNEL_ID__": "id",
                "__PROJECT_PATH__": "project",
                "__EXTRA__": "extra",
            },
            "PROFILE_TOKEN_MISMATCH",
        ),
        (
            {"__TUNNEL_ID__": "", "__PROJECT_PATH__": "project"},
            "PROFILE_TOKEN_INVALID",
        ),
        (
            {"__TUNNEL_ID__": "secret\nsecond-line", "__PROJECT_PATH__": "project"},
            "PROFILE_TOKEN_INVALID",
        ),
        (
            {"__TUNNEL_ID__": "secret\x00value", "__PROJECT_PATH__": "project"},
            "PROFILE_TOKEN_INVALID",
        ),
    ],
)
def test_bad_token_maps_fail_before_profile_output(
    tmp_path: Path,
    values: dict[str, str],
    expected_code: str,
) -> None:
    config = worker(tmp_path)
    with pytest.raises(SerenaMaterializationError) as exc_info:
        SerenaRuntimeMaterializer().materialize(config, binding(tmp_path), values)

    assert exc_info.value.code == expected_code
    assert not (Path(config.run_dir) / "runtime-profile.yaml").exists()


def test_error_text_never_echoes_sensitive_token_value(tmp_path: Path) -> None:
    config = worker(tmp_path)
    sensitive = "do-not-echo-me\nunsafe"
    with pytest.raises(SerenaMaterializationError) as exc_info:
        SerenaRuntimeMaterializer().materialize(
            config,
            binding(tmp_path),
            {
                "__TUNNEL_ID__": sensitive,
                "__PROJECT_PATH__": "project",
            },
        )

    assert sensitive not in str(exc_info.value)


@pytest.mark.parametrize("field_name", ["serena_home", "run_dir", "log_dir"])
def test_mutable_worker_paths_must_stay_under_instance_root(
    tmp_path: Path,
    field_name: str,
) -> None:
    config = worker(tmp_path)
    data = {
        "worker_id": config.worker_id,
        "runtime_id": config.runtime_id,
        "instance_root": config.instance_root,
        "serena_home": config.serena_home,
        "health_host": config.health_host,
        "health_port": config.health_port,
        "tunnel_binding_ref": config.tunnel_binding_ref,
        "credential_ref": config.credential_ref,
        "runtime_executable_ref": config.runtime_executable_ref,
        "profile_template_ref": config.profile_template_ref,
        "run_dir": config.run_dir,
        "log_dir": config.log_dir,
        "startup_timeout_seconds": config.startup_timeout_seconds,
        "stop_timeout_seconds": config.stop_timeout_seconds,
    }
    data[field_name] = str(tmp_path / "outside" / field_name)
    bad = SerenaWorkerConfig(**data)

    with pytest.raises(SerenaMaterializationError) as exc_info:
        SerenaRuntimeMaterializer().materialize(bad, binding(tmp_path), tokens(tmp_path))

    assert exc_info.value.code == "PATH_OUTSIDE_INSTANCE_ROOT"


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "example.com"])
def test_health_host_must_be_loopback(tmp_path: Path, host: str) -> None:
    with pytest.raises(SerenaMaterializationError) as exc_info:
        SerenaRuntimeMaterializer().materialize(
            worker(tmp_path, health_host=host),
            binding(tmp_path),
            tokens(tmp_path),
        )

    assert exc_info.value.code == "HEALTH_HOST_NOT_LOOPBACK"


def test_ipv6_loopback_health_url_is_bracketed(tmp_path: Path) -> None:
    config = worker(tmp_path, health_host="::1")
    result = SerenaRuntimeMaterializer().materialize(
        config,
        binding(tmp_path),
        tokens(tmp_path),
    )
    assert result.health_url == "http://[::1]:18031/readyz"


def test_missing_template_fails_without_creating_run_state(tmp_path: Path) -> None:
    config = worker(tmp_path)
    Path(config.profile_template_ref).unlink()

    with pytest.raises(SerenaMaterializationError) as exc_info:
        SerenaRuntimeMaterializer().materialize(config, binding(tmp_path), tokens(tmp_path))

    assert exc_info.value.code == "PROFILE_TEMPLATE_NOT_FOUND"
    assert not Path(config.run_dir).exists()


def test_missing_runtime_executable_fails_without_creating_profile(tmp_path: Path) -> None:
    config = worker(tmp_path)
    Path(config.runtime_executable_ref).unlink()

    with pytest.raises(SerenaMaterializationError) as exc_info:
        SerenaRuntimeMaterializer().materialize(config, binding(tmp_path), tokens(tmp_path))

    assert exc_info.value.code == "RUNTIME_EXECUTABLE_NOT_FOUND"
    assert not (Path(config.run_dir) / "runtime-profile.yaml").exists()


def test_atomic_replace_failure_leaves_no_profile_or_temp_file(tmp_path: Path, monkeypatch) -> None:
    config = worker(tmp_path)

    def fail_replace(source, destination):
        raise OSError("replace unavailable")

    monkeypatch.setattr("a_conductor.serena_materializer.os.replace", fail_replace)

    with pytest.raises(SerenaMaterializationError) as exc_info:
        SerenaRuntimeMaterializer().materialize(config, binding(tmp_path), tokens(tmp_path))

    assert exc_info.value.code == "PROFILE_WRITE_FAILED"
    run_dir = Path(config.run_dir)
    assert not (run_dir / "runtime-profile.yaml").exists()
    assert list(run_dir.glob(".runtime-profile-*.tmp")) == []


def test_materialized_runtime_is_frozen(tmp_path: Path) -> None:
    result = SerenaRuntimeMaterializer().materialize(
        worker(tmp_path),
        binding(tmp_path),
        tokens(tmp_path),
    )
    with pytest.raises(FrozenInstanceError):
        result.health_url = "http://127.0.0.1:1/readyz"  # type: ignore[misc]
