"""Local-first SunDay Runtime execution substrate.

This module owns no scheduling, claims, leases, provider selection, review, retry,
completion, merge, or project-memory authority. It binds operations to one exact
repo/worktree/branch/HEAD/claim identity and reuses the existing bounded native
execution primitives.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from .native_execution import (
    NativeCommandResult,
    NativeCommandSpec,
    NativeExecutionError,
    NativeExecutionScope,
    NativeFileSystem,
    NativeSubprocessRunner,
)


_HEAD_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")


class SunDayRuntimeError(RuntimeError):
    """Fail-closed runtime error carrying a stable classification code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _CommandRunner(Protocol):
    def run(self, spec: NativeCommandSpec) -> NativeCommandResult: ...


def _require_text(value: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise SunDayRuntimeError(code)
    return value.strip()


def _normalized_path(value: str | Path) -> Path:
    try:
        return Path(value).resolve(strict=False)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise SunDayRuntimeError("CONTEXT_BINDING_INVALID") from exc


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.realpath(str(left))) == os.path.normcase(
        os.path.realpath(str(right))
    )


@dataclass(frozen=True, slots=True)
class RuntimeLaneBinding:
    """Immutable execution-context identity for one lane."""

    repo_root: Path | str
    worktree_root: Path | str
    branch: str
    head: str
    claim_id: str

    def __post_init__(self) -> None:
        repo_root = _normalized_path(self.repo_root)
        worktree_root = _normalized_path(self.worktree_root)
        branch = _require_text(self.branch, "CONTEXT_BINDING_INVALID")
        head = _require_text(self.head, "CONTEXT_BINDING_INVALID")
        claim_id = _require_text(self.claim_id, "CONTEXT_BINDING_INVALID")
        if _HEAD_RE.fullmatch(head) is None:
            raise SunDayRuntimeError("CONTEXT_BINDING_INVALID")
        object.__setattr__(self, "repo_root", repo_root)
        object.__setattr__(self, "worktree_root", worktree_root)
        object.__setattr__(self, "branch", branch)
        object.__setattr__(self, "head", head.lower())
        object.__setattr__(self, "claim_id", claim_id)


@dataclass(frozen=True, slots=True)
class RuntimeContextEvidence:
    repo_root: str
    worktree_root: str
    branch: str
    head: str
    claim_id: str


@dataclass(frozen=True, slots=True)
class RuntimeSearchResult:
    query: str
    paths: tuple[str, ...]
    matched: bool
    output: str
    output_sha256: str
    truncated: bool


class SunDayRuntime:
    """Bounded local execution substrate for one explicitly-bound lane."""

    def __init__(
        self,
        binding: RuntimeLaneBinding,
        *,
        mutation_allowed: bool = False,
        allowed_command_executables: Sequence[str] = (),
        environment_source: Mapping[str, str] | None = None,
        git_runner: _CommandRunner | None = None,
        search_runner: _CommandRunner | None = None,
        command_runner: _CommandRunner | None = None,
    ) -> None:
        if not isinstance(binding, RuntimeLaneBinding):
            raise SunDayRuntimeError("CONTEXT_BINDING_INVALID")
        self._binding = binding

        self._file_scope = NativeExecutionScope(
            root=binding.worktree_root,
            mutation_allowed=mutation_allowed,
        )
        self._filesystem = NativeFileSystem(self._file_scope)

        git_scope = NativeExecutionScope(
            root=binding.worktree_root,
            mutation_allowed=False,
            allowed_executables=("git",),
            max_timeout_seconds=15,
            max_output_bytes=64 * 1024,
        )
        search_scope = NativeExecutionScope(
            root=binding.worktree_root,
            mutation_allowed=False,
            allowed_executables=("rg",),
            max_timeout_seconds=60,
            max_output_bytes=512 * 1024,
        )
        command_scope = NativeExecutionScope(
            root=binding.worktree_root,
            mutation_allowed=mutation_allowed,
            allowed_executables=tuple(allowed_command_executables),
            max_timeout_seconds=300,
            max_output_bytes=1024 * 1024,
        )
        self._git_runner = git_runner or NativeSubprocessRunner(
            git_scope, environment_source=environment_source
        )
        self._search_runner = search_runner or NativeSubprocessRunner(
            search_scope, environment_source=environment_source
        )
        self._command_runner = command_runner or NativeSubprocessRunner(
            command_scope, environment_source=environment_source
        )

    @property
    def binding(self) -> RuntimeLaneBinding:
        return self._binding

    @property
    def filesystem(self) -> NativeFileSystem:
        return self._filesystem

    def _git_text(self, *args: str) -> str:
        result = self._git_runner.run(
            NativeCommandSpec(argv=("git", *args), cwd=".", timeout_seconds=10)
        )
        if result.timed_out or result.exit_code != 0:
            raise SunDayRuntimeError("CONTEXT_DRIFT")
        return result.stdout.strip()

    def verify_context(self) -> RuntimeContextEvidence:
        """Re-observe Git identity and fail closed on any mismatch."""

        try:
            top_text = self._git_text("rev-parse", "--show-toplevel")
            common_text = self._git_text("rev-parse", "--git-common-dir")
            branch = self._git_text("branch", "--show-current")
            head = self._git_text("rev-parse", "HEAD").lower()
        except (NativeExecutionError, OSError) as exc:
            raise SunDayRuntimeError("CONTEXT_DRIFT") from exc

        worktree = Path(self._binding.worktree_root)
        repo_root = Path(self._binding.repo_root)
        top = _normalized_path(top_text)
        common_path = Path(common_text)
        if not common_path.is_absolute():
            common_path = worktree / common_path
        common = _normalized_path(common_path)
        expected_common = _normalized_path(repo_root / ".git")

        if (
            not _same_path(top, worktree)
            or not _same_path(common, expected_common)
            or branch != self._binding.branch
            or head != self._binding.head
        ):
            raise SunDayRuntimeError("CONTEXT_DRIFT")

        return RuntimeContextEvidence(
            repo_root=str(repo_root),
            worktree_root=str(worktree),
            branch=branch,
            head=head,
            claim_id=self._binding.claim_id,
        )

    def read_text(self, relative_path: str | Path, *, max_bytes: int | None = None):
        self.verify_context()
        return self._filesystem.read_text(relative_path, max_bytes=max_bytes)

    def list_directory(self, relative_path: str | Path = "."):
        self.verify_context()
        return self._filesystem.list_directory(relative_path)

    def create_text_if_absent(self, relative_path: str | Path, content: str):
        self.verify_context()
        return self._filesystem.create_text_if_absent(relative_path, content)

    def write_text(
        self,
        relative_path: str | Path,
        content: str,
        *,
        expected_sha256: str | None = None,
    ):
        self.verify_context()
        return self._filesystem.write_text(
            relative_path,
            content,
            expected_sha256=expected_sha256,
        )

    def search_text(
        self,
        query: str,
        paths: Sequence[str | Path] = (".",),
        *,
        timeout_seconds: int = 30,
    ) -> RuntimeSearchResult:
        self.verify_context()
        query = _require_text(query, "SEARCH_QUERY_INVALID")
        if isinstance(paths, (str, bytes)) or not paths:
            raise SunDayRuntimeError("SEARCH_PATHS_INVALID")

        rendered: list[str] = []
        for value in paths:
            target = self._file_scope.resolve_relative(value, must_exist=True)
            rendered.append(self._file_scope.relative_display(target))

        argv = (
            "rg",
            "--line-number",
            "--no-heading",
            "--color",
            "never",
            "--fixed-strings",
            "--",
            query,
            *rendered,
        )
        try:
            result = self._search_runner.run(
                NativeCommandSpec(
                    argv=argv,
                    cwd=".",
                    timeout_seconds=timeout_seconds,
                    mutation_intent=False,
                )
            )
        except NativeExecutionError as exc:
            raise SunDayRuntimeError("SEARCH_FAILED") from exc

        if result.timed_out or result.exit_code not in {0, 1}:
            raise SunDayRuntimeError("SEARCH_FAILED")
        return RuntimeSearchResult(
            query=query,
            paths=tuple(rendered),
            matched=result.exit_code == 0,
            output=result.stdout,
            output_sha256=result.stdout_sha256,
            truncated=result.stdout_truncated,
        )

    def run_allowlisted(
        self,
        argv: Sequence[str],
        *,
        cwd: str | Path = ".",
        timeout_seconds: int = 30,
        mutation_intent: bool = False,
    ) -> NativeCommandResult:
        """Run one argv-only command against the explicitly configured allowlist."""

        self.verify_context()
        if isinstance(argv, (str, bytes)) or not argv:
            raise SunDayRuntimeError("ARGV_INVALID")
        try:
            return self._command_runner.run(
                NativeCommandSpec(
                    argv=tuple(argv),
                    cwd=cwd,
                    timeout_seconds=timeout_seconds,
                    mutation_intent=mutation_intent,
                )
            )
        except NativeExecutionError as exc:
            raise SunDayRuntimeError(exc.args[0] if exc.args else "COMMAND_FAILED") from exc
