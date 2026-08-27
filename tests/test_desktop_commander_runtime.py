"""Desktop Commander runtime-profile contracts."""

from __future__ import annotations


def test_local_profile_is_lightweight_routable_execution_hand() -> None:
    from a_conductor.desktop_commander_runtime import (
        DesktopCommanderMode,
        build_desktop_commander_profile,
    )

    profile = build_desktop_commander_profile("dc-local", DesktopCommanderMode.LOCAL)
    names = {item.name for item in profile.runtime.capabilities}
    assert profile.runtime.runtime_type == "desktop-commander"
    assert "filesystem.read" in names
    assert "process.interactive" in names
    assert "remote.device" not in names
    assert profile.traits.supports_long_running is True
    assert profile.traits.supports_resume is True
    assert profile.traits.supports_background_execution is True
    assert profile.traits.supports_repo_tools is True


def test_remote_profile_adds_remote_device_without_changing_authority() -> None:
    from a_conductor.desktop_commander_runtime import (
        DesktopCommanderMode,
        build_desktop_commander_profile,
    )

    profile = build_desktop_commander_profile("dc-remote", DesktopCommanderMode.REMOTE)
    names = {item.name for item in profile.runtime.capabilities}
    assert "remote.device" in names
    assert profile.traits.requires_human_presence is False
    assert profile.traits.max_safe_transaction_scope == "bounded-project-operation"


def test_security_posture_never_claims_guardrails_are_a_sandbox() -> None:
    from a_conductor.desktop_commander_runtime import build_desktop_commander_profile

    profile = build_desktop_commander_profile("dc-secure")
    assert profile.security.trusted_client_required is True
    assert profile.security.guardrails_are_sandbox is False
    assert profile.security.os_isolation_recommended_for_untrusted_workloads is True


def test_desktop_commander_is_execution_only_not_control_plane() -> None:
    from a_conductor.desktop_commander_runtime import build_desktop_commander_profile

    profile = build_desktop_commander_profile("dc-boundary")
    assert profile.security.task_authority is False
    assert profile.security.direct_operator_shell_allowed is False
    assert profile.security.owns_mcp_gateway is False
    names = {item.name for item in profile.runtime.capabilities}
    assert "task.authority" not in names
    assert "shell.raw" not in names
    assert "mcp.gateway" not in names
