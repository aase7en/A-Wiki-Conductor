from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from a_conductor.native_execution import NativeCommandResult, NativeExecutionError
from a_conductor.sunday_runtime import (
    RuntimeLaneBinding,
    SunDayRuntime,
    SunDayRuntimeError,
)


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        shell=False,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _lane(tmp_path: Path) -> tuple[Path, Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "runtime-test@example.invalid")
    _git(repo, "config", "user.name", "Runtime Test")
    (repo / "seed.txt").write_text("needle\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-m", "seed")
    worktree = tmp_path / "lane"
    _git(repo, "worktree", "add", "-b", "runtime-lane", str(worktree))
    head = _git(worktree, "rev-parse", "HEAD")
    return repo, worktree, head


def _binding(repo: Path, worktree: Path, base_head: str, **overrides: str) -> RuntimeLaneBinding:
    return RuntimeLaneBinding(
        repo_root=repo,
        worktree_root=worktree,
        branch=overrides.get("branch", "runtime-lane"),
        head=overrides.get("head", base_head),
        claim_id=overrides.get("claim_id", "issue:333"),
    )


def _result(
    *,
    executable: str,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
) -> NativeCommandResult:
    return NativeCommandResult(
        executable=executable,
        argument_count=1,
        exit_code=exit_code,
        timed_out=False,
        stdout=stdout,
        stderr=stderr,
        stdout_sha256=hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
        stderr_sha256=hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
        stdout_truncated=False,
        stderr_truncated=False,
    )


class _CapturingRunner:
    def __init__(self, result: NativeCommandResult) -> None:
        self.result = result
        self.specs = []

    def run(self, spec):
        self.specs.append(spec)
        return self.result


def test_runtime_verifies_exact_lane_binding(tmp_path: Path) -> None:
    repo, worktree, head = _lane(tmp_path)
    runtime = SunDayRuntime(_binding(repo, worktree, head))

    evidence = runtime.verify_context()

    assert Path(evidence.repo_root) == repo.resolve()
    assert Path(evidence.worktree_root) == worktree.resolve()
    assert evidence.branch == "runtime-lane"
    assert evidence.head == head
    assert evidence.claim_id == "issue:333"


@pytest.mark.parametrize(
    "overrides",
    [
        {"branch": "wrong-branch"},
        {"head": "0" * 40},
    ],
)
def test_runtime_fails_closed_on_context_drift(
    tmp_path: Path,
    overrides: dict[str, str],
) -> None:
    repo, worktree, head = _lane(tmp_path)
    runtime = SunDayRuntime(_binding(repo, worktree, head, **overrides))

    with pytest.raises(SunDayRuntimeError, match="CONTEXT_DRIFT") as exc:
        runtime.verify_context()

    assert exc.value.code == "CONTEXT_DRIFT"


def test_runtime_read_and_list_are_confined_to_bound_worktree(tmp_path: Path) -> None:
    repo, worktree, head = _lane(tmp_path)
    runtime = SunDayRuntime(_binding(repo, worktree, head))

    result = runtime.read_text("seed.txt")
    entries = runtime.list_directory(".")

    assert result.content.splitlines() == ["needle"]
    assert result.relative_path == "seed.txt"
    assert "seed.txt" in {entry.name for entry in entries}

    with pytest.raises(NativeExecutionError, match="PATH_OUTSIDE_ROOT"):
        runtime.read_text("../outside.txt")


def test_runtime_mutation_requires_explicit_authority(tmp_path: Path) -> None:
    repo, worktree, head = _lane(tmp_path)
    runtime = SunDayRuntime(_binding(repo, worktree, head), mutation_allowed=False)

    with pytest.raises(NativeExecutionError, match="MUTATION_FORBIDDEN"):
        runtime.create_text_if_absent("new.txt", "blocked")


def test_runtime_search_uses_rg_argv_without_shell_text(tmp_path: Path) -> None:
    repo, worktree, head = _lane(tmp_path)
    runner = _CapturingRunner(
        _result(
            executable="rg",
            stdout="seed.txt:1:needle\n",
        )
    )
    runtime = SunDayRuntime(
        _binding(repo, worktree, head),
        search_runner=runner,
    )

    result = runtime.search_text("needle && echo unsafe", ("seed.txt",))

    assert result.matched is True
    assert result.output == "seed.txt:1:needle\n"
    assert len(runner.specs) == 1
    spec = runner.specs[0]
    assert spec.argv[0] == "rg"
    assert spec.argv[-2] == "needle && echo unsafe"
    assert spec.argv[-1] == "seed.txt"
    assert spec.cwd == "."
    assert spec.mutation_intent is False


def test_runtime_search_rejects_path_escape_before_runner(tmp_path: Path) -> None:
    repo, worktree, head = _lane(tmp_path)
    runner = _CapturingRunner(_result(executable="rg"))
    runtime = SunDayRuntime(
        _binding(repo, worktree, head),
        search_runner=runner,
    )

    with pytest.raises(NativeExecutionError, match="PATH_OUTSIDE_ROOT"):
        runtime.search_text("needle", ("../outside.txt",))

    assert runner.specs == []


def test_runtime_has_no_raw_shell_default(tmp_path: Path) -> None:
    repo, worktree, head = _lane(tmp_path)
    runtime = SunDayRuntime(_binding(repo, worktree, head))

    with pytest.raises(SunDayRuntimeError, match="ARGV_INVALID"):
        runtime.run_allowlisted("git status")  # type: ignore[arg-type]

    with pytest.raises(SunDayRuntimeError, match="EXECUTABLE_NOT_ALLOWED") as exc:
        runtime.run_allowlisted(("git", "status", "--short"))

    assert exc.value.code == "EXECUTABLE_NOT_ALLOWED"
