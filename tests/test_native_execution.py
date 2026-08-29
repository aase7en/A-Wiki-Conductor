from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

import a_conductor.native_execution as native_execution
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


def test_temp_directory_creation_error_preserves_execution_error_contract(tmp_path: Path, monkeypatch) -> None:
    runner = NativeSubprocessRunner(
        scope_for(tmp_path.resolve(), allowed_executables=(python_name(),))
    )
    monkeypatch.setattr(
        native_execution.tempfile,
        "mkdtemp",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("temp unavailable")),
    )

    with pytest.raises(NativeExecutionError) as exc_info:
        runner.run(NativeCommandSpec(argv=(sys.executable, "-c", "print('unused')")))

    assert exc_info.value.code == "COMMAND_EXECUTION_FAILED"


def test_timeout_result_survives_transient_temp_cleanup_lock(tmp_path: Path, monkeypatch) -> None:
    runner = NativeSubprocessRunner(
        scope_for(
            tmp_path.resolve(),
            allowed_executables=(python_name(),),
            max_timeout_seconds=2,
        )
    )
    real_rmtree = native_execution.shutil.rmtree
    attempts: list[Path] = []

    def transient_lock(path, *args, **kwargs):
        candidate = Path(path)
        if candidate.name.startswith("a-conductor-exec-"):
            attempts.append(candidate)
            if len(attempts) <= 2:
                raise PermissionError("transient Windows temp-file lock")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(native_execution.shutil, "rmtree", transient_lock)
    monkeypatch.setattr(native_execution.time, "sleep", lambda _seconds: None)

    result = runner.run(
        NativeCommandSpec(
            argv=(sys.executable, "-c", "import time; time.sleep(2)"),
            timeout_seconds=1,
        )
    )

    assert result.timed_out is True
    assert result.exit_code is None
    assert len(attempts) == 3

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


def test_temp_cleanup_retry_is_finite_for_persistent_permission_error(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "a-conductor-exec-persistent"
    target.mkdir()
    attempts: list[Path] = []
    sleeps: list[float] = []

    def locked(path, *args, **kwargs):
        attempts.append(Path(path))
        raise PermissionError("still locked")

    monkeypatch.setattr(native_execution.shutil, "rmtree", locked)
    with pytest.raises(PermissionError, match="still locked"):
        native_execution._remove_temp_tree_with_permission_retry(
            target,
            retry_delays=(0.1, 0.2),
            sleep_fn=sleeps.append,
        )

    assert attempts == [target, target, target]
    assert sleeps == [0.1, 0.2]


def test_temp_cleanup_unrelated_oserror_fails_without_retry(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "a-conductor-exec-disk-error"
    target.mkdir()
    attempts: list[Path] = []
    sleeps: list[float] = []

    def broken(path, *args, **kwargs):
        attempts.append(Path(path))
        raise OSError("disk failure")

    monkeypatch.setattr(native_execution.shutil, "rmtree", broken)
    with pytest.raises(OSError, match="disk failure"):
        native_execution._remove_temp_tree_with_permission_retry(
            target,
            retry_delays=(0.1, 0.2),
            sleep_fn=sleeps.append,
        )

    assert attempts == [target]
    assert sleeps == []


def test_persistent_temp_cleanup_lock_is_explicit_cleanup_failure(tmp_path: Path, monkeypatch) -> None:
    runner = NativeSubprocessRunner(
        scope_for(tmp_path.resolve(), allowed_executables=(python_name(),))
    )
    real_rmtree = native_execution.shutil.rmtree
    locked_paths: list[Path] = []

    def locked(path, *args, **kwargs):
        candidate = Path(path)
        if candidate.name.startswith("a-conductor-exec-"):
            locked_paths.append(candidate)
            raise PermissionError("persistent temp lock")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(native_execution.shutil, "rmtree", locked)
    monkeypatch.setattr(native_execution.time, "sleep", lambda _seconds: None)
    try:
        with pytest.raises(NativeExecutionError) as exc_info:
            runner.run(NativeCommandSpec(argv=(sys.executable, "-c", "print('done')")))
        assert exc_info.value.code == "COMMAND_CLEANUP_FAILED"
        assert len(locked_paths) == len(native_execution._TEMP_CLEANUP_RETRY_DELAYS) + 1
    finally:
        monkeypatch.undo()
        for leftover in set(locked_paths):
            if leftover.exists():
                real_rmtree(leftover)


def test_stale_execution_temp_sweep_is_prefix_age_and_symlink_bounded(
    tmp_path: Path, monkeypatch
) -> None:
    now = native_execution.time.time()
    stale = tmp_path / "a-conductor-exec-stale"
    recent = tmp_path / "a-conductor-exec-recent"
    link_like = tmp_path / "a-conductor-exec-link"
    unrelated = tmp_path / "other-temp"
    for candidate in (stale, recent, link_like, unrelated):
        candidate.mkdir()
    os.utime(stale, (now - 90_000, now - 90_000))
    os.utime(recent, (now - 60, now - 60))
    os.utime(link_like, (now - 90_000, now - 90_000))
    os.utime(unrelated, (now - 90_000, now - 90_000))

    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: self == link_like or original_is_symlink(self),
    )

    removed = native_execution._sweep_stale_execution_temp_trees(
        tmp_path,
        now=now,
        stale_after_seconds=86_400,
    )

    assert removed == 1
    assert not stale.exists()
    assert recent.exists()
    assert link_like.exists()
    assert unrelated.exists()


def test_stale_execution_temp_sweep_is_fail_soft(
    tmp_path: Path, monkeypatch
) -> None:
    stale = tmp_path / "a-conductor-exec-locked"
    stale.mkdir()
    os.utime(stale, (1.0, 1.0))

    monkeypatch.setattr(
        native_execution,
        "_remove_temp_tree_with_permission_retry",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("locked")),
    )

    assert native_execution._sweep_stale_execution_temp_trees(
        tmp_path, now=100_000.0, stale_after_seconds=10.0
    ) == 0
    assert stale.exists()


def test_native_runner_attempts_stale_sweep_before_new_temp_dir(
    tmp_path: Path, monkeypatch
) -> None:
    runner = NativeSubprocessRunner(
        scope_for(tmp_path.resolve(), allowed_executables=(python_name(),))
    )
    calls: list[Path] = []

    monkeypatch.setattr(
        native_execution,
        "_sweep_stale_execution_temp_trees",
        lambda root, **_kwargs: calls.append(Path(root)) or 0,
    )

    result = runner.run(
        NativeCommandSpec(argv=(sys.executable, "-c", "print('ok')"))
    )

    assert result.exit_code == 0
    assert calls == [Path(native_execution.tempfile.gettempdir())]


def test_native_runner_creates_versioned_temp_directory_name(tmp_path: Path, monkeypatch) -> None:
    runner = NativeSubprocessRunner(
        scope_for(tmp_path.resolve(), allowed_executables=(python_name(),))
    )
    real_mkdtemp = native_execution.tempfile.mkdtemp
    prefixes: list[str] = []

    def capture_prefix(**kwargs):
        prefixes.append(kwargs["prefix"])
        return real_mkdtemp(**kwargs)

    monkeypatch.setattr(native_execution.tempfile, "mkdtemp", capture_prefix)
    result = runner.run(
        NativeCommandSpec(argv=(sys.executable, "-c", "print('ok')"))
    )

    assert result.exit_code == 0
    assert len(prefixes) == 1
    assert prefixes[0].startswith("a-conductor-exec-v2-")


def test_stale_execution_temp_sweep_caps_work_and_never_waits_for_locks(
    tmp_path: Path, monkeypatch
) -> None:
    for index in range(3):
        candidate = tmp_path / f"a-conductor-exec-old-{index}"
        candidate.mkdir()
        os.utime(candidate, (1.0, 1.0))
    calls: list[tuple[Path, tuple[float, ...] | None]] = []

    def locked(path, **kwargs):
        calls.append((Path(path), kwargs.get("retry_delays")))
        raise PermissionError("locked")

    monkeypatch.setattr(
        native_execution, "_remove_temp_tree_with_permission_retry", locked
    )

    assert native_execution._sweep_stale_execution_temp_trees(
        tmp_path,
        now=100_000.0,
        stale_after_seconds=10.0,
        max_candidates=2,
    ) == 0
    assert len(calls) == 2
    assert all(retry_delays == () for _path, retry_delays in calls)


def test_stale_execution_temp_sweep_skips_active_owner_lock(tmp_path: Path) -> None:
    candidate = tmp_path / "a-conductor-exec-active"
    candidate.mkdir()
    lease = native_execution._acquire_execution_temp_lease(candidate)
    try:
        os.utime(candidate, (1.0, 1.0))
        assert native_execution._sweep_stale_execution_temp_trees(
            tmp_path, now=100_000.0, stale_after_seconds=10.0
        ) == 0
        assert candidate.exists()
    finally:
        native_execution._release_execution_temp_lease(lease)

    assert native_execution._sweep_stale_execution_temp_trees(
        tmp_path, now=100_000.0, stale_after_seconds=10.0
    ) == 1
    assert not candidate.exists()


def test_native_runner_holds_owner_lock_during_subprocess(
    tmp_path: Path, monkeypatch
) -> None:
    runner = NativeSubprocessRunner(
        scope_for(tmp_path.resolve(), allowed_executables=(python_name(),))
    )
    observed: list[bool] = []

    def fake_run(*_args, **kwargs):
        temp_dir = Path(kwargs["stdout"].name).parent
        observed.append(native_execution._execution_temp_lease_available(temp_dir))
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(native_execution.subprocess, "run", fake_run)
    result = runner.run(NativeCommandSpec(argv=(sys.executable, "-c", "pass")))

    assert result.exit_code == 0
    assert observed == [False]


def test_versioned_temp_name_preserves_age_after_directory_metadata_refresh(tmp_path: Path) -> None:
    candidate = tmp_path / "a-conductor-exec-v2-1000-deadbeef"
    candidate.mkdir()
    os.utime(candidate, (100_000.0, 100_000.0))

    removed = native_execution._sweep_stale_execution_temp_trees(
        tmp_path, now=100_000.0, stale_after_seconds=10.0
    )

    assert removed == 1
    assert not candidate.exists()


def test_stale_execution_age_anchor_survives_mtime_refresh() -> None:
    class StatLike:
        st_mtime = 100_000.0
        st_ctime = 1_000.0

    assert native_execution._execution_temp_age_anchor(StatLike()) == 1_000.0
