"""Safe Kilo MCP connection-health classification for WO-P1-254.

This module classifies already-collected, already-sanitized MCP connection evidence.
It performs no subprocess, shell, filesystem, network, provider, restart, persistence,
task, claim, scheduler, review, or completion actions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


KILO_MCP_HEALTH_INVALID = "KILO_MCP_HEALTH_INVALID"
KILO_MCP_STAGE_CONTRADICTION = "KILO_MCP_STAGE_CONTRADICTION"
KILO_MCP_TIMESTAMP_INVALID = "KILO_MCP_TIMESTAMP_INVALID"
KILO_MCP_TOOL_COUNT_INVALID = "KILO_MCP_TOOL_COUNT_INVALID"

MAX_SERVER_NAME_LENGTH = 64
MAX_INJECTED_TOOL_COUNT = 4096
_SERVER_NAME_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,64}")


class KiloMcpHealthError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class KiloMcpConnectionStage(str, Enum):
    NOT_REGISTERED = "NOT_REGISTERED"
    REGISTERED = "REGISTERED"
    PROCESS_SPAWNED = "PROCESS_SPAWNED"
    HANDSHAKE_CONNECTED = "HANDSHAKE_CONNECTED"
    TOOLS_INJECTED = "TOOLS_INJECTED"


class KiloMcpBlocker(str, Enum):
    NONE = "NONE"
    NOT_REGISTERED = "NOT_REGISTERED"
    PROCESS_NOT_SPAWNED = "PROCESS_NOT_SPAWNED"
    HANDSHAKE_NOT_CONNECTED = "HANDSHAKE_NOT_CONNECTED"
    TOOLS_NOT_INJECTED = "TOOLS_NOT_INJECTED"
    STALE_BACKEND_CONFIG = "STALE_BACKEND_CONFIG"
    MALFORMED_OBSERVATION = "MALFORMED_OBSERVATION"


SAFE_OBSERVATION_FIELDS = frozenset(
    {
        "server_name",
        "registered",
        "process_spawned",
        "handshake_connected",
        "tools_injected",
        "injected_tool_count",
        "required_tool_present",
        "registration_updated_at",
        "backend_config_loaded_at",
    }
)

SAFE_RESULT_FIELDS = frozenset(
    {
        "server_name",
        "highest_stage",
        "blocker",
        "reload_required",
        "injected_tool_count",
        "required_tool_present",
    }
)


def _require_aware_utc(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise KiloMcpHealthError(KILO_MCP_TIMESTAMP_INVALID)
    if value.tzinfo is None or value.utcoffset() is None:
        raise KiloMcpHealthError(KILO_MCP_TIMESTAMP_INVALID)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class KiloMcpObservation:
    server_name: str
    registered: bool
    process_spawned: bool
    handshake_connected: bool
    tools_injected: bool
    registration_updated_at: datetime
    backend_config_loaded_at: datetime
    injected_tool_count: int | None = None
    required_tool_present: bool | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.server_name, str)
            or not self.server_name
            or len(self.server_name) > MAX_SERVER_NAME_LENGTH
            or _SERVER_NAME_PATTERN.fullmatch(self.server_name) is None
        ):
            raise KiloMcpHealthError(KILO_MCP_HEALTH_INVALID)

        for field_name in (
            "registered",
            "process_spawned",
            "handshake_connected",
            "tools_injected",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise KiloMcpHealthError(KILO_MCP_HEALTH_INVALID)

        if self.tools_injected and not self.handshake_connected:
            raise KiloMcpHealthError(KILO_MCP_STAGE_CONTRADICTION)
        if self.handshake_connected and not self.process_spawned:
            raise KiloMcpHealthError(KILO_MCP_STAGE_CONTRADICTION)
        if self.process_spawned and not self.registered:
            raise KiloMcpHealthError(KILO_MCP_STAGE_CONTRADICTION)

        if self.required_tool_present is not None and not isinstance(
            self.required_tool_present, bool
        ):
            raise KiloMcpHealthError(KILO_MCP_HEALTH_INVALID)
        if self.required_tool_present is True and not self.tools_injected:
            raise KiloMcpHealthError(KILO_MCP_STAGE_CONTRADICTION)

        count = self.injected_tool_count
        if count is not None:
            if isinstance(count, bool) or not isinstance(count, int):
                raise KiloMcpHealthError(KILO_MCP_TOOL_COUNT_INVALID)
            if count < 0 or count > MAX_INJECTED_TOOL_COUNT:
                raise KiloMcpHealthError(KILO_MCP_TOOL_COUNT_INVALID)
            if self.tools_injected and count == 0:
                raise KiloMcpHealthError(KILO_MCP_TOOL_COUNT_INVALID)
            if not self.tools_injected and count > 0:
                raise KiloMcpHealthError(KILO_MCP_TOOL_COUNT_INVALID)

        object.__setattr__(
            self,
            "registration_updated_at",
            _require_aware_utc(self.registration_updated_at),
        )
        object.__setattr__(
            self,
            "backend_config_loaded_at",
            _require_aware_utc(self.backend_config_loaded_at),
        )


@dataclass(frozen=True, slots=True)
class KiloMcpHealthResult:
    server_name: str
    highest_stage: KiloMcpConnectionStage
    blocker: KiloMcpBlocker
    reload_required: bool
    injected_tool_count: int | None
    required_tool_present: bool | None

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "server_name": self.server_name,
            "highest_stage": self.highest_stage.value,
            "blocker": self.blocker.value,
            "reload_required": self.reload_required,
            "injected_tool_count": self.injected_tool_count,
            "required_tool_present": self.required_tool_present,
        }


def _highest_fresh_stage(
    observation: KiloMcpObservation,
) -> KiloMcpConnectionStage:
    if observation.tools_injected:
        return KiloMcpConnectionStage.TOOLS_INJECTED
    if observation.handshake_connected:
        return KiloMcpConnectionStage.HANDSHAKE_CONNECTED
    if observation.process_spawned:
        return KiloMcpConnectionStage.PROCESS_SPAWNED
    if observation.registered:
        return KiloMcpConnectionStage.REGISTERED
    return KiloMcpConnectionStage.NOT_REGISTERED


def _fresh_blocker(observation: KiloMcpObservation) -> KiloMcpBlocker:
    if not observation.registered:
        return KiloMcpBlocker.NOT_REGISTERED
    if not observation.process_spawned:
        return KiloMcpBlocker.PROCESS_NOT_SPAWNED
    if not observation.handshake_connected:
        return KiloMcpBlocker.HANDSHAKE_NOT_CONNECTED
    if not observation.tools_injected:
        return KiloMcpBlocker.TOOLS_NOT_INJECTED
    return KiloMcpBlocker.NONE


def classify_kilo_mcp_observation(
    observation: KiloMcpObservation,
) -> KiloMcpHealthResult:
    if not isinstance(observation, KiloMcpObservation):
        raise KiloMcpHealthError(KILO_MCP_HEALTH_INVALID)

    stale = (
        observation.registered
        and observation.backend_config_loaded_at < observation.registration_updated_at
    )
    if stale:
        return KiloMcpHealthResult(
            server_name=observation.server_name,
            highest_stage=KiloMcpConnectionStage.REGISTERED,
            blocker=KiloMcpBlocker.STALE_BACKEND_CONFIG,
            reload_required=True,
            injected_tool_count=None,
            required_tool_present=None,
        )

    return KiloMcpHealthResult(
        server_name=observation.server_name,
        highest_stage=_highest_fresh_stage(observation),
        blocker=_fresh_blocker(observation),
        reload_required=False,
        injected_tool_count=observation.injected_tool_count,
        required_tool_present=observation.required_tool_present,
    )
