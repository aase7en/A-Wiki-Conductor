"""Exact-owned Windows process lifecycle primitive.

This module is the first production host-mutation boundary in A-Conductor.
It may spawn a process described by an ``OwnedProcessSpec`` and may stop only
an exact PID whose executable/profile fingerprint is proven by an injected
observer. Mutable metadata/log paths are confined to one explicit runtime root.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PureWindowsPath
from typing import Protocol

from .runtime_safety import ProcessObservation, ProcessOwnership, classify_process_ownership
from .windows_observer import PidMetadataObservation, PidMetadataStatus


class OwnedProcessMutationState(str, Enum):
    STARTED = "STARTED"
    ALREADY_RUNNING = "ALREADY_RUNNING"
    STOPPED = "STOPPED"
    NOT_RUNNING = "NOT_RUNNING"
    REFUSED = "REFUSED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class OwnedProcessMutationResult:
    state: OwnedProcessMutationState
    reason_code: str
    pid: int | None = None


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _require_pid(pid: int) -> int:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
        raise ValueError("pid must be >= 1")
    return pid


def _require_timeout(timeout_seconds: int) -> int:
    if (
        not isinstance(timeout_seconds, int)
        or isinstance(timeout_seconds, bool)
        or timeout_seconds < 1
    ):
        raise ValueError("stop_timeout_seconds must be >= 1")
    return timeout_seconds


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _require_under_root(path: Path, root: Path, field_name: str) -> Path:
    resolved = _resolved(path)
    resolved_root = _resolved(root)
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"{field_name} must stay under allowed_root")
    return resolved


@dataclass(frozen=True, slots=True)
class OwnedProcessSpec:
    allowed_root: Path
    cwd: Path
    pid_path: Path
    stdout_path: Path
    stderr_path: Path
    command: tuple[str, ...]
    expected_executable_name: str
    expected_profile_marker: str
    stop_timeout_seconds: int = 5

    def __post_init__(self) -> None:
        root = _resolved(Path(self.allowed_root))
        if not root.name and root.parent == root:
            raise ValueError("allowed_root must not be a filesystem root")

        cwd = _require_under_root(Path(self.cwd), root, "cwd")
        pid_path = _require_under_root(Path(self.pid_path), root, "pid_path")
        stdout_path = _require_under_root(Path(self.stdout_path), root, "stdout_path")
        stderr_path = _require_under_root(Path(self.stderr_path), root, "stderr_path")

        if not isinstance(self.command, tuple) or not self.command:
            raise ValueError("command must not be empty")
        if any(not isinstance(item, str) or not item for item in self.command):
            raise ValueError("command arguments must be non-empty strings")

        executable_name = _require_text(
            self.expected_executable_name,
            "expected_executable_name",
        ).strip()
        profile_marker = _require_text(
            self.expected_profile_marker,
            "expected_profile_marker",
        ).strip()
        command_executable = PureWindowsPath(self.command[0]).name
        if command_executable.casefold() != executable_name.casefold():
            raise ValueError("command executable does not match expected executable name")
        if not any(profile_marker.casefold() in arg.casefold() for arg in self.command[1:]):
            raise ValueError("profile marker is not present in command")
        _require_timeout(self.stop_timeout_seconds)

        object.__setattr__(self, "allowed_root", root)
        object.__setattr__(self, "cwd", cwd)
        object.__setattr__(self, "pid_path", pid_path)
        object.__setattr__(self, "stdout_path", stdout_path)
        object.__setattr__(self, "stderr_path", stderr_path)
        object.__setattr__(self, "expected_executable_name", executable_name)
        object.__setattr__(self, "expected_profile_marker", profile_marker)


class ProcessObserver(Protocol):
    def read_pid_metadata(self, pid_path: Path) -> PidMetadataObservation: ...

    def observe_process(
        self,
        *,
        pid: int,
        expected_executable_name: str,
        expected_profile_marker: str,
    ) -> ProcessObservation: ...


class ManagedChild(Protocol):
    pid: int

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...

    def poll(self) -> int | None: ...


class ProcessSpawner(Protocol):
    def spawn(self, spec: OwnedProcessSpec) -> ManagedChild: ...


class ExactPidTerminator(Protocol):
    def terminate(self, pid: int, timeout_seconds: int) -> bool: ...


class WindowsProcessSpawner:
    def spawn(self, spec: OwnedProcessSpec) -> subprocess.Popen[bytes]:
        spec.cwd.mkdir(parents=True, exist_ok=True)
        spec.stdout_path.parent.mkdir(parents=True, exist_ok=True)
        spec.stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_handle = spec.stdout_path.open("ab", buffering=0)
        stderr_handle = spec.stderr_path.open("ab", buffering=0)
        try:
            return subprocess.Popen(
                list(spec.command),
                cwd=str(spec.cwd),
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        finally:
            stdout_handle.close()
            stderr_handle.close()


class WindowsExactPidTerminator:
    def __init__(self, powershell_executable: str = "powershell.exe") -> None:
        self._powershell_executable = _require_text(
            powershell_executable,
            "powershell_executable",
        ).strip()

    def terminate(self, pid: int, timeout_seconds: int) -> bool:
        validated_pid = _require_pid(pid)
        timeout = _require_timeout(timeout_seconds)
        script = f"Stop-Process -Id {validated_pid} -Force -ErrorAction Stop"
        try:
            completed = subprocess.run(
                [
                    self._powershell_executable,
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    script,
                ],
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (subprocess.TimeoutExpired, OSError):
            return False
        return completed.returncode == 0


def _write_pid_atomic(path: Path, pid: int) -> None:
    validated_pid = _require_pid(pid)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{validated_pid}")
    try:
        temporary.write_text(str(validated_pid), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass


def _cleanup_exact_new_child(child: ManagedChild, timeout_seconds: int) -> bool:
    try:
        if child.poll() is not None:
            return True
        child.terminate()
        try:
            child.wait(timeout=timeout_seconds)
            return True
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=timeout_seconds)
            return True
    except Exception:
        return False


class WindowsOwnedProcessController:
    def __init__(
        self,
        *,
        observer: ProcessObserver,
        spawner: ProcessSpawner | None = None,
        terminator: ExactPidTerminator | None = None,
    ) -> None:
        self._observer = observer
        self._spawner = spawner or WindowsProcessSpawner()
        self._terminator = terminator or WindowsExactPidTerminator()

    def _ownership_for(self, spec: OwnedProcessSpec, pid: int) -> ProcessOwnership:
        observation = self._observer.observe_process(
            pid=pid,
            expected_executable_name=spec.expected_executable_name,
            expected_profile_marker=spec.expected_profile_marker,
        )
        return classify_process_ownership(observation)

    def start(self, spec: OwnedProcessSpec) -> OwnedProcessMutationResult:
        metadata = self._observer.read_pid_metadata(spec.pid_path)
        if metadata.status is PidMetadataStatus.INVALID:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                "PID_METADATA_INVALID",
            )
        if metadata.status is PidMetadataStatus.UNKNOWN:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                "PID_METADATA_UNKNOWN",
            )
        if metadata.status is PidMetadataStatus.VALID:
            assert metadata.pid is not None
            ownership = self._ownership_for(spec, metadata.pid)
            if ownership is ProcessOwnership.OWNED:
                return OwnedProcessMutationResult(
                    OwnedProcessMutationState.ALREADY_RUNNING,
                    "ALREADY_RUNNING",
                    metadata.pid,
                )
            if ownership is ProcessOwnership.STALE:
                return OwnedProcessMutationResult(
                    OwnedProcessMutationState.RECOVERY_REQUIRED,
                    "STALE_PID_METADATA",
                    metadata.pid,
                )
            if ownership is ProcessOwnership.MISMATCH:
                return OwnedProcessMutationResult(
                    OwnedProcessMutationState.REFUSED,
                    "PID_MISMATCH",
                    metadata.pid,
                )
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.REFUSED,
                "PROCESS_OWNERSHIP_UNKNOWN",
                metadata.pid,
            )

        spec.allowed_root.mkdir(parents=True, exist_ok=True)
        spec.cwd.mkdir(parents=True, exist_ok=True)
        spec.pid_path.parent.mkdir(parents=True, exist_ok=True)
        spec.stdout_path.parent.mkdir(parents=True, exist_ok=True)
        spec.stderr_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            child = self._spawner.spawn(spec)
        except Exception:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                "PROCESS_START_FAILED",
            )

        try:
            child_pid = _require_pid(child.pid)
            _write_pid_atomic(spec.pid_path, child_pid)
        except Exception:
            cleanup_ok = _cleanup_exact_new_child(child, spec.stop_timeout_seconds)
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                (
                    "PID_METADATA_PERSISTENCE_FAILED"
                    if cleanup_ok
                    else "PID_METADATA_PERSISTENCE_AND_CLEANUP_FAILED"
                ),
                getattr(child, "pid", None),
            )

        return OwnedProcessMutationResult(
            OwnedProcessMutationState.STARTED,
            "STARTED",
            child_pid,
        )

    def stop(self, spec: OwnedProcessSpec) -> OwnedProcessMutationResult:
        metadata = self._observer.read_pid_metadata(spec.pid_path)
        if metadata.status is PidMetadataStatus.ABSENT:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.NOT_RUNNING,
                "NOT_RUNNING",
            )
        if metadata.status is PidMetadataStatus.INVALID:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                "PID_METADATA_INVALID",
            )
        if metadata.status is PidMetadataStatus.UNKNOWN:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                "PID_METADATA_UNKNOWN",
            )

        assert metadata.pid is not None
        pid = metadata.pid
        ownership = self._ownership_for(spec, pid)
        if ownership is ProcessOwnership.STALE:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                "STALE_PID_METADATA",
                pid,
            )
        if ownership is ProcessOwnership.MISMATCH:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.REFUSED,
                "PID_MISMATCH",
                pid,
            )
        if ownership is ProcessOwnership.UNKNOWN:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.REFUSED,
                "PROCESS_OWNERSHIP_UNKNOWN",
                pid,
            )

        if not self._terminator.terminate(pid, spec.stop_timeout_seconds):
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                "PROCESS_STOP_FAILED",
                pid,
            )

        deadline = time.monotonic() + spec.stop_timeout_seconds
        while time.monotonic() < deadline:
            current = self._ownership_for(spec, pid)
            if current is ProcessOwnership.STALE:
                break
            if current in {ProcessOwnership.MISMATCH, ProcessOwnership.UNKNOWN}:
                return OwnedProcessMutationResult(
                    OwnedProcessMutationState.RECOVERY_REQUIRED,
                    "PROCESS_EXIT_OWNERSHIP_UNCERTAIN",
                    pid,
                )
            time.sleep(0.05)
        else:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                "PROCESS_EXIT_UNCONFIRMED",
                pid,
            )

        latest = self._observer.read_pid_metadata(spec.pid_path)
        if latest.status is not PidMetadataStatus.VALID or latest.pid != pid:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                "PID_METADATA_CHANGED",
                pid,
            )

        try:
            spec.pid_path.unlink()
        except OSError:
            return OwnedProcessMutationResult(
                OwnedProcessMutationState.RECOVERY_REQUIRED,
                "PID_METADATA_CLEANUP_FAILED",
                pid,
            )

        return OwnedProcessMutationResult(
            OwnedProcessMutationState.STOPPED,
            "STOPPED",
            pid,
        )
