"""Read-only Windows observations for Serena-backed worker runtimes.

This module does not own command execution or HTTP transport. Callers inject
those capabilities. Generated PowerShell commands only inspect one exact PID
or one exact listening port; target lifecycle mutation is outside this module.
"""

from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PureWindowsPath
from typing import Protocol

from .runtime_safety import PortBindingState, ProcessObservation, classify_port_binding


@dataclass(frozen=True, slots=True)
class CommandResult:
    return_code: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(self, argv: tuple[str, ...], timeout_seconds: int) -> CommandResult: ...


class HealthProbeState(str, Enum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class HealthProbeObservation:
    state: HealthProbeState
    status_code: int | None
    error_code: str | None


class HttpProbe(Protocol):
    def get(self, url: str, timeout_seconds: int) -> HealthProbeObservation: ...


class PidMetadataStatus(str, Enum):
    ABSENT = "ABSENT"
    VALID = "VALID"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class PidMetadataObservation:
    status: PidMetadataStatus
    pid: int | None


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _require_pid(pid: int) -> int:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
        raise ValueError("pid must be >= 1")
    return pid


def _require_optional_pid(pid: int | None) -> int | None:
    if pid is None:
        return None
    return _require_pid(pid)


def _require_port(port: int) -> int:
    if (
        not isinstance(port, int)
        or isinstance(port, bool)
        or not 1 <= port <= 65535
    ):
        raise ValueError("port must be between 1 and 65535")
    return port


def _require_timeout(timeout_seconds: int) -> int:
    if (
        not isinstance(timeout_seconds, int)
        or isinstance(timeout_seconds, bool)
        or timeout_seconds < 1
    ):
        raise ValueError("timeout_seconds must be >= 1")
    return timeout_seconds


def _is_loopback_host(host: str) -> bool:
    normalized = _require_text(host, "health_host").strip()
    if normalized.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _ready_url(host: str, port: int) -> str:
    if not _is_loopback_host(host):
        raise ValueError("health_host must resolve to an explicit loopback target")
    validated_port = _require_port(port)
    normalized = host.strip()
    if ":" in normalized and not normalized.startswith("["):
        normalized = f"[{normalized}]"
    return f"http://{normalized}:{validated_port}/readyz"


class WindowsRuntimeObserver:
    """Collect bounded Windows runtime facts through injected read-only I/O."""

    def __init__(
        self,
        *,
        runner: CommandRunner,
        http_probe: HttpProbe,
        powershell_executable: str = "powershell.exe",
    ) -> None:
        self._runner = runner
        self._http_probe = http_probe
        self._powershell_executable = _require_text(
            powershell_executable,
            "powershell_executable",
        )

    def read_pid_metadata(self, pid_path: Path) -> PidMetadataObservation:
        try:
            if not pid_path.is_file():
                return PidMetadataObservation(PidMetadataStatus.ABSENT, None)
            text = pid_path.read_text(encoding="utf-8").strip()
        except OSError:
            return PidMetadataObservation(PidMetadataStatus.UNKNOWN, None)

        try:
            pid = int(text)
        except ValueError:
            return PidMetadataObservation(PidMetadataStatus.INVALID, None)

        if pid < 1:
            return PidMetadataObservation(PidMetadataStatus.INVALID, None)
        return PidMetadataObservation(PidMetadataStatus.VALID, pid)

    def observe_process(
        self,
        *,
        pid: int,
        expected_executable_name: str,
        expected_profile_marker: str,
    ) -> ProcessObservation:
        validated_pid = _require_pid(pid)
        executable_name = _require_text(
            expected_executable_name,
            "expected_executable_name",
        ).strip()
        profile_marker = _require_text(
            expected_profile_marker,
            "expected_profile_marker",
        ).strip()

        script = (
            f'$p = Get-CimInstance Win32_Process -Filter "ProcessId={validated_pid}" '
            '-ErrorAction SilentlyContinue; '
            'if ($null -eq $p) { exit 0 }; '
            '$p | Select-Object ProcessId,Name,ExecutablePath,CommandLine '
            '| ConvertTo-Json -Compress'
        )
        result = self._run_powershell(script, timeout_seconds=5)
        if result.return_code != 0:
            return ProcessObservation(True, validated_pid, None, None, None)
        if not result.stdout.strip():
            return ProcessObservation(True, validated_pid, False, None, None)

        try:
            payload = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError):
            return ProcessObservation(True, validated_pid, None, None, None)

        if not isinstance(payload, dict):
            return ProcessObservation(True, validated_pid, None, None, None)

        observed_name = payload.get("Name")
        executable_path = payload.get("ExecutablePath")
        command_line = payload.get("CommandLine")

        executable_matches: bool | None
        if isinstance(observed_name, str) and observed_name.strip():
            executable_matches = observed_name.casefold() == executable_name.casefold()
        elif isinstance(executable_path, str) and executable_path.strip():
            executable_matches = (
                PureWindowsPath(executable_path).name.casefold()
                == executable_name.casefold()
            )
        else:
            executable_matches = None

        profile_matches = (
            profile_marker.casefold() in command_line.casefold()
            if isinstance(command_line, str)
            else None
        )
        return ProcessObservation(
            pid_metadata_present=True,
            pid=validated_pid,
            process_exists=True,
            executable_matches=executable_matches,
            profile_matches=profile_matches,
        )

    def observe_port_binding(
        self,
        *,
        port: int,
        expected_pid: int | None,
    ) -> PortBindingState:
        validated_port = _require_port(port)
        validated_expected_pid = _require_optional_pid(expected_pid)
        script = (
            '$c = Get-NetTCPConnection -State Listen '
            f'-LocalPort {validated_port} -ErrorAction SilentlyContinue '
            '| Select-Object -First 1; '
            'if ($null -eq $c) { exit 0 }; '
            '$c | Select-Object LocalAddress,LocalPort,OwningProcess '
            '| ConvertTo-Json -Compress'
        )
        result = self._run_powershell(script, timeout_seconds=5)
        if result.return_code != 0:
            return classify_port_binding(
                listening=None,
                owning_pid=None,
                expected_pid=validated_expected_pid,
            )
        if not result.stdout.strip():
            return classify_port_binding(
                listening=False,
                owning_pid=None,
                expected_pid=validated_expected_pid,
            )

        try:
            payload = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError):
            return classify_port_binding(
                listening=None,
                owning_pid=None,
                expected_pid=validated_expected_pid,
            )

        if not isinstance(payload, dict):
            return classify_port_binding(
                listening=None,
                owning_pid=None,
                expected_pid=validated_expected_pid,
            )

        owning_pid = payload.get("OwningProcess")
        if not isinstance(owning_pid, int) or isinstance(owning_pid, bool):
            owning_pid = None
        return classify_port_binding(
            listening=True,
            owning_pid=owning_pid,
            expected_pid=validated_expected_pid,
        )

    def probe_ready(
        self,
        *,
        health_host: str,
        health_port: int,
        timeout_seconds: int,
    ) -> HealthProbeObservation:
        timeout = _require_timeout(timeout_seconds)
        url = _ready_url(health_host, health_port)
        return self._http_probe.get(url, timeout)

    def _run_powershell(self, script: str, *, timeout_seconds: int) -> CommandResult:
        return self._runner.run(
            (
                self._powershell_executable,
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ),
            timeout_seconds,
        )
