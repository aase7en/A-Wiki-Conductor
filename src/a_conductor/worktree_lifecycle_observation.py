"""WO-P1-417 WTL-1: read-only worktree observation collectors.

This module assembles one immutable :class:`WtlWorktreeFacts` snapshot for the
pure classifier. It executes no cleanup commands, performs no Git mutation
(``--no-optional-locks`` read-only invocations only), and never writes to any
store. Every collector is an injected read-only callable over an existing
authority (worker lease store, job store, durable execution store, review
freeze evidence, goal-closeout fold/release evidence, exact process-identity
observation); a missing, failing, or unwired collector yields UNKNOWN (None)
— never an invented observed absence.
"""

from __future__ import annotations

import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from .registry import windows_worktree_key
from .windows_observer import CommandResult, CommandRunner
from .worktree_lifecycle import (
    WtlExecutionFact,
    WtlLeaseFact,
    WtlMergeFoldFact,
    WtlProcessFact,
    WtlReviewFreezeFact,
    WtlWorktreeFacts,
    WtlRemoteEvidence,
    wtl_input_fingerprint,
)

_HEAD_RE_MIN = 7
_HEAD_RE_MAX = 64
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class WtlGitObservationPort(Protocol):
    """Read-only Git identity/status seams; None means unknown."""

    def read_head(self, worktree: str) -> str | None: ...

    def read_branch(self, worktree: str) -> str | None: ...

    def read_status_porcelain(self, worktree: str) -> tuple[str, ...] | None: ...


class WtlLeaseFactsCollector(Protocol):
    def __call__(self, worktree_key: str) -> tuple[WtlLeaseFact, ...] | None: ...


class WtlExecutionFactsCollector(Protocol):
    def __call__(self, worktree_key: str) -> tuple[WtlExecutionFact, ...] | None: ...


class WtlProcessFactsCollector(Protocol):
    def __call__(self, worktree_key: str) -> tuple[WtlProcessFact, ...] | None: ...


class WtlReviewFreezeCollector(Protocol):
    def __call__(self, worktree_key: str) -> tuple[WtlReviewFreezeFact, ...] | None: ...


class WtlMergeFoldCollector(Protocol):
    def __call__(self, worktree_key: str) -> WtlMergeFoldFact | None: ...


class WtlRemoteEvidencePort(Protocol):
    """Injected remote evidence seam (open PR / remote branch / unmerged).

    Returning None or raising means the remote facts are unavailable, which
    classifies as EVIDENCE_INCOMPLETE — never safe."""

    def __call__(
        self, worktree_key: str, branch: str | None, head: str | None
    ) -> WtlRemoteEvidence | None: ...


def _require_git_executable(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("git_executable must not be blank")
    return value.strip()


def _require_timeout(timeout_seconds: int) -> int:
    if (
        not isinstance(timeout_seconds, int)
        or isinstance(timeout_seconds, bool)
        or timeout_seconds < 1
    ):
        raise ValueError("timeout_seconds must be >= 1")
    return timeout_seconds


def _valid_head(value: str) -> str | None:
    cleaned = value.strip().casefold()
    if not _HEAD_RE_MIN <= len(cleaned) <= _HEAD_RE_MAX:
        return None
    if any(char not in _HEX_DIGITS for char in cleaned):
        return None
    return cleaned


class _NativeGitRunner:
    """Subprocess runner for read-only git invocations (no shell, no writes)."""

    def __init__(self, timeout_seconds: int = 10) -> None:
        self._timeout_seconds = _require_timeout(timeout_seconds)

    def run(self, argv: tuple[str, ...], timeout_seconds: int) -> CommandResult:
        try:
            completed = subprocess.run(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            return CommandResult(1, "", "observation failed")
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)


class StrictGitObservationPort:
    """Default read-only Git observation port.

    Mirrors the strict read-only runner contract (safe.directory, -C, fixed
    subcommand allowlist, timeout, CREATE_NO_WINDOW) and adds
    ``--no-optional-locks`` so even index refresh cannot write Git metadata.
    It accepts only rev-parse HEAD, rev-parse --abbrev-ref HEAD, and
    status --porcelain=v1; no mutation subcommand is reachable.
    """

    def __init__(
        self,
        *,
        runner: CommandRunner | None = None,
        git_executable: str = "git",
        timeout_seconds: int = 10,
    ) -> None:
        self._runner = runner or _NativeGitRunner(timeout_seconds)
        self._git_executable = _require_git_executable(git_executable)
        self._timeout_seconds = _require_timeout(timeout_seconds)

    def _run(self, worktree: str, args: tuple[str, ...]) -> CommandResult:
        path = Path(worktree).expanduser().resolve(strict=False)
        argv = (
            self._git_executable,
            "--no-optional-locks",
            "-c",
            f"safe.directory={path.as_posix()}",
            "-C",
            str(path),
            *args,
        )
        return self._runner.run(argv, self._timeout_seconds)

    def read_head(self, worktree: str) -> str | None:
        result = self._run(worktree, ("rev-parse", "HEAD"))
        if result.return_code != 0 or not result.stdout.strip():
            return None
        return _valid_head(result.stdout)

    def read_branch(self, worktree: str) -> str | None:
        result = self._run(worktree, ("rev-parse", "--abbrev-ref", "HEAD"))
        if result.return_code != 0 or not result.stdout.strip():
            return None
        return result.stdout.strip()

    def read_status_porcelain(self, worktree: str) -> tuple[str, ...] | None:
        result = self._run(
            worktree,
            ("status", "--porcelain=v1", "--untracked-files=all"),
        )
        if result.return_code != 0:
            return None
        return tuple(
            line for line in result.stdout.splitlines() if line.strip()
        )


def _parse_status(
    lines: tuple[str, ...] | None,
) -> tuple[bool | None, tuple[str, ...] | None]:
    if lines is None:
        return (None, None)
    tracked = any(not line.startswith("??") for line in lines)
    untracked = tuple(
        dict.fromkeys(
            line[3:].rstrip("/\\") or line[3:]
            for line in lines
            if line.startswith("??") and line[3:].strip()
        )
    )
    return (tracked, untracked)


def _format_timestamp(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return (
        moment.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _call_collector(collector, *args):
    """Fail closed: any collector failure maps to UNKNOWN (None), never to an
    invented observed absence."""
    try:
        return collector(*args)
    except Exception:
        return None


class WtlObservationService:
    """Assembles WtlWorktreeFacts through injected read-only collectors."""

    def __init__(
        self,
        *,
        git_port: WtlGitObservationPort | None = None,
        lease_collector: WtlLeaseFactsCollector | None = None,
        execution_collector: WtlExecutionFactsCollector | None = None,
        process_collector: WtlProcessFactsCollector | None = None,
        review_freeze_collector: WtlReviewFreezeCollector | None = None,
        merge_fold_collector: WtlMergeFoldCollector | None = None,
        remote_evidence_port: WtlRemoteEvidencePort | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if git_port is not None and not all(
            callable(getattr(git_port, name, None))
            for name in ("read_head", "read_branch", "read_status_porcelain")
        ):
            raise ValueError("git_port must expose the read-only observation seams")
        for name, collector in (
            ("lease_collector", lease_collector),
            ("execution_collector", execution_collector),
            ("process_collector", process_collector),
            ("review_freeze_collector", review_freeze_collector),
            ("merge_fold_collector", merge_fold_collector),
            ("remote_evidence_port", remote_evidence_port),
        ):
            if collector is not None and not callable(collector):
                raise ValueError(f"{name} must be callable")
        if now is not None and not callable(now):
            raise ValueError("now must be callable")
        self._git = git_port or StrictGitObservationPort()
        self._leases = lease_collector
        self._executions = execution_collector
        self._processes = process_collector
        self._reviews = review_freeze_collector
        self._merge_fold = merge_fold_collector
        self._remote = remote_evidence_port
        self._now = now or (lambda: datetime.now(timezone.utc))

    def _protected_root(
        self,
        worktree_key: str,
        *,
        repo_root: str | None,
        protected_worktrees: tuple[str, ...] | None,
    ) -> bool | None:
        if protected_worktrees is None and repo_root is None:
            return None
        protected_keys: set[str] = set()
        if repo_root is not None:
            try:
                protected_keys.add(windows_worktree_key(repo_root))
            except ValueError:
                return None
        if protected_worktrees is not None:
            try:
                protected_keys.update(
                    windows_worktree_key(item) for item in protected_worktrees
                )
            except ValueError:
                return None
        return worktree_key in protected_keys

    def collect(
        self,
        worktree_path: str,
        *,
        repo_root: str | None = None,
        protected_worktrees: tuple[str, ...] | None = None,
    ) -> WtlWorktreeFacts:
        """Collect one factual snapshot; read-only, no cleanup side effects."""
        path = str(Path(worktree_path).expanduser().resolve(strict=False))
        worktree_key = windows_worktree_key(path)

        branch_raw = self._git.read_branch(path)
        branch: str | None
        detached: bool | None
        if branch_raw is None:
            branch = None
            detached = None
        else:
            detached = branch_raw.strip() == "HEAD"
            branch = None if detached else branch_raw.strip()

        head = self._git.read_head(path)
        tracked_dirty, untracked_paths = _parse_status(
            self._git.read_status_porcelain(path)
        )

        leases = (
            _call_collector(self._leases, worktree_key)
            if self._leases is not None
            else None
        )
        executions = (
            _call_collector(self._executions, worktree_key)
            if self._executions is not None
            else None
        )
        processes = (
            _call_collector(self._processes, worktree_key)
            if self._processes is not None
            else None
        )
        reviews = (
            _call_collector(self._reviews, worktree_key)
            if self._reviews is not None
            else None
        )
        merge_fold = (
            _call_collector(self._merge_fold, worktree_key)
            if self._merge_fold is not None
            else None
        )
        remote = (
            _call_collector(self._remote, worktree_key, branch, head)
            if self._remote is not None
            else None
        )

        head_recheck = self._git.read_head(path)
        protected_root = self._protected_root(
            worktree_key,
            repo_root=repo_root,
            protected_worktrees=protected_worktrees,
        )
        try:
            observed_at = _format_timestamp(self._now())
        except Exception:
            observed_at = ""

        bundle = WtlWorktreeFacts(
            worktree_path=path,
            worktree_key=worktree_key,
            repo_root=repo_root,
            branch=branch,
            detached=detached,
            head=head,
            head_recheck=head_recheck,
            protected_root=protected_root,
            tracked_dirty=tracked_dirty,
            untracked_paths=untracked_paths,
            leases=leases,
            durable_executions=executions,
            process_observations=processes,
            review_freezes=reviews,
            merge_fold=merge_fold,
            remote=remote,
            durable_task_refs=(),
            observed_at=observed_at,
            input_fingerprint="",
        )
        return replace(bundle, input_fingerprint=wtl_input_fingerprint(bundle))


__all__ = [
    "WtlGitObservationPort",
    "WtlLeaseFactsCollector",
    "WtlExecutionFactsCollector",
    "WtlProcessFactsCollector",
    "WtlReviewFreezeCollector",
    "WtlMergeFoldCollector",
    "WtlRemoteEvidencePort",
    "StrictGitObservationPort",
    "WtlObservationService",
]
