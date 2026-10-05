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
        "nodefe80::1",
        "node2001::1",
        "nodefd00::1",
        "node2001:db8::1",
        "NODEFE80::1",
        "NodeFe80::1",
        "node::1",
        "node0:0:0:0:0:0:0:1",
        "node::ffff:192.0.2.1",
        "node1e80::1",
        "aaaafe80::1",
    ),
)
def test_fully_glued_ipv6_literals_fall_back(unsafe_name: str) -> None:
    result = _build(unsafe_name)
    assert result.state is AiPassDiscoveryState.OK
    assert result.models[0].name == "safe-model"
    assert unsafe_name not in str(result.to_dict())


def test_ipv6_hardening_preserves_semantic_hex_colon_text() -> None:
    for safe_name in (
        "IPv6 Research",
        "Release fe80 notes",
        "Model 2001 series",
        "sha256:deadbeef",
        "face:1 notes",
        "release:2026",
        "HTTP 200: OK",
        "build 1:2:3",
        "port:443",
        "ratio 16:9",
        "Time 23:59:59",
        "MAC 00:11:22:33:44:55",
        "x:y:z notes",
    ):
        result = _build(safe_name)
        assert result.state is AiPassDiscoveryState.OK
        assert result.models[0].name == safe_name
