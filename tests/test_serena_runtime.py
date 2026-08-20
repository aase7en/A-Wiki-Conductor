from dataclasses import FrozenInstanceError, fields

import pytest

from a_conductor.serena_runtime import (
    ProjectIdentityPolicy,
    SerenaProjectBinding,
    SerenaWorkerConfig,
)


def make_worker_config(**overrides) -> SerenaWorkerConfig:
    values = {
        "worker_id": "a-worker-01",
        "runtime_id": "serena-runtime-01",
        "instance_root": "C:/runtime/a-worker-01",
        "serena_home": "C:/runtime/a-worker-01/serena-home",
        "health_host": "127.0.0.1",
        "health_port": 18011,
        "tunnel_binding_ref": "tunnel-binding-a-worker-01",
        "credential_ref": "credential-ref-runtime",
        "runtime_executable_ref": "runtime-executable",
        "profile_template_ref": "profile-template",
        "run_dir": "C:/runtime/a-worker-01/run",
        "log_dir": "C:/runtime/a-worker-01/logs",
        "startup_timeout_seconds": 30,
        "stop_timeout_seconds": 10,
    }
    values.update(overrides)
    return SerenaWorkerConfig(**values)


def test_worker_config_contains_stable_resources_not_project_binding() -> None:
    config = make_worker_config()

    assert config.worker_id == "a-worker-01"
    assert config.health_port == 18011
    assert not hasattr(config, "project_id")
    assert not hasattr(config, "worktree_path")


def test_project_binding_is_separate_and_reusable_with_same_worker_config() -> None:
    config = make_worker_config()
    first = SerenaProjectBinding(
        project_id="project-a",
        worktree_path="C:/projects/project-a",
        identity_policy=ProjectIdentityPolicy.EXACT,
        expected_branch="main",
        expected_head="abcdef1",
        mutation_allowed=True,
    )
    second = SerenaProjectBinding(
        project_id="project-b",
        worktree_path="C:/projects/project-b",
        identity_policy=ProjectIdentityPolicy.AUTHORIZED_SUCCESSOR,
        expected_branch="feature/runtime",
        expected_head="1234567",
        mutation_allowed=True,
    )

    assert config.worker_id == "a-worker-01"
    assert first.project_id != second.project_id
    assert first.worktree_path != second.worktree_path


@pytest.mark.parametrize("port", [0, -1, 65536])
def test_health_port_must_be_valid(port: int) -> None:
    with pytest.raises(ValueError, match="health_port must be between 1 and 65535"):
        make_worker_config(health_port=port)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("worker_id", " "),
        ("runtime_id", ""),
        ("instance_root", "\t"),
        ("serena_home", " "),
        ("health_host", ""),
        ("runtime_executable_ref", " "),
        ("profile_template_ref", ""),
        ("run_dir", " "),
        ("log_dir", ""),
    ],
)
def test_required_worker_config_text_rejects_blank(field_name: str, value: str) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        make_worker_config(**{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("tunnel_binding_ref", " "),
        ("credential_ref", ""),
    ],
)
def test_optional_references_reject_blank_when_present(field_name: str, value: str) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        make_worker_config(**{field_name: value})


def test_transport_and_credential_references_may_be_absent() -> None:
    config = make_worker_config(tunnel_binding_ref=None, credential_ref=None)

    assert config.tunnel_binding_ref is None
    assert config.credential_ref is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("startup_timeout_seconds", 0),
        ("startup_timeout_seconds", -1),
        ("stop_timeout_seconds", 0),
        ("stop_timeout_seconds", -1),
    ],
)
def test_timeouts_must_be_positive(field_name: str, value: int) -> None:
    with pytest.raises(ValueError, match="must be >= 1"):
        make_worker_config(**{field_name: value})


def test_worker_config_has_no_secret_value_fields() -> None:
    names = {field.name.lower() for field in fields(SerenaWorkerConfig)}

    assert "api_key" not in names
    assert "token" not in names
    assert "secret" not in names
    assert "password" not in names
    assert "credential_ref" in names


def test_project_binding_rejects_blank_identity() -> None:
    with pytest.raises(ValueError, match="project_id must not be blank"):
        SerenaProjectBinding(
            project_id=" ",
            worktree_path="C:/projects/project-a",
            identity_policy=ProjectIdentityPolicy.EXACT,
            mutation_allowed=True,
        )


def test_read_only_identity_policy_cannot_allow_mutation() -> None:
    with pytest.raises(ValueError, match="READ_ONLY_DISCOVERY cannot allow mutation"):
        SerenaProjectBinding(
            project_id="project-a",
            worktree_path="C:/projects/project-a",
            identity_policy=ProjectIdentityPolicy.READ_ONLY_DISCOVERY,
            mutation_allowed=True,
        )


def test_project_binding_is_immutable() -> None:
    binding = SerenaProjectBinding(
        project_id="project-a",
        worktree_path="C:/projects/project-a",
        identity_policy=ProjectIdentityPolicy.NO_GIT,
        mutation_allowed=True,
    )

    with pytest.raises(FrozenInstanceError):
        binding.project_id = "project-b"  # type: ignore[misc]


def test_identity_policy_matches_task_contract_vocabulary() -> None:
    assert {policy.value for policy in ProjectIdentityPolicy} == {
        "EXACT",
        "AUTHORIZED_SUCCESSOR",
        "NO_GIT",
        "READ_ONLY_DISCOVERY",
    }
