"""Read-only Git project identity verification.

The concrete runner exposes only fixed read-only Git operations. It does not
accept arbitrary Git subcommands and never performs network or repository
mutation.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .serena_lifecycle_backend import SerenaOperationResult
from .serena_runtime import ProjectIdentityPolicy, SerenaProjectBinding


@dataclass(frozen=True, slots=True)
class GitReadResult:
    success: bool
    stdout: str = ""
    stderr: str = ""


class GitReadOnlyRunner(Protocol):
    def show_toplevel(self, worktree: Path) -> GitReadResult: ...

    def branch(self, worktree: Path) -> GitReadResult: ...

    def head(self, worktree: Path) -> GitReadResult: ...

    def is_ancestor(self, worktree: Path, ancestor: str) -> GitReadResult: ...


class StrictReadOnlyGitRunner:
    def __init__(self, git_executable: str = "git", timeout_seconds: int = 5) -> None:
        if not isinstance(git_executable, str) or not git_executable.strip():
            raise ValueError("git_executable must not be blank")
        if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or timeout_seconds < 1:
            raise ValueError("timeout_seconds must be >= 1")
        self._git_executable = git_executable.strip()
        self._timeout_seconds = timeout_seconds

    def _run(self, worktree: Path, args: tuple[str, ...]) -> GitReadResult:
        path = Path(worktree).expanduser().resolve(strict=False)
        argv = [
            self._git_executable,
            "-c",
            f"safe.directory={path.as_posix()}",
            "-C",
            str(path),
            *args,
        ]
        try:
            completed = subprocess.run(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout_seconds,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            return GitReadResult(False)
        return GitReadResult(
            completed.returncode == 0,
            completed.stdout.strip(),
            completed.stderr.strip(),
        )

    def show_toplevel(self, worktree: Path) -> GitReadResult:
        return self._run(worktree, ("rev-parse", "--show-toplevel"))

    def branch(self, worktree: Path) -> GitReadResult:
        return self._run(worktree, ("rev-parse", "--abbrev-ref", "HEAD"))

    def head(self, worktree: Path) -> GitReadResult:
        return self._run(worktree, ("rev-parse", "HEAD"))

    def is_ancestor(self, worktree: Path, ancestor: str) -> GitReadResult:
        if (
            not isinstance(ancestor, str)
            or not ancestor.strip()
            or "\x00" in ancestor
            or "\r" in ancestor
            or "\n" in ancestor
        ):
            return GitReadResult(False)
        return self._run(
            worktree,
            ("merge-base", "--is-ancestor", ancestor.strip(), "HEAD"),
        )


def _same_path(left: str | Path, right: str | Path) -> bool:
    try:
        a = str(Path(left).expanduser().resolve(strict=False)).casefold()
        b = str(Path(right).expanduser().resolve(strict=False)).casefold()
    except OSError:
        return False
    return a == b


class GitProjectIdentityVerifier:
    def __init__(self, *, runner: GitReadOnlyRunner | None = None) -> None:
        self._runner = runner or StrictReadOnlyGitRunner()

    def verify(self, binding: SerenaProjectBinding) -> SerenaOperationResult:
        worktree = Path(binding.worktree_path).expanduser().resolve(strict=False)
        if not worktree.is_dir():
            return SerenaOperationResult(success=False, error_code="PROJECT_NOT_FOUND")

        if binding.identity_policy is ProjectIdentityPolicy.NO_GIT:
            return SerenaOperationResult(success=True)

        root = self._runner.show_toplevel(worktree)
        if not root.success:
            if binding.identity_policy is ProjectIdentityPolicy.READ_ONLY_DISCOVERY:
                return SerenaOperationResult(success=True)
            return SerenaOperationResult(
                success=False,
                error_code="PROJECT_GIT_IDENTITY_FAILED",
            )
        if not _same_path(root.stdout, worktree):
            return SerenaOperationResult(
                success=False,
                error_code="PROJECT_ROOT_MISMATCH",
            )

        if binding.identity_policy is ProjectIdentityPolicy.READ_ONLY_DISCOVERY:
            return SerenaOperationResult(success=True)

        if binding.expected_branch is not None:
            branch = self._runner.branch(worktree)
            if not branch.success:
                return SerenaOperationResult(
                    success=False,
                    error_code="PROJECT_GIT_IDENTITY_FAILED",
                )
            if branch.stdout != binding.expected_branch:
                return SerenaOperationResult(
                    success=False,
                    error_code="PROJECT_BRANCH_MISMATCH",
                )

        head = self._runner.head(worktree)
        if not head.success:
            return SerenaOperationResult(
                success=False,
                error_code="PROJECT_GIT_IDENTITY_FAILED",
            )

        if binding.identity_policy is ProjectIdentityPolicy.EXACT:
            if binding.expected_head is not None and head.stdout != binding.expected_head:
                return SerenaOperationResult(
                    success=False,
                    error_code="PROJECT_HEAD_MISMATCH",
                )
            return SerenaOperationResult(success=True)

        if binding.identity_policy is ProjectIdentityPolicy.AUTHORIZED_SUCCESSOR:
            if binding.expected_head is None:
                return SerenaOperationResult(
                    success=False,
                    error_code="EXPECTED_HEAD_REQUIRED",
                )
            if head.stdout == binding.expected_head:
                return SerenaOperationResult(success=True)
            relation = self._runner.is_ancestor(worktree, binding.expected_head)
            if not relation.success:
                return SerenaOperationResult(
                    success=False,
                    error_code="PROJECT_HEAD_NOT_AUTHORIZED_SUCCESSOR",
                )
            return SerenaOperationResult(success=True)

        return SerenaOperationResult(
            success=False,
            error_code="PROJECT_IDENTITY_POLICY_UNSUPPORTED",
        )
