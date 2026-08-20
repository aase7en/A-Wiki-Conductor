"""Preconditioned Git stage/commit transactions over native execution."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .native_adapters import NativeCommandRunner, NativeGitReadAdapter
from .native_execution import (
    NativeCommandResult,
    NativeCommandSpec,
    NativeExecutionError,
    NativeExecutionScope,
    NativeSubprocessRunner,
)


class NativeGitTransactionError(NativeExecutionError):
    def __init__(self, code: str, result: NativeCommandResult | None = None) -> None:
        self.result = result
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GitMutationSnapshot:
    head: str
    status: NativeCommandResult
    cached_diff: NativeCommandResult


@dataclass(frozen=True, slots=True)
class GitStageOutcome:
    command: NativeCommandResult
    snapshot: GitMutationSnapshot


@dataclass(frozen=True, slots=True)
class GitCommitOutcome:
    command: NativeCommandResult
    previous_head: str
    new_head: str
    snapshot: GitMutationSnapshot


def _require_text(value: str, code: str, *, max_length: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise NativeExecutionError(code)
    if max_length is not None and len(value) > max_length:
        raise NativeExecutionError(code)
    return value


def _require_sha256(value: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise NativeExecutionError("GIT_PRECONDITION_INVALID")
    lowered = value.casefold()
    if any(char not in "0123456789abcdef" for char in lowered):
        raise NativeExecutionError("GIT_PRECONDITION_INVALID")
    return lowered


class NativeGitTransactionAdapter:
    def __init__(
        self,
        scope: NativeExecutionScope,
        *,
        runner: NativeCommandRunner | None = None,
        git_executable: str = "git",
    ) -> None:
        self._scope = scope
        self._runner = runner or NativeSubprocessRunner(scope)
        self._git_executable = _require_text(git_executable, "GIT_EXECUTABLE_INVALID")
        self._read = NativeGitReadAdapter(
            scope,
            runner=self._runner,
            git_executable=self._git_executable,
        )

    def _base_argv(self, *extra_configs: str) -> tuple[str, ...]:
        root = Path(self._scope.root)
        argv: list[str] = [
            self._git_executable,
            "-c",
            f"safe.directory={root.as_posix()}",
            "-c",
            "core.fsmonitor=false",
        ]
        for config in extra_configs:
            argv.extend(("-c", config))
        argv.extend(("-C", str(root)))
        return tuple(argv)

    def _run_read(
        self,
        args: tuple[str, ...],
        *,
        timeout_seconds: int = 10,
    ) -> NativeCommandResult:
        return self._runner.run(
            NativeCommandSpec(
                argv=(*self._base_argv(), *args),
                cwd=".",
                timeout_seconds=timeout_seconds,
                mutation_intent=False,
            )
        )

    def _require_mutation_authority(self) -> None:
        if not self._scope.mutation_allowed:
            raise NativeExecutionError("MUTATION_FORBIDDEN")

    def snapshot(self) -> GitMutationSnapshot:
        head_result = self._run_read(("rev-parse", "HEAD"))
        if (
            head_result.timed_out
            or head_result.exit_code != 0
            or not head_result.stdout.strip()
        ):
            raise NativeGitTransactionError("GIT_HEAD_READ_FAILED", head_result)
        status = self._read.status_short()
        if status.timed_out or status.exit_code != 0:
            raise NativeGitTransactionError("GIT_STATUS_READ_FAILED", status)
        cached = self._read.cached_diff()
        if cached.timed_out or cached.exit_code != 0:
            raise NativeGitTransactionError("GIT_INDEX_READ_FAILED", cached)
        return GitMutationSnapshot(
            head=head_result.stdout.strip(),
            status=status,
            cached_diff=cached,
        )

    def _assert_preconditions(
        self,
        *,
        expected_head: str,
        expected_status_sha256: str,
        expected_cached_diff_sha256: str,
    ) -> GitMutationSnapshot:
        head = _require_text(expected_head, "GIT_PRECONDITION_INVALID")
        status_hash = _require_sha256(expected_status_sha256)
        index_hash = _require_sha256(expected_cached_diff_sha256)
        current = self.snapshot()
        if current.head != head:
            raise NativeExecutionError("GIT_HEAD_DRIFT")
        if current.cached_diff.stdout_sha256.casefold() != index_hash:
            raise NativeExecutionError("GIT_INDEX_DRIFT")
        if current.status.stdout_sha256.casefold() != status_hash:
            raise NativeExecutionError("GIT_STATUS_DRIFT")
        return current

    def _ensure_filter_policy_safe(self, pathspecs: tuple[str, ...]) -> None:
        attributes = self._run_read(
            ("check-attr", "filter", "--", *pathspecs),
            timeout_seconds=10,
        )
        if attributes.timed_out or attributes.exit_code != 0:
            raise NativeGitTransactionError("GIT_FILTER_POLICY_READ_FAILED", attributes)
        active_filters: set[str] = set()
        for line in attributes.stdout.splitlines():
            marker = ": filter: "
            if marker not in line:
                continue
            value = line.rsplit(marker, 1)[1].strip()
            if value and value not in {"unspecified", "unset"}:
                active_filters.add(value.casefold())
        if not active_filters:
            return

        configured = self._run_read(
            ("config", "--get-regexp", r"^filter\..*\.(clean|process)$"),
            timeout_seconds=10,
        )
        if configured.timed_out:
            raise NativeGitTransactionError("GIT_FILTER_POLICY_READ_FAILED", configured)
        if configured.exit_code == 1 and not configured.stdout.strip():
            return
        if configured.exit_code != 0:
            raise NativeGitTransactionError("GIT_FILTER_POLICY_READ_FAILED", configured)
        configured_filters: set[str] = set()
        for line in configured.stdout.splitlines():
            key = line.split(None, 1)[0].casefold() if line.strip() else ""
            if not key.startswith("filter."):
                continue
            if key.endswith(".clean"):
                configured_filters.add(key[len("filter.") : -len(".clean")])
            elif key.endswith(".process"):
                configured_filters.add(key[len("filter.") : -len(".process")])
        if active_filters & configured_filters:
            raise NativeExecutionError("GIT_FILTER_POLICY_UNSAFE")

    def _stage_paths(self, paths: Sequence[str | Path]) -> tuple[str, ...]:
        if isinstance(paths, (str, bytes)):
            raise NativeExecutionError("GIT_STAGE_PATH_INVALID")
        rendered: list[str] = []
        seen: set[str] = set()
        for value in paths:
            if not isinstance(value, (str, Path)) or not str(value).strip():
                raise NativeExecutionError("GIT_STAGE_PATH_INVALID")
            resolved = self._scope.resolve_relative(value, must_exist=False)
            display = self._scope.relative_display(resolved)
            if display == "." or (resolved.exists() and resolved.is_dir()):
                raise NativeExecutionError("GIT_STAGE_PATH_INVALID")
            key = display.casefold()
            if key in seen:
                raise NativeExecutionError("GIT_STAGE_PATH_INVALID")
            seen.add(key)
            rendered.append(display)
        if not rendered:
            raise NativeExecutionError("GIT_STAGE_PATH_REQUIRED")
        return tuple(rendered)

    def _run_mutation(
        self,
        args: tuple[str, ...],
        *,
        timeout_seconds: int,
        extra_configs: tuple[str, ...] = (),
    ) -> NativeCommandResult:
        self._require_mutation_authority()
        with tempfile.TemporaryDirectory(prefix="a-conductor-empty-hooks-") as hooks_dir:
            configs = (
                f"core.hooksPath={Path(hooks_dir).as_posix()}",
                *extra_configs,
            )
            return self._runner.run(
                NativeCommandSpec(
                    argv=(*self._base_argv(*configs), *args),
                    cwd=".",
                    timeout_seconds=timeout_seconds,
                    mutation_intent=True,
                )
            )

    def stage(
        self,
        paths: Sequence[str | Path],
        *,
        expected_head: str,
        expected_status_sha256: str,
        expected_cached_diff_sha256: str,
        timeout_seconds: int = 20,
    ) -> GitStageOutcome:
        self._require_mutation_authority()
        pathspecs = self._stage_paths(paths)
        self._assert_preconditions(
            expected_head=expected_head,
            expected_status_sha256=expected_status_sha256,
            expected_cached_diff_sha256=expected_cached_diff_sha256,
        )
        self._ensure_filter_policy_safe(pathspecs)
        result = self._run_mutation(
            ("add", "--", *pathspecs),
            timeout_seconds=timeout_seconds,
        )
        if result.timed_out or result.exit_code != 0:
            raise NativeGitTransactionError("GIT_STAGE_FAILED", result)
        return GitStageOutcome(command=result, snapshot=self.snapshot())

    def commit(
        self,
        message: str,
        *,
        expected_head: str,
        expected_status_sha256: str,
        expected_cached_diff_sha256: str,
        timeout_seconds: int = 30,
    ) -> GitCommitOutcome:
        self._require_mutation_authority()
        commit_message = _require_text(
            message,
            "GIT_COMMIT_MESSAGE_INVALID",
            max_length=10_000,
        )
        before = self._assert_preconditions(
            expected_head=expected_head,
            expected_status_sha256=expected_status_sha256,
            expected_cached_diff_sha256=expected_cached_diff_sha256,
        )
        if not before.cached_diff.stdout.strip():
            raise NativeExecutionError("GIT_NOTHING_STAGED")
        result = self._run_mutation(
            ("commit", "--no-verify", "--no-gpg-sign", "-m", commit_message),
            timeout_seconds=timeout_seconds,
            extra_configs=("commit.gpgSign=false",),
        )
        if result.timed_out or result.exit_code != 0:
            raise NativeGitTransactionError("GIT_COMMIT_FAILED", result)
        after = self.snapshot()
        if after.head == before.head:
            raise NativeGitTransactionError("GIT_COMMIT_POSTCONDITION_FAILED", result)
        return GitCommitOutcome(
            command=result,
            previous_head=before.head,
            new_head=after.head,
            snapshot=after,
        )
