"""Deterministic, project-confined native execution primitives.

This module is deliberately lower-level than orchestration. It does not decide
*what* should run and must not be exposed as an unrestricted model-facing
shell. Trusted adapters/policy layers construct the specs consumed here.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Mapping, Sequence


class NativeExecutionError(RuntimeError):
    """Code-only execution failure safe for higher-level logging."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_TEMP_CLEANUP_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.4)


def _remove_temp_tree_with_permission_retry(
    target: Path,
    *,
    retry_delays: tuple[float, ...] = _TEMP_CLEANUP_RETRY_DELAYS,
    sleep_fn=None,
) -> None:
    """Remove one private execution temp tree with finite transient-lock retry."""
    sleeper = time.sleep if sleep_fn is None else sleep_fn
    for delay in retry_delays:
        try:
            shutil.rmtree(target)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            sleeper(delay)
    try:
        shutil.rmtree(target)
    except FileNotFoundError:
        return


_TEMP_ORPHAN_STALE_AFTER_SECONDS = 86_400.0
_TEMP_ORPHAN_SWEEP_LIMIT = 32

_TEMP_OWNER_LOCK_NAME = ".a-conductor-owner.lock"


def _lock_execution_temp_handle(handle: BinaryIO, *, blocking: bool) -> bool:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
        try:
            msvcrt.locking(handle.fileno(), mode, 1)
        except OSError:
            return False
        return True

    import fcntl

    flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
    try:
        fcntl.flock(handle.fileno(), flags)
    except (BlockingIOError, OSError):
        return False
    return True


def _unlock_execution_temp_handle(handle: BinaryIO) -> None:
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


def _acquire_execution_temp_lease(temp_dir: Path) -> BinaryIO:
    handle = (Path(temp_dir) / _TEMP_OWNER_LOCK_NAME).open("a+b")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"1")
            handle.flush()
        if not _lock_execution_temp_handle(handle, blocking=True):
            raise OSError("EXECUTION_TEMP_LEASE_FAILED")
        return handle
    except Exception:
        handle.close()
        raise


def _release_execution_temp_lease(handle: BinaryIO) -> None:
    try:
        _unlock_execution_temp_handle(handle)
    finally:
        handle.close()


def _execution_temp_lease_available(temp_dir: Path) -> bool:
    lock_path = Path(temp_dir) / _TEMP_OWNER_LOCK_NAME
    if not lock_path.exists():
        return True
    try:
        handle = lock_path.open("r+b")
    except OSError:
        return False
    locked = False
    try:
        locked = _lock_execution_temp_handle(handle, blocking=False)
        return locked
    finally:
        if locked:
            _unlock_execution_temp_handle(handle)
        handle.close()


def _execution_temp_age_anchor(stat_result) -> float:
    return min(float(stat_result.st_mtime), float(stat_result.st_ctime))


def _sweep_stale_execution_temp_trees(
    temp_root: Path,
    *,
    now: float | None = None,
    stale_after_seconds: float = _TEMP_ORPHAN_STALE_AFTER_SECONDS,
    max_candidates: int = _TEMP_ORPHAN_SWEEP_LIMIT,
) -> int:
    """Best-effort cleanup for stale private execution temp trees only."""
    current = time.time() if now is None else float(now)
    try:
        candidates = tuple(sorted(Path(temp_root).glob("a-conductor-exec-*")))
    except OSError:
        return 0
    removed = 0
    attempted = 0
    for candidate in candidates:
        try:
            if candidate.is_symlink() or not candidate.is_dir():
                continue
            if current - _execution_temp_age_anchor(candidate.stat()) < stale_after_seconds:
                continue
            if attempted >= max_candidates:
                break
            if not _execution_temp_lease_available(candidate):
                continue
            attempted += 1
            _remove_temp_tree_with_permission_retry(candidate, retry_delays=())
        except OSError:
            continue
        removed += 1
    return removed


_SAFE_INHERITED_ENVIRONMENT_KEYS = frozenset(
    {
        "appdata",
        "comspec",
        "home",
        "homedrive",
        "homepath",
        "localappdata",
        "path",
        "pathext",
        "systemroot",
        "temp",
        "tmp",
        "userprofile",
        "username",
        "windir",
    }
)


def _require_positive_int(value: int, code: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise NativeExecutionError(code)
    return value


def _normalize_root(root: str | Path) -> Path:
    candidate = Path(root).expanduser()
    if not candidate.is_absolute():
        raise NativeExecutionError("ROOT_PATH_INVALID")
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise NativeExecutionError("ROOT_PATH_INVALID") from exc
    if not resolved.is_dir():
        raise NativeExecutionError("ROOT_NOT_FOUND")
    return resolved


def _normalize_name_tuple(values: Sequence[str], code: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise NativeExecutionError(code)
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise NativeExecutionError(code)
        normalized.append(value.strip())
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class NativeExecutionScope:
    root: Path | str
    mutation_allowed: bool = False
    allowed_executables: tuple[str, ...] = ()
    allowed_environment_overrides: tuple[str, ...] = ()
    max_timeout_seconds: int = 300
    max_output_bytes: int = 1_048_576
    max_file_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", _normalize_root(self.root))
        if not isinstance(self.mutation_allowed, bool):
            raise NativeExecutionError("MUTATION_AUTHORITY_INVALID")
        object.__setattr__(
            self,
            "allowed_executables",
            _normalize_name_tuple(self.allowed_executables, "EXECUTABLE_POLICY_INVALID"),
        )
        object.__setattr__(
            self,
            "allowed_environment_overrides",
            _normalize_name_tuple(
                self.allowed_environment_overrides,
                "ENV_POLICY_INVALID",
            ),
        )
        _require_positive_int(self.max_timeout_seconds, "TIMEOUT_POLICY_INVALID")
        _require_positive_int(self.max_output_bytes, "OUTPUT_LIMIT_INVALID")
        _require_positive_int(self.max_file_bytes, "FILE_LIMIT_INVALID")

    def resolve_relative(
        self,
        relative_path: str | Path,
        *,
        must_exist: bool = False,
    ) -> Path:
        raw = Path(relative_path)
        if raw.is_absolute():
            raise NativeExecutionError("ABSOLUTE_PATH_FORBIDDEN")
        if not str(raw).strip():
            raise NativeExecutionError("PATH_INVALID")
        try:
            candidate = (Path(self.root) / raw).resolve(strict=False)
        except OSError as exc:
            raise NativeExecutionError("PATH_INVALID") from exc
        try:
            candidate.relative_to(Path(self.root))
        except ValueError as exc:
            raise NativeExecutionError("PATH_OUTSIDE_ROOT") from exc
        if must_exist and not candidate.exists():
            raise NativeExecutionError("PATH_NOT_FOUND")
        return candidate

    def relative_display(self, path: Path) -> str:
        relative = path.relative_to(Path(self.root))
        value = relative.as_posix()
        return value if value else "."


@dataclass(frozen=True, slots=True)
class NativeReadResult:
    relative_path: str
    content: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class NativeDirectoryEntry:
    name: str
    kind: str
    size_bytes: int | None


@dataclass(frozen=True, slots=True)
class NativeWriteResult:
    relative_path: str
    size_bytes: int
    sha256: str
    created: bool


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_sha256(value: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise NativeExecutionError("SHA256_INVALID")
    lowered = value.casefold()
    if any(char not in "0123456789abcdef" for char in lowered):
        raise NativeExecutionError("SHA256_INVALID")
    return lowered


class NativeFileSystem:
    """Bounded text filesystem operations confined to one project root."""

    def __init__(self, scope: NativeExecutionScope) -> None:
        self._scope = scope

    def read_text(
        self,
        relative_path: str | Path,
        *,
        max_bytes: int | None = None,
    ) -> NativeReadResult:
        limit = self._scope.max_file_bytes if max_bytes is None else max_bytes
        _require_positive_int(limit, "FILE_LIMIT_INVALID")
        if limit > self._scope.max_file_bytes:
            raise NativeExecutionError("FILE_LIMIT_EXCEEDED")
        target = self._scope.resolve_relative(relative_path, must_exist=True)
        if not target.is_file():
            raise NativeExecutionError("FILE_NOT_FOUND")
        try:
            size = target.stat().st_size
        except OSError as exc:
            raise NativeExecutionError("FILE_READ_FAILED") from exc
        if size > limit:
            raise NativeExecutionError("FILE_TOO_LARGE")
        try:
            raw = target.read_bytes()
            content = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise NativeExecutionError("FILE_ENCODING_INVALID") from exc
        except OSError as exc:
            raise NativeExecutionError("FILE_READ_FAILED") from exc
        return NativeReadResult(
            relative_path=self._scope.relative_display(target),
            content=content,
            size_bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
        )

    def list_directory(
        self,
        relative_path: str | Path = ".",
    ) -> tuple[NativeDirectoryEntry, ...]:
        target = self._scope.resolve_relative(relative_path, must_exist=True)
        if not target.is_dir():
            raise NativeExecutionError("DIRECTORY_NOT_FOUND")
        entries: list[NativeDirectoryEntry] = []
        try:
            children = sorted(target.iterdir(), key=lambda path: (path.name.casefold(), path.name))
            for child in children:
                if child.is_symlink():
                    entries.append(NativeDirectoryEntry(child.name, "symlink", None))
                elif child.is_dir():
                    entries.append(NativeDirectoryEntry(child.name, "directory", None))
                elif child.is_file():
                    entries.append(
                        NativeDirectoryEntry(child.name, "file", child.stat().st_size)
                    )
                else:
                    entries.append(NativeDirectoryEntry(child.name, "other", None))
        except OSError as exc:
            raise NativeExecutionError("DIRECTORY_READ_FAILED") from exc
        return tuple(entries)

    def write_text(
        self,
        relative_path: str | Path,
        content: str,
        *,
        expected_sha256: str | None = None,
    ) -> NativeWriteResult:
        if not self._scope.mutation_allowed:
            raise NativeExecutionError("MUTATION_FORBIDDEN")
        if not isinstance(content, str):
            raise NativeExecutionError("CONTENT_INVALID")
        encoded = content.encode("utf-8")
        if len(encoded) > self._scope.max_file_bytes:
            raise NativeExecutionError("FILE_TOO_LARGE")

        target = self._scope.resolve_relative(relative_path)
        parent = target.parent
        if not parent.is_dir():
            raise NativeExecutionError("PARENT_NOT_FOUND")
        if target.exists() and not target.is_file():
            raise NativeExecutionError("FILE_TARGET_INVALID")

        existed = target.exists()
        validated_precondition: str | None = None
        if existed:
            if expected_sha256 is None:
                raise NativeExecutionError("OVERWRITE_PRECONDITION_REQUIRED")
            validated_precondition = _validate_sha256(expected_sha256)
            try:
                if _sha256_file(target) != validated_precondition:
                    raise NativeExecutionError("FILE_PRECONDITION_FAILED")
            except OSError as exc:
                raise NativeExecutionError("FILE_READ_FAILED") from exc
        elif expected_sha256 is not None:
            raise NativeExecutionError("FILE_PRECONDITION_FAILED")

        temporary = parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            if existed and validated_precondition is not None:
                if not target.is_file() or _sha256_file(target) != validated_precondition:
                    raise NativeExecutionError("FILE_PRECONDITION_FAILED")
            os.replace(temporary, target)
        except NativeExecutionError:
            raise
        except OSError as exc:
            raise NativeExecutionError("FILE_WRITE_FAILED") from exc
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

        return NativeWriteResult(
            relative_path=self._scope.relative_display(target),
            size_bytes=len(encoded),
            sha256=hashlib.sha256(encoded).hexdigest(),
            created=not existed,
        )


@dataclass(frozen=True, slots=True)
class NativeCommandSpec:
    argv: tuple[str, ...] | Sequence[str]
    cwd: str | Path = "."
    timeout_seconds: int = 30
    environment_overrides: tuple[tuple[str, str], ...] = ()
    mutation_intent: bool = False


@dataclass(frozen=True, slots=True)
class NativeCommandResult:
    executable: str
    argument_count: int
    exit_code: int | None
    timed_out: bool
    stdout: str
    stderr: str
    stdout_sha256: str
    stderr_sha256: str
    stdout_truncated: bool
    stderr_truncated: bool


def _build_environment(
    source: Mapping[str, str],
    overrides: tuple[tuple[str, str], ...],
    allowed_override_keys: tuple[str, ...],
) -> dict[str, str]:
    environment: dict[str, str] = {}
    for key, value in source.items():
        if (
            isinstance(key, str)
            and isinstance(value, str)
            and key.casefold() in _SAFE_INHERITED_ENVIRONMENT_KEYS
        ):
            environment[key] = value

    allowed = {key.casefold() for key in allowed_override_keys}
    seen: set[str] = set()
    for pair in overrides:
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise NativeExecutionError("ENV_OVERRIDE_INVALID")
        key, value = pair
        if (
            not isinstance(key, str)
            or not key.strip()
            or "=" in key
            or "\x00" in key
            or not isinstance(value, str)
            or "\x00" in value
        ):
            raise NativeExecutionError("ENV_OVERRIDE_INVALID")
        folded = key.casefold()
        if folded not in allowed:
            raise NativeExecutionError("ENV_OVERRIDE_NOT_ALLOWED")
        if folded in seen:
            raise NativeExecutionError("ENV_OVERRIDE_INVALID")
        seen.add(folded)
        for existing_key in tuple(environment):
            if existing_key.casefold() == folded:
                del environment[existing_key]
        environment[key] = value
    return environment


def _bounded_file_result(path: Path, max_bytes: int) -> tuple[str, str, bool]:
    digest = hashlib.sha256()
    captured = bytearray()
    total = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
            if len(captured) < max_bytes:
                remaining = max_bytes - len(captured)
                captured.extend(chunk[:remaining])
    return (
        bytes(captured).decode("utf-8", errors="replace"),
        digest.hexdigest(),
        total > max_bytes,
    )


class NativeSubprocessRunner:
    """Run an already-authorized argv command without a shell."""

    def __init__(
        self,
        scope: NativeExecutionScope,
        *,
        environment_source: Mapping[str, str] | None = None,
    ) -> None:
        self._scope = scope
        source = os.environ if environment_source is None else environment_source
        self._environment_source = dict(source)

    def run(self, spec: NativeCommandSpec) -> NativeCommandResult:
        if isinstance(spec.argv, (str, bytes)) or not isinstance(spec.argv, Sequence):
            raise NativeExecutionError("ARGV_INVALID")
        argv = tuple(spec.argv)
        if not argv:
            raise NativeExecutionError("ARGV_INVALID")
        for argument in argv:
            if not isinstance(argument, str) or not argument or "\x00" in argument:
                raise NativeExecutionError("ARGV_INVALID")
        if not isinstance(spec.mutation_intent, bool):
            raise NativeExecutionError("MUTATION_INTENT_INVALID")
        if spec.mutation_intent and not self._scope.mutation_allowed:
            raise NativeExecutionError("MUTATION_FORBIDDEN")

        executable = Path(argv[0]).name
        allowed = {Path(value).name.casefold() for value in self._scope.allowed_executables}
        if executable.casefold() not in allowed:
            raise NativeExecutionError("EXECUTABLE_NOT_ALLOWED")

        timeout = _require_positive_int(spec.timeout_seconds, "TIMEOUT_INVALID")
        if timeout > self._scope.max_timeout_seconds:
            raise NativeExecutionError("TIMEOUT_INVALID")
        cwd = self._scope.resolve_relative(spec.cwd, must_exist=True)
        if not cwd.is_dir():
            raise NativeExecutionError("CWD_INVALID")
        environment = _build_environment(
            self._environment_source,
            spec.environment_overrides,
            self._scope.allowed_environment_overrides,
        )

        timed_out = False
        exit_code: int | None = None
        _sweep_stale_execution_temp_trees(Path(tempfile.gettempdir()))
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix="a-conductor-exec-"))
        except OSError as exc:
            raise NativeExecutionError("COMMAND_EXECUTION_FAILED") from exc
        try:
            lease = _acquire_execution_temp_lease(temp_dir)
            try:
                stdout_path = temp_dir / "stdout.bin"
                stderr_path = temp_dir / "stderr.bin"
                with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
                    try:
                        completed = subprocess.run(
                            list(argv),
                            cwd=str(cwd),
                            shell=False,
                            stdin=subprocess.DEVNULL,
                            stdout=stdout_handle,
                            stderr=stderr_handle,
                            env=environment,
                            timeout=timeout,
                            check=False,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        )
                        exit_code = completed.returncode
                    except subprocess.TimeoutExpired:
                        timed_out = True
                stdout, stdout_sha256, stdout_truncated = _bounded_file_result(
                    stdout_path,
                    self._scope.max_output_bytes,
                )
                stderr, stderr_sha256, stderr_truncated = _bounded_file_result(
                    stderr_path,
                    self._scope.max_output_bytes,
                )
            finally:
                _release_execution_temp_lease(lease)
        except Exception as exc:
            try:
                _remove_temp_tree_with_permission_retry(temp_dir)
            except OSError:
                pass
            if isinstance(exc, NativeExecutionError):
                raise
            if isinstance(exc, OSError):
                raise NativeExecutionError("COMMAND_EXECUTION_FAILED") from exc
            raise

        try:
            _remove_temp_tree_with_permission_retry(temp_dir)
        except OSError as exc:
            raise NativeExecutionError("COMMAND_CLEANUP_FAILED") from exc

        return NativeCommandResult(
            executable=executable,
            argument_count=len(argv),
            exit_code=exit_code,
            timed_out=timed_out,
            stdout=stdout,
            stderr=stderr,
            stdout_sha256=stdout_sha256,
            stderr_sha256=stderr_sha256,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
        )
