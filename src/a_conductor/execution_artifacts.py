"""Bounded read-only access to durable execution artifacts.

AC-RES-002 owns artifact creation. This module only resolves durable refs under
the recorded run directory and returns bounded tails/chunks plus metadata.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from .execution_record import DurableExecutionRecord
from .execution_store import ExecutionStoreError


MAX_ARTIFACT_READ_BYTES = 64 * 1024
_HASH_CHUNK_BYTES = 64 * 1024


class ExecutionArtifactError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ExecutionArtifactKind(str, Enum):
    STDOUT = "STDOUT"
    STDERR = "STDERR"
    REPORT = "REPORT"


@dataclass(frozen=True, slots=True)
class ExecutionArtifactSlice:
    execution_id: str
    kind: ExecutionArtifactKind
    artifact_ref: str
    total_bytes: int
    offset: int
    returned_bytes: int
    sha256: str
    raw: bytes
    text: str
    truncated: bool

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ExecutionArtifactKind):
            raise ValueError("kind must be an ExecutionArtifactKind")
        if self.returned_bytes != len(self.raw):
            raise ValueError("returned_bytes must match raw length")
        if self.total_bytes < 0 or self.offset < 0 or self.returned_bytes < 0:
            raise ValueError("artifact sizes must be non-negative")
        if self.returned_bytes > MAX_ARTIFACT_READ_BYTES:
            raise ValueError("artifact slice exceeds hard response limit")
        if len(self.sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.sha256):
            raise ValueError("sha256 must be lowercase SHA-256 hex")
        if not isinstance(self.truncated, bool):
            raise ValueError("truncated must be a bool")


@dataclass(frozen=True, slots=True)
class PytestExecutionSummary:
    passed: int | None
    failed: int | None
    skipped: int | None
    warnings: int | None
    duration_seconds: float | None
    source_truncated: bool
    artifact_sha256: str


class ExecutionArtifactStore(Protocol):
    def get(self, execution_id: str) -> DurableExecutionRecord: ...


def _require_budget(value: int, field_name: str = "max_bytes") -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
        or value > MAX_ARTIFACT_READ_BYTES
    ):
        raise ValueError(f"{field_name} must be between 1 and {MAX_ARTIFACT_READ_BYTES}")
    return value


def _require_offset(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("offset must be >= 0")
    return value


def _full_digest(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(_HASH_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise ExecutionArtifactError("ARTIFACT_READ_FAILED") from exc
    return total, digest.hexdigest()


def _under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


class ExecutionArtifactService:
    def __init__(self, *, store: ExecutionArtifactStore) -> None:
        self._store = store

    def _record(self, execution_id: str) -> DurableExecutionRecord:
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("execution_id must not be blank")
        try:
            return self._store.get(execution_id)
        except ExecutionStoreError as exc:
            if exc.code == "EXECUTION_NOT_FOUND":
                raise ExecutionArtifactError("ARTIFACT_EXECUTION_NOT_FOUND") from exc
            raise

    @staticmethod
    def _ref_for(record: DurableExecutionRecord, kind: ExecutionArtifactKind) -> str:
        if not isinstance(kind, ExecutionArtifactKind):
            raise ValueError("kind must be an ExecutionArtifactKind")
        ref = {
            ExecutionArtifactKind.STDOUT: record.stdout_ref,
            ExecutionArtifactKind.STDERR: record.stderr_ref,
            ExecutionArtifactKind.REPORT: record.report_ref,
        }[kind]
        if ref is None:
            raise ExecutionArtifactError("ARTIFACT_NOT_CONFIGURED")
        return ref

    def _path(self, record: DurableExecutionRecord, kind: ExecutionArtifactKind) -> tuple[str, Path]:
        if record.run_dir_ref is None:
            raise ExecutionArtifactError("ARTIFACT_RUN_DIR_NOT_CONFIGURED")
        ref = self._ref_for(record, kind)
        try:
            root = Path(record.repo_root).expanduser().resolve(strict=False)
            run_dir = (root / record.run_dir_ref).resolve(strict=False)
            artifact = (root / ref).resolve(strict=False)
        except OSError as exc:
            raise ExecutionArtifactError("ARTIFACT_PATH_INVALID") from exc
        if not root.is_dir():
            raise ExecutionArtifactError("ARTIFACT_REPO_NOT_FOUND")
        if not _under(run_dir, root):
            raise ExecutionArtifactError("ARTIFACT_OUTSIDE_RUN_DIR")
        if not _under(artifact, run_dir):
            raise ExecutionArtifactError("ARTIFACT_OUTSIDE_RUN_DIR")
        if not artifact.exists():
            raise ExecutionArtifactError("ARTIFACT_NOT_FOUND")
        if not artifact.is_file():
            raise ExecutionArtifactError("ARTIFACT_NOT_FILE")
        # Resolve once more with the existing file so symlink targets are part
        # of the confinement decision on platforms that support symlinks.
        try:
            resolved = artifact.resolve(strict=True)
            resolved_run_dir = run_dir.resolve(strict=True)
        except OSError as exc:
            raise ExecutionArtifactError("ARTIFACT_PATH_INVALID") from exc
        if not _under(resolved, resolved_run_dir):
            raise ExecutionArtifactError("ARTIFACT_OUTSIDE_RUN_DIR")
        return ref, resolved

    def _slice(
        self,
        execution_id: str,
        kind: ExecutionArtifactKind,
        *,
        offset: int,
        max_bytes: int,
        tail: bool,
    ) -> ExecutionArtifactSlice:
        budget = _require_budget(max_bytes)
        requested_offset = _require_offset(offset)
        record = self._record(execution_id)
        ref, path = self._path(record, kind)
        total, digest = _full_digest(path)
        actual_offset = max(0, total - budget) if tail else min(requested_offset, total)
        try:
            with path.open("rb") as handle:
                handle.seek(actual_offset)
                raw = handle.read(budget)
        except OSError as exc:
            raise ExecutionArtifactError("ARTIFACT_READ_FAILED") from exc
        truncated = actual_offset > 0 or actual_offset + len(raw) < total
        return ExecutionArtifactSlice(
            execution_id=record.execution_id,
            kind=kind,
            artifact_ref=ref,
            total_bytes=total,
            offset=actual_offset,
            returned_bytes=len(raw),
            sha256=digest,
            raw=raw,
            text=raw.decode("utf-8", errors="replace"),
            truncated=truncated,
        )

    def read_tail(
        self,
        execution_id: str,
        kind: ExecutionArtifactKind,
        *,
        max_bytes: int = 16 * 1024,
    ) -> ExecutionArtifactSlice:
        return self._slice(
            execution_id,
            kind,
            offset=0,
            max_bytes=max_bytes,
            tail=True,
        )

    def read_chunk(
        self,
        execution_id: str,
        kind: ExecutionArtifactKind,
        *,
        offset: int,
        max_bytes: int = 16 * 1024,
    ) -> ExecutionArtifactSlice:
        return self._slice(
            execution_id,
            kind,
            offset=offset,
            max_bytes=max_bytes,
            tail=False,
        )

    def summarize_pytest(
        self,
        execution_id: str,
        *,
        max_tail_bytes: int = 16 * 1024,
    ) -> PytestExecutionSummary:
        artifact = self.read_tail(
            execution_id,
            ExecutionArtifactKind.STDOUT,
            max_bytes=_require_budget(max_tail_bytes, "max_tail_bytes"),
        )
        text = artifact.text

        def count(name: str) -> int | None:
            matches = list(re.finditer(rf"(?<!\d)(\d+)\s+{name}\b", text, re.IGNORECASE))
            return int(matches[-1].group(1)) if matches else None

        duration_matches = list(
            re.finditer(r"\bin\s+([0-9]+(?:\.[0-9]+)?)s\b", text, re.IGNORECASE)
        )
        duration = float(duration_matches[-1].group(1)) if duration_matches else None
        return PytestExecutionSummary(
            passed=count("passed"),
            failed=count("failed"),
            skipped=count("skipped"),
            warnings=count("warnings?"),
            duration_seconds=duration,
            source_truncated=artifact.truncated,
            artifact_sha256=artifact.sha256,
        )
