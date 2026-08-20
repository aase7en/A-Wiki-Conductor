"""Pure configuration models for Serena-backed A-Workers.

The models deliberately separate stable worker-owned runtime resources from a
Project/worktree binding. They perform validation only and contain no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProjectIdentityPolicy(str, Enum):
    EXACT = "EXACT"
    AUTHORIZED_SUCCESSOR = "AUTHORIZED_SUCCESSOR"
    NO_GIT = "NO_GIT"
    READ_ONLY_DISCOVERY = "READ_ONLY_DISCOVERY"


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _require_optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name)


@dataclass(frozen=True, slots=True)
class SerenaWorkerConfig:
    worker_id: str
    runtime_id: str
    instance_root: str
    serena_home: str
    health_host: str
    health_port: int
    tunnel_binding_ref: str | None
    credential_ref: str | None
    runtime_executable_ref: str
    profile_template_ref: str
    run_dir: str
    log_dir: str
    startup_timeout_seconds: int = 30
    stop_timeout_seconds: int = 10

    def __post_init__(self) -> None:
        _require_text(self.worker_id, "worker_id")
        _require_text(self.runtime_id, "runtime_id")
        _require_text(self.instance_root, "instance_root")
        _require_text(self.serena_home, "serena_home")
        _require_text(self.health_host, "health_host")
        _require_optional_text(self.tunnel_binding_ref, "tunnel_binding_ref")
        _require_optional_text(self.credential_ref, "credential_ref")
        _require_text(self.runtime_executable_ref, "runtime_executable_ref")
        _require_text(self.profile_template_ref, "profile_template_ref")
        _require_text(self.run_dir, "run_dir")
        _require_text(self.log_dir, "log_dir")

        if not 1 <= self.health_port <= 65535:
            raise ValueError("health_port must be between 1 and 65535")
        if self.startup_timeout_seconds < 1:
            raise ValueError("startup_timeout_seconds must be >= 1")
        if self.stop_timeout_seconds < 1:
            raise ValueError("stop_timeout_seconds must be >= 1")


@dataclass(frozen=True, slots=True)
class SerenaProjectBinding:
    project_id: str
    worktree_path: str
    identity_policy: ProjectIdentityPolicy
    expected_branch: str | None = None
    expected_head: str | None = None
    mutation_allowed: bool = False

    def __post_init__(self) -> None:
        _require_text(self.project_id, "project_id")
        _require_text(self.worktree_path, "worktree_path")
        _require_optional_text(self.expected_branch, "expected_branch")
        _require_optional_text(self.expected_head, "expected_head")

        if (
            self.identity_policy is ProjectIdentityPolicy.READ_ONLY_DISCOVERY
            and self.mutation_allowed
        ):
            raise ValueError("READ_ONLY_DISCOVERY cannot allow mutation")
