from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone

import pytest

from a_conductor.kilo_mcp_health import (
    KILO_MCP_HEALTH_INVALID,
    KILO_MCP_STAGE_CONTRADICTION,
    KILO_MCP_TIMESTAMP_INVALID,
    KILO_MCP_TOOL_COUNT_INVALID,
    MAX_INJECTED_TOOL_COUNT,
    MAX_SERVER_NAME_LENGTH,
    SAFE_OBSERVATION_FIELDS,
    SAFE_RESULT_FIELDS,
    KiloMcpBlocker,
    KiloMcpConnectionStage,
    KiloMcpHealthError,
    KiloMcpHealthResult,
    KiloMcpObservation,
    classify_kilo_mcp_observation,
)


def _ts(hour: int, *, offset_hours: int = 0) -> datetime:
    return datetime(
        2026,
        9,
        19,
        hour,
        tzinfo=timezone(timedelta(hours=offset_hours)),
    )


def _observation(**overrides: object) -> KiloMcpObservation:
    values: dict[str, object] = {
        "server_name": "sunday-remote-mcp",
        "registered": True,
        "process_spawned": True,
        "handshake_connected": True,
        "tools_injected": True,
        "registration_updated_at": _ts(10),
        "backend_config_loaded_at": _ts(12),
        "injected_tool_count": 3,
        "required_tool_present": True,
    }
    values.update(overrides)
    return KiloMcpObservation(**values)


@pytest.mark.parametrize(
    ("overrides", "stage", "blocker"),
    [
        (
            {
                "registered": False,
                "process_spawned": False,
                "handshake_connected": False,
                "tools_injected": False,
                "injected_tool_count": None,
                "required_tool_present": None,
            },
            KiloMcpConnectionStage.NOT_REGISTERED,
            KiloMcpBlocker.NOT_REGISTERED,
        ),
        (
            {
                "process_spawned": False,
                "handshake_connected": False,
                "tools_injected": False,
                "injected_tool_count": None,
                "required_tool_present": None,
            },
            KiloMcpConnectionStage.REGISTERED,
            KiloMcpBlocker.PROCESS_NOT_SPAWNED,
        ),
        (
            {
                "handshake_connected": False,
                "tools_injected": False,
                "injected_tool_count": None,
                "required_tool_present": None,
            },
            KiloMcpConnectionStage.PROCESS_SPAWNED,
            KiloMcpBlocker.HANDSHAKE_NOT_CONNECTED,
        ),
        (
            {
                "tools_injected": False,
                "injected_tool_count": 0,
                "required_tool_present": False,
            },
            KiloMcpConnectionStage.HANDSHAKE_CONNECTED,
            KiloMcpBlocker.TOOLS_NOT_INJECTED,
        ),
        (
            {},
            KiloMcpConnectionStage.TOOLS_INJECTED,
            KiloMcpBlocker.NONE,
        ),
    ],
)
def test_each_valid_stage_is_reported_without_upward_inference(
    overrides: dict[str, object],
    stage: KiloMcpConnectionStage,
    blocker: KiloMcpBlocker,
) -> None:
    result = classify_kilo_mcp_observation(_observation(**overrides))
    assert result.highest_stage is stage
    assert result.blocker is blocker
    assert result.reload_required is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"registered": False, "process_spawned": True},
        {"process_spawned": False, "handshake_connected": True},
        {"handshake_connected": False, "tools_injected": True},
    ],
)
def test_monotonic_stage_contradictions_fail_closed(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(KiloMcpHealthError) as exc_info:
        _observation(**overrides)
    assert exc_info.value.code == KILO_MCP_STAGE_CONTRADICTION


def test_required_tool_present_requires_tools_injected() -> None:
    with pytest.raises(KiloMcpHealthError) as exc_info:
        _observation(
            tools_injected=False,
            injected_tool_count=0,
            required_tool_present=True,
        )
    assert exc_info.value.code == KILO_MCP_STAGE_CONTRADICTION


def test_positive_tool_count_without_tools_injected_is_invalid() -> None:
    with pytest.raises(KiloMcpHealthError) as exc_info:
        _observation(
            tools_injected=False,
            injected_tool_count=1,
            required_tool_present=False,
        )
    assert exc_info.value.code == KILO_MCP_TOOL_COUNT_INVALID


def test_tools_injected_with_zero_measured_tools_is_invalid() -> None:
    with pytest.raises(KiloMcpHealthError) as exc_info:
        _observation(injected_tool_count=0)
    assert exc_info.value.code == KILO_MCP_TOOL_COUNT_INVALID


@pytest.mark.parametrize("count", [True, -1, MAX_INJECTED_TOOL_COUNT + 1, 1.5])
def test_tool_count_is_bounded_and_bool_is_not_an_int(count: object) -> None:
    with pytest.raises(KiloMcpHealthError) as exc_info:
        _observation(injected_tool_count=count)
    assert exc_info.value.code == KILO_MCP_TOOL_COUNT_INVALID


@pytest.mark.parametrize(
    "server_name",
    [
        "",
        " ",
        "bad/name",
        "bad:name",
        "x" * (MAX_SERVER_NAME_LENGTH + 1),
    ],
)
def test_server_name_is_bounded_and_safe(server_name: str) -> None:
    with pytest.raises(KiloMcpHealthError) as exc_info:
        _observation(server_name=server_name)
    assert exc_info.value.code == KILO_MCP_HEALTH_INVALID


@pytest.mark.parametrize(
    "field_name",
    ["registered", "process_spawned", "handshake_connected", "tools_injected"],
)
def test_stage_flags_require_real_booleans(field_name: str) -> None:
    with pytest.raises(KiloMcpHealthError) as exc_info:
        _observation(**{field_name: 1})
    assert exc_info.value.code == KILO_MCP_HEALTH_INVALID


@pytest.mark.parametrize(
    "field_name",
    ["registration_updated_at", "backend_config_loaded_at"],
)
@pytest.mark.parametrize("value", ["2026-09-19T10:00:00Z", 1, datetime(2026, 9, 19, 10)])
def test_timestamps_require_timezone_aware_datetime(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(KiloMcpHealthError) as exc_info:
        _observation(**{field_name: value})
    assert exc_info.value.code == KILO_MCP_TIMESTAMP_INVALID


def test_timestamps_are_normalized_to_utc_for_deterministic_comparison() -> None:
    observation = _observation(
        registration_updated_at=_ts(17, offset_hours=7),
        backend_config_loaded_at=_ts(19, offset_hours=7),
    )
    assert observation.registration_updated_at == _ts(10)
    assert observation.backend_config_loaded_at == _ts(12)
    assert observation.registration_updated_at.tzinfo is timezone.utc
    assert observation.backend_config_loaded_at.tzinfo is timezone.utc


def test_stale_backend_suppresses_stale_tool_usability() -> None:
    result = classify_kilo_mcp_observation(
        _observation(
            registration_updated_at=_ts(14),
            backend_config_loaded_at=_ts(12),
        )
    )
    assert result.highest_stage is KiloMcpConnectionStage.REGISTERED
    assert result.blocker is KiloMcpBlocker.STALE_BACKEND_CONFIG
    assert result.reload_required is True
    assert result.injected_tool_count is None
    assert result.required_tool_present is None


def test_equal_config_and_registration_timestamps_are_fresh() -> None:
    result = classify_kilo_mcp_observation(
        _observation(
            registration_updated_at=_ts(12),
            backend_config_loaded_at=_ts(12),
        )
    )
    assert result.highest_stage is KiloMcpConnectionStage.TOOLS_INJECTED
    assert result.blocker is KiloMcpBlocker.NONE
    assert result.reload_required is False


def test_unregistered_observation_is_not_overridden_by_irrelevant_stale_times() -> None:
    result = classify_kilo_mcp_observation(
        _observation(
            registered=False,
            process_spawned=False,
            handshake_connected=False,
            tools_injected=False,
            injected_tool_count=None,
            required_tool_present=None,
            registration_updated_at=_ts(14),
            backend_config_loaded_at=_ts(12),
        )
    )
    assert result.highest_stage is KiloMcpConnectionStage.NOT_REGISTERED
    assert result.blocker is KiloMcpBlocker.NOT_REGISTERED
    assert result.reload_required is False


def test_safe_projection_has_exact_allowlisted_fields_and_values() -> None:
    result = classify_kilo_mcp_observation(_observation())
    assert {field.name for field in fields(KiloMcpObservation)} == SAFE_OBSERVATION_FIELDS
    assert {field.name for field in fields(KiloMcpHealthResult)} == SAFE_RESULT_FIELDS
    assert result.to_safe_dict() == {
        "server_name": "sunday-remote-mcp",
        "highest_stage": "TOOLS_INJECTED",
        "blocker": "NONE",
        "reload_required": False,
        "injected_tool_count": 3,
        "required_tool_present": True,
    }
    forbidden_fragments = ("command", "config", "env", "header", "token", "secret", "url")
    assert all(
        not any(fragment in key.casefold() for fragment in forbidden_fragments)
        for key in result.to_safe_dict()
    )


def test_slots_and_frozen_dataclasses_reject_arbitrary_metadata_and_mutation() -> None:
    observation = _observation()
    result = classify_kilo_mcp_observation(observation)
    with pytest.raises((AttributeError, TypeError)):
        setattr(observation, "raw_config", "forbidden")
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.server_name = "changed"  # type: ignore[misc]


def test_classifier_rejects_non_observation_input() -> None:
    with pytest.raises(KiloMcpHealthError) as exc_info:
        classify_kilo_mcp_observation(object())  # type: ignore[arg-type]
    assert exc_info.value.code == KILO_MCP_HEALTH_INVALID
