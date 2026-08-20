from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from a_conductor.project_identity import (
    GitProjectIdentityVerifier,
    GitReadResult,
    StrictReadOnlyGitRunner,
)
from a_conductor.serena_runtime import ProjectIdentityPolicy, SerenaProjectBinding


class FakeRunner:
    def __init__(self) -> None:
        self.root_result = GitReadResult(True, "")
        self.branch_result = GitReadResult(True, "main")
        self.head_result = GitReadResult(True, "abc123")
        self.ancestor_result = GitReadResult(True, "")
        self.calls: list[tuple[str, object]] = []

    def show_toplevel(self, worktree: Path) -> GitReadResult:
        self.calls.append(("root", worktree))
        return self.root_result

    def branch(self, worktree: Path) -> GitReadResult:
        self.calls.append(("branch", worktree))
        return self.branch_result

    def head(self, worktree: Path) -> GitReadResult:
        self.calls.append(("head", worktree))
        return self.head_result

    def is_ancestor(self, worktree: Path, ancestor: str) -> GitReadResult:
        self.calls.append(("ancestor", ancestor))
        return self.ancestor_result


def binding(
    tmp_path: Path,
    *,
    policy: ProjectIdentityPolicy = ProjectIdentityPolicy.EXACT,
    expected_branch: str | None = "main",
    expected_head: str | None = "abc123",
    create: bool = True,
) -> SerenaProjectBinding:
    worktree = tmp_path / "project"
    if create:
        worktree.mkdir(parents=True, exist_ok=True)
    return SerenaProjectBinding(
        project_id="project-test",
        worktree_path=str(worktree),
        identity_policy=policy,
        expected_branch=expected_branch,
        expected_head=expected_head,
        mutation_allowed=False,
    )


def verifier_for(tmp_path: Path, runner: FakeRunner, **kwargs) -> tuple[GitProjectIdentityVerifier, SerenaProjectBinding]:
    target = binding(tmp_path, **kwargs)
    runner.root_result = GitReadResult(True, str(Path(target.worktree_path).resolve()))
    return GitProjectIdentityVerifier(runner=runner), target


def test_exact_policy_success(tmp_path: Path) -> None:
    runner = FakeRunner()
    verifier, target = verifier_for(tmp_path, runner)

    result = verifier.verify(target)

    assert result.success is True
    assert [name for name, _ in runner.calls] == ["root", "branch", "head"]


def test_exact_policy_rejects_root_mismatch(tmp_path: Path) -> None:
    runner = FakeRunner()
    verifier, target = verifier_for(tmp_path, runner)
    runner.root_result = GitReadResult(True, str((tmp_path / "other").resolve()))

    result = verifier.verify(target)

    assert result.success is False
    assert result.error_code == "PROJECT_ROOT_MISMATCH"
    assert [name for name, _ in runner.calls] == ["root"]


def test_exact_policy_rejects_branch_mismatch(tmp_path: Path) -> None:
    runner = FakeRunner()
    verifier, target = verifier_for(tmp_path, runner)
    runner.branch_result = GitReadResult(True, "feature")

    result = verifier.verify(target)

    assert result.success is False
    assert result.error_code == "PROJECT_BRANCH_MISMATCH"


def test_exact_policy_rejects_head_mismatch(tmp_path: Path) -> None:
    runner = FakeRunner()
    verifier, target = verifier_for(tmp_path, runner)
    runner.head_result = GitReadResult(True, "different")

    result = verifier.verify(target)

    assert result.success is False
    assert result.error_code == "PROJECT_HEAD_MISMATCH"


def test_git_failure_is_redacted(tmp_path: Path) -> None:
    runner = FakeRunner()
    verifier, target = verifier_for(tmp_path, runner)
    runner.root_result = GitReadResult(False, "", "secret stderr should not leak")

    result = verifier.verify(target)

    assert result.success is False
    assert result.error_code == "PROJECT_GIT_IDENTITY_FAILED"
    assert "secret stderr" not in repr(result)


def test_authorized_successor_accepts_descendant(tmp_path: Path) -> None:
    runner = FakeRunner()
    verifier, target = verifier_for(
        tmp_path,
        runner,
        policy=ProjectIdentityPolicy.AUTHORIZED_SUCCESSOR,
        expected_head="base123",
    )
    runner.head_result = GitReadResult(True, "child456")
    runner.ancestor_result = GitReadResult(True, "")

    result = verifier.verify(target)

    assert result.success is True
    assert ("ancestor", "base123") in runner.calls


def test_authorized_successor_rejects_non_descendant(tmp_path: Path) -> None:
    runner = FakeRunner()
    verifier, target = verifier_for(
        tmp_path,
        runner,
        policy=ProjectIdentityPolicy.AUTHORIZED_SUCCESSOR,
        expected_head="base123",
    )
    runner.head_result = GitReadResult(True, "other456")
    runner.ancestor_result = GitReadResult(False, "")

    result = verifier.verify(target)

    assert result.success is False
    assert result.error_code == "PROJECT_HEAD_NOT_AUTHORIZED_SUCCESSOR"


def test_authorized_successor_requires_expected_head(tmp_path: Path) -> None:
    runner = FakeRunner()
    verifier, target = verifier_for(
        tmp_path,
        runner,
        policy=ProjectIdentityPolicy.AUTHORIZED_SUCCESSOR,
        expected_head=None,
    )

    result = verifier.verify(target)

    assert result.success is False
    assert result.error_code == "EXPECTED_HEAD_REQUIRED"


def test_no_git_policy_only_checks_directory(tmp_path: Path) -> None:
    runner = FakeRunner()
    verifier, target = verifier_for(
        tmp_path,
        runner,
        policy=ProjectIdentityPolicy.NO_GIT,
        expected_branch=None,
        expected_head=None,
    )

    result = verifier.verify(target)

    assert result.success is True
    assert runner.calls == []


def test_read_only_discovery_allows_non_git_directory(tmp_path: Path) -> None:
    runner = FakeRunner()
    verifier, target = verifier_for(
        tmp_path,
        runner,
        policy=ProjectIdentityPolicy.READ_ONLY_DISCOVERY,
        expected_branch=None,
        expected_head=None,
    )
    runner.root_result = GitReadResult(False, "")

    result = verifier.verify(target)

    assert result.success is True
    assert [name for name, _ in runner.calls] == ["root"]


def test_missing_directory_fails_before_git(tmp_path: Path) -> None:
    runner = FakeRunner()
    verifier, target = verifier_for(tmp_path, runner, create=False)

    result = verifier.verify(target)

    assert result.success is False
    assert result.error_code == "PROJECT_NOT_FOUND"
    assert runner.calls == []


def test_strict_runner_uses_only_read_only_direct_argv(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        if "--show-toplevel" in argv:
            stdout = str(tmp_path)
        elif "--abbrev-ref" in argv:
            stdout = "main"
        elif "merge-base" in argv:
            stdout = ""
        else:
            stdout = "abc123"
        return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")

    monkeypatch.setattr("a_conductor.project_identity.subprocess.run", fake_run)
    runner = StrictReadOnlyGitRunner(git_executable="git.exe")

    assert runner.show_toplevel(tmp_path).success is True
    assert runner.branch(tmp_path).success is True
    assert runner.head(tmp_path).success is True
    assert runner.is_ancestor(tmp_path, "abc123").success is True

    assert len(calls) == 4
    for argv, kwargs in calls:
        assert argv[0] == "git.exe"
        assert kwargs["shell"] is False
        joined = " ".join(argv).lower()
        for forbidden in (
            "checkout",
            "switch",
            "reset",
            "clean",
            "fetch",
            "pull",
            "merge ",
            "rebase",
            "stash",
            "push",
        ):
            assert forbidden not in joined


def test_runner_rejects_bad_ancestor_ref_before_subprocess(tmp_path: Path, monkeypatch) -> None:
    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("must not run")

    monkeypatch.setattr("a_conductor.project_identity.subprocess.run", fake_run)
    runner = StrictReadOnlyGitRunner()

    result = runner.is_ancestor(tmp_path, "bad\x00ref")

    assert result.success is False
    assert called is False
