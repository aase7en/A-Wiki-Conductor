"""Lightweight Desktop Commander execution-surface profile.

This module models Desktop Commander as an optional execution hand.  It does
not connect to MCP, launch processes, access files, or grant task authority.
Future transports must remain behind A-Conductor's durable job and fixed
operation boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .domain import Capability, ExecutionSurfaceTraits, Runtime


class DesktopCommanderMode(str, Enum):
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"


@dataclass(frozen=True, slots=True)
class DesktopCommanderSecurityPosture:
    trusted_client_required: bool = True
    guardrails_are_sandbox: bool = False
    os_isolation_recommended_for_untrusted_workloads: bool = True
    task_authority: bool = False
    direct_operator_shell_allowed: bool = False
    owns_mcp_gateway: bool = False


@dataclass(frozen=True, slots=True)
class DesktopCommanderProfile:
    runtime: Runtime
    traits: ExecutionSurfaceTraits
    security: DesktopCommanderSecurityPosture
    mode: DesktopCommanderMode


_BASE_CAPABILITIES = (
    Capability("filesystem.read"),
    Capability("filesystem.search"),
    Capability("filesystem.write"),
    Capability("process.execute"),
    Capability("process.interactive"),
    Capability("process.long-running"),
    Capability("output.pagination"),
    Capability("repo.tools"),
    Capability("document.read"),
    Capability("data.analysis"),
)


def build_desktop_commander_profile(
    runtime_id: str,
    mode: DesktopCommanderMode = DesktopCommanderMode.LOCAL,
) -> DesktopCommanderProfile:
    """Create deterministic routing metadata with zero external side effects."""
    if not isinstance(mode, DesktopCommanderMode):
        raise ValueError("mode must be a DesktopCommanderMode")
    capabilities = _BASE_CAPABILITIES
    if mode is DesktopCommanderMode.REMOTE:
        capabilities = (*capabilities, Capability("remote.device"))

    return DesktopCommanderProfile(
        runtime=Runtime(
            runtime_id=runtime_id,
            runtime_type="desktop-commander",
            capabilities=capabilities,
        ),
        traits=ExecutionSurfaceTraits(
            supports_long_running=True,
            supports_resume=True,
            supports_background_execution=True,
            supports_repo_tools=True,
            requires_human_presence=False,
            max_safe_transaction_scope="bounded-project-operation",
        ),
        security=DesktopCommanderSecurityPosture(),
        mode=mode,
    )
