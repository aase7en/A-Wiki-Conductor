from __future__ import annotations

from datetime import datetime, timezone

import pytest

from a_conductor.aipass_discovery import AiPassDiscoveryState, build_aipass_discovery


NOW = datetime(2026, 9, 3, 8, 0, tzinfo=timezone.utc)


def _build(name: str):
    return build_aipass_discovery(
        models_payload={"object": "list", "data": [{"id": "safe-model", "name": name}]},
        quota_payload={},
        observed_at=NOW,
        now=NOW,
        configuration_generation=1,
    )


@pytest.mark.parametrize(
    "unsafe_name",
    (
        r'{\\"password\\":\\"abcdef0123456789abcdef\\"}',
        r'{\\\"session_id\\\":\\\"abcdef0123456789abcdef\\\"}',
        '"password " : "abcdef0123456789abcdef"',
    ),
)
def test_multilevel_escaped_sensitive_assignments_fall_back(unsafe_name: str) -> None:
    result = _build(unsafe_name)
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name not in str(result.to_dict())


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "backend8.8.8.8",
        "host127.0.0.1",
        "node2001:db8::1",
    ),
)
def test_glued_raw_ip_literals_fall_back(unsafe_name: str) -> None:
    result = _build(unsafe_name)
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name not in str(result.to_dict())


def test_hardening_preserves_existing_semantic_controls() -> None:
    for safe_name in ("model-1.2.3.4", "Version 1.2.3", "IPv4 Research", "IPv6 Research"):
        result = _build(safe_name)
        assert result.state is AiPassDiscoveryState.OK
        assert result.models[0].name == safe_name
