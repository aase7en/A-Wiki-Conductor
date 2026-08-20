from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

from a_conductor.native_execution import (
    NativeCommandSpec,
    NativeExecutionError,
    NativeExecutionScope,
    NativeFileSystem,
    NativeSubprocessRunner,
)


def scope_for(
    root: Path,
    *,
    mutation_allowed: bool = False,
    allowed_executables: tuple[str, ...] = (),
    allowed_environment_overrides: tuple[str, ...] = (),
    max_timeout_seconds: int = 60,
    max_output_bytes: int = 1024,
) -> NativeExecutionScope:
    return NativeExecutionScope(
        root=root,
        mutation_allowed=mutation_allowed,
        allowed_executables=allowed_executables,
        allowed_environment_overrides=allowed_environment_overrides,
        max_timeout_seconds=max_timeout_seconds,
        max_output_bytes=max_output_bytes,
    )


def python_name() -> str:
    return Path(sys.executable).name


def test_scope_requires_absolute_existing_directory(tmp_path: Path) -> None:
    with pytest.raises(NativeExecutionError) as exc_info:
        NativeExecutionScope(root=Path("relative"))
    assert exc_info.value.code == "ROOT_PATH_INVALID"

    missing = tmp_path / "missing"
    with pytest.raises(NativeExecutionError) as exc_info:
        NativeExecutionScope(root=missing.resolve())
    assert exc_info.value.code == "ROOT_NOT_FOUND"


def test_read_text_is_root_confined_bounded_and_hashed(tmp_path: Path) -> None:
    target = tmp_path / "note.txt"
    target.write_text("hello", encoding="utf-8")
    fs = NativeFileSystem(scope_for(tmp_path.resolve()))

    result = fs.read_text("note.txt", max_bytes=10)

    assert result.relative_path == "note.txt"
    assert result.content == "hello"
    assert result.size_bytes == 5
    assert result.sha256 == hashlib.sha256(b"hello").hexdigest()

    with pytest.raises(NativeExecutionError) as exc_info:
        fs.read_text("note.txt", max_bytes=4)
    assert exc_info.value.code == "FILE_TOO_LARGE"


def test_paths_reject_absolute_and_parent_escape(tmp_path: Path) -> None:
    fs = NativeFileSystem(scope_for(tmp_path.resolve()))

    with pytest.raises(NativeExecutionError) as exc_info:
        fs.read_text(str((tmp_path / "outside.txt").resolve()))
    assert exc_info.value.code == "ABSOLUTE_PATH_FORBIDDEN"

    with pytest.raises(NativeExecutionError) as exc_info:
        fs.read_text("../outside.txt")
    assert exc_info.value.code == "PATH_OUTSIDE_ROOT"


def test_symlink_escape_is_rejected_when_platform_allows_symlinks(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(exist_ok=True)
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    link = tmp_path / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")

    fs = NativeFileSystem(scope_for(tmp_path.resolve()))
    with pytest.raises(NativeExecutionError) as exc_info:
        fs.read_text("link/secret.txt")
    assert exc_info.value.code == "PATH_OUTSIDE_ROOT"


def test_list_directory_is_single_level_and_deterministic(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_text("bb", encoding="utf-8")
    (tmp_path / "A.txt").write_text("a", encoding="utf-8")
    (tmp_path / "folder").mkdir()
    fs = NativeFileSystem(scope_for(tmp_path.resolve()))

    entries = fs.list_directory(".")

    assert [entry.name for entry in entries] == ["A.txt", "b.txt", "folder"]
    assert [entry.kind for entry in entries] == ["file", "file", "directory"]
    assert entries[0].size_bytes == 1
    assert entries[2].size_bytes is None


def test_write_requires_mutation_authority(tmp_path: Path) -> None:
    fs = NativeFileSystem(scope_for(tmp_path.resolve(), mutation_allowed=False))

    with pytest.raises(NativeExecutionError) as exc_info:
        fs.write_text("new.txt", "hello")
    assert exc_info.value.code == "MUTATION_FORBIDDEN"
    assert not (tmp_path / "new.txt").exists()


def test_new_write_is_atomic_and_returns_digest(tmp_path: Path) -> None:
    fs = NativeFileSystem(scope_for(tmp_path.resolve(), mutation_allowed=True))

    result = fs.write_text("new.txt", "hello")

    assert result.created is True
    assert result.relative_path == "new.txt"
    assert result.sha256 == hashlib.sha256(b"hello").hexdigest()
    assert (tmp_path / "new.txt").read_text(encoding="utf-8") == "hello"
    assert not tuple(tmp_path.glob(".new.txt.*.tmp"))


def test_existing_write_requires_matching_sha256_precondition(tmp_path: Path) -> None:
    target = tmp_path / "existing.txt"
    target.write_text("old", encoding="utf-8")
    fs = NativeFileSystem(scope_for(tmp_path.resolve(), mutation_allowed=True))

    with pytest.raises(NativeExecutionError) as exc_info:
        fs.write_text("existing.txt", "new")
    assert exc_info.value.code == "OVERWRITE_PRECONDITION_REQUIRED"
    assert target.read_text(encoding="utf-8") == "old"

    with pytest.raises(NativeExecutionError) as exc_info:
        fs.write_text("existing.txt", "new", expected_sha256="0" * 64)
    assert exc_info.value.code == "FILE_PRECONDITION_FAILED"
    assert target.read_text(encoding="utf-8") == "old"

    current = hashlib.sha256(b"old").hexdigest()
    result = fs.write_text("existing.txt", "new", expected_sha256=current)
    assert result.created is False
    assert target.read_text(encoding="utf-8") == "new"


def test_write_requires_existing_parent_and_does_not_create_tree(tmp_path: Path) -> None:
    fs = NativeFileSystem(scope_for(tmp_path.resolve(), mutation_allowed=True))

    with pytest.raises(NativeExecutionError) as exc_info:
        fs.write_text("missing/child.txt", "x")
    assert exc_info.value.code == "PARENT_NOT_FOUND"
    assert not (tmp_path / "missing").exists()


def test_subprocess_rejects_string_command_and_unlisted_executable(tmp_path: Path) -> None:
    runner = NativeSubprocessRunner(scope_for(tmp_path.resolve()))

    with pytest.raises(NativeExecutionError) as exc_info:
        runner.run(NativeCommandSpec(argv="echo hello"))  # type: ignore[arg-type]
    assert exc_info.value.code == "ARGV_INVALID"

    with pytest.raises(NativeExecutionError) as exc_info:
        runner.run(NativeCommandSpec(argv=(sys.executable, "-c", "print('x')")))
    assert exc_info.value.code == "EXECUTABLE_NOT_ALLOWED"


def test_subprocess_runs_allowed_argv_with_confined_cwd(tmp_path: Path) -> None:
    child = tmp_path / "child"
    child.mkdir()
    runner = NativeSubprocessRunner(
        scope_for(tmp_path.resolve(), allowed_executables=(python_name(),))
    )

    result = runner.run(
        NativeCommandSpec(
            argv=(sys.executable, "-c", "import os; print(os.path.basename(os.getcwd()))"),
            cwd="child",
        )
    )

    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.stdout.strip() == "child"
    assert result.stderr == ""
    assert result.executable == python_name()
    assert result.argument_count == 3

    with pytest.raises(NativeExecutionError) as exc_info:
        runner.run(
            NativeCommandSpec(
                argv=(sys.executable, "-c", "print('x')"),
                cwd="..",
            )
        )
    assert exc_info.value.code == "PATH_OUTSIDE_ROOT"


def test_subprocess_does_not_inherit_arbitrary_secret_environment(tmp_path: Path) -> None:
    environment = dict(os.environ)
    environment["TOP_SECRET_VALUE"] = "should-not-leak"
    runner = NativeSubprocessRunner(
        scope_for(tmp_path.resolve(), allowed_executables=(python_name(),)),
        environment_source=environment,
    )

    result = runner.run(
        NativeCommandSpec(
            argv=(
                sys.executable,
                "-c",
                "import os; print(os.environ.get('TOP_SECRET_VALUE', 'absent'))",
            )
        )
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == "absent"
    assert "should-not-leak" not in result.stdout


def test_subprocess_environment_override_requires_explicit_key_authority(tmp_path: Path) -> None:
    base = scope_for(tmp_path.resolve(), allowed_executables=(python_name(),))
    runner = NativeSubprocessRunner(base)
    spec = NativeCommandSpec(
        argv=(sys.executable, "-c", "print('x')"),
        environment_overrides=(("TEST_VISIBLE", "yes"),),
    )
    with pytest.raises(NativeExecutionError) as exc_info:
        runner.run(spec)
    assert exc_info.value.code == "ENV_OVERRIDE_NOT_ALLOWED"

    allowed = scope_for(
        tmp_path.resolve(),
        allowed_executables=(python_name(),),
        allowed_environment_overrides=("TEST_VISIBLE",),
    )
    result = NativeSubprocessRunner(allowed).run(
        NativeCommandSpec(
            argv=(
                sys.executable,
                "-c",
                "import os; print(os.environ.get('TEST_VISIBLE', 'absent'))",
            ),
            environment_overrides=(("TEST_VISIBLE", "yes"),),
        )
    )
    assert result.stdout.strip() == "yes"


def test_mutation_intent_requires_project_mutation_authority(tmp_path: Path) -> None:
    runner = NativeSubprocessRunner(
        scope_for(
            tmp_path.resolve(),
            mutation_allowed=False,
            allowed_executables=(python_name(),),
        )
    )

    with pytest.raises(NativeExecutionError) as exc_info:
        runner.run(
            NativeCommandSpec(
                argv=(sys.executable, "-c", "print('not run')"),
                mutation_intent=True,
            )
        )
    assert exc_info.value.code == "MUTATION_FORBIDDEN"


def test_subprocess_timeout_is_bounded_and_reported(tmp_path: Path) -> None:
    runner = NativeSubprocessRunner(
        scope_for(
            tmp_path.resolve(),
            allowed_executables=(python_name(),),
            max_timeout_seconds=2,
        )
    )

    result = runner.run(
        NativeCommandSpec(
            argv=(sys.executable, "-c", "import time; time.sleep(2)"),
            timeout_seconds=1,
        )
    )

    assert result.timed_out is True
    assert result.exit_code is None

    with pytest.raises(NativeExecutionError) as exc_info:
        runner.run(
            NativeCommandSpec(
                argv=(sys.executable, "-c", "print('x')"),
                timeout_seconds=3,
            )
        )
    assert exc_info.value.code == "TIMEOUT_INVALID"


def test_subprocess_output_is_bounded_but_digest_covers_full_stream(tmp_path: Path) -> None:
    runner = NativeSubprocessRunner(
        scope_for(
            tmp_path.resolve(),
            allowed_executables=(python_name(),),
            max_output_bytes=10,
        )
    )

    result = runner.run(
        NativeCommandSpec(
            argv=(sys.executable, "-c", "import sys; sys.stdout.write('x' * 100)"),
        )
    )

    assert result.exit_code == 0
    assert result.stdout == "x" * 10
    assert result.stdout_truncated is True
    assert result.stdout_sha256 == hashlib.sha256(b"x" * 100).hexdigest()
    assert result.stderr_truncated is False
    assert result.stderr_sha256 == hashlib.sha256(b"").hexdigest()
