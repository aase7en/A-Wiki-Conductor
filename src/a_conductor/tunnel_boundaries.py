"""Secret-safe tunnel reference, ownership, and preflight boundaries."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Mapping

from .owned_process import build_owned_child_environment
from .serena_lifecycle_backend import SerenaOperationResult
from .serena_materializer import (
    SerenaMaterializedRuntime,
    discover_profile_placeholders,
)
from .serena_runtime import SerenaProjectBinding, SerenaWorkerConfig


class ReferenceResolutionError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _resolved(path: Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


class LocalFileReferenceStore:
    """Map opaque reference IDs to allowlisted local read-only files."""

    def __init__(
        self,
        references: Mapping[str, Path],
        *,
        allowed_roots: tuple[Path, ...],
    ) -> None:
        if not allowed_roots:
            raise ValueError("at least one allowed root is required")
        roots = tuple(_resolved(root) for root in allowed_roots)
        normalized: dict[str, Path] = {}
        for reference, path in references.items():
            if not isinstance(reference, str) or not reference.strip():
                raise ValueError("reference ID must not be blank")
            if reference in normalized:
                raise ValueError("duplicate reference ID")
            candidate = _resolved(Path(path))
            if not any(candidate == root or root in candidate.parents for root in roots):
                raise ValueError("reference path must stay under an allowed root")
            normalized[reference] = candidate
        self._references = normalized

    def read_text(self, reference: str) -> str:
        if not isinstance(reference, str) or not reference.strip():
            raise ReferenceResolutionError("REFERENCE_NOT_FOUND")
        path = self._references.get(reference)
        if path is None:
            raise ReferenceResolutionError("REFERENCE_NOT_FOUND")
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ReferenceResolutionError("REFERENCE_READ_FAILED") from exc
        value = raw.strip()
        if (
            not value
            or "\x00" in value
            or "\n" in value
            or "\r" in value
        ):
            raise ReferenceResolutionError("REFERENCE_VALUE_INVALID")
        return value


class ReferenceBackedSerenaTokenProvider:
    def __init__(self, reference_store: LocalFileReferenceStore) -> None:
        self._reference_store = reference_store

    def resolve(
        self,
        worker: SerenaWorkerConfig,
        binding: SerenaProjectBinding,
    ) -> Mapping[str, str]:
        template_path = _resolved(Path(worker.profile_template_ref))
        try:
            template_text = template_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ReferenceResolutionError("PROFILE_TEMPLATE_READ_FAILED") from exc
        placeholders = discover_profile_placeholders(template_text)
        values: dict[str, str] = {}
        for placeholder in placeholders:
            if placeholder == "__TUNNEL_ID__":
                if worker.tunnel_binding_ref is None:
                    raise ReferenceResolutionError("TUNNEL_REFERENCE_REQUIRED")
                values[placeholder] = self._reference_store.read_text(
                    worker.tunnel_binding_ref
                )
            elif placeholder == "__PROJECT_PATH__":
                values[placeholder] = str(
                    _resolved(Path(binding.worktree_path))
                )
            elif placeholder == "__SERENA_HOME__":
                values[placeholder] = str(_resolved(Path(worker.serena_home)))
            elif placeholder == "__HEALTH_LISTEN_ADDRESS__":
                values[placeholder] = f"{worker.health_host}:{worker.health_port}"
            elif placeholder == "__WORKER_ID__":
                values[placeholder] = worker.worker_id
            else:
                raise ReferenceResolutionError("PROFILE_TOKEN_UNSUPPORTED")
        return values


class LocalTunnelOwnershipGuard:
    """Check configured tunnel binding ownership without revealing binding values."""

    def __init__(self, owners: Mapping[str, str]) -> None:
        self._owners = dict(owners)

    def verify_available(self, worker: SerenaWorkerConfig) -> SerenaOperationResult:
        reference = worker.tunnel_binding_ref
        if reference is None:
            return SerenaOperationResult(success=True)
        owner = self._owners.get(reference)
        if owner is None or owner == worker.worker_id:
            return SerenaOperationResult(success=True)
        return SerenaOperationResult(success=False, error_code="TUNNEL_COLLISION")

    def verify_released(self, worker: SerenaWorkerConfig) -> SerenaOperationResult:
        reference = worker.tunnel_binding_ref
        if reference is None:
            return SerenaOperationResult(success=True)
        owner = self._owners.get(reference)
        if owner is None:
            return SerenaOperationResult(success=True)
        if owner == worker.worker_id:
            return SerenaOperationResult(
                success=False,
                error_code="TUNNEL_STILL_OWNED",
                recovery_required=True,
            )
        return SerenaOperationResult(success=False, error_code="TUNNEL_COLLISION")


class StrictTunnelClientPreflightService:
    """Run one bounded tunnel-client doctor command with redacted results."""

    def __init__(
        self,
        *,
        timeout_seconds: int = 15,
        environment_source: Mapping[str, str] | None = None,
    ) -> None:
        if (
            not isinstance(timeout_seconds, int)
            or isinstance(timeout_seconds, bool)
            or timeout_seconds < 1
        ):
            raise ValueError("timeout_seconds must be >= 1")
        self._timeout_seconds = timeout_seconds
        self._environment_source = (
            None if environment_source is None else dict(environment_source)
        )

    def run(self, materialized: SerenaMaterializedRuntime) -> SerenaOperationResult:
        spec = materialized.process_spec
        argv = [
            spec.command[0],
            "doctor",
            "--profile-file",
            str(materialized.profile_path),
            "--explain",
        ]
        try:
            completed = subprocess.run(
                argv,
                cwd=str(spec.cwd),
                shell=False,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=build_owned_child_environment(
                    spec,
                    self._environment_source,
                ),
                timeout=self._timeout_seconds,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            return SerenaOperationResult(
                success=False,
                error_code="TUNNEL_PREFLIGHT_TIMEOUT",
            )
        except OSError:
            return SerenaOperationResult(
                success=False,
                error_code="TUNNEL_PREFLIGHT_EXECUTION_FAILED",
            )
        if completed.returncode != 0:
            return SerenaOperationResult(
                success=False,
                error_code="TUNNEL_PREFLIGHT_FAILED",
            )
        return SerenaOperationResult(success=True)
