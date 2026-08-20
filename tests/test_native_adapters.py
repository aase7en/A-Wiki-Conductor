from __future__ import annotations

import sys
from pathlib import Path

import pytest

from a_conductor.native_adapters import NativeGitReadAdapter, NativeVerificationAdapter
from a_conductor.native_execution import (
    NativeCommandResult,
    NativeExecutionError,
    NativeExecutionScope,
)


class FakeRunner:
    def __init__(self) -> None:
        self.calls = []

    def run(self, spec):
        self.calls.append(spec)
        return NativeCommandResult(
            executable=Path(spec.argv[0]).name,
            argument_count=len(spec.argv),
            exit_code=0,
            timed_out=False,
            stdout="ok",
            stderr="",
            stdout_sha256="0" * 64,
            stderr_sha256="0" * 64,
            stdout_truncated=False,
            stderr_truncated=False,
        )


def make_scope(
    root: Path,
    *,
    mutation_allowed: bool = True,
    allowed_executables: tuple[str, ...] = ("git.exe", "python.exe"),
) -> NativeExecutionScope:
    return NativeExecutionScope(
        root=root.resolve(),
        mutation_allowed=mutation_allowed,
        allowed_executables=allowed_executables,
        max_timeout_seconds=120,
    )


def test_git_status_uses_fixed_read_only_shape_and_safe_directory(tmp_path: Path) -> None:
    runner = FakeRunner()
    adapter = NativeGitReadAdapter(make_scope(tmp_path), runner=runner, git_executable="git.exe")

    result = adapter.status_short(timeout_seconds=7)

    assert result.stdout == "ok"
    assert len(runner.calls) == 1
    spec = runner.calls[0]
    assert spec.argv == (
        "git.exe",
        "-c",
        f"safe.directory={tmp_path.resolve().as_posix()}",
        "-c",
        "core.fsmonitor=false",
        "-C",
        str(tmp_path.resolve()),
        "status",
        "--short",
        "--untracked-files=all",
    )
    assert spec.cwd == "."
    assert spec.timeout_seconds == 7
    assert spec.mutation_intent is False


def test_git_working_diff_places_confined_pathspecs_after_separator(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x", encoding="utf-8")
    runner = FakeRunner()
    adapter = NativeGitReadAdapter(make_scope(tmp_path), runner=runner, git_executable="git.exe")

    adapter.working_diff(("src/a.py",), timeout_seconds=9)

    spec = runner.calls[0]
    assert spec.argv[-5:] == ("diff", "--no-ext-diff", "--no-textconv", "--", "src/a.py")
    separator = spec.argv.index("--")
    assert spec.argv[separator + 1 :] == ("src/a.py",)
    assert spec.mutation_intent is False

    with pytest.raises(NativeExecutionError) as exc_info:
        adapter.working_diff(("../outside.py",))
    assert exc_info.value.code == "PATH_OUTSIDE_ROOT"
    assert len(runner.calls) == 1


def test_git_cached_diff_is_fixed_and_cannot_be_widened_to_mutation(tmp_path: Path) -> None:
    runner = FakeRunner()
    adapter = NativeGitReadAdapter(make_scope(tmp_path), runner=runner, git_executable="git.exe")

    adapter.cached_diff()

    spec = runner.calls[0]
    assert spec.argv[-5:] == ("diff", "--cached", "--no-ext-diff", "--no-textconv", "--")
    for forbidden in ("add", "commit", "reset", "clean", "checkout", "stash", "rebase", "merge", "push"):
        assert not hasattr(adapter, forbidden)


def test_git_path_named_like_option_is_safe_after_double_dash(tmp_path: Path) -> None:
    target = tmp_path / "--danger"
    target.write_text("x", encoding="utf-8")
    runner = FakeRunner()
    adapter = NativeGitReadAdapter(make_scope(tmp_path), runner=runner, git_executable="git.exe")

    adapter.working_diff(("--danger",))

    spec = runner.calls[0]
    separator = spec.argv.index("--")
    assert spec.argv[separator + 1 :] == ("--danger",)


def test_pytest_adapter_uses_fixed_python_module_shape_and_mutation_intent(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    runner = FakeRunner()
    adapter = NativeVerificationAdapter(
        make_scope(tmp_path),
        runner=runner,
        python_executable=sys.executable,
    )

    adapter.pytest(("tests",), timeout_seconds=60)

    spec = runner.calls[0]
    assert spec.argv == (sys.executable, "-m", "pytest", "-q", "tests")
    assert spec.cwd == "."
    assert spec.timeout_seconds == 60
    assert spec.mutation_intent is True


def test_compileall_adapter_uses_fixed_shape(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    runner = FakeRunner()
    adapter = NativeVerificationAdapter(
        make_scope(tmp_path),
        runner=runner,
        python_executable=sys.executable,
    )

    adapter.compileall(("src",), timeout_seconds=30)

    spec = runner.calls[0]
    assert spec.argv == (sys.executable, "-m", "compileall", "-q", "src")
    assert spec.mutation_intent is True


def test_verification_refuses_read_only_project_before_runner(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    runner = FakeRunner()
    adapter = NativeVerificationAdapter(
        make_scope(tmp_path, mutation_allowed=False),
        runner=runner,
        python_executable=sys.executable,
    )

    with pytest.raises(NativeExecutionError) as exc_info:
        adapter.pytest(("tests",))
    assert exc_info.value.code == "MUTATION_FORBIDDEN"
    assert runner.calls == []


def test_verification_paths_must_exist_and_stay_in_root(tmp_path: Path) -> None:
    runner = FakeRunner()
    adapter = NativeVerificationAdapter(
        make_scope(tmp_path),
        runner=runner,
        python_executable=sys.executable,
    )

    with pytest.raises(NativeExecutionError) as exc_info:
        adapter.pytest(("missing",))
    assert exc_info.value.code == "PATH_NOT_FOUND"

    with pytest.raises(NativeExecutionError) as exc_info:
        adapter.compileall(("../outside",))
    assert exc_info.value.code == "PATH_OUTSIDE_ROOT"
    assert runner.calls == []


def test_verification_path_named_like_option_is_rendered_as_path(tmp_path: Path) -> None:
    target = tmp_path / "-tests"
    target.mkdir()
    runner = FakeRunner()
    adapter = NativeVerificationAdapter(
        make_scope(tmp_path),
        runner=runner,
        python_executable=sys.executable,
    )

    adapter.pytest(("-tests",))

    spec = runner.calls[0]
    assert spec.argv[-1] == "./-tests"
    assert spec.argv[-1].startswith("./")


def test_adapters_do_not_expose_generic_run_method(tmp_path: Path) -> None:
    runner = FakeRunner()
    git = NativeGitReadAdapter(make_scope(tmp_path), runner=runner, git_executable="git.exe")
    verify = NativeVerificationAdapter(
        make_scope(tmp_path),
        runner=runner,
        python_executable=sys.executable,
    )

    assert not hasattr(git, "run")
    assert not hasattr(verify, "run")
