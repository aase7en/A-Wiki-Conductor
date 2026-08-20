"""Bounded materialization for one Serena-backed A-Worker runtime.

The materializer performs local filesystem preparation only. It does not start
processes, access the network, resolve secret stores, or persist lifecycle
checkpoints. Sensitive profile token values are accepted only for the duration
of rendering and are never retained in public result objects or exception text.
"""

from __future__ import annotations

import ipaddress
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Mapping

from .owned_process import OwnedProcessSpec
from .serena_runtime import SerenaProjectBinding, SerenaWorkerConfig


_PLACEHOLDER_RE = re.compile(r"__[A-Z][A-Z0-9_]*__")


class SerenaMaterializationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _absolute_path(value: str, code: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise SerenaMaterializationError(code)
    try:
        return path.resolve(strict=False)
    except OSError as exc:
        raise SerenaMaterializationError(code) from exc


def _require_under_root(path: Path, root: Path) -> Path:
    if path != root and root not in path.parents:
        raise SerenaMaterializationError("PATH_OUTSIDE_INSTANCE_ROOT")
    return path


def _loopback_host(host: str) -> str:
    normalized = host.strip()
    if normalized.casefold() == "localhost":
        return "localhost"
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError as exc:
        raise SerenaMaterializationError("HEALTH_HOST_NOT_LOOPBACK") from exc
    if not address.is_loopback:
        raise SerenaMaterializationError("HEALTH_HOST_NOT_LOOPBACK")
    return normalized


def _health_url(host: str, port: int) -> str:
    display_host = f"[{host}]" if ":" in host else host
    return f"http://{display_host}:{port}/readyz"


def _validate_token_map(
    template_text: str,
    token_values: Mapping[str, str],
) -> tuple[str, ...]:
    placeholders = tuple(sorted(set(_PLACEHOLDER_RE.findall(template_text))))
    try:
        supplied_keys = set(token_values.keys())
    except Exception as exc:
        raise SerenaMaterializationError("PROFILE_TOKEN_INVALID") from exc
    if supplied_keys != set(placeholders):
        raise SerenaMaterializationError("PROFILE_TOKEN_MISMATCH")
    for key in placeholders:
        value = token_values.get(key)
        if (
            not isinstance(value, str)
            or not value
            or "\x00" in value
            or "\r" in value
            or "\n" in value
        ):
            raise SerenaMaterializationError("PROFILE_TOKEN_INVALID")
    return placeholders


def _validate_known_binding_tokens(
    token_values: Mapping[str, str],
    *,
    worker: SerenaWorkerConfig,
    binding: SerenaProjectBinding,
    serena_home: Path,
    health_host: str,
) -> None:
    expected = {
        "__WORKER_ID__": worker.worker_id,
        "__PROJECT_PATH__": str(Path(binding.worktree_path).expanduser().resolve(strict=False)),
        "__SERENA_HOME__": str(serena_home),
        "__HEALTH_LISTEN_ADDRESS__": f"{health_host}:{worker.health_port}",
    }
    for key, expected_value in expected.items():
        if key in token_values and token_values[key] != expected_value:
            raise SerenaMaterializationError("PROFILE_BINDING_MISMATCH")


def _render_profile(
    *,
    template_text: str,
    placeholders: tuple[str, ...],
    token_values: Mapping[str, str],
) -> str:
    rendered = template_text
    for placeholder in placeholders:
        rendered = rendered.replace(placeholder, token_values[placeholder])
    if _PLACEHOLDER_RE.search(rendered):
        raise SerenaMaterializationError("PROFILE_TOKEN_UNRESOLVED")
    return rendered


def _write_atomic_profile(output_path: Path, rendered: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=output_path.parent,
            prefix=".runtime-profile-",
            suffix=".tmp",
        ) as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, output_path)
        temporary_path = None
    except (OSError, ValueError) as exc:
        raise SerenaMaterializationError("PROFILE_WRITE_FAILED") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


@dataclass(frozen=True, slots=True)
class SerenaMaterializedRuntime:
    profile_path: Path
    serena_home: Path
    health_url: str
    process_spec: OwnedProcessSpec


def _describe_layout(worker: SerenaWorkerConfig) -> SerenaMaterializedRuntime:
    instance_root = _absolute_path(worker.instance_root, "INSTANCE_ROOT_INVALID")
    serena_home = _require_under_root(
        _absolute_path(worker.serena_home, "SERENA_HOME_INVALID"),
        instance_root,
    )
    run_dir = _require_under_root(
        _absolute_path(worker.run_dir, "RUN_DIR_INVALID"),
        instance_root,
    )
    log_dir = _require_under_root(
        _absolute_path(worker.log_dir, "LOG_DIR_INVALID"),
        instance_root,
    )
    health_host = _loopback_host(worker.health_host)
    executable_path = _absolute_path(
        worker.runtime_executable_ref,
        "RUNTIME_EXECUTABLE_INVALID",
    )
    if not executable_path.is_file():
        raise SerenaMaterializationError("RUNTIME_EXECUTABLE_NOT_FOUND")
    profile_path = run_dir / "runtime-profile.yaml"
    try:
        process_spec = OwnedProcessSpec(
            allowed_root=instance_root,
            cwd=run_dir,
            pid_path=run_dir / "runtime.pid",
            stdout_path=log_dir / "runtime.stdout.log",
            stderr_path=log_dir / "runtime.stderr.log",
            command=(
                str(executable_path),
                "run",
                "--profile-file",
                str(profile_path),
            ),
            expected_executable_name=PureWindowsPath(executable_path).name,
            expected_profile_marker=str(profile_path),
            stop_timeout_seconds=worker.stop_timeout_seconds,
            environment_overrides=(("SERENA_HOME", str(serena_home)),),
        )
    except ValueError as exc:
        raise SerenaMaterializationError("OWNED_PROCESS_SPEC_INVALID") from exc
    return SerenaMaterializedRuntime(
        profile_path=profile_path,
        serena_home=serena_home,
        health_url=_health_url(health_host, worker.health_port),
        process_spec=process_spec,
    )


class SerenaRuntimeMaterializer:
    def describe_existing(self, worker: SerenaWorkerConfig) -> SerenaMaterializedRuntime:
        """Describe deterministic runtime paths/spec without rendering profile secrets."""
        return _describe_layout(worker)

    def materialize(
        self,
        worker: SerenaWorkerConfig,
        binding: SerenaProjectBinding,
        token_values: Mapping[str, str],
    ) -> SerenaMaterializedRuntime:
        instance_root = _absolute_path(worker.instance_root, "INSTANCE_ROOT_INVALID")
        serena_home = _require_under_root(
            _absolute_path(worker.serena_home, "SERENA_HOME_INVALID"),
            instance_root,
        )
        run_dir = _require_under_root(
            _absolute_path(worker.run_dir, "RUN_DIR_INVALID"),
            instance_root,
        )
        log_dir = _require_under_root(
            _absolute_path(worker.log_dir, "LOG_DIR_INVALID"),
            instance_root,
        )
        health_host = _loopback_host(worker.health_host)

        template_path = _absolute_path(
            worker.profile_template_ref,
            "PROFILE_TEMPLATE_INVALID",
        )
        executable_path = _absolute_path(
            worker.runtime_executable_ref,
            "RUNTIME_EXECUTABLE_INVALID",
        )
        if not template_path.is_file():
            raise SerenaMaterializationError("PROFILE_TEMPLATE_NOT_FOUND")
        if not executable_path.is_file():
            raise SerenaMaterializationError("RUNTIME_EXECUTABLE_NOT_FOUND")

        try:
            template_text = template_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise SerenaMaterializationError("PROFILE_TEMPLATE_READ_FAILED") from exc

        placeholders = _validate_token_map(template_text, token_values)
        _validate_known_binding_tokens(
            token_values,
            worker=worker,
            binding=binding,
            serena_home=serena_home,
            health_host=health_host,
        )
        rendered = _render_profile(
            template_text=template_text,
            placeholders=placeholders,
            token_values=token_values,
        )

        profile_path = run_dir / "runtime-profile.yaml"
        try:
            process_spec = OwnedProcessSpec(
                allowed_root=instance_root,
                cwd=run_dir,
                pid_path=run_dir / "runtime.pid",
                stdout_path=log_dir / "runtime.stdout.log",
                stderr_path=log_dir / "runtime.stderr.log",
                command=(
                    str(executable_path),
                    "run",
                    "--profile-file",
                    str(profile_path),
                ),
                expected_executable_name=PureWindowsPath(executable_path).name,
                expected_profile_marker=str(profile_path),
                stop_timeout_seconds=worker.stop_timeout_seconds,
                environment_overrides=(("SERENA_HOME", str(serena_home)),),
            )
        except ValueError as exc:
            raise SerenaMaterializationError("OWNED_PROCESS_SPEC_INVALID") from exc

        _write_atomic_profile(profile_path, rendered)
        return SerenaMaterializedRuntime(
            profile_path=profile_path,
            serena_home=serena_home,
            health_url=_health_url(health_host, worker.health_port),
            process_spec=process_spec,
        )
