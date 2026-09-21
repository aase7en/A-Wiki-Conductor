"""Bounded writer for allowlisted A-Wiki env secret keys (WO-P1-459).

Reuses the accepted private-Drive reader contract from
``awiki_environment_resolver`` (``_ENV_KEY_RE``, ``_parse_env_file``,
``AWikiDriveEnvironmentSource``) without ever changing the reader. The only
mutable surface is ``<authorized_drive_root>/secrets/global.env``; the root
must be supplied explicitly and is never auto-discovered.

Bounded contract:
- Operations are INSERT (absent key), ROTATE (exactly one existing plain
  assignment), DELETE (exactly one existing plain assignment). Duplicate or
  ``export``-prefixed target assignments fail typed without mutation.
- ``export KEY=`` lines and comment text are never treated as owned
  assignments; comments are preserved byte-for-byte.
- Values are rejected unless they round-trip exactly through the accepted
  reader (no surrounding whitespace, no symmetric quote wrapper, no
  line-break/control characters).
- Encoding marker (UTF-8 BOM), per-line newline style, final-newline shape,
  and unrelated bytes are preserved; the only documented exception is that
  INSERT may add the missing terminator after an unterminated final line.
- Writes go through a uniquely owned same-directory temporary file with
  flush+fsync, mode preservation, a pre-replace drift fence, atomic replace,
  read-back verification through the accepted source, and verified rollback.
  Rollback restores original bytes when safely possible and must prove both
  byte and permission/mode restoration before reporting success; an unproven
  mode restoration is reported as RECOVERY_REQUIRED, never WRITE_ROLLED_BACK.
  Ambiguous outcomes return distinct typed errors; there is never a blind
  retry. The writer never creates a missing target or secrets directory.
- ``_ENV_KEY_RE`` is shape validation only; every key must additionally be
  present in an explicit caller-supplied ``AWikiSecretWriteAuthority`` before
  any disk access. Raw values never appear in results, representations,
  error codes, temporary-file names, or exception messages.
"""

from __future__ import annotations

import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .awiki_environment_resolver import (
    _ENV_KEY_RE,
    _parse_env_file,
    AWikiDriveEnvironmentSource,
    AWikiEnvironmentResolutionError,
)

_BOM = b"\xef\xbb\xbf"
_TEMP_PREFIX = ".awiki-secret-writer-"
_ROLLBACK_PREFIX = ".awiki-secret-writer-rollback-"
_TEMP_SUFFIX = ".tmp"
_MAX_ALLOWED_KEYS = 64
_VALUE_FORBIDDEN_RE = re.compile(r"[\x00\x0b\x0c\r\n\x1c\x1d\x1e\x85\u2028\u2029]")


class AWikiSecretWriteError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _VerificationMismatch(Exception):
    """Internal sentinel: post-replace read-back did not match."""


@dataclass(frozen=True, slots=True)
class AWikiSecretWriteResult:
    operation: str
    key: str
    target: Path


class AWikiSecretWriteAuthority:
    """Explicit non-empty allowlist of writable keys; retains no secret values."""

    def __init__(self, allowed_keys: Iterable[str]) -> None:
        if isinstance(allowed_keys, (str, bytes)):
            raise AWikiSecretWriteError("ALLOWED_KEYS_INVALID")
        try:
            materialized = list(allowed_keys)
        except TypeError as exc:
            raise AWikiSecretWriteError("ALLOWED_KEYS_INVALID") from exc
        seen: set[str] = set()
        for member in materialized:
            if not isinstance(member, str) or _ENV_KEY_RE.fullmatch(member) is None:
                raise AWikiSecretWriteError("ALLOWED_KEYS_INVALID")
            if member in seen:
                raise AWikiSecretWriteError("ALLOWED_KEYS_INVALID")
            seen.add(member)
        if not seen or len(seen) > _MAX_ALLOWED_KEYS:
            raise AWikiSecretWriteError("ALLOWED_KEYS_INVALID")
        self._allowed_keys = frozenset(seen)

    def is_allowed(self, key: str) -> bool:
        return key in self._allowed_keys

    def __contains__(self, key: object) -> bool:
        return key in self._allowed_keys

    def __len__(self) -> int:
        return len(self._allowed_keys)

    def __repr__(self) -> str:
        return f"AWikiSecretWriteAuthority(keys={len(self._allowed_keys)})"


def _read_file_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _target_mode(path: Path) -> int:
    return os.stat(path).st_mode


def _target_identity(path: Path) -> tuple[int, int, int, int, int, int]:
    info = os.stat(path)
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _classify_line(content: str) -> tuple[str | None, bool]:
    """Mirror the accepted reader's per-line assignment ownership exactly."""
    line = content.strip()
    if not line or line[0] in "#;":
        return (None, False)
    is_export = False
    if line.startswith("export "):
        line = line[7:].strip()
        is_export = True
    if "=" not in line:
        return (None, False)
    key = line.split("=", 1)[0].strip()
    if _ENV_KEY_RE.fullmatch(key) is None:
        return (None, False)
    return (key, is_export)


def _split_line_units(captured: bytes) -> tuple[list[tuple[str, str]], bool]:
    """Split captured bytes into (content, exact-terminator) units."""
    has_bom = captured.startswith(_BOM)
    text = captured.decode("utf-8-sig", errors="strict")
    if text == "":
        return [], has_bom
    units: list[tuple[str, str]] = []
    parts = text.split("\n")
    for index, part in enumerate(parts):
        if index == len(parts) - 1:
            units.append((part, ""))
        elif part.endswith("\r"):
            units.append((part[:-1], "\r\n"))
        else:
            units.append((part, "\n"))
    return units, has_bom


def _dominant_terminator(units: list[tuple[str, str]]) -> str:
    crlf = sum(1 for _content, terminator in units if terminator == "\r\n")
    lf = sum(1 for _content, terminator in units if terminator == "\n")
    return "\r\n" if crlf > 0 and lf == 0 else "\n"


def _render_units(units: list[tuple[str, str]], has_bom: bool) -> bytes:
    text = "".join(content + terminator for content, terminator in units)
    return (_BOM if has_bom else b"") + text.encode("utf-8")


def _write_owned_temp(directory: Path, data: bytes, mode: int) -> Path:
    fd, name = tempfile.mkstemp(prefix=_TEMP_PREFIX, suffix=_TEMP_SUFFIX, dir=str(directory))
    temp_path = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        _best_effort_unlink(temp_path)
        raise AWikiSecretWriteError("WRITE_FAILED") from exc
    try:
        os.chmod(temp_path, stat.S_IMODE(mode))
    except OSError as exc:
        _best_effort_unlink(temp_path)
        raise AWikiSecretWriteError("TARGET_INSPECTION_FAILED") from exc
    return temp_path


def _best_effort_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _observe_target_bytes(path: Path) -> bytes | None:
    try:
        return _read_file_bytes(path)
    except OSError:
        return None


class AWikiSecretWriter:
    """Single-target bounded secret writer for ``secrets/global.env``."""

    def __init__(self, authorized_drive_root: str | Path, *, allowed_keys: AWikiSecretWriteAuthority) -> None:
        if not isinstance(allowed_keys, AWikiSecretWriteAuthority):
            raise TypeError("allowed_keys must be an AWikiSecretWriteAuthority")
        try:
            root = Path(authorized_drive_root).resolve(strict=True)
        except (OSError, RuntimeError, ValueError) as exc:
            raise AWikiSecretWriteError("DRIVE_ROOT_INVALID") from exc
        if not root.is_dir():
            raise AWikiSecretWriteError("DRIVE_ROOT_INVALID")
        self._root = root
        self._secrets_dir = root / "secrets"
        self._target = self._secrets_dir / "global.env"
        self._authority = allowed_keys
        self._source = AWikiDriveEnvironmentSource(root)

    @property
    def authorized_drive_root(self) -> Path:
        return self._root

    @property
    def target_path(self) -> Path:
        return self._target

    def insert(self, key: str, value: str) -> AWikiSecretWriteResult:
        return self._execute("insert", key, value)

    def rotate(self, key: str, value: str) -> AWikiSecretWriteResult:
        return self._execute("rotate", key, value)

    def delete(self, key: str) -> AWikiSecretWriteResult:
        return self._execute("delete", key, None)

    def _validate_key(self, key: str) -> None:
        if not isinstance(key, str) or _ENV_KEY_RE.fullmatch(key) is None:
            raise AWikiSecretWriteError("KEY_INVALID")
        if not self._authority.is_allowed(key):
            raise AWikiSecretWriteError("KEY_NOT_ALLOWED")

    def _validate_value(self, value: str | None) -> None:
        if not isinstance(value, str) or not value:
            raise AWikiSecretWriteError("VALUE_INVALID")
        if value != value.strip():
            raise AWikiSecretWriteError("VALUE_INVALID")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            raise AWikiSecretWriteError("VALUE_INVALID")
        if _VALUE_FORBIDDEN_RE.search(value) is not None:
            raise AWikiSecretWriteError("VALUE_INVALID")

    def _prepare_target(self) -> Path:
        secrets = self._secrets_dir
        try:
            if secrets.is_symlink() or self._target.is_symlink():
                raise AWikiSecretWriteError("TARGET_ESCAPE")
            for component in (secrets, self._target):
                junction_check = getattr(component, "is_junction", None)
                if junction_check is not None and junction_check():
                    raise AWikiSecretWriteError("TARGET_ESCAPE")
            if not secrets.is_dir():
                raise AWikiSecretWriteError("TARGET_DIRECTORY_MISSING")
            if not self._target.exists():
                raise AWikiSecretWriteError("TARGET_MISSING")
            if not self._target.is_file():
                raise AWikiSecretWriteError("TARGET_ESCAPE")
            if not self._target.resolve(strict=False).is_relative_to(self._root):
                raise AWikiSecretWriteError("TARGET_ESCAPE")
        except OSError as exc:
            raise AWikiSecretWriteError("TARGET_INSPECTION_FAILED") from exc
        return secrets

    def _execute(self, operation: str, key: str, value: str | None) -> AWikiSecretWriteResult:
        self._validate_key(key)
        if operation != "delete":
            self._validate_value(value)

        secrets_dir = self._prepare_target()
        target = self._target

        try:
            identity_before = _target_identity(target)
        except OSError as exc:
            raise AWikiSecretWriteError("TARGET_INSPECTION_FAILED") from exc
        try:
            captured = _read_file_bytes(target)
        except OSError as exc:
            raise AWikiSecretWriteError("TARGET_READ_FAILED") from exc
        try:
            original_identity = _target_identity(target)
            original_mode = _target_mode(target)
        except OSError as exc:
            raise AWikiSecretWriteError("TARGET_INSPECTION_FAILED") from exc
        if identity_before != original_identity:
            raise AWikiSecretWriteError("TARGET_DRIFTED")
        try:
            original_projection = dict(_parse_env_file(target))
        except AWikiEnvironmentResolutionError as exc:
            raise AWikiSecretWriteError("TARGET_PARSE_FAILED") from exc
        try:
            units, has_bom = _split_line_units(captured)
        except UnicodeDecodeError as exc:
            raise AWikiSecretWriteError("TARGET_PARSE_FAILED") from exc

        plain: list[int] = []
        exported: list[int] = []
        for index, (content, _terminator) in enumerate(units):
            owner, is_export = _classify_line(content)
            if owner == key:
                (exported if is_export else plain).append(index)

        if operation == "insert":
            if len(plain) > 1:
                raise AWikiSecretWriteError("DUPLICATE_KEY_ASSIGNMENT")
            if len(plain) == 1:
                raise AWikiSecretWriteError("KEY_ALREADY_EXISTS")
            if exported:
                raise AWikiSecretWriteError("EXPORT_SYNTAX_UNSUPPORTED")
        else:
            if len(plain) > 1 or (len(plain) == 1 and exported):
                raise AWikiSecretWriteError("DUPLICATE_KEY_ASSIGNMENT")
            if not plain and exported:
                raise AWikiSecretWriteError("EXPORT_SYNTAX_UNSUPPORTED")
            if not plain:
                raise AWikiSecretWriteError("KEY_NOT_FOUND")

        terminator = _dominant_terminator(units)
        assignment_line = f"{key}={value}"

        if operation == "insert":
            if not units:
                new_units = [(assignment_line, terminator)]
            else:
                new_units = list(units)
                last_content, last_terminator = new_units[-1]
                if last_content == "" and last_terminator == "":
                    new_units[-1] = (assignment_line, terminator)
                elif last_terminator == "":
                    new_units[-1] = (last_content, terminator)
                    new_units.append((assignment_line, terminator))
                else:
                    new_units.append((assignment_line, terminator))
        elif operation == "rotate":
            new_units = list(units)
            new_units[plain[0]] = (assignment_line, units[plain[0]][1])
        else:
            index = plain[0]
            new_units = units[:index] + units[index + 1 :]

        desired = _render_units(new_units, has_bom)

        if operation == "delete":
            expected_projection = {
                name: existing for name, existing in original_projection.items() if name != key
            }
        else:
            expected_projection = dict(original_projection)
            expected_projection[key] = value  # type: ignore[index]

        self._atomic_replace(
            target=target,
            secrets_dir=secrets_dir,
            desired=desired,
            captured=captured,
            original_identity=original_identity,
            original_mode=original_mode,
            expected_projection=expected_projection,
        )
        try:
            self._verify_after_write(operation, key, value)
        except Exception as exc:
            self._rollback(target, captured, original_mode)
            raise AWikiSecretWriteError("WRITE_ROLLED_BACK") from exc
        return AWikiSecretWriteResult(operation=operation, key=key, target=target)

    def _atomic_replace(
        self,
        *,
        target: Path,
        secrets_dir: Path,
        desired: bytes,
        captured: bytes,
        original_identity: tuple[int, int, int, int, int, int],
        original_mode: int,
        expected_projection: dict[str, str],
    ) -> None:
        temp_path: Path | None = None
        try:
            temp_path = _write_owned_temp(secrets_dir, desired, original_mode)
            try:
                observed_projection = _parse_env_file(temp_path)
            except AWikiEnvironmentResolutionError as exc:
                raise AWikiSecretWriteError("WRITE_VERIFICATION_FAILED") from exc
            if observed_projection != expected_projection:
                raise AWikiSecretWriteError("WRITE_VERIFICATION_FAILED")
            try:
                identity_before_replace = _target_identity(target)
            except OSError as exc:
                raise AWikiSecretWriteError("TARGET_INSPECTION_FAILED") from exc
            try:
                reobserved = _read_file_bytes(target)
            except OSError as exc:
                raise AWikiSecretWriteError("TARGET_READ_FAILED") from exc
            try:
                identity_after_read = _target_identity(target)
            except OSError as exc:
                raise AWikiSecretWriteError("TARGET_INSPECTION_FAILED") from exc
            if (
                reobserved != captured
                or identity_before_replace != original_identity
                or identity_after_read != original_identity
            ):
                raise AWikiSecretWriteError("TARGET_DRIFTED")
            try:
                os.replace(temp_path, target)
            except OSError as exc:
                current = _observe_target_bytes(target)
                if current is None:
                    raise AWikiSecretWriteError("RECOVERY_REQUIRED") from exc
                if current == captured:
                    raise AWikiSecretWriteError("REPLACE_FAILED") from exc
                if current == desired:
                    self._rollback(target, captured, original_mode)
                    raise AWikiSecretWriteError("WRITE_ROLLED_BACK") from exc
                raise AWikiSecretWriteError("RECOVERY_REQUIRED") from exc
            temp_path = None
        except OSError as exc:
            raise AWikiSecretWriteError("WRITE_FAILED") from exc
        finally:
            if temp_path is not None:
                _best_effort_unlink(temp_path)

    def _verify_after_write(self, operation: str, key: str, value: str | None) -> None:
        if operation == "delete":
            try:
                self._source.resolve_key(key)
            except AWikiEnvironmentResolutionError as exc:
                if exc.code == "SECRET_REFERENCE_NOT_FOUND":
                    return
                raise _VerificationMismatch from exc
            raise _VerificationMismatch("deleted key still resolves")
        try:
            observed = self._source.resolve_key(key)
        except AWikiEnvironmentResolutionError as exc:
            raise _VerificationMismatch from exc
        if observed != value:
            raise _VerificationMismatch("read-back mismatch")

    def _rollback(self, target: Path, original_bytes: bytes, original_mode: int) -> None:
        rollback_temp: Path | None = None
        mode_restoration_unproven = False
        try:
            try:
                fd, name = tempfile.mkstemp(
                    prefix=_ROLLBACK_PREFIX, suffix=_TEMP_SUFFIX, dir=str(target.parent)
                )
            except OSError as exc:
                raise AWikiSecretWriteError("RECOVERY_REQUIRED") from exc
            rollback_temp = Path(name)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(original_bytes)
                    handle.flush()
                    os.fsync(handle.fileno())
                try:
                    os.chmod(rollback_temp, stat.S_IMODE(original_mode))
                except OSError:
                    mode_restoration_unproven = True
                os.replace(rollback_temp, target)
                rollback_temp = None
            except OSError as exc:
                raise AWikiSecretWriteError("RECOVERY_REQUIRED") from exc
            try:
                restored = _read_file_bytes(target)
            except OSError as exc:
                raise AWikiSecretWriteError("RECOVERY_REQUIRED") from exc
            if restored != original_bytes:
                raise AWikiSecretWriteError("RECOVERY_REQUIRED")
            if mode_restoration_unproven:
                raise AWikiSecretWriteError("RECOVERY_REQUIRED")
        finally:
            if rollback_temp is not None:
                _best_effort_unlink(rollback_temp)
