"""DEX admission-side physical identity and binding digest helpers.

This module owns no task, claim, receipt, retry, review, or completion authority.
It only forms deterministic identity evidence for the accepted DEX contract.
"""
from __future__ import annotations

from dataclasses import dataclass
import ctypes
import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
from typing import Callable


_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_TEXT = 1024
_MAX_ARGV_ITEMS = 64
_MAX_ARG_CHARS = 2048


class DexIdentityError(RuntimeError):
    """Fail-closed DEX identity error with a stable typed code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: str, field: str, *, max_chars: int = _MAX_TEXT) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > max_chars
        or any(char in value for char in ("\x00", "\r", "\n"))
    ):
        raise ValueError(f"{field} is invalid")
    return value


def _normalize_windows_final_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise DexIdentityError("PROJECT_IDENTITY_FAILED")
    path = value.replace("/", "\\")
    marker = path.find("?\\")
    if marker >= 2 and set(path[:marker]) == {"\\"}:
        path = path[marker + 2 :]
        if path[:4].casefold() == "unc\\":
            path = "\\\\" + path[4:]
    path = ntpath.normpath(path)
    if not ntpath.isabs(path):
        raise DexIdentityError("PROJECT_IDENTITY_FAILED")
    return path.casefold()


def _windows_final_path(path: Path) -> str:
    if os.name != "nt":
        raise DexIdentityError("PROJECT_IDENTITY_FAILED")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    get_final = kernel32.GetFinalPathNameByHandleW
    get_final.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
    get_final.restype = ctypes.c_uint32
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_int

    file_read_attributes = 0x0080
    share_all = 0x00000001 | 0x00000002 | 0x00000004
    open_existing = 3
    backup_semantics = 0x02000000
    handle = create_file(
        str(path),
        file_read_attributes,
        share_all,
        None,
        open_existing,
        backup_semantics,
        None,
    )
    invalid = ctypes.c_void_p(-1).value
    if not handle or handle == invalid:
        raise DexIdentityError("PROJECT_IDENTITY_FAILED")
    try:
        size = get_final(handle, None, 0, 0)
        if not size or size > 32768:
            raise DexIdentityError("PROJECT_IDENTITY_FAILED")
        buffer = ctypes.create_unicode_buffer(size + 1)
        written = get_final(handle, buffer, len(buffer), 0)
        if not written or written >= len(buffer):
            raise DexIdentityError("PROJECT_IDENTITY_FAILED")
        return buffer.value
    finally:
        close_handle(handle)


def canonicalize_existing_root(
    path: str | Path,
    *,
    platform_name: str | None = None,
    final_path_resolver: Callable[[Path], str] | None = None,
) -> str:
    """Return one physical identity for an existing repository/worktree root.

    Windows uses final-handle path resolution so junction/reparse aliases
    converge. POSIX uses realpath semantics and preserves case.
    """
    try:
        candidate = Path(path).expanduser()
    except (TypeError, ValueError, OSError) as exc:
        raise DexIdentityError("PROJECT_IDENTITY_FAILED") from exc
    if not candidate.exists() or not candidate.is_dir():
        raise DexIdentityError("PROJECT_IDENTITY_FAILED")

    platform = os.name if platform_name is None else platform_name
    if platform == "nt":
        resolver = final_path_resolver or _windows_final_path
        try:
            final = resolver(candidate)
        except DexIdentityError:
            raise
        except Exception as exc:
            raise DexIdentityError("PROJECT_IDENTITY_FAILED") from exc
        return _normalize_windows_final_path(final)

    try:
        resolved = os.path.realpath(os.fspath(candidate), strict=True)
    except (OSError, TypeError, ValueError) as exc:
        raise DexIdentityError("PROJECT_IDENTITY_FAILED") from exc
    if not os.path.isdir(resolved):
        raise DexIdentityError("PROJECT_IDENTITY_FAILED")
    return resolved


@dataclass(frozen=True, slots=True)
class DexBindingIdentity:
    execution_id: str
    attempt_id: str
    task_ref: str
    lane_ref: str
    claim_ref: str
    claim_generation: int
    authority_repo_identity: str
    execution_repo_identity: str
    authority_sha: str
    execution_sha: str
    host_id: str
    boot_id: str
    executable_path: str
    executable_sha256: str
    argv_shape: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in (
            "execution_id",
            "attempt_id",
            "task_ref",
            "lane_ref",
            "claim_ref",
            "authority_repo_identity",
            "execution_repo_identity",
            "host_id",
            "boot_id",
            "executable_path",
        ):
            _text(getattr(self, field), field)
        if (
            not isinstance(self.claim_generation, int)
            or isinstance(self.claim_generation, bool)
            or self.claim_generation < 0
        ):
            raise ValueError("claim_generation is invalid")
        if not isinstance(self.authority_sha, str) or not _GIT_SHA_RE.fullmatch(self.authority_sha):
            raise ValueError("authority_sha is invalid")
        if not isinstance(self.execution_sha, str) or not _GIT_SHA_RE.fullmatch(self.execution_sha):
            raise ValueError("execution_sha is invalid")
        if (
            not isinstance(self.executable_sha256, str)
            or not _SHA256_RE.fullmatch(self.executable_sha256)
        ):
            raise ValueError("executable_sha256 is invalid")
        if (
            not isinstance(self.argv_shape, tuple)
            or not self.argv_shape
            or len(self.argv_shape) > _MAX_ARGV_ITEMS
        ):
            raise ValueError("argv_shape is invalid")
        for item in self.argv_shape:
            _text(item, "argv_shape item", max_chars=_MAX_ARG_CHARS)


def binding_digest(binding: DexBindingIdentity) -> str:
    if not isinstance(binding, DexBindingIdentity):
        raise ValueError("binding must be DexBindingIdentity")
    payload = {
        "attempt_id": binding.attempt_id,
        "authority_repo_identity": binding.authority_repo_identity,
        "authority_sha": binding.authority_sha,
        "argv_shape": list(binding.argv_shape),
        "boot_id": binding.boot_id,
        "claim_generation": binding.claim_generation,
        "claim_ref": binding.claim_ref,
        "executable_path": binding.executable_path,
        "executable_sha256": binding.executable_sha256,
        "execution_id": binding.execution_id,
        "execution_repo_identity": binding.execution_repo_identity,
        "execution_sha": binding.execution_sha,
        "host_id": binding.host_id,
        "lane_ref": binding.lane_ref,
        "schema": "dex.binding.v1",
        "task_ref": binding.task_ref,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
