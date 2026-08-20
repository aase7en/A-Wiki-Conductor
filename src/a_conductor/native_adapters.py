"""Fixed-method adapters over the project-confined native execution core."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol, Sequence

from .native_execution import (
    NativeCommandResult,
    NativeCommandSpec,
    NativeExecutionError,
    NativeExecutionScope,
    NativeSubprocessRunner,
)


class NativeCommandRunner(Protocol):
    def run(self, spec: NativeCommandSpec) -> NativeCommandResult: ...


def _require_executable(value: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise NativeExecutionError(code)
    return value.strip()


def _validated_paths(
    scope: NativeExecutionScope,
    paths: Sequence[str | Path],
    *,
    must_exist: bool,
    option_safe: bool,
) -> tuple[str, ...]:
    if isinstance(paths, (str, bytes)):
        raise NativeExecutionError("PATH_LIST_INVALID")
    rendered: list[str] = []
    for value in paths:
        if not isinstance(value, (str, Path)) or not str(value).strip():
            raise NativeExecutionError("PATH_INVALID")
        resolved = scope.resolve_relative(value, must_exist=must_exist)
        display = scope.relative_display(resolved)
        if option_safe and display.startswith("-"):
            display = f"./{display}"
        rendered.append(display)
    return tuple(rendered)


class NativeGitReadAdapter:
    """Read-only fixed Git command family."""

    def __init__(
        self,
        scope: NativeExecutionScope,
        *,
        runner: NativeCommandRunner | None = None,
        git_executable: str = "git",
    ) -> None:
        self._scope = scope
        self._runner = runner or NativeSubprocessRunner(scope)
        self._git_executable = _require_executable(git_executable, "GIT_EXECUTABLE_INVALID")

    def _base_argv(self) -> tuple[str, ...]:
        root = Path(self._scope.root)
        return (
            self._git_executable,
            "-c",
            f"safe.directory={root.as_posix()}",
            "-C",
            str(root),
        )

    def _run(self, args: tuple[str, ...], *, timeout_seconds: int) -> NativeCommandResult:
        return self._runner.run(
            NativeCommandSpec(
                argv=(*self._base_argv(), *args),
                cwd=".",
                timeout_seconds=timeout_seconds,
                mutation_intent=False,
            )
        )

    def status_short(self, *, timeout_seconds: int = 10) -> NativeCommandResult:
        return self._run(
            ("status", "--short", "--untracked-files=all"),
            timeout_seconds=timeout_seconds,
        )

    def working_diff(
        self,
        paths: Sequence[str | Path] = (),
        *,
        timeout_seconds: int = 15,
    ) -> NativeCommandResult:
        pathspecs = _validated_paths(
            self._scope,
            paths,
            must_exist=False,
            option_safe=False,
        )
        return self._run(
            ("diff", "--no-ext-diff", "--", *pathspecs),
            timeout_seconds=timeout_seconds,
        )

    def cached_diff(
        self,
        paths: Sequence[str | Path] = (),
        *,
        timeout_seconds: int = 15,
    ) -> NativeCommandResult:
        pathspecs = _validated_paths(
            self._scope,
            paths,
            must_exist=False,
            option_safe=False,
        )
        return self._run(
            ("diff", "--cached", "--no-ext-diff", "--", *pathspecs),
            timeout_seconds=timeout_seconds,
        )


class NativeVerificationAdapter:
    """Fixed verification commands that may create local cache/artifact files."""

    def __init__(
        self,
        scope: NativeExecutionScope,
        *,
        runner: NativeCommandRunner | None = None,
        python_executable: str = sys.executable,
    ) -> None:
        self._scope = scope
        self._runner = runner or NativeSubprocessRunner(scope)
        self._python_executable = _require_executable(
            python_executable,
            "PYTHON_EXECUTABLE_INVALID",
        )

    def _require_mutation_authority(self) -> None:
        if not self._scope.mutation_allowed:
            raise NativeExecutionError("MUTATION_FORBIDDEN")

    def pytest(
        self,
        paths: Sequence[str | Path] = ("tests",),
        *,
        timeout_seconds: int = 120,
    ) -> NativeCommandResult:
        self._require_mutation_authority()
        verified = _validated_paths(
            self._scope,
            paths,
            must_exist=True,
            option_safe=True,
        )
        return self._runner.run(
            NativeCommandSpec(
                argv=(self._python_executable, "-m", "pytest", "-q", *verified),
                cwd=".",
                timeout_seconds=timeout_seconds,
                mutation_intent=True,
            )
        )

    def compileall(
        self,
        paths: Sequence[str | Path] = ("src",),
        *,
        timeout_seconds: int = 120,
    ) -> NativeCommandResult:
        self._require_mutation_authority()
        verified = _validated_paths(
            self._scope,
            paths,
            must_exist=True,
            option_safe=True,
        )
        return self._runner.run(
            NativeCommandSpec(
                argv=(self._python_executable, "-m", "compileall", "-q", *verified),
                cwd=".",
                timeout_seconds=timeout_seconds,
                mutation_intent=True,
            )
        )
