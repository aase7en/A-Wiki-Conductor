"""Safe non-secret runtime setup for A-Workers and project identity."""

from __future__ import annotations

import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from .control_center import ControlCenterService
from .project_identity import GitReadOnlyRunner, StrictReadOnlyGitRunner
from .serena_config_store import (
    LocalReferencePath,
    SerenaConfigStoreError,
    SQLiteSerenaConfigStore,
)
from .serena_runtime import (
    ProjectIdentityPolicy,
    SerenaProjectBinding,
    SerenaWorkerConfig,
)
from .registry import windows_worktree_key


class RuntimeSetupError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SetupReadiness:
    ready: bool
    code: str


@dataclass(frozen=True, slots=True)
class WorkerSetupDraft:
    worker_id: str
    configured: bool
    instance_root: str
    serena_home: str
    run_dir: str
    log_dir: str
    health_host: str
    health_port: int
    runtime_executable_ref: str
    profile_template_ref: str
    tunnel_binding_ref: str | None
    reference_file_path: str | None
    reference_allowed_root: str | None
    startup_timeout_seconds: int = 15
    stop_timeout_seconds: int = 10


def _absolute(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        raise RuntimeSetupError("PATH_INVALID")
    try:
        return candidate.resolve(strict=False)
    except OSError as exc:
        raise RuntimeSetupError("PATH_INVALID") from exc


def _worker_number(worker_id: str) -> int:
    try:
        value = int(worker_id.rsplit("-", 1)[1])
    except (IndexError, ValueError) as exc:
        raise RuntimeSetupError("WORKER_ID_INVALID") from exc
    if value < 1 or value > 99:
        raise RuntimeSetupError("WORKER_ID_INVALID")
    return value


class RuntimeSetupService:
    def __init__(
        self,
        *,
        control_center: ControlCenterService,
        config_store: SQLiteSerenaConfigStore,
        git_runner: GitReadOnlyRunner | None = None,
        instance_base: str | Path | None = None,
    ) -> None:
        self._control_center = control_center
        self._config_store = config_store
        self._git = git_runner or StrictReadOnlyGitRunner()
        if instance_base is None:
            from .platform_support import default_instances_root

            instance_base = default_instances_root()
        self._instance_base = _absolute(instance_base)

    def _worker_row(self, worker_id: str):
        for row in self._control_center.snapshot().workers:
            if row.worker_id == worker_id:
                return row
        raise RuntimeSetupError("WORKER_NOT_FOUND")

    def worker_setup(self, worker_id: str) -> WorkerSetupDraft:
        self._worker_row(worker_id)
        existing = self._config_store.get_worker_config(worker_id)
        if existing is None:
            number = _worker_number(worker_id)
            root = (self._instance_base / worker_id).resolve(strict=False)
            return WorkerSetupDraft(
                worker_id=worker_id,
                configured=False,
                instance_root=str(root),
                serena_home=str(root / "serena-home"),
                run_dir=str(root / "run"),
                log_dir=str(root / "logs"),
                health_host="127.0.0.1",
                health_port=18010 + number,
                runtime_executable_ref="",
                profile_template_ref="",
                tunnel_binding_ref=None,
                reference_file_path=None,
                reference_allowed_root=None,
                startup_timeout_seconds=15,
                stop_timeout_seconds=10,
            )

        reference_file_path: str | None = None
        reference_allowed_root: str | None = None
        if existing.tunnel_binding_ref is not None:
            reference = self._config_store.get_local_reference(
                existing.tunnel_binding_ref
            )
            if reference is not None:
                reference_file_path = reference.file_path
                reference_allowed_root = reference.allowed_root
        return WorkerSetupDraft(
            worker_id=existing.worker_id,
            configured=True,
            instance_root=existing.instance_root,
            serena_home=existing.serena_home,
            run_dir=existing.run_dir,
            log_dir=existing.log_dir,
            health_host=existing.health_host,
            health_port=existing.health_port,
            runtime_executable_ref=existing.runtime_executable_ref,
            profile_template_ref=existing.profile_template_ref,
            tunnel_binding_ref=existing.tunnel_binding_ref,
            reference_file_path=reference_file_path,
            reference_allowed_root=reference_allowed_root,
            startup_timeout_seconds=existing.startup_timeout_seconds,
            stop_timeout_seconds=existing.stop_timeout_seconds,
        )

    @staticmethod
    def _copy_serena_config(source: Path, target: Path) -> None:
        if not source.is_file():
            raise RuntimeSetupError("SERENA_CONFIG_SOURCE_NOT_FOUND")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(
                f".{target.name}.{uuid.uuid4().hex}.tmp"
            )
            try:
                shutil.copyfile(source, temporary)
                with temporary.open("rb+") as handle:
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
            finally:
                if temporary.exists():
                    temporary.unlink(missing_ok=True)
        except RuntimeSetupError:
            raise
        except OSError as exc:
            raise RuntimeSetupError("SERENA_CONFIG_COPY_FAILED") from exc

    def save_worker_setup(
        self,
        draft: WorkerSetupDraft,
        *,
        serena_config_source: str | Path | None,
    ) -> WorkerSetupDraft:
        self._worker_row(draft.worker_id)
        if not isinstance(draft.runtime_executable_ref, str) or not draft.runtime_executable_ref.strip():
            raise RuntimeSetupError("RUNTIME_EXECUTABLE_NOT_FOUND")
        executable = _absolute(draft.runtime_executable_ref)
        if not executable.is_file():
            raise RuntimeSetupError("RUNTIME_EXECUTABLE_NOT_FOUND")
        if not isinstance(draft.profile_template_ref, str) or not draft.profile_template_ref.strip():
            raise RuntimeSetupError("PROFILE_TEMPLATE_NOT_FOUND")
        template = _absolute(draft.profile_template_ref)
        if not template.is_file():
            raise RuntimeSetupError("PROFILE_TEMPLATE_NOT_FOUND")
        instance_root = _absolute(draft.instance_root)
        serena_home = _absolute(draft.serena_home)
        run_dir = _absolute(draft.run_dir)
        log_dir = _absolute(draft.log_dir)
        target_config = serena_home / "serena_config.yml"

        source_path: Path | None = None
        if serena_config_source is not None:
            source_path = _absolute(serena_config_source)
            if not source_path.is_file():
                raise RuntimeSetupError("SERENA_CONFIG_SOURCE_NOT_FOUND")
        elif not target_config.is_file():
            raise RuntimeSetupError("SERENA_CONFIG_SOURCE_REQUIRED")

        tunnel_ref = (
            draft.tunnel_binding_ref.strip()
            if isinstance(draft.tunnel_binding_ref, str)
            and draft.tunnel_binding_ref.strip()
            else None
        )
        reference: LocalReferencePath | None = None
        if tunnel_ref is not None:
            if not draft.reference_file_path or not draft.reference_allowed_root:
                raise RuntimeSetupError("TUNNEL_REFERENCE_METADATA_REQUIRED")
            reference = LocalReferencePath(
                reference_id=tunnel_ref,
                file_path=str(_absolute(draft.reference_file_path)),
                allowed_root=str(_absolute(draft.reference_allowed_root)),
            )

        config = SerenaWorkerConfig(
            worker_id=draft.worker_id,
            runtime_id=f"runtime-{draft.worker_id}",
            instance_root=str(instance_root),
            serena_home=str(serena_home),
            health_host=draft.health_host,
            health_port=draft.health_port,
            tunnel_binding_ref=tunnel_ref,
            credential_ref=None,
            runtime_executable_ref=str(executable),
            profile_template_ref=str(template),
            run_dir=str(run_dir),
            log_dir=str(log_dir),
            startup_timeout_seconds=draft.startup_timeout_seconds,
            stop_timeout_seconds=draft.stop_timeout_seconds,
        )

        if source_path is not None:
            self._copy_serena_config(source_path, target_config)
        try:
            self._config_store.save_worker_config(config)
            if reference is not None:
                self._config_store.save_local_reference(reference)
        except (SerenaConfigStoreError, ValueError) as exc:
            code = getattr(exc, "code", "CONFIG_INVALID")
            raise RuntimeSetupError(code) from exc
        return self.worker_setup(draft.worker_id)

    def _assigned_project(self, worker_id: str):
        row = self._worker_row(worker_id)
        if row.assignment_id is None or row.project_id is None:
            raise RuntimeSetupError("ASSIGNMENT_MISSING")
        project = next(
            (
                project
                for project in self._control_center.snapshot().projects
                if project.project_id == row.project_id
            ),
            None,
        )
        if project is None:
            raise RuntimeSetupError("PROJECT_NOT_FOUND")
        return row, project

    def capture_exact_project_identity(
        self,
        worker_id: str,
    ) -> SerenaProjectBinding:
        row, project = self._assigned_project(worker_id)
        worktree = _absolute(project.root_path)
        root = self._git.show_toplevel(worktree)
        if not root.success:
            raise RuntimeSetupError("PROJECT_GIT_IDENTITY_FAILED")
        if windows_worktree_key(root.stdout) != windows_worktree_key(str(worktree)):
            raise RuntimeSetupError("PROJECT_ROOT_MISMATCH")
        branch = self._git.branch(worktree)
        head = self._git.head(worktree)
        if not branch.success or not head.success or not branch.stdout or not head.stdout:
            raise RuntimeSetupError("PROJECT_GIT_IDENTITY_FAILED")
        binding = SerenaProjectBinding(
            project_id=project.project_id,
            worktree_path=str(worktree),
            identity_policy=ProjectIdentityPolicy.EXACT,
            expected_branch=branch.stdout,
            expected_head=head.stdout,
            mutation_allowed=bool(row.mutation_allowed),
        )
        try:
            self._config_store.save_project_binding(binding)
        except SerenaConfigStoreError as exc:
            raise RuntimeSetupError(exc.code) from exc
        return binding

    def save_no_git_project_identity(
        self,
        worker_id: str,
    ) -> SerenaProjectBinding:
        row, project = self._assigned_project(worker_id)
        binding = SerenaProjectBinding(
            project_id=project.project_id,
            worktree_path=str(_absolute(project.root_path)),
            identity_policy=ProjectIdentityPolicy.NO_GIT,
            expected_branch=None,
            expected_head=None,
            mutation_allowed=bool(row.mutation_allowed),
        )
        try:
            self._config_store.save_project_binding(binding)
        except SerenaConfigStoreError as exc:
            raise RuntimeSetupError(exc.code) from exc
        return binding

    def lifecycle_readiness(self, worker_id: str) -> SetupReadiness:
        row = self._worker_row(worker_id)
        if row.assignment_id is None or row.project_id is None:
            return SetupReadiness(False, "ASSIGNMENT_MISSING")
        config = self._config_store.get_worker_config(worker_id)
        if config is None:
            return SetupReadiness(False, "WORKER_CONFIG_MISSING")
        binding = self._config_store.get_project_binding(row.project_id)
        if binding is None:
            return SetupReadiness(False, "PROJECT_BINDING_MISSING")
        if not Path(config.runtime_executable_ref).is_file():
            return SetupReadiness(False, "RUNTIME_EXECUTABLE_NOT_FOUND")
        if not Path(config.profile_template_ref).is_file():
            return SetupReadiness(False, "PROFILE_TEMPLATE_NOT_FOUND")
        if not (Path(config.serena_home) / "serena_config.yml").is_file():
            return SetupReadiness(False, "SERENA_CONFIG_NOT_FOUND")
        if config.tunnel_binding_ref is not None:
            reference = self._config_store.get_local_reference(
                config.tunnel_binding_ref
            )
            if reference is None:
                return SetupReadiness(False, "TUNNEL_REFERENCE_METADATA_MISSING")
            if not Path(reference.file_path).is_file():
                return SetupReadiness(False, "TUNNEL_REFERENCE_FILE_NOT_FOUND")
        return SetupReadiness(True, "READY")
