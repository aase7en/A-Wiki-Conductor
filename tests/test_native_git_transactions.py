from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from a_conductor.native_execution import NativeExecutionError, NativeExecutionScope
from a_conductor.native_git_transactions import NativeGitTransactionAdapter


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "a-conductor@example.invalid")
    git(repo, "config", "user.name", "A-Conductor Test")
    tracked = repo / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    git(repo, "add", "--", "tracked.txt")
    git(repo, "-c", "commit.gpgSign=false", "commit", "--no-verify", "-m", "initial")
    return repo


def adapter_for(repo: Path, *, mutation_allowed: bool = True) -> NativeGitTransactionAdapter:
    scope = NativeExecutionScope(
        root=repo.resolve(),
        mutation_allowed=mutation_allowed,
        allowed_executables=("git",),
        max_timeout_seconds=30,
        max_output_bytes=200_000,
    )
    return NativeGitTransactionAdapter(scope, git_executable="git")


def expected(snapshot):
    return {
        "expected_head": snapshot.head,
        "expected_status_sha256": snapshot.status.stdout_sha256,
        "expected_cached_diff_sha256": snapshot.cached_diff.stdout_sha256,
    }


def test_snapshot_captures_exact_head_status_and_index(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    adapter = adapter_for(repo)

    snapshot = adapter.snapshot()

    assert snapshot.head == git(repo, "rev-parse", "HEAD")
    assert snapshot.status.exit_code == 0
    assert snapshot.status.stdout == ""
    assert snapshot.cached_diff.exit_code == 0
    assert snapshot.cached_diff.stdout == ""


def test_stage_requires_explicit_file_and_returns_new_snapshot(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    adapter = adapter_for(repo)
    before = adapter.snapshot()

    outcome = adapter.stage(("tracked.txt",), **expected(before))

    assert outcome.command.exit_code == 0
    assert outcome.snapshot.head == before.head
    assert outcome.snapshot.cached_diff.stdout != ""
    assert git(repo, "diff", "--cached", "--name-only") == "tracked.txt"


def test_stage_refuses_status_drift_before_mutation(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    adapter = adapter_for(repo)
    before = adapter.snapshot()
    (repo / "new.txt").write_text("drift\n", encoding="utf-8")

    with pytest.raises(NativeExecutionError) as exc_info:
        adapter.stage(("tracked.txt",), **expected(before))
    assert exc_info.value.code == "GIT_STATUS_DRIFT"
    assert git(repo, "diff", "--cached", "--name-only") == ""


def test_stage_refuses_head_drift_even_when_status_and_index_match(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    adapter = adapter_for(repo)
    before = adapter.snapshot()
    git(repo, "-c", "commit.gpgSign=false", "commit", "--allow-empty", "--no-verify", "-m", "other")

    with pytest.raises(NativeExecutionError) as exc_info:
        adapter.stage(("tracked.txt",), **expected(before))
    assert exc_info.value.code == "GIT_HEAD_DRIFT"


def test_stage_refuses_index_drift_before_mutation(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    adapter = adapter_for(repo)
    before = adapter.snapshot()
    git(repo, "add", "--", "tracked.txt")

    with pytest.raises(NativeExecutionError) as exc_info:
        adapter.stage(("tracked.txt",), **expected(before))
    assert exc_info.value.code == "GIT_INDEX_DRIFT"


def test_stage_rejects_blanket_and_directory_pathspecs(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    folder = repo / "folder"
    folder.mkdir()
    (folder / "x.txt").write_text("x", encoding="utf-8")
    adapter = adapter_for(repo)
    snapshot = adapter.snapshot()

    for pathspec in (".", "folder"):
        with pytest.raises(NativeExecutionError) as exc_info:
            adapter.stage((pathspec,), **expected(snapshot))
        assert exc_info.value.code == "GIT_STAGE_PATH_INVALID"
    assert git(repo, "diff", "--cached", "--name-only") == ""


def test_stage_refuses_read_only_scope(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    observer = adapter_for(repo)
    snapshot = observer.snapshot()
    read_only = adapter_for(repo, mutation_allowed=False)

    with pytest.raises(NativeExecutionError) as exc_info:
        read_only.stage(("tracked.txt",), **expected(snapshot))
    assert exc_info.value.code == "MUTATION_FORBIDDEN"
    assert git(repo, "diff", "--cached", "--name-only") == ""


def test_stage_refuses_active_external_clean_filter(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / ".gitattributes").write_text("*.txt filter=evil\n", encoding="utf-8")
    git(repo, "add", "--", ".gitattributes")
    git(repo, "-c", "commit.gpgSign=false", "commit", "--no-verify", "-m", "attrs")
    git(repo, "config", "filter.evil.clean", "cat")
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    adapter = adapter_for(repo)
    snapshot = adapter.snapshot()

    with pytest.raises(NativeExecutionError) as exc_info:
        adapter.stage(("tracked.txt",), **expected(snapshot))
    assert exc_info.value.code == "GIT_FILTER_POLICY_UNSAFE"
    assert git(repo, "diff", "--cached", "--name-only") == ""


def test_commit_requires_nonempty_cached_diff(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    adapter = adapter_for(repo)
    snapshot = adapter.snapshot()

    with pytest.raises(NativeExecutionError) as exc_info:
        adapter.commit("nothing", **expected(snapshot))
    assert exc_info.value.code == "GIT_NOTHING_STAGED"


def test_commit_refuses_drift_after_stage(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    adapter = adapter_for(repo)
    staged = adapter.stage(("tracked.txt",), **expected(adapter.snapshot()))
    (repo / "new.txt").write_text("drift\n", encoding="utf-8")

    with pytest.raises(NativeExecutionError) as exc_info:
        adapter.commit("should refuse", **expected(staged.snapshot))
    assert exc_info.value.code == "GIT_STATUS_DRIFT"
    assert git(repo, "log", "-1", "--pretty=%s") == "initial"


def test_commit_is_noninteractive_skips_hooks_and_disables_signing(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    hook_sentinel = repo / "hook-ran.txt"
    post_hook_sentinel = repo / "post-hook-ran.txt"
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text(
        f"#!/bin/sh\necho ran > '{hook_sentinel.as_posix()}'\nexit 1\n",
        encoding="utf-8",
    )
    os.chmod(hook, 0o755)
    post_hook = repo / ".git" / "hooks" / "post-commit"
    post_hook.write_text(
        f"#!/bin/sh\necho ran > '{post_hook_sentinel.as_posix()}'\n",
        encoding="utf-8",
    )
    os.chmod(post_hook, 0o755)
    git(repo, "config", "commit.gpgSign", "true")
    git(repo, "config", "gpg.program", "definitely-not-a-real-gpg-program")

    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    adapter = adapter_for(repo)
    staged = adapter.stage(("tracked.txt",), **expected(adapter.snapshot()))

    outcome = adapter.commit("safe commit", **expected(staged.snapshot))

    assert outcome.command.exit_code == 0
    assert outcome.previous_head != outcome.new_head
    assert outcome.new_head == git(repo, "rev-parse", "HEAD")
    assert git(repo, "log", "-1", "--pretty=%s") == "safe commit"
    assert not hook_sentinel.exists()
    assert not post_hook_sentinel.exists()
    assert outcome.snapshot.cached_diff.stdout == ""


def test_transaction_adapter_exposes_no_destructive_or_network_methods(tmp_path: Path) -> None:
    adapter = adapter_for(make_repo(tmp_path))
    for forbidden in (
        "reset",
        "clean",
        "checkout",
        "switch",
        "stash",
        "rebase",
        "merge",
        "push",
        "fetch",
        "pull",
        "remote",
        "run",
    ):
        assert not hasattr(adapter, forbidden)
