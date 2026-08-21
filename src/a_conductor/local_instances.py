"""One-app orchestration of validated local Serena tunnel instances.

Discovery parses the validated ``instance.ps1`` format, health uses the
existing loopback readyz probe, and start/stop only invoke the instance's own
validated scripts (credential handling, preflight, and PID-ownership checks
stay inside those scripts). The orchestrator never kills processes directly.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol

from .windows_io import LoopbackReadyzHttpProbe

DEFAULT_INSTANCES_ROOT = Path("C:/AI/serena-instances")

_INSTANCE_LINE_RE = re.compile(
    r"^\s*\$(InstanceName|ProjectPath|HealthListenAddress)\s*=\s*'([^']*)'\s*$",
    re.MULTILINE,
)


class InstanceHealthState(str, Enum):
    READY = "READY"
    STOPPED = "STOPPED"
    UNKNOWN = "UNKNOWN"


class InstanceResultCode(str, Enum):
    RUNNING = "RUNNING"
    ALREADY_RUNNING = "ALREADY_RUNNING"
    STARTED_NOT_READY = "STARTED_NOT_READY"
    STOPPED = "STOPPED"
    ALREADY_STOPPED = "ALREADY_STOPPED"
    STOP_FAILED = "STOP_FAILED"
    SCRIPT_MISSING = "SCRIPT_MISSING"
    LAUNCH_FAILED = "LAUNCH_FAILED"


@dataclass(frozen=True, slots=True)
class LocalInstance:
    name: str
    project_path: str
    health_address: str
    instance_root: Path


@dataclass(frozen=True, slots=True)
class InstanceOrchestrationOutcome:
    action: str
    result_code: InstanceResultCode
    exit_code: int | None = None
    output_tail: str = ""


class _HealthProbe(Protocol):
    def get(self, url: str, timeout_seconds: int): ...


def discover_local_instances(
    instances_root: Path | str = DEFAULT_INSTANCES_ROOT,
) -> tuple[LocalInstance, ...]:
    root = Path(instances_root).expanduser().resolve(strict=False)
    if not root.is_dir():
        return ()
    found: list[LocalInstance] = []
    for child in sorted(root.iterdir()):
        marker = child / "instance.ps1"
        if not child.is_dir() or not marker.is_file():
            continue
        text = marker.read_text(encoding="utf-8", errors="replace")
        fields = dict(_INSTANCE_LINE_RE.findall(text))
        name = fields.get("InstanceName", "").strip()
        project = fields.get("ProjectPath", "").strip()
        address = fields.get("HealthListenAddress", "").strip()
        if not name or not project or not address:
            continue
        found.append(
            LocalInstance(
                name=name,
                project_path=project,
                health_address=address,
                instance_root=child.resolve(strict=False),
            )
        )
    return tuple(found)


def instance_health_state(
    instance: LocalInstance,
    *,
    probe: _HealthProbe | None = None,
    timeout_seconds: int = 3,
) -> InstanceHealthState:
    if not isinstance(instance, LocalInstance):
        raise ValueError("instance must be a LocalInstance")
    active_probe = probe or LoopbackReadyzHttpProbe()
    observation = active_probe.get(
        f"http://{instance.health_address}/readyz", timeout_seconds
    )
    state_name = getattr(observation, "state", None)
    state_value = getattr(state_name, "value", state_name)
    if state_value == "READY":
        return InstanceHealthState.READY
    if getattr(observation, "error_code", None) == "TRANSPORT_ERROR":
        return InstanceHealthState.STOPPED
    return InstanceHealthState.UNKNOWN


Launcher = Callable[[Path, Path], None]
Waiter = Callable[[list[str], int], tuple[int, str]]
SleepFn = Callable[[float], None]
BrainSettingsProvider = Callable[[], "object | None"]
BrainApplier = Callable[[object, object], str]


def _default_launcher(script: Path, cwd: Path) -> None:
    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
    subprocess.Popen(
        ["cmd.exe", "/c", str(script)],
        cwd=str(cwd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        shell=False,
        creationflags=creationflags,
    )


def _default_waiter(argv: list[str], timeout: int) -> tuple[int, str]:
    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(
        argv,
        cwd=None,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        creationflags=creationflags,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, output[-2000:]


def _single_script(instance_root: Path, pattern: str) -> Path | None:
    matches = sorted(instance_root.glob(pattern))
    if len(matches) != 1:
        return None
    return matches[0]


class LocalInstanceOrchestrator:
    """Start/stop validated instances through their own scripts."""

    def __init__(
        self,
        *,
        instances_root: Path | str = DEFAULT_INSTANCES_ROOT,
        probe: _HealthProbe | None = None,
        launcher: Launcher | None = None,
        waiter: Waiter | None = None,
        sleep_fn: SleepFn = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
        startup_timeout_seconds: int = 30,
        stop_timeout_seconds: int = 60,
        poll_interval_seconds: float = 0.5,
        health_timeout_seconds: int = 3,
        brain_settings_provider: BrainSettingsProvider | None = None,
        brain_applier: BrainApplier | None = None,
    ) -> None:
        if startup_timeout_seconds < 1 or stop_timeout_seconds < 1:
            raise ValueError("timeouts must be >= 1")
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be > 0")
        self._root = Path(instances_root).expanduser().resolve(strict=False)
        self._probe = probe or LoopbackReadyzHttpProbe()
        self._launcher = launcher or _default_launcher
        self._waiter = waiter or _default_waiter
        self._sleep_fn = sleep_fn
        self._clock_fn = clock_fn
        self._startup_timeout_seconds = startup_timeout_seconds
        self._stop_timeout_seconds = stop_timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._health_timeout_seconds = health_timeout_seconds
        self._brain_settings_provider = brain_settings_provider
        self._brain_applier = brain_applier

    def _require_inside_root(self, instance: LocalInstance) -> None:
        if not isinstance(instance, LocalInstance):
            raise ValueError("instance must be a LocalInstance")
        root = instance.instance_root.resolve(strict=False)
        if self._root not in root.parents:
            raise RuntimeError("INSTANCE_OUTSIDE_ROOT")

    def _state(self, instance: LocalInstance) -> InstanceHealthState:
        return instance_health_state(
            instance,
            probe=self._probe,
            timeout_seconds=self._health_timeout_seconds,
        )

    def _apply_brain(self, instance: LocalInstance) -> str:
        """Materialize the global brain into the instance serena-home (best-effort).

        The brain is an advisory layer: apply failures never block the start;
        they are surfaced in the outcome output tail instead.
        """
        if self._brain_settings_provider is None:
            return ""
        try:
            profile = self._brain_settings_provider()
        except Exception:
            return "brain:PROVIDER_FAILED"
        if profile is None:
            return ""
        if self._brain_applier is None:
            from .worker_serena_settings import apply_brain_to_serena_home

            def default_applier(inst, prof) -> str:
                return apply_brain_to_serena_home(
                    prof, inst.instance_root / "serena-home"
                )

            applier = default_applier
        else:
            applier = self._brain_applier
        try:
            return f"brain:{applier(instance, profile)}"
        except Exception:
            return "brain:APPLY_FAILED"

    def start(self, instance: LocalInstance) -> InstanceOrchestrationOutcome:
        self._require_inside_root(instance)
        if self._state(instance) is InstanceHealthState.READY:
            return InstanceOrchestrationOutcome(
                action="start", result_code=InstanceResultCode.ALREADY_RUNNING
            )
        script = _single_script(instance.instance_root, "Start-*.cmd")
        if script is None:
            return InstanceOrchestrationOutcome(
                action="start", result_code=InstanceResultCode.SCRIPT_MISSING
            )
        brain_note = self._apply_brain(instance)
        try:
            self._launcher(script, instance.instance_root)
        except OSError as exc:
            return InstanceOrchestrationOutcome(
                action="start",
                result_code=InstanceResultCode.LAUNCH_FAILED,
                output_tail=(brain_note + " " + str(exc))[-500:],
            )
        deadline = self._clock_fn() + self._startup_timeout_seconds
        while self._clock_fn() < deadline:
            self._sleep_fn(self._poll_interval_seconds)
            if self._state(instance) is InstanceHealthState.READY:
                return InstanceOrchestrationOutcome(
                    action="start",
                    result_code=InstanceResultCode.RUNNING,
                    output_tail=brain_note,
                )
        return InstanceOrchestrationOutcome(
            action="start",
            result_code=InstanceResultCode.STARTED_NOT_READY,
            output_tail=brain_note,
        )

    def stop(self, instance: LocalInstance) -> InstanceOrchestrationOutcome:
        self._require_inside_root(instance)
        if self._state(instance) is InstanceHealthState.STOPPED:
            return InstanceOrchestrationOutcome(
                action="stop", result_code=InstanceResultCode.ALREADY_STOPPED
            )
        script = _single_script(instance.instance_root, "Stop-*.cmd")
        if script is None:
            return InstanceOrchestrationOutcome(
                action="stop", result_code=InstanceResultCode.SCRIPT_MISSING
            )
        try:
            exit_code, output = self._waiter(
                ["cmd.exe", "/c", str(script)], self._stop_timeout_seconds
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            return InstanceOrchestrationOutcome(
                action="stop",
                result_code=InstanceResultCode.STOP_FAILED,
                output_tail=str(exc)[-500:],
            )
        if exit_code == 0 and self._state(instance) is InstanceHealthState.STOPPED:
            return InstanceOrchestrationOutcome(
                action="stop",
                result_code=InstanceResultCode.STOPPED,
                exit_code=exit_code,
                output_tail=output[-500:],
            )
        return InstanceOrchestrationOutcome(
            action="stop",
            result_code=InstanceResultCode.STOP_FAILED,
            exit_code=exit_code,
            output_tail=output[-500:],
        )


def connector_name_for_project(
    instances: tuple[LocalInstance, ...], project_root: str | Path | None
) -> str | None:
    """Return the connector instance bound to the same project root, if any."""
    if project_root is None:
        return None
    try:
        target = Path(project_root).expanduser().resolve(strict=False)
    except (OSError, ValueError):
        return None
    for instance in instances:
        try:
            if Path(instance.project_path).expanduser().resolve(strict=False) == target:
                return instance.name
        except (OSError, ValueError):
            continue
    return None
